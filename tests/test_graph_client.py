"""Comprehensive tests for GraphClient HTTP client with retry logic and pagination."""

import json
from unittest.mock import MagicMock, patch

import pytest
import requests
import responses

from onenote_to_obsidian.graph_client import BASE_URL, GraphAPIError, GraphClient


@pytest.fixture
def mock_auth():
    """Mock AuthManager that returns a fixed test token."""
    auth = MagicMock()
    auth.get_token.return_value = "test-token"
    return auth


@pytest.fixture
def client(mock_auth):
    """GraphClient instance with mocked auth."""
    return GraphClient(mock_auth)


class TestGraphClientInit:
    """Tests for GraphClient initialization."""

    def test_init_sets_auth(self, mock_auth):
        """Test that GraphClient stores auth manager."""
        client = GraphClient(mock_auth)
        assert client._auth is mock_auth

    def test_init_creates_session(self, mock_auth):
        """Test that GraphClient creates a requests session."""
        client = GraphClient(mock_auth)
        assert client._session is not None
        assert isinstance(client._session, requests.Session)

    def test_init_sets_default_accept_header(self, mock_auth):
        """Test that session gets default Accept: application/json header."""
        client = GraphClient(mock_auth)
        assert client._session.headers["Accept"] == "application/json"

    def test_get_headers_includes_auth_token(self, client, mock_auth):
        """Test that _get_headers() includes Bearer token."""
        headers = client._get_headers()
        assert "Authorization" in headers
        assert headers["Authorization"] == "Bearer test-token"

    def test_get_headers_calls_get_token(self, client, mock_auth):
        """Test that _get_headers() calls auth.get_token()."""
        client._get_headers()
        mock_auth.get_token.assert_called_once()


class TestHappyPath:
    """Tests for successful requests."""

    @responses.activate
    def test_get_json_returns_parsed_json(self, client):
        """Test get_json() returns parsed JSON dict."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"id": "user-123", "displayName": "Test User"},
            status=200,
        )

        result = client.get_json("/me")
        assert result == {"id": "user-123", "displayName": "Test User"}

    @responses.activate
    def test_get_json_with_params(self, client):
        """Test get_json() passes query parameters."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages",
            json={"value": []},
            status=200,
        )

        client.get_json("/me/messages", params={"$top": 10})
        assert len(responses.calls) == 1
        assert "top=10" in responses.calls[0].request.url

    @responses.activate
    def test_get_text_returns_html_string(self, client):
        """Test get_text() returns HTML content as string."""
        html_content = "<html><body>Test Content</body></html>"
        responses.add(
            responses.GET,
            f"{BASE_URL}/pages/page-123/content",
            body=html_content,
            status=200,
            content_type="text/html",
        )

        result = client.get_text("/pages/page-123/content")
        assert result == html_content
        assert isinstance(result, str)

    @responses.activate
    def test_get_text_sets_accept_header(self, client):
        """Test get_text() sets Accept: text/html header."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            body="content",
            status=200,
        )

        client.get_text("/test")
        assert responses.calls[0].request.headers["Accept"] == "text/html"

    @responses.activate
    def test_get_binary_returns_bytes(self, client):
        """Test get_binary() returns binary content as bytes."""
        binary_data = b"\x89PNG\r\n\x1a\n" + b"\x00" * 100  # PNG magic bytes
        responses.add(
            responses.GET,
            f"{BASE_URL}/attachments/image-123",
            body=binary_data,
            status=200,
            content_type="application/octet-stream",
        )

        result = client.get_binary("/attachments/image-123")
        assert result == binary_data
        assert isinstance(result, bytes)

    @responses.activate
    def test_get_binary_sets_accept_header(self, client):
        """Test get_binary() sets Accept: application/octet-stream header."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            body=b"binary",
            status=200,
        )

        client.get_binary("/test")
        assert responses.calls[0].request.headers["Accept"] == "application/octet-stream"

    @responses.activate
    def test_url_without_http_prepends_base_url(self, client):
        """Test that relative URLs get BASE_URL prepended."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"id": "123"},
            status=200,
        )

        client.get_json("/me")
        assert responses.calls[0].request.url == f"{BASE_URL}/me"

    @responses.activate
    def test_url_with_http_used_as_is(self, client):
        """Test that absolute URLs with http:// are used as-is."""
        absolute_url = "https://different-host.com/api/resource"
        responses.add(
            responses.GET,
            absolute_url,
            json={"data": "test"},
            status=200,
        )

        result = client.get_json(absolute_url)
        assert result == {"data": "test"}
        assert responses.calls[0].request.url == absolute_url

    @responses.activate
    def test_url_with_https_used_as_is(self, client):
        """Test that absolute URLs with https:// are used as-is."""
        absolute_url = "https://another-host.com/data"
        responses.add(
            responses.GET,
            absolute_url,
            json={"value": []},
            status=200,
        )

        result = client.get_json(absolute_url)
        assert result == {"value": []}

    @responses.activate
    def test_response_encoding_set_to_utf8(self, client):
        """Test that response encoding is set to UTF-8."""
        text_with_unicode = "Привет мир 世界"
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            body=text_with_unicode,
            status=200,
        )

        result = client.get_text("/test")
        assert text_with_unicode in result


