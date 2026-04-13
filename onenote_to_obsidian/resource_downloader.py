"""Download images and file attachments from OneNote Graph API."""

import logging
from pathlib import Path

from .onenote_api import OneNoteAPI
from .utils import deduplicate_path

logger = logging.getLogger(__name__)


class ResourceDownloader:
    """Downloads OneNote page resources (images, file attachments) to local storage."""

    def __init__(self, api: OneNoteAPI):
        self._api = api

    def download_resources(
        self,
        resource_urls: dict[str, tuple[str, str]],
        attachments_dir: Path,
    ) -> dict[str, str]:
        """Download all resources for a page.

        Args:
            resource_urls: {graph_url: (filename, media_type)} from preprocess_onenote_html
            attachments_dir: Directory to save files to

        Returns:
            resource_map: {graph_url: local_filename} for the HTML converter
        """
        if not resource_urls:
            return {}

        attachments_dir.mkdir(parents=True, exist_ok=True)
        resource_map: dict[str, str] = {}
        used_paths: set[Path] = set()

        for url, (filename, media_type) in resource_urls.items():
            local_path = attachments_dir / filename
            local_path = deduplicate_path(local_path, existing_paths=used_paths)
            used_paths.add(local_path)

            if local_path.exists():
                # Resume support: skip already downloaded files
                logger.debug("Skipping existing resource: %s", local_path.name)
                resource_map[url] = local_path.name
                continue

            try:
                data = self._api.get_resource(url)
                local_path.write_bytes(data)
                resource_map[url] = local_path.name
                logger.debug(
                    "Downloaded resource: %s (%d bytes)", local_path.name, len(data)
                )
            except Exception as e:  # noqa: BLE001 — intentionally broad to not break export
                logger.warning("Failed to download resource %s: %s", url, e)
                # Still map to expected filename so Markdown reference isn't broken
                resource_map[url] = local_path.name

        return resource_map
