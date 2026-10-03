from typing import List

from backend.app.core.config import settings
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import RESULTS_PER_PAGE, USER_AGENT, AssetProvider, pick_video_file
from backend.app.services.assets.search_cache import normalize_query


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
        headers = {"User-Agent": USER_AGENT}
        q = normalize_query(query)

        try:
            # 1. Search Videos
            data = self._get_json(
                "https://pixabay.com/api/videos/",
                params={"key": self.api_key, "q": q, "orientation": px_orientation, "per_page": RESULTS_PER_PAGE},
                headers=headers,
            )
            for v in (data or {}).get("hits", []):
                vds = v.get("videos", {}) or {}
                best_file = pick_video_file([vds.get(k) for k in ("large", "medium", "small", "tiny")], url_key="url")
                if not best_file:
                    continue

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
                    width=best_file.get("width") or 0,
                    height=best_file.get("height") or 0,
                    duration=v.get("duration", 0.0),
                    attribution_required=False,
                    tags=[t.strip() for t in v.get("tags", "").split(",") if t.strip()],
                    query=query,
                    preview_image_url=f"https://i.vimeocdn.com/video/{v['picture_id']}_295x166.jpg" if v.get("picture_id") else None  # noqa: E501
                ))

            # 2. Search Images
            data = self._get_json(
                "https://pixabay.com/api/",
                params={"key": self.api_key, "q": q, "orientation": px_orientation, "per_page": RESULTS_PER_PAGE, "image_type": "photo"},  # noqa: E501
                headers=headers,
            )
            for p in (data or {}).get("hits", []):
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
                    query=query,
                    preview_image_url=p.get("webformatURL", p.get("previewURL"))
                ))
        except Exception as e:
            logger.warning(f"Pixabay search failed for '{query}': {type(e).__name__}")

        return results
