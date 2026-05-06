"""Binary file downloads (PDF, DOCX, etc.) referenced from crawled pages.

Sibling to :mod:`markcrawl.images` but parametrized by allowed MIME
types / file extensions and with strict streaming + size enforcement.
Used when ``crawl(download_types=[...])`` is set.

Design notes:

* **Streaming, not buffered.** `images.py` reads `response.content`
  in full — fine for ~100 KB images.  Binaries can legitimately reach
  25 MB (default cap) and a malicious server could feed gigabytes.
  We use ``stream=True`` on ``requests`` and ``client.stream(...)``
  on ``httpx`` to enforce the size cap per chunk and abort cleanly
  when exceeded.
* **Atomic write via .tmp + rename.** Partial writes get a `.tmp`
  suffix; only on full success do we atomically rename to the final
  filename.  A SIGKILL / watchdog kill leaves identifiable
  `.tmp` debris that resume can clean up.
* **Content-type validation BEFORE writing bytes.** A `.pdf` URL
  that 302-redirects to a login wall (HTML response) gets dropped
  immediately, no disk written, URL recorded in type-skipped list.
"""
from __future__ import annotations

import hashlib
import logging
import os
import urllib.parse as up
from typing import Any, Iterable, Optional

logger = logging.getLogger(__name__)

DOWNLOADS_DIR = "downloads"
DEFAULT_DOWNLOAD_MAX_FILES = 200
DEFAULT_DOWNLOAD_MAX_SIZE_MB = 25
_CHUNK_SIZE = 64 * 1024  # 64 KB per stream chunk


# --- Type / extension matching ---------------------------------------------

def _normalize_type_token(token: str) -> str:
    """Lowercase a download_types entry; strip leading '.' for extensions."""
    t = token.strip().lower()
    if t.startswith("."):
        t = t[1:]
    return t


def url_extension(url: str) -> str:
    """Lowercase file extension from the URL path, including leading dot.

    Returns empty string when no extension is present.  Strips query
    parameters and URL fragments before extracting.
    """
    path = up.urlsplit(url).path or ""
    base = path.rsplit("/", 1)[-1]
    if "." not in base:
        return ""
    ext = "." + base.rsplit(".", 1)[-1].lower()
    # Defend against "." in middle but no real extension (e.g. "example.com" or
    # the rare basename like "v1.0").
    if len(ext) > 8 or len(ext) < 2:
        return ""
    return ext


def url_matches_download_types(url: str, types: Iterable[str]) -> bool:
    """Cheap pre-filter: does the URL extension match any configured type?

    Used at link-discovery time to avoid even fetching obviously
    irrelevant URLs.  Authoritative validation is the content-type
    check inside :func:`download_binary` / :func:`download_binary_async`.
    """
    if not types:
        return False
    ext = url_extension(url)
    if not ext:
        return False
    ext_no_dot = ext[1:]
    for t in types:
        nt = _normalize_type_token(t)
        if nt == ext_no_dot:
            return True
    return False


def content_type_matches(content_type: str, types: Iterable[str]) -> bool:
    """Authoritative content-type validation.

    Strips parameters (``application/pdf; charset=...`` → ``application/pdf``)
    and accepts both extension-shaped and MIME-prefix-shaped tokens in
    ``types``::

        content_type_matches("application/pdf", ["pdf"])              -> True
        content_type_matches("application/pdf", ["application/pdf"])  -> True
        content_type_matches("text/html", ["pdf"])                    -> False
    """
    if not content_type:
        return False
    primary = content_type.split(";", 1)[0].strip().lower()
    if not primary:
        return False
    primary_subtype = primary.rsplit("/", 1)[-1] if "/" in primary else primary
    for t in types:
        nt = _normalize_type_token(t)
        if not nt:
            continue
        # Match shapes: "pdf" → subtype match, "application/pdf" → full match,
        # "application/" → prefix match.
        if nt == primary:
            return True
        if "/" in nt and primary.startswith(nt):
            return True
        if "/" not in nt and primary_subtype == nt:
            return True
    return False


# --- Filename safety -------------------------------------------------------

_SAFE_FILENAME_KEEP = "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789._-"


def safe_binary_filename(url: str, content_type: str = "") -> str:
    """Filesystem-safe filename derived from the URL.

    Uses URL extension when present, falls back to content-type's
    subtype (``application/pdf`` → ``.pdf``), then ``.bin``.  Path is
    restricted to ``[a-zA-Z0-9._-]`` and a 12-char sha1 hash suffix is
    appended for uniqueness.
    """
    parsed = up.urlsplit(url)
    path = parsed.path.rstrip("/")

    ext = url_extension(url)
    if not ext and content_type:
        primary = content_type.split(";", 1)[0].strip().lower()
        if "/" in primary:
            subtype = primary.rsplit("/", 1)[-1]
            if subtype and len(subtype) <= 6 and subtype.isalnum():
                ext = "." + subtype
    if not ext:
        ext = ".bin"

    basename = os.path.basename(path).rsplit(".", 1)[0] if path else "file"
    stub_chars = []
    for ch in basename[:120]:
        stub_chars.append(ch if ch in _SAFE_FILENAME_KEEP else "-")
    stub = "".join(stub_chars).strip("-") or "file"

    h = hashlib.sha1(url.encode("utf-8")).hexdigest()[:12]
    return f"{stub}__{h}{ext}"


# --- Sync download (requests-style session) --------------------------------

