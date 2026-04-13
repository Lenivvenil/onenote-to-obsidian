"""Tests for resource downloading (images, file attachments)."""

from pathlib import Path
from unittest.mock import MagicMock

import pytest

from onenote_to_obsidian.resource_downloader import ResourceDownloader
from onenote_to_obsidian.graph_client import GraphAPIError


@pytest.fixture
def mock_api():
    return MagicMock()


@pytest.fixture
def downloader(mock_api):
    return ResourceDownloader(mock_api)


class TestDownloadResources:
    def test_empty_urls_returns_empty_map(self, downloader, tmp_path):
        result = downloader.download_resources({}, tmp_path / "attachments")
        assert result == {}

    def test_single_image_downloaded(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url = "https://graph.microsoft.com/v1.0/me/onenote/resources/0-img1/$value"
        resource_urls = {url: ("0-img1.png", "image/png")}
        mock_api.get_resource.return_value = b"\x89PNG\r\n"

        result = downloader.download_resources(resource_urls, attachments_dir)

        assert result[url] == "0-img1.png"
        assert (attachments_dir / "0-img1.png").exists()
        assert (attachments_dir / "0-img1.png").read_bytes() == b"\x89PNG\r\n"
        mock_api.get_resource.assert_called_once_with(url)

    def test_multiple_resources_downloaded(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url1 = "https://graph.example.com/resources/img1/$value"
        url2 = "https://graph.example.com/resources/file1/$value"
        resource_urls = {
            url1: ("img1.png", "image/png"),
            url2: ("report.pdf", "application/pdf"),
        }
        mock_api.get_resource.side_effect = [b"img-data", b"pdf-data"]

        result = downloader.download_resources(resource_urls, attachments_dir)

        assert len(result) == 2
        assert (attachments_dir / "img1.png").read_bytes() == b"img-data"
        assert (attachments_dir / "report.pdf").read_bytes() == b"pdf-data"

    def test_creates_attachments_dir(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "deep" / "nested" / "attachments"
        url = "https://graph.example.com/res/0-x/$value"
        resource_urls = {url: ("file.png", "image/png")}
        mock_api.get_resource.return_value = b"data"

        downloader.download_resources(resource_urls, attachments_dir)

        assert attachments_dir.exists()

    def test_skip_existing_file(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        attachments_dir.mkdir()
        existing = attachments_dir / "0-img1.png"
        existing.write_bytes(b"already-here")

        url = "https://graph.example.com/resources/0-img1/$value"
        resource_urls = {url: ("0-img1.png", "image/png")}

        result = downloader.download_resources(resource_urls, attachments_dir)

        assert result[url] == "0-img1.png"
        # Should NOT have called get_resource since file exists
        mock_api.get_resource.assert_not_called()
        # Original content preserved
        assert existing.read_bytes() == b"already-here"

    def test_download_error_maps_to_filename(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url = "https://graph.example.com/resources/0-broken/$value"
        resource_urls = {url: ("broken.png", "image/png")}
        mock_api.get_resource.side_effect = GraphAPIError(500, "Server error")

        result = downloader.download_resources(resource_urls, attachments_dir)

        # Still maps URL to filename despite error
        assert result[url] == "broken.png"
        # File should NOT exist
        assert not (attachments_dir / "broken.png").exists()

    def test_download_network_error_handled(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url = "https://graph.example.com/resources/0-net/$value"
        resource_urls = {url: ("net.png", "image/png")}
        mock_api.get_resource.side_effect = ConnectionError("Network unreachable")

        result = downloader.download_resources(resource_urls, attachments_dir)

        assert result[url] == "net.png"

    def test_deduplication_of_filenames(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url1 = "https://graph.example.com/resources/a/$value"
        url2 = "https://graph.example.com/resources/b/$value"
        resource_urls = {
            url1: ("image.png", "image/png"),
            url2: ("image.png", "image/png"),
        }
        mock_api.get_resource.side_effect = [b"data1", b"data2"]

        result = downloader.download_resources(resource_urls, attachments_dir)

        filenames = set(result.values())
        assert len(filenames) == 2  # Should be deduplicated
        assert "image.png" in filenames
        assert "image_1.png" in filenames

    def test_mixed_success_and_failure(self, downloader, mock_api, tmp_path):
        attachments_dir = tmp_path / "attachments"
        url1 = "https://graph.example.com/resources/ok/$value"
        url2 = "https://graph.example.com/resources/fail/$value"
        url3 = "https://graph.example.com/resources/ok2/$value"
        resource_urls = {
            url1: ("ok.png", "image/png"),
            url2: ("fail.png", "image/png"),
            url3: ("ok2.png", "image/png"),
        }
        mock_api.get_resource.side_effect = [
            b"data1",
            GraphAPIError(404, "Not found"),
            b"data3",
        ]

        result = downloader.download_resources(resource_urls, attachments_dir)

        assert len(result) == 3
        assert (attachments_dir / "ok.png").exists()
        assert not (attachments_dir / "fail.png").exists()
        assert (attachments_dir / "ok2.png").exists()
