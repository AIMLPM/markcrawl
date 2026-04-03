#!/usr/bin/env python3
"""
crawl_website_show_progress.py

Crawl a website (e.g., https://www.WEBSITE-TO-CRAWL.com/) and extract Markdown (default) or
plain text from each HTML page for ingestion. Shows total pages (when available
via sitemap) and prints progress along the way.

Usage (single line):
  python crawl_website.py --base https://www.WEBSITE-TO-CRAWL.com/ --out ./website_to_crawl_output --format markdown --include-subdomains true
"""

import argparse
import hashlib
import json
import os
import re
import time
import urllib.parse as up
import xml.etree.ElementTree as ET
from collections import deque
from typing import List, Optional, Set, Tuple

import requests
from bs4 import BeautifulSoup
from urllib import robotparser

# Optional but helps avoid local CA/SSL issues
try:
    import certifi
    CERT_PATH = certifi.where()
except Exception:
    CERT_PATH = True  # fall back to system default

# Optional: preserve headings/bold/italics/lists/links/tables/code when using --format markdown
try:
    from markdownify import markdownify as md_convert
except Exception:
    md_convert = None

DEFAULT_UA = (
    "Mozilla/5.0 (Macintosh; Intel Mac OS X) AppleWebKit/605.1.15 "
    "(KHTML, like Gecko) Version/17.0 Safari/605.1.15"
)

EXCLUDE_TAGS = {"script", "style", "noscript", "template", "svg", "canvas"}
STRUCTURE_TAGS = {"nav", "header", "footer", "aside"}


# -------------------- helpers -------------------- #

def norm_url(url: str) -> str:
    p = up.urlsplit(url)
    normalized = up.urlunsplit((p.scheme.lower(), p.netloc.lower(), p.path or "/", p.query, ""))
    normalized = re.sub(r"(?<!:)/{2,}", "/", normalized)
    return normalized


def same_scope(url: str, base_netloc: str, include_subdomains: bool) -> bool:
    target = up.urlsplit(url).netloc.lower()
    base = base_netloc.lower()
    if target == base:
        return True
    return include_subdomains and target.endswith("." + base)


def safe_filename(url: str, ext: str) -> str:
    p = up.urlsplit(url)
    path = p.path.strip("/")
    if not path:
        stub = "index"
    else:
        stub = re.sub(r"[^a-zA-Z0-9._-]+", "-", path)[:120].strip("-") or "page"
    if p.query:
        qpart = re.sub(r"[^a-zA-Z0-9._-]+", "-", p.query)[:40].strip("-")
        if qpart:
            stub += f"__{qpart}"
    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:10]
    return f"{stub}__{h}.{ext}"


def fetch(session: requests.Session, url: str, timeout: int) -> Optional[requests.Response]:
    try:
        return session.get(url, timeout=timeout, allow_redirects=True)
    except requests.RequestException as e:
        print(f"[warn] fetch error for {url}: {e}")
        return None


def parse_robots_txt(session: requests.Session, robots_url: str) -> robotparser.RobotFileParser:
    rp = robotparser.RobotFileParser()
    try:
        r = session.get(robots_url, timeout=10)
        content = r.text if r and r.ok else ""
        print(f"[info] robots.txt status: {r.status_code if r else 'n/a'} at {robots_url}")
    except requests.RequestException as e:
        print(f"[warn] could not load robots.txt ({e}); proceeding with defaults")
        content = ""
    rp.parse(content.splitlines())
    return rp


def discover_sitemaps(session: requests.Session, base: str) -> List[str]:
    robots_url = up.urljoin(base, "/robots.txt")
    sitemaps = []
    try:
        r = session.get(robots_url, timeout=10)
        if r and r.ok:
            for line in r.text.splitlines():
                if line.lower().startswith("sitemap:"):
                    sm = line.split(":", 1)[1].strip()
                    if sm:
                        sitemaps.append(sm)
            if sitemaps:
                print(f"[info] discovered {len(sitemaps)} sitemap(s) via robots.txt")
        else:
            print("[info] no robots.txt or not OK; skipping sitemap discovery")
    except requests.RequestException as e:
        print(f"[warn] sitemap discovery failed: {e}")
    return sitemaps


