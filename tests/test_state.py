"""Tests for export state tracking."""

import json

from onenote_to_obsidian.state import ExportState, FailedResourceState


class TestExportState:
    def test_fresh_state_empty(self, tmp_path):
        state = ExportState(tmp_path / "state.json")
        assert state.count == 0

    def test_mark_and_check(self, tmp_path):
        state = ExportState(tmp_path / "state.json")
        state.mark_exported("page-1", "2024-01-01T00:00:00Z")
        assert state.is_exported("page-1", "2024-01-01T00:00:00Z")
        assert state.count == 1

    def test_modified_page_not_exported(self, tmp_path):
        state = ExportState(tmp_path / "state.json")
        state.mark_exported("page-1", "2024-01-01T00:00:00Z")
        assert not state.is_exported("page-1", "2024-06-15T12:00:00Z")

    def test_unknown_page_not_exported(self, tmp_path):
        state = ExportState(tmp_path / "state.json")
        assert not state.is_exported("unknown-page", "2024-01-01T00:00:00Z")

    def test_persistence(self, tmp_path):
        state_path = tmp_path / "state.json"
        state = ExportState(state_path)
        state.mark_exported("page-1", "2024-01-01T00:00:00Z")
        state.mark_exported("page-2", "2024-02-01T00:00:00Z")

        # Load from file again
        state2 = ExportState(state_path)
        assert state2.is_exported("page-1", "2024-01-01T00:00:00Z")
        assert state2.is_exported("page-2", "2024-02-01T00:00:00Z")
        assert state2.count == 2

    def test_clear(self, tmp_path):
        state_path = tmp_path / "state.json"
        state = ExportState(state_path)
        state.mark_exported("page-1", "2024-01-01T00:00:00Z")
        state.clear()
        assert state.count == 0
        assert not state.is_exported("page-1", "2024-01-01T00:00:00Z")
        assert not state_path.exists()

    def test_corrupted_file_handled(self, tmp_path):
        state_path = tmp_path / "state.json"
        state_path.write_text("not valid json{{{")
        state = ExportState(state_path)
        assert state.count == 0

    def test_update_existing_page(self, tmp_path):
        state = ExportState(tmp_path / "state.json")
        state.mark_exported("page-1", "2024-01-01T00:00:00Z")
        state.mark_exported("page-1", "2024-06-15T12:00:00Z")
        assert not state.is_exported("page-1", "2024-01-01T00:00:00Z")
        assert state.is_exported("page-1", "2024-06-15T12:00:00Z")
        assert state.count == 1

    def test_state_file_format(self, tmp_path):
        state_path = tmp_path / "state.json"
        state = ExportState(state_path)
        state.mark_exported("p1", "t1")
        data = json.loads(state_path.read_text())
        assert "exported_pages" in data
        assert data["exported_pages"]["p1"] == "t1"


SAMPLE_RESOURCES = [
    {"url": "https://graph.example.com/res/img/$value", "filename": "img.png",
     "media_type": "image/png"}
]

_TS = "2024-01-01T00:00:00Z"
_ADIR = "NB/S/attachments"


def _mark(state: FailedResourceState, pid: str = "page-1", title: str = "P", ts: str = _TS,
          adir: str = _ADIR, res: list | None = None) -> None:
    state.mark_failed(pid, title, ts, adir, res if res is not None else SAMPLE_RESOURCES)


class TestFailedResourceState:
    def test_fresh_state_empty(self, tmp_path):
        state = FailedResourceState(tmp_path / "failed.json")
        assert state.count == 0
        assert state.pages() == {}

    def test_mark_failed_and_load(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state = FailedResourceState(state_path)
        state.mark_failed(
            "page-1", "My Page", "2024-06-20T00:00:00Z", "NB/Sec/attachments", SAMPLE_RESOURCES
        )

        assert state.count == 1
        assert state_path.exists()

        state2 = FailedResourceState(state_path)
        assert state2.count == 1
        data = state2.pages()["page-1"]
        assert data["title"] == "My Page"
        assert data["last_modified"] == "2024-06-20T00:00:00Z"
        assert data["attachments_dir"] == "NB/Sec/attachments"
        assert data["resources"] == SAMPLE_RESOURCES

    def test_clear_page_removes_single_page(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state = FailedResourceState(state_path)
        _mark(state, "page-1", adir="NB/S1/attachments")
        _mark(state, "page-2", adir="NB/S2/attachments")

        state.clear_page("page-1")

        assert state.count == 1
        assert "page-1" not in state.pages()
        assert "page-2" in state.pages()
        assert state_path.exists()

    def test_clear_page_last_entry_removes_file(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state = FailedResourceState(state_path)
        _mark(state)

        state.clear_page("page-1")

        assert state.count == 0
        assert not state_path.exists()

    def test_clear_page_nonexistent_is_noop(self, tmp_path):
        state = FailedResourceState(tmp_path / "failed.json")
        state.clear_page("no-such-page")
        assert state.count == 0

    def test_clear_removes_all(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state = FailedResourceState(state_path)
        _mark(state, "page-1")
        _mark(state, "page-2")

        state.clear()

        assert state.count == 0
        assert not state_path.exists()

    def test_clear_on_empty_state_is_noop(self, tmp_path):
        state = FailedResourceState(tmp_path / "failed.json")
        state.clear()
        assert state.count == 0

    def test_file_format(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state = FailedResourceState(state_path)
        _mark(state, "p1", title="Title")

        data = json.loads(state_path.read_text())
        assert "failed_resources" in data
        assert "p1" in data["failed_resources"]
        assert data["failed_resources"]["p1"]["title"] == "Title"

    def test_corrupted_file_handled(self, tmp_path):
        state_path = tmp_path / "failed.json"
        state_path.write_text("not valid json{{{")
        state = FailedResourceState(state_path)
        assert state.count == 0

    def test_mark_failed_overwrites_existing_page(self, tmp_path):
        state = FailedResourceState(tmp_path / "failed.json")
        _mark(state, "page-1", title="Old Title")
        new_resources = [
            {"url": "https://example.com/new", "filename": "new.png", "media_type": "image/png"}
        ]
        _mark(state, "page-1", title="Old Title", res=new_resources)

        assert state.count == 1
        assert state.pages()["page-1"]["resources"] == new_resources
