"""Tests for CLI entry point (__main__.py)."""

from unittest.mock import MagicMock, patch

import pytest

from onenote_to_obsidian.__main__ import main
from onenote_to_obsidian.config import Config
from onenote_to_obsidian.graph_client import GraphAPIError
from onenote_to_obsidian.onenote_api import Notebook, Page, Section


class TestCLIHelp:
    def test_help_exits_zero(self, capsys):
        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian", "--help"]):
                main()
        assert exc_info.value.code == 0

    def test_help_shows_options(self, capsys):
        with pytest.raises(SystemExit):
            with patch("sys.argv", ["onenote_to_obsidian", "--help"]):
                main()
        captured = capsys.readouterr()
        assert "--vault" in captured.out
        assert "--notebook" in captured.out
        assert "--list" in captured.out
        assert "--setup" in captured.out
        assert "--reset-state" in captured.out
        assert "--verbose" in captured.out


class TestCLISetup:
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_setup_mode(self, mock_setup, capsys):
        mock_setup.return_value = Config()
        with patch("sys.argv", ["onenote_to_obsidian", "--setup"]):
            main()
        mock_setup.assert_called_once()
        assert mock_setup.call_args.kwargs["force_setup"] is True

    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_setup_prints_message_and_returns(self, mock_setup, capsys):
        mock_setup.return_value = Config()
        with patch("sys.argv", ["onenote_to_obsidian", "--setup"]):
            main()
        captured = capsys.readouterr()
        # Should print setup complete message (currently in Russian)
        assert len(captured.out) > 0


class TestCLIResetState:
    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_reset_state(self, mock_setup, mock_exporter, tmp_path, capsys):
        config = Config(config_dir=str(tmp_path / "config"))
        mock_setup.return_value = config

        with patch("sys.argv", ["onenote_to_obsidian", "--reset-state"]):
            main()

        captured = capsys.readouterr()
        # Should mention reset
        assert len(captured.out) > 0


class TestCLIList:
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_list_notebooks(self, mock_setup, capsys):
        config = Config()
        mock_setup.return_value = config

        mock_api = MagicMock()
        page = Page(
            id="p1", title="Page", created_time="", last_modified_time="",
            content_url="", order=0,
        )
        section = Section(id="s1", display_name="Section A", pages=[page])
        notebook = Notebook(
            id="nb1", display_name="My Notebook",
            sections=[section], section_groups=[],
        )
        mock_api.list_notebooks.return_value = [notebook]
        mock_api.enumerate_notebook.return_value = notebook

        with patch("sys.argv", ["onenote_to_obsidian", "--list"]), \
             patch("onenote_to_obsidian.auth.AuthManager"), \
             patch("onenote_to_obsidian.graph_client.GraphClient"), \
             patch("onenote_to_obsidian.onenote_api.OneNoteAPI", return_value=mock_api):
            main()

        captured = capsys.readouterr()
        assert "My Notebook" in captured.out
        assert "Section A" in captured.out

    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_list_empty(self, mock_setup, capsys):
        config = Config()
        mock_setup.return_value = config

        mock_api = MagicMock()
        mock_api.list_notebooks.return_value = []

        with patch("sys.argv", ["onenote_to_obsidian", "--list"]), \
             patch("onenote_to_obsidian.auth.AuthManager"), \
             patch("onenote_to_obsidian.graph_client.GraphClient"), \
             patch("onenote_to_obsidian.onenote_api.OneNoteAPI", return_value=mock_api):
            main()

        captured = capsys.readouterr()
        # Should indicate no notebooks found
        assert len(captured.out) > 0


