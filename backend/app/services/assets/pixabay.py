from typing import List

import httpx

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import USER_AGENT, AssetProvider


class PixabayProvider(AssetProvider):
    def __init__(self):
        super().__init__("Pixabay")
        self.api_key = settings.PIXABAY_API_KEY
        if not self.api_key:
            logger.info("Pixabay API key not configured. Pixabay will be disabled.")
        else:
            logger.info("Pixabay API key configured.")

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
                headers={"User-Agent": USER_AGENT},
                params={"key": self.api_key, "q": query, "orientation": px_orientation, "per_page": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for v in data.get("hits", []):
                    vds = v.get("videos", {})
                    best_file = vds.get("large") or vds.get("medium") or vds.get("small")
                    if not best_file: continue  # noqa: E701
                    
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(v["id"]),
                        asset_key=f"{self.name}:{v['id']}",
                        media_url=best_file["url"],
                        source_page_url=v.get("pageURL"),
                        author=v.get("user", "unknown"),
                        license_name="Pixabay License",
                        license_url="https://pixabay.com/service/license-summary/",
                        media_type="video",
                        width=best_file.get("width", 0),
                        height=best_file.get("height", 0),
                        duration=v.get("duration", 0.0),
                        attribution_required=False,
                        tags=[t.strip() for t in v.get("tags", "").split(",") if t.strip()],
                        query=query
                    ))
            
            # 2. Search Images
            resp = httpx.get(
                "https://pixabay.com/api/",
                headers={"User-Agent": USER_AGENT},
                params={"key": self.api_key, "q": query, "orientation": px_orientation, "per_page": 5, "image_type": "photo"},  # noqa: E501
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get("hits", []):
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(p["id"]),
                        asset_key=f"{self.name}:{p['id']}",
                        media_url=p.get("largeImageURL", p.get("webformatURL")),
                        source_page_url=p.get("pageURL"),
                        author=p.get("user", "unknown"),
                        license_name="Pixabay License",
                        license_url="https://pixabay.com/service/license-summary/",
                        media_type="image",
                        width=p.get("imageWidth", 0),
                        height=p.get("imageHeight", 0),
                        attribution_required=False,
                        tags=[t.strip() for t in p.get("tags", "").split(",") if t.strip()],
                        query=query
                    ))
        except Exception as e:
            logger.warning(f"Pixabay search failed for '{query}': {type(e).__name__}")
            
        return results
