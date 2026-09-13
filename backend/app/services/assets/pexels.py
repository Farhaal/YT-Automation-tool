import httpx
from typing import List
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import AssetProvider

class PexelsProvider(AssetProvider):
    def __init__(self):
        super().__init__("Pexels")
        self.api_key = settings.PEXELS_API_KEY
        self.headers = {"Authorization": self.api_key} if self.api_key else {}

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
                    # Find highest res video file
                    video_files = v.get("video_files", [])
                    if not video_files: continue
                    best_file = max(video_files, key=lambda f: f.get("width", 0) * f.get("height", 0))
                    
                    results.append(AssetMetadata(
                        id=str(v["id"]),
                        provider=self.name,
                        url=best_file["link"],
                        author=v.get("user", {}).get("name", "Unknown"),
                        license="Pexels License",
                        media_type="video",
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=v.get("duration", 0.0),
                        attribution_required=False
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
                        id=str(p["id"]),
                        provider=self.name,
                        url=p["src"].get("large2x", p["src"].get("original")),
                        author=p.get("photographer", "Unknown"),
                        license="Pexels License",
                        media_type="image",
                        width=p.get("width", 0),
                        height=p.get("height", 0),
                        attribution_required=False
                    ))
        except Exception as e:
            logger.warning(f"Pexels search failed for '{query}': {type(e).__name__}")
            
        return results
