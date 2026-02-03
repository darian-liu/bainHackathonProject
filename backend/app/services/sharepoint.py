from typing import List, Tuple
import os

from app.services.document_source import DocumentSource, Folder, File


class SharePointSource(DocumentSource):
    """Document source that reads from SharePoint via MS Graph API."""
    
    def __init__(self):
        self.client_id = os.getenv("AZURE_CLIENT_ID", "")
        self.client_secret = os.getenv("AZURE_CLIENT_SECRET", "")
        self.tenant_id = os.getenv("AZURE_TENANT_ID", "")
        self.site_id = os.getenv("SHAREPOINT_SITE_ID", "")
        self._client = None
    
    async def _get_client(self):
        """Get or create MS Graph client."""
        if self._client is None:
            # Import here to avoid loading when not needed
            from msal import ConfidentialClientApplication
            
            app = ConfidentialClientApplication(
                self.client_id,
                authority=f"https://login.microsoftonline.com/{self.tenant_id}",
                client_credential=self.client_secret
            )
            
            result = app.acquire_token_for_client(
                scopes=["https://graph.microsoft.com/.default"]
            )
            
            if "access_token" not in result:
                raise Exception(f"Failed to acquire token: {result.get('error_description', 'Unknown error')}")
            
            self._access_token = result["access_token"]
        
        return self._access_token
    
    async def list_folders(self, parent_id: str | None = None) -> List[Folder]:
        """List folders from SharePoint."""
        import httpx
        
        token = await self._get_client()
        headers = {"Authorization": f"Bearer {token}"}
        
        if parent_id is None:
            # List root drive
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/root/children"
        else:
            url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/items/{parent_id}/children"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        folders = []
        for item in data.get("value", []):
            if "folder" in item:
                folders.append(Folder(
                    id=item["id"],
                    name=item["name"],
                    path=item.get("parentReference", {}).get("path", "") + "/" + item["name"]
                ))
        
        return folders
    
    async def list_files(self, folder_id: str) -> List[File]:
        """List files in a SharePoint folder."""
        import httpx
        
        token = await self._get_client()
        headers = {"Authorization": f"Bearer {token}"}
        
        url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/items/{folder_id}/children"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(url, headers=headers)
            response.raise_for_status()
            data = response.json()
        
        files = []
        for item in data.get("value", []):
            if "file" in item:
                files.append(File(
                    id=item["id"],
                    name=item["name"],
                    path=item.get("parentReference", {}).get("path", "") + "/" + item["name"],
                    mime_type=item.get("file", {}).get("mimeType", "application/octet-stream"),
                    size=item.get("size", 0)
                ))
        
        return files
    
    async def download_file(self, file_id: str) -> Tuple[bytes, str]:
        """Download file from SharePoint."""
        import httpx
        
        token = await self._get_client()
        headers = {"Authorization": f"Bearer {token}"}
        
        # Get file metadata first
        meta_url = f"https://graph.microsoft.com/v1.0/sites/{self.site_id}/drive/items/{file_id}"
        
        async with httpx.AsyncClient() as client:
            response = await client.get(meta_url, headers=headers)
            response.raise_for_status()
            metadata = response.json()
            
            # Download content
            download_url = metadata.get("@microsoft.graph.downloadUrl")
            if not download_url:
                raise Exception("No download URL available")
            
            content_response = await client.get(download_url)
            content_response.raise_for_status()
        
        return content_response.content, metadata["name"]