def parse_sitemap_xml(session: requests.Session, url: str, timeout: int) -> List[str]:
    try:
        r = session.get(url, timeout=timeout)
        if not (r and r.ok):
            print(f"[warn] sitemap fetch not OK: {url}")
            return []
        if not (r.headers.get("Content-Type", "").lower().startswith("application/xml")
                or r.text.strip().startswith("<")):
            print(f"[warn] sitemap not XML-like: {url}")
            return []
        root = ET.fromstring(r.content)
    except Exception as e:
        print(f"[warn] error parsing sitemap {url}: {e}")
        return []

    ns = {"sm": "http://www.sitemaps.org/schemas/sitemap/0.9"}
    urls = []

    # sitemap index
    for loc in root.findall(".//sm:sitemap/sm:loc", ns):
        child = (loc.text or "").strip()
        if child:
            urls.extend(parse_sitemap_xml(session, child, timeout))

    # urlset
    for loc in root.findall(".//sm:url/sm:loc", ns):
        t = (loc.text or "").strip()
        if t:
            urls.append(t)

    # fallback without namespaces
    if not urls:
        for loc in root.findall(".//loc"):
            t = (loc.text or "").strip()
            if t:
                urls.append(t)

    # dedupe (preserve order)
    deduped = list(dict.fromkeys(urls))
    print(f"[info] parsed {len(deduped)} URL(s) from sitemap: {url}")
    return deduped


