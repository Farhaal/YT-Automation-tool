import httpx
import re
from typing import List
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.base import AssetProvider

class WikimediaProvider(AssetProvider):
    def __init__(self):
        super().__init__("Wikimedia")

    def search(self, query: str, orientation: str = "landscape") -> List[AssetMetadata]:
        results = []
        try:
            resp = httpx.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {query}",
                    "gsrnamespace": 6,
                    "gsrlimit": 5,
                    "prop": "imageinfo",
                    "iiprop": "url|size|extmetadata",
                    "format": "json"
                },
                timeout=5.0
            )
            if resp.status_code == 200:
                data = resp.json()
                pages = data.get("query", {}).get("pages", {})
                for page_id, page in pages.items():
                    info = page.get("imageinfo", [{}])[0]
                    if not info or "url" not in info:
                        continue
                    
                    meta = info.get("extmetadata", {})
                    author = meta.get("Artist", {}).get("value", "unknown")
                    author = re.sub('<[^<]+>', '', author)
                    
                    license_name = meta.get("LicenseShortName", {}).get("value", "unknown")
                    license_url = meta.get("LicenseUrl", {}).get("value")
                    desc_url = info.get("descriptionurl")
                    title = page.get("title", "Image")
                    
                    attribution_text = f'"{title}" by {author} is licensed under {license_name}.'
                    if desc_url:
                        attribution_text += f' Source: {desc_url}'
                    
                    results.append(AssetMetadata(
                        provider=self.name,
                        provider_asset_id=str(page_id),
                        asset_key=f"{self.name}:{page_id}",
                        media_url=info["url"],
                        source_page_url=desc_url,
                        author=author,
                        license_name=license_name,
                        license_url=license_url,
                        media_type="image",
                        width=info.get("width", 0),
                        height=info.get("height", 0),
                        attribution_required=True,
                        attribution_text=attribution_text,
                        query=query
                    ))
        except Exception as e:
            logger.warning(f"Wikimedia search failed for '{query}': {type(e).__name__}")
            
        return results
