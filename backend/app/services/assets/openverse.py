import httpx
from typing import List
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import AssetProvider

class OpenverseProvider(AssetProvider):
    def __init__(self):
        super().__init__("Openverse")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        results = []
        try:
            # Mostly images, videos are less stable in Openverse
            resp = httpx.get(
                "https://api.openverse.engineering/v1/images/",
                params={"q": query, "page_size": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get("results", []):
                    results.append(AssetMetadata(
                        id=str(p["id"]),
                        provider=self.name,
                        url=p.get("url"),
                        author=p.get("creator", "Unknown"),
                        license=p.get("license", "CC"),
                        media_type="image",
                        width=p.get("width", 0) or 0,
                        height=p.get("height", 0) or 0,
                        attribution_required=True
                    ))
        except Exception as e:
            logger.warning(f"Openverse search failed for '{query}': {type(e).__name__}")
            
        return results
