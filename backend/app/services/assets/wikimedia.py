import httpx
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
            # Simple Commons image search
            resp = httpx.get(
                "https://commons.wikimedia.org/w/api.php",
                params={
                    "action": "query",
                    "generator": "search",
                    "gsrsearch": f"filetype:bitmap {query}",
                    "gsrnamespace": 6,  # File namespace
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
                    author = meta.get("Artist", {}).get("value", "Unknown")
                    # strip HTML from author if present
                    import re
                    author = re.sub('<[^<]+>', '', author)
                    
                    results.append(AssetMetadata(
                        id=str(page_id),
                        provider=self.name,
                        url=info["url"],
                        author=author,
                        license=meta.get("LicenseShortName", {}).get("value", "CC"),
                        media_type="image",
                        width=info.get("width", 0),
                        height=info.get("height", 0),
                        attribution_required=True
                    ))
        except Exception as e:
            logger.warning(f"Wikimedia search failed for '{query}': {type(e).__name__}")
            
        return results
