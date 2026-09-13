import os
from pathlib import Path
from typing import List, Dict, Any, Tuple
from backend.app.core.paths import DATA
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.pexels import PexelsProvider
from backend.app.services.assets.pixabay import PixabayProvider
from backend.app.services.assets.openverse import OpenverseProvider
from backend.app.services.assets.wikimedia import WikimediaProvider

CACHE_DIR = str(DATA / "assets")
os.makedirs(CACHE_DIR, exist_ok=True)

class AssetManager:
    def __init__(self):
        self.providers = [
            PexelsProvider(),
            PixabayProvider(),
            OpenverseProvider(),
            WikimediaProvider()
        ]
        self.used_asset_ids = set()

    def rank_assets(self, assets: List[AssetMetadata], orientation: str) -> List[AssetMetadata]:
        def score(a: AssetMetadata) -> int:
            s = 0
            if a.media_type == "video":
                s += 50
            if a.width >= 1920:
                s += 20
            elif a.width >= 1080:
                s += 10
                
            # Orientation logic
            is_landscape = a.width > a.height
            is_portrait = a.height > a.width
            is_square = a.width == a.height
            
            if orientation == "landscape" and is_landscape:
                s += 15
            elif orientation == "portrait" and is_portrait:
                s += 15
            elif orientation == "square" and is_square:
                s += 15
                
            if not a.attribution_required:
                s += 5
                
            return s

        # Filter out used assets unless we have to fallback
        unused = [a for a in assets if a.id not in self.used_asset_ids]
        if not unused:
            unused = assets  # Fallback to used if absolutely necessary
            
        return sorted(unused, key=score, reverse=True)

    def select_assets_for_scenes(self, scenes: List[Dict[str, Any]], orientation: str = "landscape") -> List[Dict[str, Any]]:
        for scene in scenes:
            queries = scene.get("queries", [])
            if not queries:
                queries = [scene["text"]]
                
            candidates = []
            seen_ids = set()
            for query in queries:
                for provider in self.providers:
                    res = provider.search(query, orientation=orientation)
                    for a in res:
                        if a.id not in seen_ids:
                            seen_ids.add(a.id)
                            candidates.append(a)
                    if len(candidates) > 20:
                        break
                if len(candidates) > 20:
                    break
                    
            ranked = self.rank_assets(candidates, orientation)
            
            best_asset = None
            backup_asset = None
            
            for asset in ranked:
                # Find the provider instance that yielded this asset to download it
                provider = next(p for p in self.providers if p.name == asset.provider)
                local_path = provider.download(asset, CACHE_DIR)
                
                if local_path:
                    if not best_asset:
                        best_asset = asset
                        self.used_asset_ids.add(asset.id)
                    elif not backup_asset:
                        backup_asset = asset
                        break
                        
            scene["asset"] = best_asset.model_dump() if best_asset else None
            scene["backup_asset"] = backup_asset.model_dump() if backup_asset else None
            
        return scenes
