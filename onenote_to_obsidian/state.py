"""Export state tracking for resume capability.

Tracks which pages have been exported (by page ID and modification time)
so that re-running the exporter skips unchanged pages.
"""

import json
import logging
from pathlib import Path

logger = logging.getLogger(__name__)


class ExportState:
    """Persisted state: which pages have been exported and when."""

    def __init__(self, state_path: Path):
        self._state_path = state_path
        self._exported_pages: dict[str, str] = {}  # page_id -> last_modified_time
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text())
                self._exported_pages = data.get("exported_pages", {})
                logger.debug(
                    "Loaded export state: %d pages tracked",
                    len(self._exported_pages),
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to load export state: %s", e)
                self._exported_pages = {}

    def is_exported(self, page_id: str, last_modified: str) -> bool:
        """Check if a page was already exported with this modification time."""
        return self._exported_pages.get(page_id) == last_modified

    def mark_exported(self, page_id: str, last_modified: str) -> None:
        """Record that a page has been successfully exported."""
        self._exported_pages[page_id] = last_modified
        self._save()

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"exported_pages": self._exported_pages}, indent=2))

    def clear(self) -> None:
        """Clear all export state (forces full re-export)."""
        self._exported_pages.clear()
        if self._state_path.exists():
            self._state_path.unlink()

    @property
    def count(self) -> int:
        return len(self._exported_pages)


class FailedResourceState:
    """Persisted state: pages with resources that failed to download."""

    def __init__(self, state_path: Path):
        self._state_path = state_path
        self._failed_pages: dict[str, dict] = {}
        self._load()

    def _load(self) -> None:
        if self._state_path.exists():
            try:
                data = json.loads(self._state_path.read_text())
                self._failed_pages = data.get("failed_resources", {})
                logger.debug(
                    "Loaded failed resource state: %d pages tracked",
                    len(self._failed_pages),
                )
            except (json.JSONDecodeError, ValueError) as e:
                logger.warning("Failed to load failed resource state: %s", e)
                self._failed_pages = {}

    def mark_failed(
        self,
        page_id: str,
        title: str,
        last_modified: str,
        attachments_dir: str,
        resources: list[dict],
    ) -> None:
        """Record failed resources for a page."""
        self._failed_pages[page_id] = {
            "title": title,
            "last_modified": last_modified,
            "attachments_dir": attachments_dir,
            "resources": resources,
        }
        self._save()

    def clear_page(self, page_id: str) -> None:
        """Remove a page from failed state (all resources recovered or page re-exported)."""
        if page_id not in self._failed_pages:
            return
        del self._failed_pages[page_id]
        if self._failed_pages:
            self._save()
        elif self._state_path.exists():
            self._state_path.unlink()

    def clear(self) -> None:
        """Clear all failed resource state."""
        self._failed_pages.clear()
        if self._state_path.exists():
            self._state_path.unlink()

    def pages(self) -> dict[str, dict]:
        """Return a snapshot of all pages with failed resources."""
        return dict(self._failed_pages)

    def _save(self) -> None:
        self._state_path.parent.mkdir(parents=True, exist_ok=True)
        self._state_path.write_text(json.dumps({"failed_resources": self._failed_pages}, indent=2))

    @property
    def count(self) -> int:
        return len(self._failed_pages)
