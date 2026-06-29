import json, os, re, subprocess, time, urllib.request, urllib.error
from concurrent.futures import ThreadPoolExecutor, as_completed

SITE_URL = "https://ctrluserknown.github.io/website-ctrluserknown/"
RESULTS_DIR = os.path.join(os.getcwd(), "results")


def curl(url):
    result = subprocess.run(["curl", "-sL", url], capture_output=True, text=True)
    return result.stdout


def check_link(url):
    try:
        result = subprocess.run(
            ["curl", "-s", "-o", "/dev/null", "-w", "%{http_code}",
             "--max-time", "10", url],
            capture_output=True, text=True, timeout=15,
        )
        code = result.stdout.strip()
        ok = code.startswith("2") or code in ("304",)
        return url, code, ok
    except Exception as e:
        return url, str(e), False


def run_health_checks(html, repo_path):
    checks = {}
    issues = []
    warnings = []

    # ── External link checking ──
    links = re.findall(
        r'<a[^>]*href=["\'](https?://[^"\']+)["\']', html, re.IGNORECASE
    )
    checks["external_links_found"] = len(links)

    broken = []
    with ThreadPoolExecutor(max_workers=5) as ex:
        futures = {ex.submit(check_link, link): link for link in links}
        for future in as_completed(futures):
            url, code, ok = future.result()
            if not ok and code not in ("429", "403"):
                broken.append((url, code))

    checks["broken_links"] = broken
    if broken:
        issues.append(f"Broken external links: {len(broken)}")
        for url, code in broken:
            warnings.append(f"  {url} → {code}")

    # ── Asset file existence ──
    asset_refs = set()
    for pat in [
        r'<script[^>]*src=["\']([^"\']+)["\']',
        r'<link[^>]*href=["\']([^"\']+\.css[^"\']*)["\']',
        r'<img[^>]*src=["\']([^"\']+)["\']',
        r'<link[^>]*href=["\']([^"\']+\.(?:ico|png|svg))["\']',
    ]:
        for m in re.finditer(pat, html, re.IGNORECASE):
            asset_refs.add(m.group(1))

    missing_assets = []
    for ref in sorted(asset_refs):
        if ref.startswith("http"):
            continue
        local_path = ref.lstrip("./")
        full_path = os.path.join(repo_path, local_path)
        if not os.path.exists(full_path):
            missing_assets.append(ref)

    checks["missing_assets"] = missing_assets
    if missing_assets:
        issues.append(f"Missing asset files: {len(missing_assets)}")
        for a in missing_assets:
            warnings.append(f"  {a} not found")

    # ── PWA manifest ──
    manifest_path = os.path.join(repo_path, "site.webmanifest")
    manifest_issues = []
    if os.path.exists(manifest_path):
        try:
            with open(manifest_path) as f:
                manifest = json.load(f)
            checks["manifest_valid"] = True
            for key in ("name", "short_name", "start_url", "display"):
                if key not in manifest:
                    manifest_issues.append(f"Manifest missing '{key}'")
            icons = manifest.get("icons", [])
            if not icons:
                manifest_issues.append("Manifest has no icons")
            else:
                for icon in icons:
                    for k in ("src", "sizes"):
                        if k not in icon:
                            manifest_issues.append(f"Manifest icon missing '{k}'")
                            break
        except json.JSONDecodeError:
            checks["manifest_valid"] = False
            manifest_issues.append("Manifest has invalid JSON")
    else:
        checks["manifest_valid"] = False
        manifest_issues.append("site.webmanifest not found")

    checks["manifest_issues"] = manifest_issues
    issues.extend(manifest_issues)

    # ── Service worker ──
    sw_path = os.path.join(repo_path, "sw.js")
    if os.path.exists(sw_path):
        checks["sw_exists"] = True
        with open(sw_path) as f:
            sw = f.read()
        checks["sw_has_fetch"] = "'fetch'" in sw or '"fetch"' in sw
        checks["sw_has_activate"] = "'activate'" in sw or '"activate"' in sw
        if not checks["sw_has_fetch"]:
            issues.append("Service worker missing fetch event listener")
    else:
        checks["sw_exists"] = False
        issues.append("sw.js not found")

    # ── robots.txt / sitemap.xml ──
    checks["has_robots_txt"] = os.path.exists(os.path.join(repo_path, "robots.txt"))
    checks["has_sitemap_xml"] = os.path.exists(os.path.join(repo_path, "sitemap.xml"))

    return {"checks": checks, "issues": issues, "warnings": warnings}


def get_lighthouse_scores():
    path = os.path.join(RESULTS_DIR, "lighthouse-health.json")
    try:
        with open(path) as f:
            data = json.load(f)
        cats = data.get("categories", {})
        scores = {}
        for key, cat_name in [
            ("accessibility", "accessibility"),
            ("best_practices", "best-practices"),
            ("performance", "performance"),
        ]:
            score = cats.get(cat_name, {}).get("score")
            scores[key] = round(score * 100) if score is not None else None
        return scores
    except (FileNotFoundError, json.JSONDecodeError):
        return {}


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
    repo_root = os.getcwd()

    html = curl(SITE_URL)
    health = run_health_checks(html, repo_root)
    health["lighthouse"] = get_lighthouse_scores()
    health["url"] = SITE_URL

    prompt = f"""You are a site reliability engineer. Below are automated health check results for a personal portfolio site. Be practical — only flag things that actually need fixing for a small static site.

{json.dumps(health, indent=2)}

Respond in this exact format:

## Summary
(one paragraph)

## Issues Found
(bullet list of issues, or "No significant issues found.")

## Recommendations
(bullet list of fixes, or "None at this time.")

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

    with open(os.path.join(RESULTS_DIR, "health-report.md"), "w") as f:
        f.write(
            f"# Site Health Report\n\n"
            f"**URL:** {SITE_URL}\n"
            f"**Date:** {time.strftime('%Y-%m-%d %H:%M UTC', time.gmtime())}\n\n"
            f"{report}\n"
        )
    with open(os.path.join(RESULTS_DIR, "health-verdict.txt"), "w") as f:
        f.write(verdict)

    print(f"Verdict: {'NEEDS_ATTENTION' if verdict == 'true' else 'PASS'}")


if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        with open(os.path.join(RESULTS_DIR, "health-report.md"), "w") as f:
            f.write(f"# Site Health Report\n\n**Status:** Health check failed\n**Error:** {e}")
        with open(os.path.join(RESULTS_DIR, "health-verdict.txt"), "w") as f:
            f.write("false")
        raise
