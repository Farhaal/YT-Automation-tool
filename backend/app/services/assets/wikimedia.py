import re
from typing import List

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import RESULTS_PER_PAGE, TARGET_LONG_SIDE, USER_AGENT, AssetProvider
from backend.app.services.assets.search_cache import normalize_query


class WikimediaProvider(AssetProvider):
    def __init__(self):
        super().__init__("Wikimedia")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        results = []
        try:
            data = self._get_json(
                "https://commons.wikimedia.org/w/api.php",
                headers={"User-Agent": USER_AGENT},
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {normalize_query(query)}",
                    "gsrnamespace": 6,
                    "gsrlimit": RESULTS_PER_PAGE,
                    "srsort": "relevance",
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    # A ~1080p rendition to download instead of multi-megapixel originals.
                    "iiurlwidth": TARGET_LONG_SIDE,
                    "format": "json"
                },
                timeout=5.0,
                follow_redirects=True
            )
            if data:
                pages = data.get("query", {}).get("pages", {})
                
                query_tokens = set(re.findall(r'\w+', query.lower()))
                
                for page_id, page in pages.items():
                    info = page.get("imageinfo", [{}])[0]
                    if not info or "url" not in info:
                        continue
                    
                    title = page.get("title", "Image")
                    title_tokens = set(re.findall(r'\w+', title.lower()))
                    if query_tokens and not query_tokens.intersection(title_tokens):
                        continue
                        
                    meta = info.get("extmetadata", {})
                    author = meta.get("Artist", {}).get("value", "unknown")
                    author = re.sub('<[^<]+>', '', author)
                    
                    license_name = meta.get("LicenseShortName", {}).get("value", "unknown")
                    license_url = meta.get("LicenseUrl", {}).get("value")
                    desc_url = info.get("descriptionurl")
                    
                    attribution_text = f'"{title}" by {author} is licensed under {license_name}.'
                    if desc_url:
                        attribution_text += f' Source: {desc_url}'
                    
                    thumb = info.get("thumburl")
                    media_url = thumb if thumb and (info.get("width") or 0) > TARGET_LONG_SIDE else info["url"]
                    preview = thumb.replace(f"/{TARGET_LONG_SIDE}px-", "/400px-") if thumb else info["url"]

                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(page_id),
                        asset_key=f"{self.name}:{page_id}",
                        media_url=media_url,
                        source_page_url=desc_url,
                        author=author,
                        license_name=license_name,
                        license_url=license_url,
                        media_type="image",
                        width=info.get("width", 0),
                        height=info.get("height", 0),
                        attribution_required=True,
                        attribution_text=attribution_text,
                        query=query,
                        preview_image_url=preview
                    ))
        except Exception as e:
            logger.warning(f"Wikimedia search failed for '{query}': {type(e).__name__}")
            
        return results
