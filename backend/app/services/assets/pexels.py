from typing import List

import httpx

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import USER_AGENT, AssetProvider


class PexelsProvider(AssetProvider):
    def __init__(self):
        super().__init__("Pexels")
        self.api_key = settings.PEXELS_API_KEY
        self.headers = {"Authorization": self.api_key, "User-Agent": USER_AGENT} if self.api_key else {"User-Agent": USER_AGENT}  # noqa: E501
        if not self.api_key:
            logger.info("Pexels API key not configured. Pexels will be disabled.")
        else:
            logger.info("Pexels API key configured.")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        if not self.api_key:
            return []
            
        results = []
        try:
            # 1. Search Videos
            resp = httpx.get(
                "https://api.pexels.com/videos/search",
                headers=self.headers,
                params={"query": query, "orientation": orientation, "per_page": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for v in data.get("videos", []):
                    video_files = v.get("video_files", [])
                    if not video_files: continue  # noqa: E701
                    best_file = max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))
                    
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(v["id"]),
                        asset_key=f"{self.name}:{v['id']}",
                        media_url=best_file["link"],
                        source_page_url=v.get("url"),
                        author=v.get("user", {}).get("name", "unknown"),
                        license_name="Pexels License",
                        license_url="https://www.pexels.com/license/",
                        media_type="video",
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=v.get("duration", 0.0),
                        attribution_required=False,
                        query=query,
                        preview_image_url=v.get("image")
                    ))
            
            # 2. Search Images (Fallback)
            resp = httpx.get(
                "https://api.pexels.com/v1/search",
                headers=self.headers,
                params={"query": query, "orientation": orientation, "per_page": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get("photos", []):
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(p["id"]),
                        asset_key=f"{self.name}:{p['id']}",
                        media_url=p["src"].get("large2x", p["src"].get("original")),
                        source_page_url=p.get("url"),
                        author=p.get("photographer", "unknown"),
                        license_name="Pexels License",
                        license_url="https://www.pexels.com/license/",
                        media_type="image",
                        width=p.get("width", 0),
                        height=p.get("height", 0),
                        attribution_required=False,
                        title=p.get("alt") or None,
                        query=query,
                        preview_image_url=p.get("src", {}).get("medium")
                    ))
        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {type(e).__name__}")
            
        return results
