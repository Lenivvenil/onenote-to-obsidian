"""Integration tests for the main export orchestrator."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch, call

import pytest

from onenote_to_obsidian.config import Config
from onenote_to_obsidian.exporter import OneNoteExporter
from onenote_to_obsidian.graph_client import GraphAPIError
from onenote_to_obsidian.onenote_api import Notebook, Section, SectionGroup, Page
from onenote_to_obsidian.resource_downloader import DownloadResult


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------

def make_page(id="page-001", title="Test Page", modified="2024-06-20T14:22:00Z"):
    return Page(
        id=id,
        title=title,
        created_time="2024-01-15T10:30:00Z",
        last_modified_time=modified,
        content_url="",
        order=0,
    )


def make_section(id="section-001", name="Test Section", pages=None):
    return Section(id=id, display_name=name, pages=pages or [])


def make_notebook(id="nb-001", name="Test Notebook", sections=None, groups=None):
    return Notebook(
        id=id,
        display_name=name,
        sections=sections or [],
        section_groups=groups or [],
    )


SIMPLE_HTML = "<html><body><p>Hello World</p></body></html>"


@pytest.fixture
def exporter_with_mocks(tmp_path):
    """Create OneNoteExporter with all external dependencies mocked."""
    config = Config(
        client_id="test-id",
        vault_path=str(tmp_path / "vault"),
        config_dir=str(tmp_path / "config"),
    )
    (tmp_path / "config").mkdir(parents=True, exist_ok=True)

    with patch("onenote_to_obsidian.exporter.AuthManager") as MockAuth, \
         patch("onenote_to_obsidian.exporter.GraphClient") as MockClient, \
         patch("onenote_to_obsidian.exporter.OneNoteAPI") as MockAPI, \
         patch("onenote_to_obsidian.exporter.ResourceDownloader") as MockDownloader:

        mock_api = MockAPI.return_value
        mock_downloader = MockDownloader.return_value
        mock_downloader.download_resources.return_value = DownloadResult(resource_map={})
        mock_api.get_page_content.return_value = SIMPLE_HTML

        exporter = OneNoteExporter(config)

        yield exporter, mock_api, mock_downloader, tmp_path


class TestExportAll:
    def test_single_page_export(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks
        vault = tmp_path / "vault"

        page = make_page()
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        # Verify directory structure
        nb_dir = vault / "Test Notebook"
        sec_dir = nb_dir / "Test Section"
        assert sec_dir.exists()

        # Verify .md file created
        md_file = sec_dir / "Test Page.md"
        assert md_file.exists()
        content = md_file.read_text()
        assert "Hello World" in content

    def test_frontmatter_generated(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page()
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        md_file = tmp_path / "vault" / "Test Notebook" / "Test Section" / "Test Page.md"
        content = md_file.read_text()
        assert "---" in content
        assert 'created: "2024-01-15T10:30:00Z"' in content
        assert 'modified: "2024-06-20T14:22:00Z"' in content
        assert "source: onenote" in content
        assert 'onenote_id: "page-001"' in content

    def test_multiple_pages_exported(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        pages = [make_page(id=f"p{i}", title=f"Page {i}") for i in range(3)]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        sec_dir = tmp_path / "vault" / "Test Notebook" / "Test Section"
        for i in range(3):
            assert (sec_dir / f"Page {i}.md").exists()

    def test_duplicate_page_titles_deduplicated(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        pages = [
            make_page(id="p1", title="Same Title", modified="2024-01-01T00:00:00Z"),
            make_page(id="p2", title="Same Title", modified="2024-01-02T00:00:00Z"),
        ]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        sec_dir = tmp_path / "vault" / "Test Notebook" / "Test Section"
        assert (sec_dir / "Same Title.md").exists()
        assert (sec_dir / "Same Title_1.md").exists()

    def test_section_groups_nested_dirs(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page(id="pg-nested", title="Nested Page")
        nested_section = make_section(id="s-nested", name="Nested Section", pages=[page])
        group = SectionGroup(
            id="sg-001",
            display_name="My Group",
            sections=[nested_section],
            section_groups=[],
        )
        notebook = make_notebook(sections=[], groups=[group])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        nested_dir = tmp_path / "vault" / "Test Notebook" / "My Group" / "Nested Section"
        assert nested_dir.exists()
        assert (nested_dir / "Nested Page.md").exists()

    def test_deeply_nested_section_groups(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page(id="pg-deep", title="Deep Page")
        inner_section = make_section(id="s-inner", name="Inner", pages=[page])
        inner_group = SectionGroup(
            id="sg-inner", display_name="Inner Group",
            sections=[inner_section], section_groups=[],
        )
        outer_group = SectionGroup(
            id="sg-outer", display_name="Outer Group",
            sections=[], section_groups=[inner_group],
        )
        notebook = make_notebook(sections=[], groups=[outer_group])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        deep_dir = tmp_path / "vault" / "Test Notebook" / "Outer Group" / "Inner Group" / "Inner"
        assert (deep_dir / "Deep Page.md").exists()


class TestExportFiltering:
    def test_notebook_filter_matches(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page()
        section = make_section(pages=[page])
        nb1 = make_notebook(id="nb1", name="Target", sections=[section])
        nb2 = make_notebook(id="nb2", name="Other", sections=[])
        mock_api.list_notebooks.return_value = [nb1, nb2]
        mock_api.enumerate_notebook.return_value = nb1

        exporter.export_all(notebook_filter="Target")

        assert (tmp_path / "vault" / "Target").exists()
        assert not (tmp_path / "vault" / "Other").exists()

    def test_notebook_filter_case_insensitive(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page()
        section = make_section(pages=[page])
        nb = make_notebook(name="My Notebook", sections=[section])
        mock_api.list_notebooks.return_value = [nb]
        mock_api.enumerate_notebook.return_value = nb

        exporter.export_all(notebook_filter="my notebook")

        assert (tmp_path / "vault" / "My Notebook").exists()

    def test_notebook_filter_no_match(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        nb = make_notebook(name="Existing")
        mock_api.list_notebooks.return_value = [nb]
        # Also mock the second call for showing available notebooks
        mock_api.list_notebooks.return_value = [nb]

        exporter.export_all(notebook_filter="NonExistent")

        # No directories created
        assert not (tmp_path / "vault" / "NonExistent").exists()


class TestExportResume:
    def test_skips_unchanged_pages(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page(id="p1", modified="2024-06-01T00:00:00Z")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        # First export
        exporter.export_all()
        assert mock_api.get_page_content.call_count == 1

        # Reset call count, export again
        mock_api.get_page_content.reset_mock()
        exporter._stats = {
            "exported": 0, "skipped": 0, "errors": 0, "failed_resources": 0, "total": 0
        }
        exporter.export_all()

        # Should skip — page unchanged
        mock_api.get_page_content.assert_not_called()
        assert exporter._stats["skipped"] == 1

    def test_reexports_modified_page(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        page = make_page(id="p1", modified="2024-06-01T00:00:00Z")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        # First export
        exporter.export_all()

        # Change modification time
        page.last_modified_time = "2024-07-01T00:00:00Z"
        mock_api.get_page_content.reset_mock()
        exporter._stats = {
            "exported": 0, "skipped": 0, "errors": 0, "failed_resources": 0, "total": 0
        }

        exporter.export_all()

        # Should re-export — page modified
        mock_api.get_page_content.assert_called_once()
        assert exporter._stats["exported"] == 1


class TestExportErrorHandling:
    def test_graph_error_continues(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        pages = [
            make_page(id="p1", title="Fails"),
            make_page(id="p2", title="Succeeds"),
        ]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        # First page fails, second succeeds
        mock_api.get_page_content.side_effect = [
            GraphAPIError(500, "Server error"),
            SIMPLE_HTML,
        ]

        exporter.export_all()

        assert exporter._stats["errors"] == 1
        assert exporter._stats["exported"] == 1
        # Second page file should exist
        sec_dir = tmp_path / "vault" / "Test Notebook" / "Test Section"
        assert (sec_dir / "Succeeds.md").exists()

    def test_generic_error_continues(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        pages = [
            make_page(id="p1", title="Error Page"),
            make_page(id="p2", title="Good Page"),
        ]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        mock_api.get_page_content.side_effect = [
            ValueError("Unexpected error"),
            SIMPLE_HTML,
        ]

        exporter.export_all()

        assert exporter._stats["errors"] == 1
        assert exporter._stats["exported"] == 1


class TestExportStats:
    def test_stats_correct_counts(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        pages = [make_page(id=f"p{i}", title=f"Page {i}") for i in range(5)]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        assert exporter._stats["exported"] == 5
        assert exporter._stats["skipped"] == 0
        assert exporter._stats["errors"] == 0
        assert exporter._stats["total"] == 5

    def test_empty_notebook(self, exporter_with_mocks):
        exporter, mock_api, _, tmp_path = exporter_with_mocks

        notebook = make_notebook(sections=[], groups=[])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        exporter.export_all()

        assert exporter._stats["total"] == 0
        assert exporter._stats["exported"] == 0


class TestBuildFrontmatter:
    def test_frontmatter_format(self, exporter_with_mocks):
        exporter, _, _, _ = exporter_with_mocks
        page = make_page()
        fm = exporter._build_frontmatter(page)

        lines = fm.strip().split("\n")
        assert lines[0] == "---"
        assert lines[-1] == "---"
        assert any("created:" in l for l in lines)
        assert any("modified:" in l for l in lines)
        assert any("source: onenote" in l for l in lines)
        assert any('onenote_id: "page-001"' in l for l in lines)

    def test_frontmatter_missing_created(self, exporter_with_mocks):
        exporter, _, _, _ = exporter_with_mocks
        page = make_page()
        page.created_time = ""  # Empty
        fm = exporter._build_frontmatter(page)
        assert "created:" not in fm

    def test_frontmatter_missing_modified(self, exporter_with_mocks):
        exporter, _, _, _ = exporter_with_mocks
        page = make_page()
        page.last_modified_time = ""  # Empty
        fm = exporter._build_frontmatter(page)
        assert "modified:" not in fm


class TestCountHelpers:
    def test_count_pages(self):
        pages = [make_page(id=f"p{i}") for i in range(3)]
        section = make_section(pages=pages)
        notebook = make_notebook(sections=[section])
        assert OneNoteExporter._count_pages(notebook) == 3

    def test_count_pages_with_groups(self):
        page1 = make_page(id="p1")
        page2 = make_page(id="p2")
        section1 = make_section(id="s1", pages=[page1])
        section2 = make_section(id="s2", pages=[page2])
        group = SectionGroup(
            id="sg1", display_name="G",
            sections=[section2], section_groups=[],
        )
        notebook = make_notebook(sections=[section1], groups=[group])
        assert OneNoteExporter._count_pages(notebook) == 2

    def test_count_sections(self):
        section1 = make_section(id="s1")
        section2 = make_section(id="s2")
        group = SectionGroup(
            id="sg1", display_name="G",
            sections=[section2], section_groups=[],
        )
        notebook = make_notebook(sections=[section1], groups=[group])
        assert OneNoteExporter._count_sections(notebook) == 2


class TestFailedResources:
    """Tests for partial resource failure tracking and retry."""

    def test_partial_resource_failure_not_marked_exported(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        page = make_page(id="p1", title="Partial Fail Page")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        url = "https://graph.example.com/res/img/$value"
        mock_api.get_page_content.return_value = SIMPLE_HTML
        mock_downloader.download_resources.return_value = DownloadResult(
            resource_map={url: "img.png"},
            failed_resources=[{"url": url, "filename": "img.png", "media_type": "image/png"}],
        )

        exporter.export_all()

        assert exporter._stats["exported"] == 0
        assert exporter._stats["failed_resources"] == 1
        assert not exporter._state.is_exported("p1", page.last_modified_time)

    def test_partial_failure_recorded_in_failed_state(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        page = make_page(id="p1", title="Page With Broken Image")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        url = "https://graph.example.com/res/img/$value"
        mock_downloader.download_resources.return_value = DownloadResult(
            resource_map={url: "img.png"},
            failed_resources=[{"url": url, "filename": "img.png", "media_type": "image/png"}],
        )
        exporter.export_all()

        failed_pages = exporter._failed_state.pages()
        assert "p1" in failed_pages
        resources = failed_pages["p1"]["resources"]
        assert len(resources) == 1
        assert resources[0]["url"] == url
        assert resources[0]["filename"] == "img.png"
        assert resources[0]["media_type"] == "image/png"

    def test_all_resources_succeed_marks_exported(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        page = make_page(id="p1")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        url = "https://graph.example.com/res/img/$value"
        mock_downloader.download_resources.return_value = DownloadResult(
            resource_map={url: "img.png"},
            failed_resources=[],
        )

        exporter.export_all()

        assert exporter._stats["exported"] == 1
        assert exporter._stats["failed_resources"] == 0
        assert exporter._state.is_exported("p1", page.last_modified_time)

    def test_stale_failed_state_cleared_on_reexport(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        page = make_page(id="p1", modified="2024-06-01T00:00:00Z")
        section = make_section(pages=[page])
        notebook = make_notebook(sections=[section])
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        # Seed stale failed state for this page
        exporter._failed_state.mark_failed(
            "p1", "Old Title", "2024-05-01T00:00:00Z",
            "NB/Sec/attachments",
            [{"url": "https://old.example.com/img", "filename": "old.png",
              "media_type": "image/png"}],
        )

        exporter.export_all()

        # After fresh export succeeds, stale entry should be gone
        assert "p1" not in exporter._failed_state.pages()
        assert exporter._state.is_exported("p1", page.last_modified_time)

    def test_retry_empty_state_prints_nothing_to_retry(self, exporter_with_mocks, capsys):
        exporter, _, _, _ = exporter_with_mocks

        exporter.retry_failed_resources()

        out = capsys.readouterr().out
        assert "No failed resources recorded" in out

    def test_retry_recovers_page(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        url = "https://graph.example.com/res/img/$value"
        exporter._failed_state.mark_failed(
            "p1", "My Page", "2024-06-20T00:00:00Z",
            "Test Notebook/Test Section/attachments",
            [{"url": url, "filename": "img.png", "media_type": "image/png"}],
        )
        (tmp_path / "vault" / "Test Notebook" / "Test Section" / "attachments").mkdir(
            parents=True, exist_ok=True
        )

        mock_downloader.download_resources.return_value = DownloadResult(
            resource_map={url: "img.png"},
            failed_resources=[],
        )

        exporter.retry_failed_resources()

        assert exporter._state.is_exported("p1", "2024-06-20T00:00:00Z")
        assert "p1" not in exporter._failed_state.pages()

    def test_retry_partial_failure_updates_state(self, exporter_with_mocks):
        exporter, mock_api, mock_downloader, tmp_path = exporter_with_mocks

        url1 = "https://graph.example.com/res/ok/$value"
        url2 = "https://graph.example.com/res/fail/$value"
        exporter._failed_state.mark_failed(
            "p1", "My Page", "2024-06-20T00:00:00Z",
            "Test Notebook/Test Section/attachments",
            [
                {"url": url1, "filename": "ok.png", "media_type": "image/png"},
                {"url": url2, "filename": "fail.png", "media_type": "image/png"},
            ],
        )
        (tmp_path / "vault" / "Test Notebook" / "Test Section" / "attachments").mkdir(
            parents=True, exist_ok=True
        )

        mock_downloader.download_resources.return_value = DownloadResult(
            resource_map={url1: "ok.png", url2: "fail.png"},
            failed_resources=[{"url": url2, "filename": "fail.png", "media_type": "image/png"}],
        )

        exporter.retry_failed_resources()

        # Page still has one failed resource — not marked exported
        assert not exporter._state.is_exported("p1", "2024-06-20T00:00:00Z")
        remaining = exporter._failed_state.pages()["p1"]["resources"]
        assert len(remaining) == 1
        assert remaining[0]["url"] == url2
