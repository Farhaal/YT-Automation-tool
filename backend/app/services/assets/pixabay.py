import httpx
from typing import List
from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import AssetProvider

class PixabayProvider(AssetProvider):
    def __init__(self):
        super().__init__("Pixabay")
        self.api_key = settings.PIXABAY_API_KEY

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        if not self.api_key:
            return []
            
        results = []
        orientation_map = {"landscape": "horizontal", "portrait": "vertical", "square": "all"}
        px_orientation = orientation_map.get(orientation, "all")
        
        try:
            # 1. Search Videos
            resp = httpx.get(
                "https://pixabay.com/api/videos/",
                params={"key": self.api_key, "q": query, "orientation": px_orientation, "per_page": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for v in data.get("hits", []):
                    vds = v.get("videos", {})
                    best_file = vds.get("large") or vds.get("medium") or vds.get("small")
                    if not best_file: continue
                    
                    results.append(AssetMetadata(
                        id=str(v["id"]),
                        provider=self.name,
                        url=best_file["url"],
                        author=v.get("user", "Unknown"),
                        license="Pixabay License",
                        media_type="video",
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=v.get("duration", 0.0),
                        attribution_required=False
                    ))
            
            # 2. Search Images
            resp = httpx.get(
                "https://pixabay.com/api/",
                params={"key": self.api_key, "q": query, "orientation": px_orientation, "per_page": 5, "image_type": "photo"},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get("hits", []):
                    results.append(AssetMetadata(
                        id=str(p["id"]),
                        provider=self.name,
                        url=p.get("largeImageURL", p.get("webformatURL")),
                        author=p.get("user", "Unknown"),
                        license="Pixabay License",
                        media_type="image",
                        width=p.get("imageWidth", 0),
                        height=p.get("imageHeight", 0),
                        attribution_required=False
                    ))
        except Exception as e:
            logger.warning(f"Pixabay search failed for '{query}': {type(e).__name__}")
            
        return results
