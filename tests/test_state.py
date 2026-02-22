"""Tests for export state tracking."""

import json

from onenote_to_obsidian.state import ExportState


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
