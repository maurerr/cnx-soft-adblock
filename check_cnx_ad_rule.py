#!/usr/bin/env python3
"""
check_cnx_ad_rule.py

Reads the current cosmetic-filter rule from cnx-software.txt, fetches the
latest article on cnx-software.com, and verifies that the CSS class/id
referenced by the rule is still present on the page.

If the rule's selector is missing, the script scans the article HTML for
ad-like class/id attributes (using a keyword heuristic) and overwrites
cnx-software.txt with a freshly generated rule (or rules).
"""
import re
import sys
import urllib.request

DOMAIN = "cnx-software.com"
HOME_URL = f"https://www.{DOMAIN}/"
RULES_FILE = "cnx-software.txt"
UA = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
      "(KHTML, like Gecko) Chrome/124.0 Safari/537.36")

AD_KEYWORDS = re.compile(
    r"ad[s]?[-_]|advert|sponsor|banner|adsbygoogle|adsense|adthrive|"
    r"mediavine|taboola|outbrain|criteo|grampeg|promo[-_]?ad|native-ad|"
    r"gpt-ad|dfp-ad|widget-ad",
    re.IGNORECASE,
)

RULE_RE = re.compile(r"^\s*[\w.\-]+##(?P<sel>[#.][\w\-]+)\s*$")


def fetch(url: str) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA})
    with urllib.request.urlopen(req, timeout=30) as resp:
        return resp.read().decode("utf-8", errors="replace")


def latest_article_url(home_html: str) -> str:
    m = re.search(
        r'href="(https://www\.cnx-software\.com/20\d{2}/\d{2}/\d{2}/[^"]+)"\s+rel="bookmark"',
        home_html,
    )
    if m:
        return m.group(1)
    m = re.search(
        r"https://www\.cnx-software\.com/20\d{2}/\d{2}/\d{2}/[a-z0-9\-]+/",
        home_html,
    )
    if m:
        return m.group(0)
    raise RuntimeError("Could not locate latest article URL on homepage")


def selectors_in_html(html: str) -> set:
    found = set()
    for attr_type, values in re.findall(r'\b(id|class)\s*=\s*"([^"]*)"', html, re.IGNORECASE):
        for token in values.split():
            if AD_KEYWORDS.search(token):
                prefix = "#" if attr_type.lower() == "id" else "."
                found.add(f"{prefix}{token}")
    return found


def read_current_rule(path: str):
    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("!"):
                    continue
                m = RULE_RE.match(line)
                if m:
                    return m.group("sel")
    except FileNotFoundError:
        pass
    return None


def write_rules(path: str, selectors: set) -> None:
    with open(path, "w", encoding="utf-8") as f:
        for sel in sorted(selectors):
            f.write(f"{DOMAIN}##{sel}\n")


def main() -> int:
    home_html = fetch(HOME_URL)
    article_url = latest_article_url(home_html)
    print(f"Latest article: {article_url}", file=sys.stderr)

    article_html = fetch(article_url)
    live_selectors = selectors_in_html(article_html)

    current_rule = read_current_rule(RULES_FILE)
    print(f"Current rule selector: {current_rule}", file=sys.stderr)
    print(f"Selectors found on article: {sorted(live_selectors)}", file=sys.stderr)

    if current_rule and current_rule in live_selectors:
        print("Existing rule still valid, no change needed.", file=sys.stderr)
        return 0

    if not live_selectors:
        print("WARNING: no ad-like selectors detected on latest article; "
              "leaving file unchanged.", file=sys.stderr)
        return 0

    print("Existing rule missing or stale, rewriting cnx-software.txt", file=sys.stderr)
    write_rules(RULES_FILE, live_selectors)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
