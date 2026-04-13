"""Tests for OneNote API operations (notebooks, sections, pages, resources)."""

from unittest.mock import MagicMock
import pytest

from onenote_to_obsidian.onenote_api import (
    OneNoteAPI,
    Page,
    Section,
    SectionGroup,
    Notebook,
)


class TestDataclasses:
    """Test dataclass defaults and initialization."""

    def test_page_defaults(self):
        page = Page(
            id="p1",
            title="Test",
            created_time="2024-01-01T00:00:00Z",
            last_modified_time="2024-01-02T00:00:00Z",
            content_url="http://example.com",
        )
        assert page.order == 0

    def test_page_with_order(self):
        page = Page(
            id="p1",
            title="Test",
            created_time="2024-01-01T00:00:00Z",
            last_modified_time="2024-01-02T00:00:00Z",
            content_url="http://example.com",
            order=5,
        )
        assert page.order == 5

    def test_section_empty_pages_list(self):
        section = Section(id="s1", display_name="Test Section")
        assert section.pages == []

    def test_section_with_pages(self):
        page = Page(
            id="p1",
            title="Test",
            created_time="2024-01-01T00:00:00Z",
            last_modified_time="2024-01-02T00:00:00Z",
            content_url="http://example.com",
        )
        section = Section(id="s1", display_name="Test Section", pages=[page])
        assert len(section.pages) == 1
        assert section.pages[0].id == "p1"

    def test_section_group_empty_defaults(self):
        group = SectionGroup(id="sg1", display_name="Test Group")
        assert group.sections == []
        assert group.section_groups == []

    def test_section_group_with_sections(self):
        section = Section(id="s1", display_name="Test Section")
        group = SectionGroup(id="sg1", display_name="Test Group", sections=[section])
        assert len(group.sections) == 1
        assert group.sections[0].id == "s1"

    def test_section_group_with_nested_groups(self):
        nested_group = SectionGroup(id="sg2", display_name="Nested Group")
        group = SectionGroup(
            id="sg1", display_name="Parent Group", section_groups=[nested_group]
        )
        assert len(group.section_groups) == 1
        assert group.section_groups[0].id == "sg2"

    def test_notebook_empty_defaults(self):
        notebook = Notebook(id="nb1", display_name="Test Notebook")
        assert notebook.sections == []
        assert notebook.section_groups == []

    def test_notebook_with_sections_and_groups(self):
        section = Section(id="s1", display_name="Test Section")
        group = SectionGroup(id="sg1", display_name="Test Group")
        notebook = Notebook(
            id="nb1",
            display_name="Test Notebook",
            sections=[section],
            section_groups=[group],
        )
        assert len(notebook.sections) == 1
        assert len(notebook.section_groups) == 1


