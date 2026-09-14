import hashlib
from abc import ABC, abstractmethod
from pathlib import Path
from typing import List, Optional

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata


class AssetProvider(ABC):
    def __init__(self, name: str):
        self.name = name

    @abstractmethod
    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        pass

    def download(self, asset: AssetMetadata, cache_dir: Path) -> Optional[str]:
        cache_dir.mkdir(parents=True, exist_ok=True)
        hash_str = hashlib.md5(asset.asset_key.encode()).hexdigest()
        asset.cache_key = hash_str
        ext = "mp4" if asset.media_type == "video" else "jpg"
        local_path = cache_dir / f"{hash_str}.{ext}"
        
        if local_path.exists() and local_path.stat().st_size > 0:
            asset.local_path = str(local_path)
            return asset.local_path
            
        try:
            import httpx
            with httpx.stream("GET", asset.media_url, follow_redirects=True, timeout=15.0) as response:
                response.raise_for_status()
                with open(local_path, "wb") as f:
                    for chunk in response.iter_bytes():
                        f.write(chunk)
            asset.local_path = str(local_path)
            return asset.local_path
        except Exception as e:
            logger.error(f"Download failed for {self.name} asset {asset.asset_key}: {type(e).__name__}")
            if local_path.exists():
                local_path.unlink(missing_ok=True)
            return None