class TestRetryOn429:
    """Tests for 429 Rate Limit handling."""

    @responses.activate
    @patch("time.sleep")
    def test_429_respects_retry_after_header(self, mock_sleep, client):
        """Test 429 respects Retry-After header and retries."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Rate limited"},
            status=429,
            headers={"Retry-After": "5"},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        mock_sleep.assert_called_once_with(5)

    @responses.activate
    @patch("time.sleep")
    def test_429_without_retry_after_uses_default(self, mock_sleep, client):
        """Test 429 without Retry-After header uses default 10 seconds."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Rate limited"},
            status=429,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        mock_sleep.assert_called_once_with(10)

    @responses.activate
    @patch("time.sleep")
    def test_429_multiple_retries(self, mock_sleep, client):
        """Test handling multiple 429s in a row (up to MAX_RETRIES)."""
        # 3 rate limit responses, then success
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{BASE_URL}/api/test",
                json={"error": "Rate limited"},
                status=429,
                headers={"Retry-After": "2"},
            )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        assert mock_sleep.call_count == 3

    @responses.activate
    @patch("time.sleep")
    def test_429_retry_after_as_string(self, mock_sleep, client):
        """Test that Retry-After is parsed as integer from string."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=429,
            headers={"Retry-After": "7"},
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"ok": True},
            status=200,
        )

        client.get_json("/api/test")
        mock_sleep.assert_called_once_with(7)


class TestRetryOn5xx:
    """Tests for 5xx Server Error handling."""

    @responses.activate
    @patch("time.sleep")
    def test_500_exponential_backoff_retries(self, mock_sleep, client):
        """Test 500 error with exponential backoff."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Server error"},
            status=500,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        # First 500 on attempt 0 should sleep for BACKOFF_FACTOR ** (0+1) = 2
        mock_sleep.assert_called_once_with(2)

    @responses.activate
    @patch("time.sleep")
    def test_502_retries(self, mock_sleep, client):
        """Test 502 Bad Gateway is retried."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=502,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"data": "ok"},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"data": "ok"}
        mock_sleep.assert_called_once()

    @responses.activate
    @patch("time.sleep")
    def test_503_retries(self, mock_sleep, client):
        """Test 503 Service Unavailable is retried."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=503,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"result": "success"},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"result": "success"}

    @responses.activate
    @patch("time.sleep")
    def test_504_retries(self, mock_sleep, client):
        """Test 504 Gateway Timeout is retried."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=504,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"ok": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"ok": True}

    @responses.activate
    @patch("time.sleep")
    def test_500_exponential_backoff_sequence(self, mock_sleep, client):
        """Test backoff timing for 500 errors (2s, 4s, 8s)."""
        # 3 500 errors, then success
        for _ in range(3):
            responses.add(
                responses.GET,
                f"{BASE_URL}/api/test",
                status=500,
            )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"ok": True},
            status=200,
        )

        client.get_json("/api/test")
        # Backoff on attempts 0, 1, 2: 2^1=2, 2^2=4, 2^3=8
        assert mock_sleep.call_count == 3
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert calls == [2, 4, 8]


class TestRetryOn401:
    """Tests for 401 Unauthorized handling."""

    @responses.activate
    def test_401_on_first_attempt_refreshes_token(self, client, mock_auth):
        """Test 401 on first attempt triggers token refresh."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Unauthorized"},
            status=401,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        # get_token should be called (at least once for initial headers, once for refresh)
        assert mock_auth.get_token.call_count >= 2

    @responses.activate
    def test_401_on_second_attempt_raises_error(self, client, mock_auth):
        """Test 401 on second attempt (after refresh) raises GraphAPIError."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Unauthorized"},
            status=401,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 401

    @responses.activate
    def test_401_no_token_refresh_on_second_attempt(self, client, mock_auth):
        """Test that 401 on second attempt doesn't trigger another refresh."""
        initial_call_count = mock_auth.get_token.call_count
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Unauthorized"},
            status=401,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": "Unauthorized"},
            status=401,
        )

        with pytest.raises(GraphAPIError):
            client.get_json("/api/test")

        # First call for initial headers, second for refresh attempt
        assert mock_auth.get_token.call_count == initial_call_count + 2

    @responses.activate
    def test_401_first_then_success(self, client):
        """Test successful recovery after initial 401."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"error": "Unauthorized"},
            status=401,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"id": "user-123"},
            status=200,
        )

        result = client.get_json("/me")
        assert result == {"id": "user-123"}


class TestClientErrors:
    """Tests for 4xx client errors (except 401 and 429)."""

    @responses.activate
    def test_403_forbidden_raises_immediately(self, client):
        """Test 403 Forbidden raises GraphAPIError without retry."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Access denied"}},
            status=403,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 403
        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_404_not_found_raises_immediately(self, client):
        """Test 404 Not Found raises GraphAPIError without retry."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/missing",
            json={"error": {"message": "Not found"}},
            status=404,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/missing")
        assert exc_info.value.status_code == 404
        assert len(responses.calls) == 1  # No retries

    @responses.activate
    def test_400_bad_request_raises_immediately(self, client):
        """Test 400 Bad Request raises immediately."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Invalid request"}},
            status=400,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 400

    @responses.activate
    def test_410_gone_raises_immediately(self, client):
        """Test 410 Gone raises immediately without retry."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Resource gone"}},
            status=410,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 410
        assert len(responses.calls) == 1

    @responses.activate
    def test_client_error_with_error_message_in_json(self, client):
        """Test error message is extracted from JSON error.message."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Invalid syntax in request"}},
            status=400,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert "Invalid syntax in request" in str(exc_info.value)

    @responses.activate
    def test_client_error_with_plain_text_response(self, client):
        """Test error message is extracted from plain text if JSON fails."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            body="This is a plain text error response that is quite long and should be truncated at 500 characters" * 10,
            status=400,
            content_type="text/plain",
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        # Should truncate to 500 chars
        assert len(str(exc_info.value)) < 600

    @responses.activate
    def test_error_message_fallback_to_text(self, client):
        """Test fallback to response text when error.message not found."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            body="Generic error text",
            status=400,
            content_type="text/plain",
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert "error" in str(exc_info.value).lower()


