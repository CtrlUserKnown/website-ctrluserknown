import json, os, re, subprocess, time, urllib.request, urllib.error

SITE_URL = "https://ctrluserknown.github.io/website-ctrluserknown/"
RESULTS_DIR = os.path.join(os.getcwd(), "results")


def curl(url):
    result = subprocess.run(["curl", "-sL", url], capture_output=True, text=True)
    return result.stdout


def get_status(url):
    result = subprocess.run(
        ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}", url],
        capture_output=True, text=True,
    )
    return result.stdout.strip()


def run_html_checks(html):
    checks = {}
    issues = []

    status = get_status(SITE_URL)
    checks["status_code"] = status
    if status != "200":
        issues.append(f"HTTP status is {status}, expected 200")

    title_m = re.search(r"<title[^>]*>(.*?)</title>", html, re.IGNORECASE | re.DOTALL)
    checks["title"] = title_m.group(1).strip() if title_m else ""
    if not title_m:
        issues.append("Missing <title> tag")
    elif not checks["title"]:
        issues.append("<title> is empty")

    desc_pat = re.compile(
        r'<meta[^>]*name=["\']description["\'][^>]*content=["\'](.*?)["\']',
        re.IGNORECASE,
    )
    desc_m = desc_pat.search(html)
    if not desc_m:
        desc_m = re.search(
            r'<meta[^>]*content=["\'](.*?)["\']'
            r'[^>]*name=["\']description["\']',
            html,
            re.IGNORECASE,
        )
    checks["meta_description"] = desc_m.group(1).strip() if desc_m else ""
    if not desc_m:
        issues.append("Missing <meta name='description'>")
    elif not checks["meta_description"]:
        issues.append("Meta description is empty")
    elif len(checks["meta_description"]) > 160:
        issues.append(f"Meta description too long ({len(checks['meta_description'])} chars, max 160)")

    h1s = re.findall(r"<h1[^>]*>(.*?)</h1>", html, re.IGNORECASE | re.DOTALL)
    checks["h1_count"] = len(h1s)
    if len(h1s) == 0:
        issues.append("No <h1> tag found")
    elif len(h1s) > 1:
        issues.append(f"Multiple <h1> tags ({len(h1s)}) — should have exactly one")

    lang_m = re.search(r'<html[^>]*lang=["\']([^"\']+)["\']', html, re.IGNORECASE)
    checks["html_lang"] = lang_m.group(1) if lang_m else ""
    if not lang_m:
        issues.append("<html> missing lang attribute")

    checks["has_viewport"] = bool(
        re.search(r'<meta[^>]*name=["\']viewport["\']', html, re.IGNORECASE)
    )
    if not checks["has_viewport"]:
        issues.append("Missing viewport meta tag")

    checks["has_favicon"] = bool(
        re.search(r'<link[^>]*rel=["\']icon["\']', html, re.IGNORECASE)
    )

    checks["has_canonical"] = bool(
        re.search(r'<link[^>]*rel=["\']canonical["\']', html, re.IGNORECASE)
    )
    if not checks["has_canonical"]:
        issues.append("Missing rel='canonical' link")

    for og in ["og:title", "og:description", "og:image", "og:url"]:
        key = "og_" + og.replace(":", "_")
        checks[key] = bool(
            re.search(
                rf'<meta[^>]*property=["\']{re.escape(og)}["\']', html, re.IGNORECASE
            )
        )
        if not checks[key]:
            issues.append(f"Missing {og} tag")

    checks["has_twitter_card"] = bool(
        re.search(r'<meta[^>]*name=["\']twitter:card["\']', html, re.IGNORECASE)
    )
    if not checks["has_twitter_card"]:
        issues.append("Missing twitter:card meta tag")

    return {"checks": checks, "issues": issues}


def get_lighthouse_score():
    path = os.path.join(RESULTS_DIR, "lighthouse.json")
    try:
        with open(path) as f:
            data = json.load(f)
        score = data.get("categories", {}).get("seo", {}).get("score")
        return round(score * 100) if score is not None else None
    except (FileNotFoundError, json.JSONDecodeError):
        return None


def call_ollama(prompt, retries=10, delay=3):
    body = json.dumps({
        "model": "gemma:2b",
        "prompt": prompt,
        "stream": False,
        "options": {"num_predict": 1024, "temperature": 0.1},
    }).encode()
    req = urllib.request.Request(
        "http://localhost:11434/api/generate",
        data=body,
        headers={"Content-Type": "application/json"},
    )
    for i in range(retries):
        try:
            with urllib.request.urlopen(req, timeout=180) as resp:
                result = json.loads(resp.read())
                return result.get("response", "")
        except (urllib.error.URLError, ConnectionResetError, OSError):
            if i == retries - 1:
                raise
            time.sleep(delay)
    return ""


def main():
    os.makedirs(RESULTS_DIR, exist_ok=True)
    html = curl(SITE_URL)
    seo = run_html_checks(html)
    seo["lighthouse_seo_score"] = get_lighthouse_score()
    seo["url"] = SITE_URL

    prompt = f"""You are an SEO expert analyzing a personal portfolio site. Below are automated audit results. Be practical — only flag what actually matters for a personal portfolio.

{json.dumps(seo, indent=2)}

Respond in this exact format:

## Summary
(one paragraph)

## Issues Found
(bullet list of issues, or "No significant issues found.")

## Recommendations
(bullet list of actionable fixes, or "None at this time.")

---
**Verdict:** PASS or NEEDS_ATTENTION
"""

    report = call_ollama(prompt)

    verdict = "false"
    for line in report.splitlines():
        if "**Verdict:**" in line or "Verdict:" in line:
            if "NEEDS_ATTENTION" in line.upper():
                verdict = "true"
            break

    with open(os.path.join(RESULTS_DIR, "report.md"), "w") as f:
        f.write(
            f"# SEO Audit Report\n\n"
            f"**URL:** {SITE_URL}\n"
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n"
            f"{report}\n"
        )
    with open(os.path.join(RESULTS_DIR, "verdict.txt"), "w") as f:
        f.write(verdict)

    print(f"Verdict: {'NEEDS_ATTENTION' if verdict == 'true' else 'PASS'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(os.path.join(RESULTS_DIR, "report.md"), "w") as f:
            f.write(f"# SEO Audit Report\n\n**Status:** Audit failed\n**Error:** {e}")
        with open(os.path.join(RESULTS_DIR, "verdict.txt"), "w") as f:
            f.write("false")
        raise