def extract_links(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        abs_url = up.urljoin(base_url, href)
        links.add(norm_url(abs_url))
    return links


def clean_dom_for_content(soup: BeautifulSoup):
    for tag in soup.find_all(EXCLUDE_TAGS):
        tag.decompose()
    for tag in soup.find_all(STRUCTURE_TAGS):
        tag.decompose()
    for el in soup.select('[role="navigation"], [aria-hidden="true"], .sr-only, .visually-hidden, .cookie, .Cookie, .cookie-banner, .consent'):
        try:
            el.decompose()
        except Exception:
            pass


def html_to_markdown(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    clean_dom_for_content(soup)
    title = (soup.title.string or "").strip() if soup.title else ""
    main = soup.find("main") or soup.find(attrs={"role": "main"}) or soup.body or soup
    html_fragment = str(main)

    if md_convert:
        md = md_convert(
            html_fragment,
            heading_style="ATX",
            strip=["img"],
            wrap=False,
            bullets="*",
            escape_asterisks=False,
            escape_underscores=False,
            code_language=False,
        )
    else:
        md = BeautifulSoup(html_fragment, "html.parser").get_text("\n")

    md_lines = [ln.rstrip() for ln in md.splitlines()]
    compact = []
    blank = 0
    for ln in md_lines:
        if ln.strip():
            blank = 0
            compact.append(ln)
        else:
            blank += 1
            if blank <= 2:
                compact.append("")
    final_md = "\n".join(compact).strip()
    return title, final_md


def html_to_text(html: str) -> Tuple[str, str]:
    soup = BeautifulSoup(html, "html.parser")
    clean_dom_for_content(soup)
    title = (soup.title.string or "").strip() if soup.title else ""
    text = soup.get_text(separator="\n")
    lines = [re.sub(r"\s+", " ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    deduped, prev = [], None
    for ln in lines:
        if ln != prev:
            deduped.append(ln)
        prev = ln
    return title, "\n".join(deduped).strip()


# -------------------- crawler -------------------- #

def crawl(
    base_url: str,
    out_dir: str,
    use_sitemap: bool,
    delay: float,
    timeout: int,
    max_pages: int,
    include_subdomains: bool,
    fmt: str,
):
    os.makedirs(out_dir, exist_ok=True)
    jsonl_path = os.path.join(out_dir, "pages.jsonl")

    session = requests.Session()
    session.verify = CERT_PATH
    session.headers.update({
        "User-Agent": DEFAULT_UA,
        "Accept": "text/html,application/xhtml+xml;q=0.9,*/*;q=0.8"
    })

    base_url = norm_url(base_url)
    base_netloc = up.urlsplit(base_url).netloc

    print("====== crawl starting ======")
    print(f"[cfg] base={base_url}")
    print(f"[cfg] out_dir={out_dir}")
    print(f"[cfg] format={fmt}  include_subdomains={include_subdomains}")
    print(f"[cfg] use_sitemap={use_sitemap}  max_pages={max_pages if max_pages>0 else 'unlimited'}  delay={delay}s  timeout={timeout}s")
    print("============================")

    # robots.txt
    rp = parse_robots_txt(session, up.urljoin(base_url, "/robots.txt"))

    def allowed(u: str) -> bool:
        try:
            ok = rp.can_fetch(DEFAULT_UA, u)
            if not ok:
                print(f"[skip] disallowed by robots.txt: {u}")
            return ok
        except Exception:
            return True

    to_visit: deque[str] = deque()
    seen: Set[str] = set()
    seeds: List[str] = []

    # Seed via sitemap(s)
    total_planned: Optional[int] = None
    if use_sitemap:
        for sm in discover_sitemaps(session, base_url):
            seeds.extend(parse_sitemap_xml(session, sm, timeout))
        seeds = [norm_url(u) for u in seeds if u]
        seeds = [u for u in seeds if same_scope(u, base_netloc, include_subdomains)]
        # Respect robots here too
        seeds = [u for u in seeds if allowed(u)]
        for u in seeds:
            to_visit.append(u)
        if seeds:
            total_planned = len(seeds)
            print(f"[total] sitemap reports {total_planned} page(s) in scope")
        else:
            print("[info] no eligible URLs from sitemap(s) after filtering")

    # Fallback seed
    if not to_visit:
        print("[info] no sitemap seeds; falling back to base page BFS")
        to_visit.append(base_url)

    count = 0
    visited_for_links = set()
    ext = "md" if fmt == "markdown" else "txt"

    def show_progress():
        if total_planned:
            pct = (count / total_planned) * 100 if total_planned else 0.0
            print(f"[prog] saved {count}/{total_planned} ({pct:.1f}%) | seen={len(seen)} queued={len(to_visit)}")
        else:
            # Unknown total — show live discovery stats
            print(f"[prog] saved {count} | seen={len(seen)} queued={len(to_visit)} (total unknown)")

    with open(jsonl_path, "w", encoding="utf-8") as jf:
        while to_visit and (max_pages <= 0 or count < max_pages):
            url = to_visit.popleft()
            if url in seen:
                continue
            if not same_scope(url, base_netloc, include_subdomains):
                print(f"[skip] out of scope: {url}")
                continue
            if not allowed(url):
                continue

            seen.add(url)
            print(f"[get ] {url}")
            resp = fetch(session, url, timeout)
            time.sleep(delay)

            if not (resp and resp.ok):
                code = getattr(resp, "status_code", "n/a")
                print(f"[warn] non-OK response ({code}) for {url}")
                show_progress()
                continue

            ctype = resp.headers.get("Content-Type", "").lower()
            if "text/html" not in ctype:
                print(f"[skip] non-HTML ({ctype}) {url}")
                show_progress()
                continue

            # Convert
            if fmt == "markdown":
                title, content = html_to_markdown(resp.text)
            else:
                title, content = html_to_text(resp.text)

            # Save file
            fname = safe_filename(url, ext)
            fpath = os.path.join(out_dir, fname)
            with open(fpath, "w", encoding="utf-8") as f:
                if fmt == "markdown":
                    header = f"# {title}\n\n" if title else ""
                    meta = f"> URL: {url}\n\n"
                else:
                    header = f"Title: {title}\n\n" if title else ""
                    meta = f"URL: {url}\n\n"
                f.write(header + meta + (content or "") + ("\n" if content else ""))

            jf.write(json.dumps({"url": url, "title": title, "path": fname, "text": content}, ensure_ascii=False) + "\n")
            count += 1
            print(f"[save] {fname}  (saved total: {count})")

            # Expand links only when BFS (no sitemaps) to avoid massive duplication
            if not seeds:
                if url not in visited_for_links:
                    visited_for_links.add(url)
                    links = extract_links(resp.text, url)
                    new_links = [
                        l for l in links
                        if l not in seen
                        and same_scope(l, base_netloc, include_subdomains)
                        and allowed(l)
                    ]
                    to_visit.extend(new_links)
                    if new_links:
                        print(f"[disc] queued {len(new_links)} new link(s) from {url}")

            show_progress()

    print("====== crawl complete ======")
    print(f"[sum] pages saved: {count}")
    if total_planned is not None:
        print(f"[sum] sitemap total: {total_planned}")
    print(f"[sum] output dir: {out_dir}")
    print(f"[sum] index file: {jsonl_path}")


# -------------------- main -------------------- #

def main():
    parser = argparse.ArgumentParser(description="Crawl a site and extract text or Markdown for ingestion (with total count + progress).")
    parser.add_argument("--base", required=True, help="Base site URL, e.g., https://www.WEBSITE-TO-CRAWL.com/")
    parser.add_argument("--out", required=True, help="Output directory")
    parser.add_argument("--use-sitemap", default="true", choices=["true", "false"], help="Use sitemap(s) if present")
    parser.add_argument("--delay", type=float, default=1.0, help="Delay between requests (seconds)")
    parser.add_argument("--timeout", type=int, default=15, help="HTTP request timeout (seconds)")
    parser.add_argument("--max-pages", type=int, default=500, help="Max pages when BFS fallback is used; 0 = unlimited")
    parser.add_argument("--include-subdomains", default="false", choices=["true", "false"], help="Include subdomains")
    parser.add_argument("--format", dest="fmt", default="markdown", choices=["markdown", "text"], help="Output format")
    args = parser.parse_args()

    crawl(
        base_url=args.base,
        out_dir=args.out,
        use_sitemap=(args.use_sitemap.lower() == "true"),
        delay=args.delay,
        timeout=args.timeout,
        max_pages=args.max_pages,
        include_subdomains=(args.include_subdomains.lower() == "true"),
        fmt=args.fmt,
    )

if __name__ == "__main__":
    main()