class TestCLIExport:
    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_default_export_all(self, mock_setup, mock_exporter_cls):
        config = Config()
        mock_setup.return_value = config
        mock_exporter = mock_exporter_cls.return_value

        with patch("sys.argv", ["onenote_to_obsidian"]):
            main()

        mock_exporter.export_all.assert_called_once_with(notebook_filter=None)

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_export_specific_notebook(self, mock_setup, mock_exporter_cls):
        config = Config()
        mock_setup.return_value = config
        mock_exporter = mock_exporter_cls.return_value

        with patch("sys.argv", ["onenote_to_obsidian", "--notebook", "My NB"]):
            main()

        mock_exporter.export_all.assert_called_once_with(notebook_filter="My NB")

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_vault_path_passed(self, mock_setup, mock_exporter_cls):
        config = Config()
        mock_setup.return_value = config

        with patch("sys.argv", ["onenote_to_obsidian", "--vault", "/custom/vault"]):
            main()

        # Vault path should be passed to load_or_setup
        call_kwargs = mock_setup.call_args
        assert call_kwargs.kwargs.get("vault_path") == "/custom/vault"


class TestCLIVerbose:
    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_verbose_sets_debug(self, mock_setup, mock_exporter_cls):
        import logging
        config = Config()
        mock_setup.return_value = config

        # Reset root logger handlers so basicConfig takes effect
        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)

        with patch("sys.argv", ["onenote_to_obsidian", "-v"]):
            main()

        assert root.level == logging.DEBUG

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_default_log_level_warning(self, mock_setup, mock_exporter_cls):
        import logging
        config = Config()
        mock_setup.return_value = config

        root = logging.getLogger()
        for h in root.handlers[:]:
            root.removeHandler(h)

        with patch("sys.argv", ["onenote_to_obsidian"]):
            main()

        assert root.level == logging.WARNING


class TestCLIErrorHandling:
    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_keyboard_interrupt_exits_130(self, mock_setup, mock_exporter_cls, capsys):
        mock_setup.return_value = Config()
        mock_exporter_cls.return_value.export_all.side_effect = KeyboardInterrupt

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian"]):
                main()
        assert exc_info.value.code == 130
        assert "cancelled" in capsys.readouterr().out.lower()

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_graph_api_error_exits_1(self, mock_setup, mock_exporter_cls, capsys):
        mock_setup.return_value = Config()
        mock_exporter_cls.return_value.export_all.side_effect = GraphAPIError(
            403, "Access denied"
        )

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr().out
        assert "API error" in captured
        assert "--verbose" in captured

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_os_error_exits_1(self, mock_setup, mock_exporter_cls, capsys):
        mock_setup.return_value = Config()
        mock_exporter_cls.return_value.export_all.side_effect = PermissionError(
            "Permission denied: /vault"
        )

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian"]):
                main()
        assert exc_info.value.code == 1
        assert "File system error" in capsys.readouterr().out

    @patch("onenote_to_obsidian.__main__.OneNoteExporter")
    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_unexpected_error_exits_1(self, mock_setup, mock_exporter_cls, capsys):
        mock_setup.return_value = Config()
        mock_exporter_cls.return_value.export_all.side_effect = RuntimeError("something broke")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian"]):
                main()
        assert exc_info.value.code == 1
        captured = capsys.readouterr().out
        assert "Unexpected error" in captured
        assert "--verbose" in captured

    @patch("onenote_to_obsidian.__main__.Config.load_or_setup")
    def test_list_mode_api_error(self, mock_setup, capsys):
        mock_setup.return_value = Config()
        mock_api = MagicMock()
        mock_api.list_notebooks.side_effect = GraphAPIError(401, "Unauthorized")

        with pytest.raises(SystemExit) as exc_info:
            with patch("sys.argv", ["onenote_to_obsidian", "--list"]), \
                 patch("onenote_to_obsidian.auth.AuthManager"), \
                 patch("onenote_to_obsidian.graph_client.GraphClient"), \
                 patch("onenote_to_obsidian.onenote_api.OneNoteAPI", return_value=mock_api):
                main()
        assert exc_info.value.code == 1
        assert "API error" in capsys.readouterr().out