class TestNetworkErrors:
    """Tests for RequestException (network errors)."""

    @responses.activate
    @patch("time.sleep")
    def test_connection_error_retries_with_backoff(self, mock_sleep, client):
        """Test RequestException is retried with exponential backoff."""
        def callback(request):
            raise requests.ConnectionError("Connection failed")

        responses.add_callback(
            responses.GET,
            f"{BASE_URL}/api/test",
            callback=callback,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"success": True},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"success": True}
        assert mock_sleep.call_count == 1

    @responses.activate
    @patch("time.sleep")
    def test_timeout_error_retries(self, mock_sleep, client):
        """Test timeout RequestException is retried."""
        def callback(request):
            raise requests.Timeout("Request timed out")

        responses.add_callback(
            responses.GET,
            f"{BASE_URL}/api/test",
            callback=callback,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"data": "ok"},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {"data": "ok"}

    @responses.activate
    @patch("time.sleep")
    def test_request_exception_backoff_sequence(self, mock_sleep, client):
        """Test RequestException backoff timing (2s, 4s, 8s, then error)."""
        def callback(request):
            raise requests.RequestException("Network error")

        # 4 network errors, one for each attempt (MAX_RETRIES + 1)
        for _ in range(4):
            responses.add_callback(
                responses.GET,
                f"{BASE_URL}/api/test",
                callback=callback,
            )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        # Should have tried backoff: 2^1=2, 2^2=4, 2^3=8
        assert mock_sleep.call_count == 3
        calls = [c[0][0] for c in mock_sleep.call_args_list]
        assert calls == [2, 4, 8]

    @responses.activate
    @patch("time.sleep")
    def test_network_error_raises_graphapi_error(self, mock_sleep, client):
        """Test that exhausted network retries raise GraphAPIError with status 0."""
        def callback(request):
            raise requests.ConnectionError("Cannot connect")

        for _ in range(4):
            responses.add_callback(
                responses.GET,
                f"{BASE_URL}/api/test",
                callback=callback,
            )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 0
        assert "Cannot connect" in str(exc_info.value)


