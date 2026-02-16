"""
TheAltText — Website Scanner Service
Crawls websites to find images and check alt text compliance.
"""

import logging
import time
from typing import List, Dict, Optional
from urllib.parse import urljoin, urlparse

import httpx
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


async def scan_page(url: str, timeout: float = 30.0) -> Dict:
    """
    Scan a single page for images and their alt text status.
    Returns a dict with page info and image details.
    """
    images = []
    page_title = ""

    try:
        async with httpx.AsyncClient(
            timeout=timeout,
            follow_redirects=True,
            headers={"User-Agent": "TheAltText/1.0 (Accessibility Scanner)"},
        ) as client:
            response = await client.get(url)
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            page_title = soup.title.string if soup.title else url

            # Find all img tags
            for img in soup.find_all("img"):
                src = img.get("src", "")
                if not src:
                    continue

                # Resolve relative URLs
                full_url = urljoin(url, src)
                alt = img.get("alt")
                aria_label = img.get("aria-label")
                role = img.get("role")

                # Determine compliance status
                has_alt = alt is not None
                is_decorative = role == "presentation" or (alt is not None and alt.strip() == "")

                if is_decorative:
                    status = "decorative"
                elif has_alt and alt.strip():
                    status = "has_alt"
                elif has_alt and not alt.strip():
                    status = "empty_alt"
                else:
                    status = "missing_alt"

                images.append({
                    "src": full_url,
                    "alt": alt,
                    "aria_label": aria_label,
                    "role": role,
                    "status": status,
                    "page_url": url,
                    "is_decorative": is_decorative,
                })

            # Also check for background images in inline styles (common issue)
            for elem in soup.find_all(style=True):
                style = elem.get("style", "")
                if "background-image" in style and "url(" in style:
                    # Extract URL from background-image
                    start = style.index("url(") + 4
                    end = style.index(")", start)
                    bg_url = style[start:end].strip("'\"")
                    if bg_url:
                        images.append({
                            "src": urljoin(url, bg_url),
                            "alt": None,
                            "aria_label": elem.get("aria-label"),
                            "role": elem.get("role"),
                            "status": "background_image",
                            "page_url": url,
                            "is_decorative": False,
                        })

    except httpx.HTTPStatusError as e:
        logger.error(f"HTTP error scanning {url}: {e.response.status_code}")
        return {"url": url, "title": "", "images": [], "error": f"HTTP {e.response.status_code}"}
    except Exception as e:
        logger.error(f"Error scanning {url}: {str(e)}")
        return {"url": url, "title": "", "images": [], "error": str(e)}

    return {
        "url": url,
        "title": page_title,
        "images": images,
        "total_images": len(images),
        "images_with_alt": sum(1 for i in images if i["status"] == "has_alt"),
        "images_missing_alt": sum(1 for i in images if i["status"] == "missing_alt"),
        "images_empty_alt": sum(1 for i in images if i["status"] == "empty_alt"),
        "images_decorative": sum(1 for i in images if i["status"] == "decorative"),
        "background_images": sum(1 for i in images if i["status"] == "background_image"),
        "error": None,
    }


async def discover_links(url: str, max_links: int = 50) -> List[str]:
    """Discover internal links on a page for deeper scanning."""
    links = set()
    base_domain = urlparse(url).netloc

    try:
        async with httpx.AsyncClient(
            timeout=20.0,
            follow_redirects=True,
            headers={"User-Agent": "TheAltText/1.0 (Accessibility Scanner)"},
        ) as client:
            response = await client.get(url)
            soup = BeautifulSoup(response.text, "html.parser")

            for a_tag in soup.find_all("a", href=True):
                href = a_tag["href"]
                full_url = urljoin(url, href)
                parsed = urlparse(full_url)

                # Only follow internal links
                if parsed.netloc == base_domain and parsed.scheme in ("http", "https"):
                    # Skip anchors, files, etc.
                    if not any(full_url.lower().endswith(ext) for ext in
                              (".pdf", ".zip", ".doc", ".xls", ".mp3", ".mp4")):
                        links.add(full_url.split("#")[0].rstrip("/"))

                if len(links) >= max_links:
                    break

    except Exception as e:
        logger.error(f"Error discovering links on {url}: {str(e)}")

    return list(links)[:max_links]


async def full_site_scan(
    url: str,
    scan_depth: int = 1,
    max_pages: int = 20,
) -> Dict:
    """
    Perform a full site scan with configurable depth.
    Returns aggregated results across all scanned pages.
    """
    start_time = time.time()
    scanned_urls = set()
    all_results = []
    urls_to_scan = [url]

    for depth in range(scan_depth):
        next_urls = []
        for scan_url in urls_to_scan:
            if scan_url in scanned_urls or len(scanned_urls) >= max_pages:
                break

            scanned_urls.add(scan_url)
            result = await scan_page(scan_url)
            all_results.append(result)

            if depth < scan_depth - 1:
                new_links = await discover_links(scan_url)
                next_urls.extend(l for l in new_links if l not in scanned_urls)

        urls_to_scan = next_urls

    # Aggregate results
    total_images = sum(r.get("total_images", 0) for r in all_results)
    images_with_alt = sum(r.get("images_with_alt", 0) for r in all_results)
    images_missing = sum(r.get("images_missing_alt", 0) for r in all_results)
    images_empty = sum(r.get("images_empty_alt", 0) for r in all_results)

    compliance_score = (images_with_alt / total_images * 100) if total_images > 0 else 100.0

    return {
        "target_url": url,
        "pages_scanned": len(scanned_urls),
        "scan_depth": scan_depth,
        "total_images": total_images,
        "images_with_alt": images_with_alt,
        "images_missing_alt": images_missing,
        "images_empty_alt": images_empty,
        "compliance_score": round(compliance_score, 1),
        "page_results": all_results,
        "scan_time_seconds": round(time.time() - start_time, 2),
    }
