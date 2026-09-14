from typing import List

import httpx

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import USER_AGENT, AssetProvider


class OpenverseProvider(AssetProvider):
    def __init__(self):
        super().__init__("Openverse")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        results = []
        try:
            resp = httpx.get(
                "https://api.openverse.org/v1/images/",
                headers={"User-Agent": USER_AGENT},
                params={"q": query, "page_size": 5},
                timeout=8.0,
                follow_redirects=True
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
                        title=p.get("title"),
                        tags=[t.get("name") for t in p.get("tags", []) if isinstance(t, dict)],
                        query=query
                    ))
        except Exception as e:
            logger.warning(f"Openverse search failed for '{query}': {type(e).__name__}")
            
        return results
