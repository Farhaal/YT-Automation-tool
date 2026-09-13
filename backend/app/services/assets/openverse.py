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
            resp = httpx.get(
                "https://api.openverse.engineering/v1/images/",
                params={"q": query, "page_size": 5},
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                for p in data.get("results", []):
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(p["id"]),
                        asset_key=f"{self.name}:{p['id']}",
                        media_url=p.get("url"),
                        source_page_url=p.get("foreign_landing_url"),
                        author=p.get("creator", "unknown"),
                        license_name=p.get("license", "unknown").upper(),
                        license_url=p.get("license_url"),
                        media_type="image",
                        width=p.get("width", 0) or 0,
                        height=p.get("height", 0) or 0,
                        attribution_required=True,
                        attribution_text=p.get("attribution"),
                        query=query
                    ))
        except Exception as e:
            logger.warning(f"Openverse search failed for '{query}': {type(e).__name__}")
            
        return results
