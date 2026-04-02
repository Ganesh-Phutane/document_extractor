"""
services/blob_service.py
────────────────────────
Azure Blob Storage helper — all read/write/list operations go through here.

The system uses ONE container with 5 virtual subdirectories (path prefixes):
    raw/        ← original uploaded files
    processed/  ← Azure DI markdown output
    extracted/  ← LLM-extracted JSON
    logs/       ← verification error logs
    prompts/    ← versioned prompt JSON templates

Usage:
    from services.blob_service import BlobService
    blob = BlobService()

    # Upload
    blob.upload_file(local_path="./file.pdf", blob_path="raw/abc123.pdf")
    blob.upload_bytes(data=b"...", blob_path="processed/abc123.md", content_type="text/markdown")

    # Download
    content: bytes = blob.download_bytes("processed/abc123.md")
    text: str      = blob.download_text("processed/abc123.md")

    # Check / List
    exists: bool   = blob.exists("extracted/abc123.json")
    blobs: list    = blob.list_blobs(prefix="logs/")

    # Delete
    blob.delete("logs/abc123_1710681366.json")

    # URL
    url: str = blob.get_blob_url("raw/abc123.pdf")
"""
import json
import os
from typing import Any

from azure.storage.blob import BlobServiceClient, ContentSettings
from azure.core.exceptions import ResourceNotFoundError

from core.config import settings
from core.logger import get_logger

logger = get_logger(__name__)