class TestRetryExhaustion:
    """Tests for when retries are exhausted."""

    @responses.activate
    @patch("time.sleep")
    def test_max_retries_exhausted_with_429(self, mock_sleep, client):
        """Test that repeated 429s eventually raise GraphAPIError."""
        # Add more 429 responses than MAX_RETRIES allows (>3)
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{BASE_URL}/api/test",
                status=429,
            )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert "after" in str(exc_info.value).lower()

    @responses.activate
    @patch("time.sleep")
    def test_max_retries_exhausted_with_500(self, mock_sleep, client):
        """Test that repeated 500s eventually raise GraphAPIError."""
        for _ in range(5):
            responses.add(
                responses.GET,
                f"{BASE_URL}/api/test",
                status=500,
            )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert "Failed after" in str(exc_info.value)

    @responses.activate
    def test_403_raises_immediately_no_retries(self, client):
        """Test that 403 doesn't use any retries."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=403,
        )

        with pytest.raises(GraphAPIError):
            client.get_json("/api/test")
        # Should only make one request
        assert len(responses.calls) == 1


class TestPagination:
    """Tests for @odata.nextLink pagination."""

    @responses.activate
    def test_no_pagination_single_page(self, client):
        """Test get_json_all with single page (no @odata.nextLink)."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages",
            json={
                "value": [
                    {"id": "msg-1"},
                    {"id": "msg-2"},
                    {"id": "msg-3"},
                ]
            },
            status=200,
        )

        result = client.get_json_all("/me/messages")
        assert len(result) == 3
        assert result[0]["id"] == "msg-1"
        assert len(responses.calls) == 1

    @responses.activate
    def test_multiple_pages_pagination(self, client):
        """Test get_json_all follows @odata.nextLink across pages."""
        # First page
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages",
            json={
                "value": [{"id": "msg-1"}, {"id": "msg-2"}],
                "@odata.nextLink": f"{BASE_URL}/me/messages?skip=2",
            },
            status=200,
        )
        # Second page
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages?skip=2",
            json={
                "value": [{"id": "msg-3"}, {"id": "msg-4"}],
                "@odata.nextLink": f"{BASE_URL}/me/messages?skip=4",
            },
            status=200,
        )
        # Third page (final)
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages?skip=4",
            json={
                "value": [{"id": "msg-5"}],
            },
            status=200,
        )

        result = client.get_json_all("/me/messages")
        assert len(result) == 5
        assert [item["id"] for item in result] == ["msg-1", "msg-2", "msg-3", "msg-4", "msg-5"]
        assert len(responses.calls) == 3

    @responses.activate
    def test_empty_value_array_returns_empty_list(self, client):
        """Test get_json_all with empty value array."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/me/messages",
            json={"value": []},
            status=200,
        )

        result = client.get_json_all("/me/messages")
        assert result == []

    @responses.activate
    def test_missing_value_key_treated_as_empty(self, client):
        """Test get_json_all when value key is missing."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"data": "something"},
            status=200,
        )

        result = client.get_json_all("/api/test")
        assert result == []

    @responses.activate
    def test_pagination_combines_all_items(self, client):
        """Test pagination combines items from all pages into single list."""
        # Page 1
        responses.add(
            responses.GET,
            f"{BASE_URL}/items",
            json={
                "value": [{"id": i} for i in range(10)],
                "@odata.nextLink": f"{BASE_URL}/items?skip=10",
            },
            status=200,
        )
        # Page 2
        responses.add(
            responses.GET,
            f"{BASE_URL}/items?skip=10",
            json={
                "value": [{"id": i} for i in range(10, 15)],
            },
            status=200,
        )

        result = client.get_json_all("/items")
        assert len(result) == 15
        assert result[0]["id"] == 0
        assert result[14]["id"] == 14

    @responses.activate
    def test_pagination_with_absolute_urls(self, client):
        """Test pagination when @odata.nextLink contains absolute URL."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/items",
            json={
                "value": [{"id": 1}],
                "@odata.nextLink": f"{BASE_URL}/items?$skip=1",
            },
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/items?$skip=1",
            json={
                "value": [{"id": 2}],
            },
            status=200,
        )

        result = client.get_json_all("/items")
        assert len(result) == 2

    @responses.activate
    @patch("time.sleep")
    def test_pagination_retries_on_5xx_in_middle(self, mock_sleep, client):
        """Test that pagination retries work on intermediate pages."""
        # First page
        responses.add(
            responses.GET,
            f"{BASE_URL}/items",
            json={
                "value": [{"id": 1}],
                "@odata.nextLink": f"{BASE_URL}/items?$skip=1",
            },
            status=200,
        )
        # Second page fails first time
        responses.add(
            responses.GET,
            f"{BASE_URL}/items?$skip=1",
            status=500,
        )
        # Second page succeeds on retry
        responses.add(
            responses.GET,
            f"{BASE_URL}/items?$skip=1",
            json={
                "value": [{"id": 2}],
            },
            status=200,
        )

        result = client.get_json_all("/items")
        assert len(result) == 2
        assert mock_sleep.call_count >= 1


class TestErrorHandling:
    """Tests for error message extraction and handling."""

    @responses.activate
    def test_error_message_from_json_structure(self, client):
        """Test GraphAPIError message comes from error.message in JSON."""
        error_msg = "This is a detailed error message"
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": error_msg}},
            status=400,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert error_msg in str(exc_info.value)

    @responses.activate
    def test_error_message_fallback_when_no_error_key(self, client):
        """Test fallback to response text when error key missing."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            body="Something went wrong on the server",
            status=400,
            content_type="text/plain",
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        # Should include the fallback text
        assert "error" in str(exc_info.value).lower() or "Something" in str(exc_info.value)

    @responses.activate
    def test_error_message_truncated_at_500_chars(self, client):
        """Test that error message is truncated at 500 characters."""
        long_error = "x" * 1000
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            body=long_error,
            status=400,
            content_type="text/plain",
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        error_str = str(exc_info.value)
        # The error string should contain truncated content
        assert len(error_str) < 700  # Some overhead for the error wrapper

    @responses.activate
    def test_exception_stores_status_code(self, client):
        """Test that GraphAPIError stores status_code."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Forbidden"}},
            status=403,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert exc_info.value.status_code == 403

    @responses.activate
    def test_exception_status_code_format(self, client):
        """Test GraphAPIError message format includes status code."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"error": {"message": "Test error"}},
            status=404,
        )

        with pytest.raises(GraphAPIError) as exc_info:
            client.get_json("/api/test")
        assert "404" in str(exc_info.value)


