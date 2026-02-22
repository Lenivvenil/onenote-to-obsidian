"""OneNote HTML → Obsidian Markdown conversion.

OneNote Graph API returns HTML with specific patterns:
- Images as <img> with Graph resource URLs in src/data-fullres-src
- File attachments as <object> with data-attachment attribute
- Checkboxes as <p data-tag="to-do"> / <p data-tag="to-do:completed">
- Embedded content as <iframe> with data-original-src
- Absolute positioning via inline CSS (irrelevant for Markdown)
"""

import logging
import re
from urllib.parse import urlparse

from bs4 import BeautifulSoup, Tag
from markdownify import MarkdownConverter

logger = logging.getLogger(__name__)


def extract_resource_id(url: str) -> str:
    """Extract resource ID from a Graph API resource URL.

    Example: https://graph.microsoft.com/v1.0/me/onenote/resources/0-abc123/$value
    Returns: 0-abc123
    """
    match = re.search(r"/resources/([^/]+)/", url)
    if match:
        return match.group(1)
    # Fallback: use last path segment
    parsed = urlparse(url)
    parts = [p for p in parsed.path.split("/") if p and p != "$value"]
    return parts[-1] if parts else "resource"


def preprocess_onenote_html(html: str) -> tuple[str, dict[str, tuple[str, str]]]:
    """Parse OneNote HTML, extract resource URLs, clean up OneNote-specific elements.

    Returns:
        cleaned_html: HTML ready for markdownify
        resource_urls: dict mapping resource URL -> (suggested_filename, media_type)
    """
    soup = BeautifulSoup(html, "html.parser")
    resource_urls: dict[str, tuple[str, str]] = {}

    # Extract image resource URLs
    for img in soup.find_all("img"):
        # Prefer full-resolution source
        for attr in ["data-fullres-src", "src"]:
            url = img.get(attr, "")
            if url and "onenote/resources" in url:
                src_type = (
                    img.get("data-fullres-src-type")
                    or img.get("data-src-type")
                    or "image/png"
                )
                ext = _ext_from_media_type(src_type)
                resource_id = extract_resource_id(url)
                filename = f"{resource_id}.{ext}"
                resource_urls[url] = (filename, src_type)
                break  # Only need one URL per image

    # Extract file attachment URLs from <object> tags
    for obj in soup.find_all("object"):
        data_url = obj.get("data", "")
        if data_url and "onenote/resources" in data_url:
            filename = obj.get("data-attachment", "attachment")
            media_type = obj.get("type", "application/octet-stream")
            resource_urls[data_url] = (filename, media_type)

    # Clean up absolute positioning (not meaningful in Markdown)
    for el in soup.find_all(style=True):
        style = el["style"]
        style = re.sub(r"position:\s*absolute;?\s*", "", style)
        style = re.sub(r"left:\s*[\d.]+px;?\s*", "", style)
        style = re.sub(r"top:\s*[\d.]+px;?\s*", "", style)
        style = re.sub(r"z-index:\s*[\d]+;?\s*", "", style)
        if style.strip().strip(";").strip():
            el["style"] = style
        else:
            del el["style"]

    # Remove empty <span> tags that OneNote sometimes generates
    for span in soup.find_all("span"):
        if not span.get_text(strip=True) and not span.find_all(["img", "object"]):
            span.decompose()

    return str(soup), resource_urls


def _ext_from_media_type(media_type: str) -> str:
    """Convert MIME type to file extension."""
    mapping = {
        "image/png": "png",
        "image/jpeg": "jpg",
        "image/gif": "gif",
        "image/bmp": "bmp",
        "image/svg+xml": "svg",
        "image/webp": "webp",
        "image/tiff": "tiff",
    }
    return mapping.get(media_type.lower(), media_type.split("/")[-1])


class OneNoteMarkdownConverter(MarkdownConverter):
    """Custom markdownify converter for OneNote HTML specifics."""

    def __init__(
        self,
        attachments_rel_path: str,
        resource_map: dict[str, str],
        **kwargs,
    ):
        """
        Args:
            attachments_rel_path: Relative path from .md file to attachments folder
            resource_map: Maps Graph resource URL -> local filename
        """
        super().__init__(**kwargs)
        self._attachments_rel = attachments_rel_path
        self._resource_map = resource_map

    def convert_img(self, el: Tag, text: str, **kwargs) -> str:
        """Convert <img> with Graph API resource URLs to local paths."""
        # Prefer full-resolution source
        src = el.get("data-fullres-src") or el.get("src", "")
        alt = el.get("alt", "image")

        local_filename = self._resource_map.get(src, "")
        if local_filename:
            return f"![{alt}]({self._attachments_rel}/{local_filename})"

        # If URL not in resource_map, keep original (external image)
        if src:
            return f"![{alt}]({src})"
        return ""

    def convert_object(self, el: Tag, text: str, **kwargs) -> str:
        """Convert <object> file attachments to markdown links."""
        data_url = el.get("data", "")
        display_name = el.get("data-attachment", "attachment")

        local_filename = self._resource_map.get(data_url, display_name)
        return f"[{display_name}]({self._attachments_rel}/{local_filename})"

    def convert_iframe(self, el: Tag, text: str, **kwargs) -> str:
        """Convert embedded iframes (videos, etc.) to markdown links."""
        src = el.get("data-original-src") or el.get("src", "")
        if src:
            return f"[Embedded content]({src})"
        return ""

    def convert_p(self, el: Tag, text: str, **kwargs) -> str:
        """Handle <p> with data-tag attribute for OneNote checkboxes/tags."""
        data_tag = el.get("data-tag", "")

        if "to-do" in data_tag:
            checked = "completed" in data_tag
            checkbox = "- [x]" if checked else "- [ ]"
            return f"{checkbox} {text.strip()}\n\n"

        # Default paragraph handling
        return super().convert_p(el, text, **kwargs)

    def convert_li(self, el: Tag, text: str, **kwargs) -> str:
        """Handle <li> with data-tag attribute for checkboxes inside lists."""
        data_tag = el.get("data-tag", "")

        if "to-do" in data_tag:
            checked = "completed" in data_tag
            checkbox = "[x]" if checked else "[ ]"
            # Get nesting depth
            parent = el.parent
            depth = 0
            while parent:
                if parent.name in ["ul", "ol"]:
                    depth += 1
                parent = parent.parent
            indent = "  " * max(0, depth - 1)
            return f"{indent}- {checkbox} {text.strip()}\n"

        return super().convert_li(el, text, **kwargs)


def convert_page_html(
    html: str,
    resource_map: dict[str, str],
    attachments_rel_path: str = "attachments",
) -> str:
    """Convert OneNote page HTML to Obsidian-compatible Markdown.

    Args:
        html: Pre-processed HTML (after preprocess_onenote_html)
        resource_map: Maps Graph resource URLs to local filenames
        attachments_rel_path: Relative path to attachments folder

    Returns:
        Markdown string
    """
    converter = OneNoteMarkdownConverter(
        attachments_rel_path=attachments_rel_path,
        resource_map=resource_map,
        heading_style="ATX",
        bullets="-",
        strong_em_symbol="*",
        newline_style="backslash",
    )

    markdown = converter.convert(html)

    # Clean up excessive blank lines
    markdown = re.sub(r"\n{3,}", "\n\n", markdown)

    # Clean up leading/trailing whitespace
    markdown = markdown.strip() + "\n"

    return markdown
