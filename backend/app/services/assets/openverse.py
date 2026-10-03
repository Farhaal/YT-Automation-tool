from typing import List

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import RESULTS_PER_PAGE, USER_AGENT, AssetProvider
from backend.app.services.assets.search_cache import normalize_query


class OpenverseProvider(AssetProvider):
    def __init__(self):
        super().__init__("Openverse")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        results = []
        try:
            data = self._get_json(
                "https://api.openverse.org/v1/images/",
                headers={"User-Agent": USER_AGENT},
                params={"q": normalize_query(query), "page_size": RESULTS_PER_PAGE},
                timeout=8.0,
                follow_redirects=True
            )
            if data:
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
                        query=query,
                        preview_image_url=p.get("thumbnail")
                    ))
        except Exception as e:
            logger.warning(f"Openverse search failed for '{query}': {type(e).__name__}")
            
        return results