class BlobService:
    """
    Thin wrapper around the Azure Blob Storage SDK.
    Uses a single container with virtual path prefixes per data type.
    """

    def __init__(self):
        self._client = BlobServiceClient.from_connection_string(
            settings.AZURE_STORAGE_CONNECTION_STRING
        )
        self._container = settings.AZURE_BLOB_CONTAINER_NAME
        self._ensure_container()

    # ── Private ──────────────────────────────────────────

    def _ensure_container(self):
        """Create the container if it doesn't already exist."""
        container_client = self._client.get_container_client(self._container)
        try:
            container_client.get_container_properties()
        except ResourceNotFoundError:
            container_client.create_container()
            logger.info("Blob container created", extra={"container": self._container})

    def _blob_client(self, blob_path: str):
        return self._client.get_blob_client(
            container=self._container, blob=blob_path
        )

    # ── Upload ───────────────────────────────────────────

    def upload_file(self, local_path: str, blob_path: str, overwrite: bool = True) -> str:
        """
        Upload a local file to Blob Storage.
        Returns the blob path on success.
        """
        with open(local_path, "rb") as f:
            self._blob_client(blob_path).upload_blob(f, overwrite=overwrite)
        logger.info("Blob uploaded (file)", extra={"blob_path": blob_path})
        return blob_path

    def upload_bytes(
        self,
        data: bytes,
        blob_path: str,
        content_type: str = "application/octet-stream",
        overwrite: bool = True,
    ) -> str:
        """
        Upload raw bytes to Blob Storage.
        Returns the blob path on success.
        """
        content_settings = ContentSettings(content_type=content_type)
        self._blob_client(blob_path).upload_blob(
            data,
            overwrite=overwrite,
            content_settings=content_settings,
        )
        logger.info("Blob uploaded (bytes)", extra={"blob_path": blob_path, "size": len(data)})
        return blob_path

    def upload_text(
        self,
        text: str,
        blob_path: str,
        content_type: str = "text/plain; charset=utf-8",
        overwrite: bool = True,
    ) -> str:
        """Upload a string (markdown, etc.) to Blob Storage."""
        return self.upload_bytes(
            data=text.encode("utf-8"),
            blob_path=blob_path,
            content_type=content_type,
            overwrite=overwrite,
        )

    def upload_json(self, data: Any, blob_path: str, overwrite: bool = True) -> str:
        """Serialize a dict/list to JSON and upload to Blob Storage."""
        return self.upload_text(
            text=json.dumps(data, indent=2, default=str),
            blob_path=blob_path,
            content_type="application/json",
            overwrite=overwrite,
        )

    # ── Download ─────────────────────────────────────────

    def download_bytes(self, blob_path: str) -> bytes:
        """Download blob content as raw bytes."""
        data = self._blob_client(blob_path).download_blob().readall()
        logger.info("Blob downloaded (bytes)", extra={"blob_path": blob_path})
        return data

    def download_text(self, blob_path: str, encoding: str = "utf-8") -> str:
        """Download blob content as a decoded string."""
        return self.download_bytes(blob_path).decode(encoding)

    def download_json(self, blob_path: str) -> Any:
        """Download and parse a JSON blob."""
        return json.loads(self.download_text(blob_path))

    def download_to_file(self, blob_path: str, local_path: str) -> str:
        """Download blob to a local file path. Returns local_path."""
        parent_dir = os.path.dirname(local_path)
        if parent_dir:  # Only makedirs if there's actually a directory component
            os.makedirs(parent_dir, exist_ok=True)
        with open(local_path, "wb") as f:
            f.write(self.download_bytes(blob_path))
        logger.info("Blob downloaded to file", extra={"blob_path": blob_path, "local_path": local_path})
        return local_path

    # ── Check / List ──────────────────────────────────────

    def exists(self, blob_path: str) -> bool:
        """Return True if the blob exists."""
        try:
            self._blob_client(blob_path).get_blob_properties()
            return True
        except ResourceNotFoundError:
            return False

    def list_blobs(self, prefix: str) -> list[str]:
        """
        List all blob paths under the given prefix.
        Example: list_blobs("logs/") → ["logs/abc123_1710.json", ...]
        """
        container_client = self._client.get_container_client(self._container)
        blobs = [b.name for b in container_client.list_blobs(name_starts_with=prefix)]
        logger.info("Blob list fetched", extra={"prefix": prefix, "count": len(blobs)})
        return blobs

    # ── Delete ───────────────────────────────────────────

    def delete(self, blob_path: str) -> None:
        """Delete a single blob. Silently ignores if it doesn't exist."""
        try:
            self._blob_client(blob_path).delete_blob()
            logger.info("Blob deleted", extra={"blob_path": blob_path})
        except ResourceNotFoundError:
            logger.warning("Delete skipped — blob not found", extra={"blob_path": blob_path})

    # ── URL ──────────────────────────────────────────────

    def get_blob_url(self, blob_path: str) -> str:
        """
        Returns the public URL of the blob.
        Note: URL is only accessible if container has public access OR you use SAS tokens.
        For private containers, use download_bytes() directly.
        """
        return self._blob_client(blob_path).url

    # ── Convenience path builders ────────────────────────

    @staticmethod
    def raw_path(document_id: str, extension: str) -> str:
        """e.g. raw/abc123.pdf"""
        ext = extension.lstrip(".")
        return f"{settings.BLOB_RAW_PREFIX}/{document_id}.{ext}"

    @staticmethod
    def processed_path(document_id: str) -> str:
        """e.g. processed/abc123.md"""
        return f"{settings.BLOB_PROCESSED_PREFIX}/{document_id}.md"

    @staticmethod
    def extracted_path(document_id: str) -> str:
        """e.g. extracted/abc123.json"""
        return f"{settings.BLOB_EXTRACTED_PREFIX}/{document_id}.json"

    @staticmethod
    def log_path(document_id: str, unix_ts: int) -> str:
        """e.g. logs/abc123_1710681366.json"""
        return f"{settings.BLOB_LOGS_PREFIX}/{document_id}_{unix_ts}.json"

    @staticmethod
    def prompt_path(doc_type: str, version: str) -> str:
        """e.g. prompts/invoice/v2.json"""
        return f"{settings.BLOB_PROMPTS_PREFIX}/{doc_type}/{version}.json"

    @staticmethod
    def prompt_latest_path(doc_type: str) -> str:
        """e.g. prompts/invoice/latest.json"""
        return f"{settings.BLOB_PROMPTS_PREFIX}/{doc_type}/latest.json"

    # ── Master Data paths (NEW — separate virtual folder) ──
    @staticmethod
    def master_md_path(document_id: str) -> str:
        """Compact token-efficient markdown for master data processing.
        e.g. master_data/abc123.md"""
        return f"master_data/{document_id}.md"

    @staticmethod
    def master_json_path(document_id: str) -> str:
        """Final validated master data JSON result.
        e.g. master_data/abc123_result.json"""
        return f"master_data/{document_id}_result.json"

    @staticmethod
    def master_prompt_path() -> str:
        """Versioned master data extraction prompt config.
        e.g. master_data/prompts/master_prompt.json"""
        return "master_data/prompts/master_prompt.json"
