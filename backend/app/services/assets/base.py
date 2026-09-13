import httpx
import hashlib
from typing import List, Optional
from abc import ABC, abstractmethod
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata

class AssetProvider(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        pass

    def download(self, asset: AssetMetadata, cache_dir: str) -> Optional[str]:
        # Stable content hash
        hash_str = hashlib.md5(f"{self.name}_{asset.id}".encode()).hexdigest()
        ext = "mp4" if asset.media_type == "video" else "jpg"
        local_path = f"{cache_dir}/{hash_str}.{ext}"
        
        import os
        if os.path.exists(local_path):
            asset.local_path = local_path
            return local_path
            
        try:
            with httpx.stream("GET", asset.url, follow_redirects=True, timeout=15.0) as response:
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            asset.local_path = local_path
            return local_path
        except Exception as e:
            logger.error(f"Download failed for {self.name} asset {asset.id}: {e}")
            if os.path.exists(local_path):
                os.remove(local_path)
            return None
