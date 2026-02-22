"""Tests for OneNote HTML → Markdown conversion."""

from onenote_to_obsidian.html_converter import (
    extract_resource_id,
    preprocess_onenote_html,
    convert_page_html,
    _ext_from_media_type,
)


class TestExtractResourceId:
    def test_standard_url(self):
        url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-abc123/$value"
        assert extract_resource_id(url) == "0-abc123"

    def test_complex_id(self):
        url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-a1b2c3d4e5f6/$value"
        assert extract_resource_id(url) == "0-a1b2c3d4e5f6"

    def test_no_match_fallback(self):
        url = "https://example.com/images/photo.png"
        result = extract_resource_id(url)
        assert result == "photo.png"

    def test_empty_url(self):
        assert extract_resource_id("") == "resource"


class TestExtFromMediaType:
    def test_common_types(self):
        assert _ext_from_media_type("image/png") == "png"
        assert _ext_from_media_type("image/jpeg") == "jpg"
        assert _ext_from_media_type("image/gif") == "gif"
        assert _ext_from_media_type("image/webp") == "webp"

    def test_case_insensitive(self):
        assert _ext_from_media_type("IMAGE/PNG") == "png"

    def test_unknown_type_fallback(self):
        assert _ext_from_media_type("image/avif") == "avif"
        assert _ext_from_media_type("application/pdf") == "pdf"


class TestPreprocessOnenoteHtml:
    def test_extracts_image_resources(self):
        html = '<img src="https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value" data-src-type="image/png">'
        _, resources = preprocess_onenote_html(html)
        assert len(resources) == 1
        url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value"
        assert url in resources
        filename, media_type = resources[url]
        assert filename == "0-img1.png"
        assert media_type == "image/png"

    def test_prefers_fullres_src(self):
        html = (
            '<img src="https://graph.microsoft.com/v1.0/me/onenote/resources/0-low/$value" '
            'data-fullres-src="https://graph.microsoft.com/v1.0/me/onenote/resources/0-high/$value" '
            'data-fullres-src-type="image/jpeg">'
        )
        _, resources = preprocess_onenote_html(html)
        assert len(resources) == 1
        high_url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-high/$value"
        assert high_url in resources
        assert resources[high_url][0] == "0-high.jpg"

    def test_extracts_object_attachments(self):
        html = (
            '<object data="https://graph.microsoft.com/v1.0/me/onenote/resources/0-file1/$value" '
            'data-attachment="report.pdf" type="application/pdf"></object>'
        )
        _, resources = preprocess_onenote_html(html)
        assert len(resources) == 1
        url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-file1/$value"
        assert resources[url] == ("report.pdf", "application/pdf")

    def test_removes_absolute_positioning(self):
        html = '<div style="position:absolute; left:100px; top:200px; z-index:5;">text</div>'
        cleaned, _ = preprocess_onenote_html(html)
        assert "position:absolute" not in cleaned
        assert "left:" not in cleaned
        assert "top:" not in cleaned

    def test_removes_empty_spans(self):
        html = "<p>hello <span> </span> world</p>"
        cleaned, _ = preprocess_onenote_html(html)
        assert "<span>" not in cleaned

    def test_keeps_spans_with_content(self):
        html = "<p><span>important</span></p>"
        cleaned, _ = preprocess_onenote_html(html)
        assert "important" in cleaned

    def test_no_resources_in_plain_html(self):
        html = "<p>Just a paragraph</p>"
        _, resources = preprocess_onenote_html(html)
        assert resources == {}


class TestConvertPageHtml:
    def test_basic_paragraph(self):
        html = "<p>Hello world</p>"
        result = convert_page_html(html, resource_map={})
        assert "Hello world" in result

    def test_heading(self):
        html = "<h1>Title</h1>"
        result = convert_page_html(html, resource_map={})
        assert "# Title" in result

    def test_bold_and_italic(self):
        html = "<p><b>bold</b> and <i>italic</i></p>"
        result = convert_page_html(html, resource_map={})
        assert "**bold**" in result
        assert "*italic*" in result

    def test_checkbox_unchecked(self):
        html = '<p data-tag="to-do">Buy milk</p>'
        result = convert_page_html(html, resource_map={})
        assert "- [ ] Buy milk" in result

    def test_checkbox_checked(self):
        html = '<p data-tag="to-do:completed">Buy milk</p>'
        result = convert_page_html(html, resource_map={})
        assert "- [x] Buy milk" in result

    def test_image_with_resource_map(self):
        src = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value"
        html = f'<img src="{src}" alt="screenshot">'
        resource_map = {src: "0-img1.png"}
        result = convert_page_html(html, resource_map=resource_map)
        assert "![screenshot](attachments/0-img1.png)" in result

    def test_image_external_url(self):
        html = '<img src="https://example.com/photo.jpg" alt="photo">'
        result = convert_page_html(html, resource_map={})
        assert "![photo](https://example.com/photo.jpg)" in result

    def test_object_attachment(self):
        data_url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-f1/$value"
        html = f'<object data="{data_url}" data-attachment="doc.pdf"></object>'
        resource_map = {data_url: "doc.pdf"}
        result = convert_page_html(html, resource_map=resource_map)
        assert "[doc.pdf](attachments/doc.pdf)" in result

    def test_iframe_embedded(self):
        html = '<iframe data-original-src="https://youtube.com/watch?v=123"></iframe>'
        result = convert_page_html(html, resource_map={})
        assert "[Embedded content](https://youtube.com/watch?v=123)" in result

    def test_table(self):
        html = "<table><tr><th>A</th><th>B</th></tr><tr><td>1</td><td>2</td></tr></table>"
        result = convert_page_html(html, resource_map={})
        assert "A" in result
        assert "B" in result
        assert "1" in result
        assert "2" in result

    def test_link(self):
        html = '<a href="https://example.com">click here</a>'
        result = convert_page_html(html, resource_map={})
        assert "[click here](https://example.com)" in result

    def test_excessive_newlines_cleaned(self):
        html = "<p>one</p><p></p><p></p><p></p><p>two</p>"
        result = convert_page_html(html, resource_map={})
        assert "\n\n\n" not in result

    def test_custom_attachments_path(self):
        src = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-x/$value"
        html = f'<img src="{src}" alt="img">'
        resource_map = {src: "0-x.png"}
        result = convert_page_html(html, resource_map=resource_map, attachments_rel_path="files")
        assert "![img](files/0-x.png)" in result

    def test_li_checkbox_unchecked(self):
        html = '<ul><li data-tag="to-do">Task</li></ul>'
        result = convert_page_html(html, resource_map={})
        assert "- [ ] Task" in result

    def test_li_checkbox_checked(self):
        html = '<ul><li data-tag="to-do:completed">Done task</li></ul>'
        result = convert_page_html(html, resource_map={})
        assert "- [x] Done task" in result