def download_binary(
    session: Any,
    url: str,
    downloads_dir: str,
    timeout: int,
    max_size_bytes: int,
    allowed_types: Iterable[str],
) -> Optional[dict]:
    """Stream a binary file to disk with size + content-type enforcement.

    Returns a metadata dict ``{path, size_bytes, content_type}`` on
    success.  Returns ``None`` on failure; failure cause is reported
    to the caller via the in-memory engine state (size_skipped,
    type_skipped, etc.) populated by the calling site.

    Behavior:
      - Streams with ``stream=True`` and ``iter_content``.
      - Validates content-type BEFORE writing any bytes.
      - Writes to ``<filename>.tmp``, atomically renames on success.
      - Aborts + unlinks the tmp file when cumulative size exceeds
        ``max_size_bytes``.
      - Connection / write errors → log debug, unlink tmp, return None.
    """
    os.makedirs(downloads_dir, exist_ok=True)
    try:
        resp = session.get(url, timeout=timeout, stream=True)
    except Exception as exc:
        logger.debug("Binary download failed for %s: %s", url, exc)
        return None

    try:
        status = getattr(resp, "status_code", None)
        if status is None or status >= 400:
            return None

        ct = ""
        headers = getattr(resp, "headers", {}) or {}
        ct = headers.get("content-type", "") or headers.get("Content-Type", "")
        if not content_type_matches(ct, allowed_types):
            logger.debug("Content-type mismatch for %s: %s", url, ct)
            return {"_type_skipped": True, "url": url, "content_type": ct}

        filename = safe_binary_filename(url, ct)
        final_path = os.path.join(downloads_dir, filename)
        tmp_path = final_path + ".tmp"

        written = 0
        try:
            with open(tmp_path, "wb") as f:
                iter_chunks = getattr(resp, "iter_content", None)
                if iter_chunks is None:
                    # Test mocks may expose a `.content` bytes attribute
                    # without an iter_content() method.  Treat the body as
                    # one chunk.
                    body = getattr(resp, "content", b"") or b""
                    if len(body) > max_size_bytes:
                        f.close()
                        os.unlink(tmp_path)
                        return {"_size_skipped": True, "url": url}
                    f.write(body)
                    written = len(body)
                else:
                    for chunk in iter_chunks(chunk_size=_CHUNK_SIZE):
                        if not chunk:
                            continue
                        written += len(chunk)
                        if written > max_size_bytes:
                            f.close()
                            try:
                                os.unlink(tmp_path)
                            except OSError:
                                pass
                            return {"_size_skipped": True, "url": url}
                        f.write(chunk)
        except Exception as exc:
            logger.warning("Write error for %s: %s", url, exc)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return None

        try:
            os.replace(tmp_path, final_path)
        except OSError as exc:
            logger.warning("Rename failed for %s: %s", url, exc)
            try:
                os.unlink(tmp_path)
            except OSError:
                pass
            return None

        return {"path": final_path, "size_bytes": written, "content_type": ct}
    finally:
        close = getattr(resp, "close", None)
        if callable(close):
            try:
                close()
            except Exception:
                pass


# --- Async download (httpx-style client) -----------------------------------

async def download_binary_async(
    client: Any,
    url: str,
    downloads_dir: str,
    timeout: int,
    max_size_bytes: int,
    allowed_types: Iterable[str],
) -> Optional[dict]:
    """Async streaming download.  Mirrors :func:`download_binary` semantics
    via ``httpx.AsyncClient.stream(...)`` + ``response.aiter_bytes(...)``.
    """
    os.makedirs(downloads_dir, exist_ok=True)
    try:
        cm = client.stream("GET", url, timeout=timeout)
    except Exception as exc:
        logger.debug("Binary stream open failed for %s: %s", url, exc)
        return None

    try:
        async with cm as resp:
            status = getattr(resp, "status_code", None)
            if status is None or status >= 400:
                return None

            ct = ""
            headers = getattr(resp, "headers", {}) or {}
            ct = headers.get("content-type", "") or headers.get("Content-Type", "")
            if not content_type_matches(ct, allowed_types):
                logger.debug("Content-type mismatch for %s: %s", url, ct)
                return {"_type_skipped": True, "url": url, "content_type": ct}

            filename = safe_binary_filename(url, ct)
            final_path = os.path.join(downloads_dir, filename)
            tmp_path = final_path + ".tmp"

            written = 0
            try:
                with open(tmp_path, "wb") as f:
                    aiter = getattr(resp, "aiter_bytes", None)
                    if aiter is None:
                        # Test mocks: fall back to .content / .read()
                        read = getattr(resp, "aread", None)
                        if read is not None:
                            body = await read()
                        else:
                            body = getattr(resp, "content", b"") or b""
                        if len(body) > max_size_bytes:
                            f.close()
                            os.unlink(tmp_path)
                            return {"_size_skipped": True, "url": url}
                        f.write(body)
                        written = len(body)
                    else:
                        async for chunk in aiter(chunk_size=_CHUNK_SIZE):
                            if not chunk:
                                continue
                            written += len(chunk)
                            if written > max_size_bytes:
                                f.close()
                                try:
                                    os.unlink(tmp_path)
                                except OSError:
                                    pass
                                return {"_size_skipped": True, "url": url}
                            f.write(chunk)
            except Exception as exc:
                logger.warning("Write error for %s: %s", url, exc)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                return None

            try:
                os.replace(tmp_path, final_path)
            except OSError as exc:
                logger.warning("Rename failed for %s: %s", url, exc)
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
                return None

            return {"path": final_path, "size_bytes": written, "content_type": ct}
    except Exception as exc:
        logger.debug("Binary download failed for %s: %s", url, exc)
        return None