class TestOneNoteAPI:
    """Test OneNoteAPI methods."""

    @pytest.fixture
    def mock_client(self):
        """Mock GraphClient."""
        return MagicMock()

    @pytest.fixture
    def api(self, mock_client):
        """OneNoteAPI instance with mocked client."""
        return OneNoteAPI(mock_client)

    # =========================================================================
    # list_notebooks tests
    # =========================================================================

    def test_list_notebooks_parses_json(self, api, mock_client):
        """list_notebooks parses id and displayName from JSON."""
        mock_client.get_json_all.return_value = [
            {"id": "nb1", "displayName": "Notebook 1"},
            {"id": "nb2", "displayName": "Notebook 2"},
        ]

        result = api.list_notebooks()

        assert len(result) == 2
        assert result[0].id == "nb1"
        assert result[0].display_name == "Notebook 1"
        assert result[1].id == "nb2"
        assert result[1].display_name == "Notebook 2"

    def test_list_notebooks_empty_list(self, api, mock_client):
        """list_notebooks returns empty list when no notebooks."""
        mock_client.get_json_all.return_value = []

        result = api.list_notebooks()

        assert result == []

    def test_list_notebooks_calls_correct_endpoint(self, api, mock_client):
        """list_notebooks calls the correct Graph API endpoint."""
        mock_client.get_json_all.return_value = []

        api.list_notebooks()

        mock_client.get_json_all.assert_called_once_with("/me/onenote/notebooks")

    def test_list_notebooks_preserves_order(self, api, mock_client):
        """list_notebooks preserves order from API response."""
        mock_client.get_json_all.return_value = [
            {"id": "nb-z", "displayName": "Z Notebook"},
            {"id": "nb-a", "displayName": "A Notebook"},
            {"id": "nb-m", "displayName": "M Notebook"},
        ]

        result = api.list_notebooks()

        assert result[0].id == "nb-z"
        assert result[1].id == "nb-a"
        assert result[2].id == "nb-m"

    # =========================================================================
    # list_sections tests
    # =========================================================================

    def test_list_sections_correct_endpoint(self, api, mock_client):
        """list_sections calls endpoint with correct notebook_id."""
        mock_client.get_json_all.return_value = [
            {"id": "s1", "displayName": "Section 1"}
        ]

        api.list_sections("nb-123")

        mock_client.get_json_all.assert_called_once_with(
            "/me/onenote/notebooks/nb-123/sections"
        )

    def test_list_sections_parses_response(self, api, mock_client):
        """list_sections parses id and displayName."""
        mock_client.get_json_all.return_value = [
            {"id": "s1", "displayName": "Section 1"},
            {"id": "s2", "displayName": "Section 2"},
        ]

        result = api.list_sections("nb-123")

        assert len(result) == 2
        assert result[0].id == "s1"
        assert result[0].display_name == "Section 1"

    def test_list_sections_empty(self, api, mock_client):
        """list_sections returns empty list when no sections."""
        mock_client.get_json_all.return_value = []

        result = api.list_sections("nb-123")

        assert result == []

    # =========================================================================
    # list_section_groups tests
    # =========================================================================

    def test_list_section_groups_correct_endpoint(self, api, mock_client):
        """list_section_groups calls endpoint with correct notebook_id."""
        mock_client.get_json_all.return_value = [
            {"id": "sg1", "displayName": "Group 1"}
        ]

        api.list_section_groups("nb-123")

        mock_client.get_json_all.assert_called_once_with(
            "/me/onenote/notebooks/nb-123/sectionGroups"
        )

    def test_list_section_groups_parses_response(self, api, mock_client):
        """list_section_groups parses id and displayName."""
        mock_client.get_json_all.return_value = [
            {"id": "sg1", "displayName": "Group 1"},
            {"id": "sg2", "displayName": "Group 2"},
        ]

        result = api.list_section_groups("nb-123")

        assert len(result) == 2
        assert result[0].id == "sg1"
        assert result[0].display_name == "Group 1"

    def test_list_section_groups_empty(self, api, mock_client):
        """list_section_groups returns empty list when no groups."""
        mock_client.get_json_all.return_value = []

        result = api.list_section_groups("nb-123")

        assert result == []

    # =========================================================================
    # list_sections_in_group tests
    # =========================================================================

    def test_list_sections_in_group_correct_endpoint(self, api, mock_client):
        """list_sections_in_group calls endpoint with correct group_id."""
        mock_client.get_json_all.return_value = [
            {"id": "s1", "displayName": "Section 1"}
        ]

        api.list_sections_in_group("sg-123")

        mock_client.get_json_all.assert_called_once_with(
            "/me/onenote/sectionGroups/sg-123/sections"
        )

    # =========================================================================
    # list_section_groups_in_group tests
    # =========================================================================

    def test_list_section_groups_in_group_correct_endpoint(self, api, mock_client):
        """list_section_groups_in_group calls endpoint with correct group_id."""
        mock_client.get_json_all.return_value = [
            {"id": "sg2", "displayName": "Nested Group"}
        ]

        api.list_section_groups_in_group("sg-123")

        mock_client.get_json_all.assert_called_once_with(
            "/me/onenote/sectionGroups/sg-123/sectionGroups"
        )

    # =========================================================================
    # list_pages tests
    # =========================================================================

    def test_list_pages_parses_all_fields(self, api, mock_client):
        """list_pages parses id, title, created/modified times, contentUrl."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "Page 1",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-06-01T14:00:00Z",
                "contentUrl": "https://graph.microsoft.com/v1.0/me/onenote/pages/p1/content",
            }
        ]

        result = api.list_pages("s-123")

        assert len(result) == 1
        page = result[0]
        assert page.id == "p1"
        assert page.title == "Page 1"
        assert page.created_time == "2024-01-01T10:00:00Z"
        assert page.last_modified_time == "2024-06-01T14:00:00Z"
        assert page.content_url == "https://graph.microsoft.com/v1.0/me/onenote/pages/p1/content"

    def test_list_pages_title_none_becomes_untitled(self, api, mock_client):
        """list_pages converts None title to 'Untitled'."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": None,
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].title == "Untitled"

    def test_list_pages_missing_title_becomes_untitled(self, api, mock_client):
        """list_pages converts missing title to 'Untitled'."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].title == "Untitled"

    def test_list_pages_missing_created_datetime(self, api, mock_client):
        """list_pages defaults createdDateTime to empty string."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "Page 1",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].created_time == ""

    def test_list_pages_missing_last_modified_datetime(self, api, mock_client):
        """list_pages defaults lastModifiedDateTime to empty string."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "Page 1",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].last_modified_time == ""

    def test_list_pages_missing_content_url(self, api, mock_client):
        """list_pages defaults contentUrl to empty string."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "Page 1",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].content_url == ""

    def test_list_pages_order_set_from_enumerate_index(self, api, mock_client):
        """list_pages sets order from enumerate index."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "First",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            },
            {
                "id": "p2",
                "title": "Second",
                "createdDateTime": "2024-01-02T10:00:00Z",
                "lastModifiedDateTime": "2024-01-02T10:00:00Z",
                "contentUrl": "",
            },
            {
                "id": "p3",
                "title": "Third",
                "createdDateTime": "2024-01-03T10:00:00Z",
                "lastModifiedDateTime": "2024-01-03T10:00:00Z",
                "contentUrl": "",
            },
        ]

        result = api.list_pages("s-123")

        assert result[0].order == 0
        assert result[1].order == 1
        assert result[2].order == 2

    def test_list_pages_correct_endpoint(self, api, mock_client):
        """list_pages calls correct endpoint with section_id."""
        mock_client.get_json_all.return_value = []

        api.list_pages("s-456")

        mock_client.get_json_all.assert_called_once_with(
            "/me/onenote/sections/s-456/pages"
        )

    def test_list_pages_empty(self, api, mock_client):
        """list_pages returns empty list when no pages."""
        mock_client.get_json_all.return_value = []

        result = api.list_pages("s-123")

        assert result == []

    # =========================================================================
    # get_page_content tests
    # =========================================================================

    def test_get_page_content_correct_endpoint(self, api, mock_client):
        """get_page_content calls get_text with correct URL."""
        mock_client.get_text.return_value = "<html>content</html>"

        api.get_page_content("p-123")

        mock_client.get_text.assert_called_once_with("/me/onenote/pages/p-123/content")

    def test_get_page_content_returns_text(self, api, mock_client):
        """get_page_content returns text from get_text."""
        html_content = "<html><body>Test page</body></html>"
        mock_client.get_text.return_value = html_content

        result = api.get_page_content("p-123")

        assert result == html_content

    def test_get_page_content_empty_content(self, api, mock_client):
        """get_page_content returns empty string for empty pages."""
        mock_client.get_text.return_value = ""

        result = api.get_page_content("p-123")

        assert result == ""

    # =========================================================================
    # get_resource tests
    # =========================================================================

    def test_get_resource_correct_endpoint(self, api, mock_client):
        """get_resource calls get_binary with correct resource URL."""
        mock_client.get_binary.return_value = b"binary_data"

        api.get_resource("https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value")

        mock_client.get_binary.assert_called_once_with(
            "https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value"
        )

    def test_get_resource_returns_binary(self, api, mock_client):
        """get_resource returns binary data from get_binary."""
        binary_data = b"\x89PNG\r\n\x1a\n"
        mock_client.get_binary.return_value = binary_data

        result = api.get_resource("https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value")

        assert result == binary_data

    # =========================================================================
    # enumerate_notebook tests
    # =========================================================================

    def test_enumerate_notebook_populates_sections_and_pages(self, api, mock_client):
        """enumerate_notebook populates sections with pages."""
        notebook = Notebook(id="nb-1", display_name="Test Notebook")

        # Mock sections
        mock_client.get_json_all.side_effect = [
            # list_sections for notebook
            [
                {"id": "s-1", "displayName": "Section 1"},
                {"id": "s-2", "displayName": "Section 2"},
            ],
            # list_pages for s-1
            [
                {
                    "id": "p-1",
                    "title": "Page 1",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_pages for s-2
            [
                {
                    "id": "p-2",
                    "title": "Page 2",
                    "createdDateTime": "2024-01-02T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-02T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups for notebook
            [],
        ]

        result = api.enumerate_notebook(notebook)

        assert result is notebook
        assert len(result.sections) == 2
        assert result.sections[0].id == "s-1"
        assert len(result.sections[0].pages) == 1
        assert result.sections[0].pages[0].id == "p-1"
        assert result.sections[1].id == "s-2"
        assert len(result.sections[1].pages) == 1
        assert result.sections[1].pages[0].id == "p-2"

    def test_enumerate_notebook_with_section_groups_recursive(self, api, mock_client):
        """enumerate_notebook recursively processes section groups."""
        notebook = Notebook(id="nb-1", display_name="Test Notebook")

        # Mock API calls in order
        mock_client.get_json_all.side_effect = [
            # list_sections for notebook
            [],
            # list_section_groups for notebook
            [{"id": "sg-1", "displayName": "Group 1"}],
            # list_sections_in_group for sg-1
            [{"id": "s-1", "displayName": "Section in Group"}],
            # list_pages for s-1
            [
                {
                    "id": "p-1",
                    "title": "Page in Group",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group for sg-1
            [],
        ]

        result = api.enumerate_notebook(notebook)

        assert len(result.section_groups) == 1
        group = result.section_groups[0]
        assert group.id == "sg-1"
        assert group.display_name == "Group 1"
        assert len(group.sections) == 1
        assert group.sections[0].id == "s-1"
        assert len(group.sections[0].pages) == 1
        assert group.sections[0].pages[0].id == "p-1"

    def test_enumerate_notebook_with_nested_section_groups(self, api, mock_client):
        """enumerate_notebook handles 2+ levels of nested section groups."""
        notebook = Notebook(id="nb-1", display_name="Test Notebook")

        # Mock API calls for nested groups
        mock_client.get_json_all.side_effect = [
            # list_sections for notebook
            [],
            # list_section_groups for notebook
            [{"id": "sg-1", "displayName": "Level 1 Group"}],
            # list_sections_in_group for sg-1
            [],
            # list_section_groups_in_group for sg-1 (has nested group)
            [{"id": "sg-2", "displayName": "Level 2 Group"}],
            # list_sections_in_group for sg-2
            [{"id": "s-1", "displayName": "Section in Level 2"}],
            # list_pages for s-1
            [
                {
                    "id": "p-1",
                    "title": "Page",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group for sg-2
            [],
        ]

        result = api.enumerate_notebook(notebook)

        assert len(result.section_groups) == 1
        level1_group = result.section_groups[0]
        assert level1_group.id == "sg-1"
        assert len(level1_group.section_groups) == 1
        level2_group = level1_group.section_groups[0]
        assert level2_group.id == "sg-2"
        assert len(level2_group.sections) == 1
        assert level2_group.sections[0].pages[0].id == "p-1"

    def test_enumerate_notebook_empty_notebook(self, api, mock_client):
        """enumerate_notebook handles notebook with no sections or groups."""
        notebook = Notebook(id="nb-1", display_name="Empty Notebook")

        mock_client.get_json_all.side_effect = [
            # list_sections
            [],
            # list_section_groups
            [],
        ]

        result = api.enumerate_notebook(notebook)

        assert result.sections == []
        assert result.section_groups == []

    def test_enumerate_notebook_preserves_notebook_metadata(self, api, mock_client):
        """enumerate_notebook preserves notebook id and display_name."""
        notebook = Notebook(id="nb-unique", display_name="My Important Notebook")

        mock_client.get_json_all.side_effect = [
            [],  # list_sections
            [],  # list_section_groups
        ]

        result = api.enumerate_notebook(notebook)

        assert result.id == "nb-unique"
        assert result.display_name == "My Important Notebook"

    def test_enumerate_notebook_returns_same_instance(self, api, mock_client):
        """enumerate_notebook returns the same notebook object passed in."""
        notebook = Notebook(id="nb-1", display_name="Test")

        mock_client.get_json_all.side_effect = [
            [],  # list_sections
            [],  # list_section_groups
        ]

        result = api.enumerate_notebook(notebook)

        assert result is notebook

    def test_enumerate_notebook_complex_structure(self, api, mock_client):
        """enumerate_notebook handles complex mixed structure."""
        notebook = Notebook(id="nb-1", display_name="Complex Notebook")

        mock_client.get_json_all.side_effect = [
            # list_sections for notebook
            [
                {"id": "s-1", "displayName": "Regular Section"},
                {"id": "s-2", "displayName": "Another Section"},
            ],
            # list_pages for s-1
            [
                {
                    "id": "p-1",
                    "title": "Page 1",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                },
                {
                    "id": "p-2",
                    "title": "Page 2",
                    "createdDateTime": "2024-01-02T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-02T10:00:00Z",
                    "contentUrl": "",
                },
            ],
            # list_pages for s-2
            [
                {
                    "id": "p-3",
                    "title": "Page 3",
                    "createdDateTime": "2024-01-03T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-03T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups for notebook
            [{"id": "sg-1", "displayName": "Group 1"}],
            # list_sections_in_group for sg-1
            [{"id": "s-3", "displayName": "Section in Group"}],
            # list_pages for s-3
            [
                {
                    "id": "p-4",
                    "title": "Page in Group",
                    "createdDateTime": "2024-01-04T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-04T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group for sg-1
            [],
        ]

        result = api.enumerate_notebook(notebook)

        # Verify sections
        assert len(result.sections) == 2
        assert len(result.sections[0].pages) == 2
        assert len(result.sections[1].pages) == 1

        # Verify section groups
        assert len(result.section_groups) == 1
        assert len(result.section_groups[0].sections) == 1
        assert len(result.section_groups[0].sections[0].pages) == 1

    def test_enumerate_section_group_private_method(self, api, mock_client):
        """_enumerate_section_group correctly processes a single group."""
        group = SectionGroup(id="sg-1", display_name="Test Group")

        mock_client.get_json_all.side_effect = [
            # list_sections_in_group
            [{"id": "s-1", "displayName": "Section"}],
            # list_pages
            [
                {
                    "id": "p-1",
                    "title": "Page",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group
            [],
        ]

        api._enumerate_section_group(group)

        assert len(group.sections) == 1
        assert len(group.sections[0].pages) == 1
        assert group.section_groups == []

    def test_list_pages_with_optional_empty_string_fields(self, api, mock_client):
        """list_pages handles optional fields that exist but are empty strings."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "Page",
                "createdDateTime": "",
                "lastModifiedDateTime": "",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].created_time == ""
        assert result[0].last_modified_time == ""
        assert result[0].content_url == ""

    def test_list_pages_empty_string_title_becomes_untitled(self, api, mock_client):
        """list_pages converts empty string title to 'Untitled'."""
        mock_client.get_json_all.return_value = [
            {
                "id": "p1",
                "title": "",
                "createdDateTime": "2024-01-01T10:00:00Z",
                "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                "contentUrl": "",
            }
        ]

        result = api.list_pages("s-123")

        assert result[0].title == "Untitled"

    def test_enumerate_notebook_with_multiple_nested_groups(self, api, mock_client):
        """enumerate_notebook handles multiple groups at same level."""
        notebook = Notebook(id="nb-1", display_name="Test")

        mock_client.get_json_all.side_effect = [
            # list_sections
            [],
            # list_section_groups - 2 groups at same level
            [
                {"id": "sg-1", "displayName": "Group 1"},
                {"id": "sg-2", "displayName": "Group 2"},
            ],
            # list_sections_in_group for sg-1
            [{"id": "s-1", "displayName": "Section 1"}],
            # list_pages for s-1
            [
                {
                    "id": "p-1",
                    "title": "Page 1",
                    "createdDateTime": "2024-01-01T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-01T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group for sg-1
            [],
            # list_sections_in_group for sg-2
            [{"id": "s-2", "displayName": "Section 2"}],
            # list_pages for s-2
            [
                {
                    "id": "p-2",
                    "title": "Page 2",
                    "createdDateTime": "2024-01-02T10:00:00Z",
                    "lastModifiedDateTime": "2024-01-02T10:00:00Z",
                    "contentUrl": "",
                }
            ],
            # list_section_groups_in_group for sg-2
            [],
        ]

        result = api.enumerate_notebook(notebook)

        assert len(result.section_groups) == 2
        assert result.section_groups[0].id == "sg-1"
        assert result.section_groups[1].id == "sg-2"
        assert len(result.section_groups[0].sections) == 1
        assert len(result.section_groups[1].sections) == 1
