from typing import List

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import RESULTS_PER_PAGE, USER_AGENT, AssetProvider, pick_video_file
from backend.app.services.assets.search_cache import normalize_query


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
        params = {"query": normalize_query(query), "orientation": orientation, "per_page": RESULTS_PER_PAGE}
        try:
            # 1. Search Videos
            data = self._get_json("https://api.pexels.com/videos/search", params=params, headers=self.headers)
            for v in (data or {}).get("videos", []):
                best_file = pick_video_file(v.get("video_files", []), url_key="link")
                if not best_file:
                    continue

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
                    width=best_file.get("width") or 0,
                    height=best_file.get("height") or 0,
                    duration=v.get("duration", 0.0),
                    attribution_required=False,
                    query=query,
                    preview_image_url=v.get("image")
                ))

            # 2. Search Images (Fallback)
            data = self._get_json("https://api.pexels.com/v1/search", params=params, headers=self.headers)
            for p in (data or {}).get("photos", []):
                results.append(AssetMetadata(
                    provider=self.name,
                    provider_asset_id=str(p["id"]),
                    asset_key=f"{self.name}:{p['id']}",
                    # large2x is ~1880px wide: right size for a 1080p export.
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