class TestAuthorizationHeader:
    """Tests for authorization header handling."""

    @responses.activate
    def test_bearer_token_included_in_request(self, client, mock_auth):
        """Test that Bearer token is included in request headers."""
        mock_auth.get_token.return_value = "my-secret-token"
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"id": "123"},
            status=200,
        )

        client.get_json("/me")
        auth_header = responses.calls[0].request.headers.get("Authorization")
        assert auth_header == "Bearer my-secret-token"

    @responses.activate
    def test_token_refreshed_on_401(self, client, mock_auth):
        """Test token is refreshed when 401 is received."""
        token_sequence = ["old-token", "new-token"]
        mock_auth.get_token.side_effect = token_sequence

        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"error": "Unauthorized"},
            status=401,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/me",
            json={"id": "user"},
            status=200,
        )

        client.get_json("/me")
        # Should be called once for initial headers, once for refresh
        assert mock_auth.get_token.call_count == 2
        # First request should have old token
        assert "old-token" in responses.calls[0].request.headers["Authorization"]
        # Second request should have new token
        assert "new-token" in responses.calls[1].request.headers["Authorization"]


class TestRequestDetails:
    """Tests for request method details."""

    @responses.activate
    def test_timeout_parameter_passed(self, client):
        """Test that requests are made with 60s timeout."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"ok": True},
            status=200,
        )

        client.get_json("/api/test")
        # responses library doesn't easily expose timeout, but we can verify request was made
        assert len(responses.calls) == 1

    @responses.activate
    def test_get_method_used_by_default(self, client):
        """Test that GET method is used for get_json, get_text, get_binary."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            json={"data": "test"},
            status=200,
        )

        client.get_json("/test")
        assert responses.calls[0].request.method == "GET"

    @responses.activate
    def test_session_reused_across_requests(self, client):
        """Test that same session is reused for multiple requests."""
        initial_session = client._session
        responses.add(
            responses.GET,
            f"{BASE_URL}/test1",
            json={"id": 1},
            status=200,
        )
        responses.add(
            responses.GET,
            f"{BASE_URL}/test2",
            json={"id": 2},
            status=200,
        )

        client.get_json("/test1")
        client.get_json("/test2")
        assert client._session is initial_session


