"""Azure Blob Storage Service.
Responsible for:
- Connecting to Azure Blob Storage.
- Checking blob existence.
- Generating read-only SAS URLs with expiry.
- Supporting videos, thumbnails, and subtitles containers.
"""
from datetime import datetime, timedelta, timezone
from typing import Literal, Optional
from urllib.parse import quote

from azure.core.exceptions import ResourceNotFoundError
from azure.storage.blob import (
    BlobClient,
    BlobSasPermissions,
    BlobServiceClient,
    ContentSettings,
    generate_blob_sas,
)

from app.core.config import settings

ResourceType = Literal["video", "thumbnail", "subtitle"]


class AzureStorageService:
    def __init__(self):
        self.account_name = settings.azure_storage_account_name
        self.account_key = settings.azure_storage_account_key.get_secret_value()
        self.service_client = BlobServiceClient(
            account_url=f"https://{self.account_name}.blob.core.windows.net",
            credential=self.account_key,
        )

    def get_container_name(self, resource_type: ResourceType) -> str:
        """Chọn đúng tên container dựa trên loại tài nguyên."""
        if resource_type == "video":
            return settings.azure_storage_container_videos
        elif resource_type == "thumbnail":
            return settings.azure_storage_container_thumbnails
        elif resource_type == "subtitle":
            return settings.azure_storage_container_subtitles
        else:
            raise ValueError(f"Unsupported resource_type: {resource_type}")

    def get_blob_client(self, blob_name: str, resource_type: ResourceType) -> BlobClient:
        """Lấy Azure Blob Client."""
        container_name = self.get_container_name(resource_type)
        return self.service_client.get_blob_client(
            container=container_name,
            blob=blob_name,
        )

    def blob_exists(self, blob_name: str, resource_type: ResourceType) -> bool:
        """Kiểm tra file có tồn tại trên Azure Blob Storage hay không."""
        try:
            blob_client = self.get_blob_client(blob_name, resource_type)
            return blob_client.exists()
        except ResourceNotFoundError:
            return False
        except Exception as e:
            print(f"Error checking blob existence for '{blob_name}': {e}")
            return False

    def upload_stream(self, blob_name: str, data, resource_type: ResourceType, content_type: str) -> None:
        """Upload a file-like stream without exposing storage credentials to clients."""
        client = self.get_blob_client(blob_name, resource_type)
        client.upload_blob(data, overwrite=True, content_settings=ContentSettings(content_type=content_type))

    def generate_read_url(
        self,
        blob_name: str,
        resource_type: ResourceType,
        expire_minutes: Optional[int] = None,
    ) -> str:
        """
        Sinh SAS URL chỉ có quyền đọc (Read-only) với thời hạn.
        - start = now - 5 phút (tránh clock skew).
        - expiry = now + expire_minutes.
        - URL path được encode an toàn (hỗ trợ blob_name chứa khoảng trắng, ký tự đặc biệt).
        """
        container_name = self.get_container_name(resource_type)
        ttl = expire_minutes or settings.azure_sas_expire_minutes

        now = datetime.now(timezone.utc)
        start_time = now - timedelta(minutes=5)
        expiry_time = now + timedelta(minutes=ttl)

        sas_token = generate_blob_sas(
            account_name=self.account_name,
            container_name=container_name,
            blob_name=blob_name,
            account_key=self.account_key,
            permission=BlobSasPermissions(read=True),
            start=start_time,
            expiry=expiry_time,
        )

        # Encode path để trình duyệt / ExoPlayer / HTTP client đọc tốt khi tên blob có space
        raw_base_url = f"https://{self.account_name}.blob.core.windows.net/{container_name}/{blob_name}"
        encoded_base_url = quote(raw_base_url, safe=":/-_.~")

        return f"{encoded_base_url}?{sas_token}"

    def close(self):
        """Đóng Azure connection."""
        if self.service_client:
            self.service_client.close()


# Singleton instance sử dụng chung
azure_storage = AzureStorageService()
