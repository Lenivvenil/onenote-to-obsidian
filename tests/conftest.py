"""Shared pytest fixtures for onenote_to_obsidian tests."""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from onenote_to_obsidian.config import Config
from onenote_to_obsidian.onenote_api import Notebook, Section, SectionGroup, Page


# ---------------------------------------------------------------------------
# Config fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def tmp_config_dir(tmp_path):
    """Temporary directory for config files."""
    config_dir = tmp_path / ".onenote_exporter"
    config_dir.mkdir()
    return config_dir


@pytest.fixture
def sample_config(tmp_path, tmp_config_dir):
    """Config with paths pointing to tmp_path."""
    return Config(
        client_id="test-client-id",
        vault_path=str(tmp_path / "vault"),
        authority="https://login.microsoftonline.com/common",
        scopes=["Notes.Read"],
        config_dir=str(tmp_config_dir),
    )


# ---------------------------------------------------------------------------
# MSAL fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def mock_msal_app():
    """Mock msal.PublicClientApplication."""
    app = MagicMock()
    app.get_accounts.return_value = []
    app.initiate_device_flow.return_value = {
        "user_code": "TESTCODE",
        "verification_uri": "https://microsoft.com/devicelogin",
        "message": "To sign in, use a web browser...",
    }
    app.acquire_token_by_device_flow.return_value = {
        "access_token": "test-access-token",
    }
    app.acquire_token_silent.return_value = None
    return app


@pytest.fixture
def mock_token_cache():
    """Mock msal.SerializableTokenCache."""
    cache = MagicMock()
    cache.has_state_changed = False
    cache.serialize.return_value = '{"tokens": {}}'
    return cache


# ---------------------------------------------------------------------------
# OneNote data fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_page():
    """A single Page dataclass."""
    return Page(
        id="page-001",
        title="Test Page",
        created_time="2024-01-15T10:30:00Z",
        last_modified_time="2024-06-20T14:22:00Z",
        content_url="https://graph.microsoft.com/v1.0/me/onenote/pages/page-001/content",
        order=0,
    )


@pytest.fixture
def sample_section(sample_page):
    """A Section with one page."""
    return Section(
        id="section-001",
        display_name="Test Section",
        pages=[sample_page],
    )


@pytest.fixture
def sample_section_group():
    """A SectionGroup with one section containing one page."""
    page = Page(
        id="page-sg-001",
        title="Nested Page",
        created_time="2024-03-01T00:00:00Z",
        last_modified_time="2024-03-01T00:00:00Z",
        content_url="",
        order=0,
    )
    section = Section(id="section-sg-001", display_name="Nested Section", pages=[page])
    return SectionGroup(
        id="sg-001",
        display_name="Test Group",
        sections=[section],
        section_groups=[],
    )


@pytest.fixture
def sample_notebook(sample_section, sample_section_group):
    """A Notebook with sections and section groups."""
    return Notebook(
        id="nb-001",
        display_name="Test Notebook",
        sections=[sample_section],
        section_groups=[sample_section_group],
    )


# ---------------------------------------------------------------------------
# HTML fixtures
# ---------------------------------------------------------------------------

SAMPLE_ONENOTE_HTML = """\
<html>
<head><title>Test Page</title></head>
<body>
<h1>Test Heading</h1>
<p>Regular paragraph.</p>
<p data-tag="to-do">Unchecked task</p>
<p data-tag="to-do:completed">Completed task</p>
<img src="https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value"
     data-src-type="image/png" alt="screenshot">
<object data="https://graph.microsoft.com/v1.0/me/onenote/resources/0-file1/$value"
        data-attachment="report.pdf" type="application/pdf"></object>
<iframe data-original-src="https://youtube.com/watch?v=abc"></iframe>
<table><tr><th>Col A</th></tr><tr><td>Val 1</td></tr></table>
</body>
</html>
"""

SAMPLE_RESOURCE_MAP = {
    "https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value": "0-img1.png",
    "https://graph.microsoft.com/v1.0/me/onenote/resources/0-file1/$value": "report.pdf",
}


@pytest.fixture
def sample_onenote_html():
    return SAMPLE_ONENOTE_HTML


@pytest.fixture
def sample_resource_map():
    return dict(SAMPLE_RESOURCE_MAP)