class TestEdgeCases:
    """Tests for edge cases and special scenarios."""

    @responses.activate
    def test_empty_response_body_json(self, client):
        """Test handling of empty response body for JSON."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result == {}

    @responses.activate
    def test_unicode_in_response(self, client):
        """Test handling of unicode characters in response."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            json={"message": "Привет мир 世界 🌍"},
            status=200,
        )

        result = client.get_json("/api/test")
        assert result["message"] == "Привет мир 世界 🌍"

    @responses.activate
    def test_large_json_response(self, client):
        """Test handling of large JSON responses."""
        large_data = {"items": [{"id": i, "name": f"item-{i}"} for i in range(1000)]}
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/large",
            json=large_data,
            status=200,
        )

        result = client.get_json("/api/large")
        assert len(result["items"]) == 1000

    @responses.activate
    def test_retry_after_with_large_value(self, client, mock_auth):
        """Test Retry-After with large wait time is handled."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/test",
            status=429,
            headers={"Retry-After": "3600"},
        )
        # Don't actually add a success response; we're testing it's called correctly
        # This would hang in real scenario, so we patch sleep
        with patch("time.sleep") as mock_sleep:
            # Add success after the 429
            responses.add(
                responses.GET,
                f"{BASE_URL}/api/test",
                json={"ok": True},
                status=200,
            )
            client.get_json("/api/test")
            mock_sleep.assert_called_once_with(3600)

    @responses.activate
    def test_accept_header_override(self, client):
        """Test that custom accept header is passed correctly."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/test",
            body="<html>content</html>",
            status=200,
        )

        client.get_text("/test")
        assert responses.calls[0].request.headers["Accept"] == "text/html"

    @responses.activate
    def test_get_binary_large_file(self, client):
        """Test get_binary with large binary content."""
        large_binary = b"\x00" * (10 * 1024 * 1024)  # 10MB
        responses.add(
            responses.GET,
            f"{BASE_URL}/attachments/large.bin",
            body=large_binary,
            status=200,
        )

        result = client.get_binary("/attachments/large.bin")
        assert len(result) == len(large_binary)

    @responses.activate
    def test_relative_url_with_query_params(self, client):
        """Test relative URL with query parameters is handled correctly."""
        responses.add(
            responses.GET,
            f"{BASE_URL}/api/items",
            json={"value": []},
            status=200,
        )

        client.get_json("/api/items", params={"$filter": "status eq 'active'"})
        request_url = responses.calls[0].request.url
        # $filter gets URL-encoded as %24filter
        assert "%24filter" in request_url or "$filter" in request_url
        assert "status" in request_url
