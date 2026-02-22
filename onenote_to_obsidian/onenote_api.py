"""OneNote-specific Graph API operations: notebooks, sections, pages, resources."""

import logging
from dataclasses import dataclass, field

from .graph_client import GraphClient

logger = logging.getLogger(__name__)


@dataclass
class Page:
    id: str
    title: str
    created_time: str
    last_modified_time: str
    content_url: str
    order: int = 0


@dataclass
class Section:
    id: str
    display_name: str
    pages: list[Page] = field(default_factory=list)


@dataclass
class SectionGroup:
    id: str
    display_name: str
    sections: list["Section"] = field(default_factory=list)
    section_groups: list["SectionGroup"] = field(default_factory=list)


@dataclass
class Notebook:
    id: str
    display_name: str
    sections: list[Section] = field(default_factory=list)
    section_groups: list[SectionGroup] = field(default_factory=list)


class OneNoteAPI:
    """High-level interface to OneNote via Microsoft Graph API."""

    def __init__(self, client: GraphClient):
        self._client = client

    def list_notebooks(self) -> list[Notebook]:
        """List all notebooks for the authenticated user."""
        data = self._client.get_json_all("/me/onenote/notebooks")
        notebooks = []
        for n in data:
            notebooks.append(
                Notebook(
                    id=n["id"],
                    display_name=n["displayName"],
                )
            )
        logger.info("Found %d notebooks", len(notebooks))
        return notebooks

    def list_sections(self, notebook_id: str) -> list[Section]:
        """List sections directly under a notebook."""
        data = self._client.get_json_all(
            f"/me/onenote/notebooks/{notebook_id}/sections"
        )
        return [
            Section(id=s["id"], display_name=s["displayName"])
            for s in data
        ]

    def list_section_groups(self, notebook_id: str) -> list[SectionGroup]:
        """List section groups under a notebook."""
        data = self._client.get_json_all(
            f"/me/onenote/notebooks/{notebook_id}/sectionGroups"
        )
        return [
            SectionGroup(id=sg["id"], display_name=sg["displayName"])
            for sg in data
        ]

    def list_sections_in_group(self, group_id: str) -> list[Section]:
        """List sections within a section group."""
        data = self._client.get_json_all(
            f"/me/onenote/sectionGroups/{group_id}/sections"
        )
        return [
            Section(id=s["id"], display_name=s["displayName"])
            for s in data
        ]

    def list_section_groups_in_group(self, group_id: str) -> list[SectionGroup]:
        """List nested section groups within a section group."""
        data = self._client.get_json_all(
            f"/me/onenote/sectionGroups/{group_id}/sectionGroups"
        )
        return [
            SectionGroup(id=sg["id"], display_name=sg["displayName"])
            for sg in data
        ]

    def list_pages(self, section_id: str) -> list[Page]:
        """List all pages in a section."""
        data = self._client.get_json_all(
            f"/me/onenote/sections/{section_id}/pages"
        )
        pages = []
        for i, p in enumerate(data):
            pages.append(
                Page(
                    id=p["id"],
                    title=p.get("title") or "Untitled",
                    created_time=p.get("createdDateTime", ""),
                    last_modified_time=p.get("lastModifiedDateTime", ""),
                    content_url=p.get("contentUrl", ""),
                    order=i,
                )
            )
        return pages

    def get_page_content(self, page_id: str) -> str:
        """Download the HTML content of a page."""
        url = f"/me/onenote/pages/{page_id}/content"
        return self._client.get_text(url)

    def get_resource(self, resource_url: str) -> bytes:
        """Download a binary resource (image or file attachment)."""
        return self._client.get_binary(resource_url)

    def enumerate_notebook(self, notebook: Notebook) -> Notebook:
        """Fully enumerate a notebook: sections, section groups (recursive), pages."""
        logger.info("Enumerating notebook: %s", notebook.display_name)

        notebook.sections = self.list_sections(notebook.id)
        for section in notebook.sections:
            section.pages = self.list_pages(section.id)
            logger.info(
                "  Section '%s': %d pages", section.display_name, len(section.pages)
            )

        notebook.section_groups = self.list_section_groups(notebook.id)
        for sg in notebook.section_groups:
            self._enumerate_section_group(sg)

        return notebook

    def _enumerate_section_group(self, group: SectionGroup):
        """Recursively enumerate sections and nested groups."""
        logger.info("  Section group: %s", group.display_name)

        group.sections = self.list_sections_in_group(group.id)
        for section in group.sections:
            section.pages = self.list_pages(section.id)
            logger.info(
                "    Section '%s': %d pages", section.display_name, len(section.pages)
            )

        group.section_groups = self.list_section_groups_in_group(group.id)
        for nested_sg in group.section_groups:
            self._enumerate_section_group(nested_sg)
