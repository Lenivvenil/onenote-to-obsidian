"""Tests for filesystem utilities: sanitize_filename, deduplicate_path."""

from pathlib import Path

from onenote_to_obsidian.utils import sanitize_filename, deduplicate_path


class TestSanitizeFilename:
    def test_simple_name(self):
        assert sanitize_filename("My Page") == "My Page"

    def test_illegal_chars_replaced(self):
        assert sanitize_filename('a/b\\c:d*e?"f<g>h|i') == "a_b_c_d_e__f_g_h_i"

    def test_collapses_whitespace(self):
        assert sanitize_filename("hello   world\t\ttab") == "hello world tab"

    def test_strips_leading_dots(self):
        assert sanitize_filename("..hidden") == "hidden"
        assert sanitize_filename("...a") == "a"

    def test_truncates_long_name(self):
        long_name = "a" * 300
        result = sanitize_filename(long_name)
        assert len(result) <= 200

    def test_empty_becomes_untitled(self):
        assert sanitize_filename("") == "Untitled"
        assert sanitize_filename("...") == "Untitled"

    def test_unicode_preserved(self):
        assert sanitize_filename("Привет мир") == "Привет мир"
        assert sanitize_filename("日本語テスト") == "日本語テスト"

    def test_custom_max_length(self):
        result = sanitize_filename("abcdefgh", max_length=5)
        assert result == "abcde"

    def test_only_illegal_chars(self):
        assert sanitize_filename("/:*?") == "____"


class TestDeduplicatePath:
    def test_no_conflict_returns_same(self):
        path = Path("/tmp/test/file.md")
        result = deduplicate_path(path, existing_paths=set())
        assert result == path

    def test_conflict_appends_counter(self):
        path = Path("/tmp/test/file.md")
        existing = {path}
        result = deduplicate_path(path, existing_paths=existing)
        assert result == Path("/tmp/test/file_1.md")

    def test_multiple_conflicts(self):
        path = Path("/tmp/test/file.md")
        existing = {path, Path("/tmp/test/file_1.md"), Path("/tmp/test/file_2.md")}
        result = deduplicate_path(path, existing_paths=existing)
        assert result == Path("/tmp/test/file_3.md")

    def test_preserves_extension(self):
        path = Path("/tmp/image.png")
        existing = {path}
        result = deduplicate_path(path, existing_paths=existing)
        assert result.suffix == ".png"
        assert result == Path("/tmp/image_1.png")

    def test_filesystem_check(self, tmp_path):
        existing_file = tmp_path / "page.md"
        existing_file.write_text("content")
        result = deduplicate_path(existing_file)
        assert result == tmp_path / "page_1.md"

    def test_filesystem_no_conflict(self, tmp_path):
        new_file = tmp_path / "new.md"
        result = deduplicate_path(new_file)
        assert result == new_file
