"""Main orchestrator: enumerate OneNote notebooks and export to Obsidian Markdown."""

from __future__ import annotations

import logging
from collections.abc import Callable
from pathlib import Path

from .auth import AuthManager
from .config import Config
from .graph_client import GraphAPIError, GraphClient
from .html_converter import convert_page_html, preprocess_onenote_html
from .onenote_api import Notebook, OneNoteAPI, Page, Section, SectionGroup
from .resource_downloader import ResourceDownloader
from .state import ExportState, FailedResourceState
from .utils import deduplicate_path, sanitize_filename

logger = logging.getLogger(__name__)


class OneNoteExporter:
    """Exports OneNote notebooks to Obsidian-compatible Markdown files."""

    def __init__(self, config: Config):
        self._config = config
        self._vault_path = Path(config.vault_path)
        self._attachments_folder = config.attachments_folder_name

        self._auth = AuthManager(config)
        self._client = GraphClient(self._auth)
        self._api = OneNoteAPI(self._client)
        self._downloader = ResourceDownloader(self._api)
        self._state = ExportState(config.config_dir_path / "export_state.json")
        self._failed_state = FailedResourceState(config.config_dir_path / "failed_resources.json")

        self._stats: dict[str, int] = {
            "exported": 0,
            "skipped": 0,
            "errors": 0,
            "failed_resources": 0,
            "total": 0,
        }
        self._failed_page_titles: list[str] = []

    def export_all(self, notebook_filter: str | None = None) -> None:
        """Export all notebooks (or a specific one by name).

        Args:
            notebook_filter: If set, only export notebook with this display name
        """
        self._stats = {"exported": 0, "skipped": 0, "errors": 0, "failed_resources": 0, "total": 0}
        self._failed_page_titles = []

        # Verify vault path
        self._vault_path.mkdir(parents=True, exist_ok=True)

        # Phase 1: Enumerate
        print("Fetching notebooks...")
        notebooks = self._api.list_notebooks()

        if notebook_filter:
            notebooks = [
                nb for nb in notebooks if nb.display_name.lower() == notebook_filter.lower()
            ]
            if not notebooks:
                print(f"Notebook '{notebook_filter}' not found.")
                print("Available notebooks:")
                all_nbs = self._api.list_notebooks()
                for nb in all_nbs:
                    print(f"  - {nb.display_name}")
                return

        print(f"Found {len(notebooks)} notebook(s)")

        total_pages = 0
        for nb in notebooks:
            self._api.enumerate_notebook(nb)
            count = self._count_pages(nb)
            total_pages += count
            print(f"  [{nb.display_name}] sections: {self._count_sections(nb)}, pages: {count}")

        self._stats["total"] = total_pages
        print(f"\nTotal pages to export: {total_pages}")
        if self._state.count > 0:
            print(f"Previously exported: {self._state.count} (unchanged pages will be skipped)")
        print()

        # Phase 2: Export
        for nb in notebooks:
            nb_dir = self._vault_path / sanitize_filename(nb.display_name)
            nb_dir.mkdir(parents=True, exist_ok=True)

            # Export sections directly under notebook
            for section in nb.sections:
                self._export_section(section, nb_dir)

            # Export section groups (recursive)
            for sg in nb.section_groups:
                self._export_section_group(sg, nb_dir)

        # Summary
        s = self._stats
        print()
        print("=" * 50)
        print("Done!")
        print(f"  Exported: {s['exported']}")
        print(f"  Skipped (unchanged): {s['skipped']}")
        print(f"  Errors: {s['errors']}")
        processed = s["exported"] + s["skipped"] + s["errors"] + s["failed_resources"]
        print(f"  Total processed: {processed}/{s['total']}")
        if s["failed_resources"] > 0:
            print(f"  Failed resources: {s['failed_resources']} page(s) — use --retry-resources")
            for title in self._failed_page_titles:
                print(f"    - {title}")
        print(f"\nFiles saved to: {self._vault_path}")

    def retry_failed_resources(self) -> None:
        """Retry downloading resources that failed in a previous export."""
        if self._failed_state.count == 0:
            print("No failed resources recorded. Nothing to retry.")
            return

        pages = self._failed_state.pages()
        print(f"Retrying failed resources for {len(pages)} page(s)...\n")

        recovered = 0
        still_failing = 0

        for page_id, data in pages.items():
            try:
                title = data["title"]
                last_modified = data["last_modified"]
                attachments_dir = self._vault_path / data["attachments_dir"]
                resources: list[dict] = data["resources"]
                resource_urls = {r["url"]: (r["filename"], r["media_type"]) for r in resources}
            except (KeyError, TypeError) as e:
                logger.warning("Skipping malformed failed-resource entry %s: %s", page_id, e)
                self._failed_state.clear_page(page_id)
                continue
            result = self._downloader.download_resources(resource_urls, attachments_dir)

            if result.failed_resources:
                self._failed_state.mark_failed(
                    page_id, title, last_modified, data["attachments_dir"], result.failed_resources
                )
                still_failing += 1
                print(f"  STILL FAILING: {title} ({len(result.failed_resources)} resource(s))")
            else:
                self._state.mark_exported(page_id, last_modified)
                self._failed_state.clear_page(page_id)
                recovered += 1
                print(f"  Recovered: {title}")

        print()
        print(f"Retry complete: {recovered} page(s) recovered, {still_failing} still failing.")

    def _export_section_group(self, group: SectionGroup, parent_dir: Path) -> None:
        """Recursively export a section group to a subdirectory."""
        group_dir = parent_dir / sanitize_filename(group.display_name)
        group_dir.mkdir(parents=True, exist_ok=True)

        for section in group.sections:
            self._export_section(section, group_dir)

        for nested_sg in group.section_groups:
            self._export_section_group(nested_sg, group_dir)

    def _export_section(self, section: Section, parent_dir: Path) -> None:
        """Export all pages in a section to a subdirectory."""
        section_dir = parent_dir / sanitize_filename(section.display_name)
        section_dir.mkdir(parents=True, exist_ok=True)
        attachments_dir = section_dir / self._attachments_folder

        # Seed dedup set from existing files on disk (for crash-resume safety)
        used_md_paths: set[Path] = set()
        if section_dir.exists():
            used_md_paths.update(section_dir.glob("*.md"))

        for page in section.pages:
            processed = self._stats["exported"] + self._stats["skipped"] + self._stats["errors"]
            progress = f"[{processed + 1}/{self._stats['total']}]"

            # Check if already exported and unchanged
            if self._state.is_exported(page.id, page.last_modified_time):
                self._stats["skipped"] += 1
                logger.debug("%s Skipped (unchanged): %s", progress, page.title)
                continue

            # Clear any stale failed state before a fresh export (page version changed)
            self._failed_state.clear_page(page.id)

            try:
                failed_records = self._export_page(
                    page, section_dir, attachments_dir, used_md_paths
                )
                if failed_records:
                    rel_attachments = str(attachments_dir.relative_to(self._vault_path))
                    self._failed_state.mark_failed(
                        page.id,
                        page.title,
                        page.last_modified_time,
                        rel_attachments,
                        failed_records,
                    )
                    self._failed_page_titles.append(page.title)
                    self._stats["failed_resources"] += 1
                    print(f"  {progress} {page.title} (some resources failed)")
                    print("    Use --retry-resources to retry.")
                else:
                    self._state.mark_exported(page.id, page.last_modified_time)
                    self._stats["exported"] += 1
                    print(f"  {progress} {page.title}")
            except GraphAPIError as e:
                self._stats["errors"] += 1
                logger.error("%s ERROR '%s': %s", progress, page.title, e)
                print(f"  {progress} ERROR: {page.title} — {e}")
            except (OSError, ValueError) as e:
                self._stats["errors"] += 1
                logger.error("%s ERROR '%s': %s", progress, page.title, e, exc_info=True)
                print(f"  {progress} ERROR: {page.title} — {e}")

    def _export_page(
        self,
        page: Page,
        section_dir: Path,
        attachments_dir: Path,
        used_md_paths: set[Path],
    ) -> list[dict]:
        """Export a single page: HTML → resources → Markdown → file.

        Returns list of failed resource records (empty if all resources downloaded).
        """
        # 1. Get page HTML content
        html_content = self._api.get_page_content(page.id)

        # 2. Pre-process HTML: extract resource URLs, clean up
        cleaned_html, resource_urls = preprocess_onenote_html(html_content)

        # 3. Download resources (images, attachments)
        result = self._downloader.download_resources(resource_urls, attachments_dir)

        # 4. Convert HTML to Markdown
        markdown = convert_page_html(
            cleaned_html,
            resource_map=result.resource_map,
            attachments_rel_path=self._attachments_folder,
        )

        # 5. Build YAML frontmatter
        frontmatter = self._build_frontmatter(page)

        # 6. Write .md file
        safe_title = sanitize_filename(page.title)
        md_path = section_dir / f"{safe_title}.md"
        md_path = deduplicate_path(md_path, existing_paths=used_md_paths)
        used_md_paths.add(md_path)

        md_path.write_text(frontmatter + markdown, encoding="utf-8")

        return result.failed_resources

    def _build_frontmatter(self, page: Page) -> str:
        """Build YAML frontmatter for an exported page."""
        lines = ["---"]
        if page.created_time:
            lines.append(f'created: "{page.created_time}"')
        if page.last_modified_time:
            lines.append(f'modified: "{page.last_modified_time}"')
        lines.append("source: onenote")
        lines.append(f'onenote_id: "{page.id}"')
        lines.append("---")
        lines.append("")
        return "\n".join(lines) + "\n"

    @staticmethod
    def _count_recursive(
        obj: Notebook | SectionGroup,
        counter: Callable[[list[Section]], int],
    ) -> int:
        """Recursively count items across sections and nested section groups."""
        count = counter(obj.sections)
        for sg in obj.section_groups:
            count += OneNoteExporter._count_recursive(sg, counter)
        return count

    @staticmethod
    def _count_pages(notebook: Notebook) -> int:
        """Count total pages in a notebook (including section groups)."""
        return OneNoteExporter._count_recursive(
            notebook, lambda secs: sum(len(s.pages) for s in secs)
        )

    @staticmethod
    def _count_sections(notebook: Notebook) -> int:
        """Count total sections in a notebook (including section groups)."""
        return OneNoteExporter._count_recursive(notebook, len)
