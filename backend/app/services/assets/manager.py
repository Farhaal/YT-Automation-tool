import os
from pathlib import Path
from typing import List, Dict, Any, Optional
from backend.app.core.paths import DATA
from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.pexels import PexelsProvider
from backend.app.services.assets.pixabay import PixabayProvider
from backend.app.services.assets.openverse import OpenverseProvider
from backend.app.services.assets.wikimedia import WikimediaProvider

class AssetManager:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.providers = [
            PexelsProvider(),
            PixabayProvider(),
            OpenverseProvider(),
            WikimediaProvider()
        ]
        self.used_asset_keys = set()
        self.cache_dir = cache_dir or (DATA / "assets")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def rank_assets(self, assets: List[AssetMetadata], orientation: str) -> List[AssetMetadata]:
        def score(a: AssetMetadata) -> int:
            s = 0
            if a.media_type == "video":
                s += 50
            if a.width >= 1920:
                s += 20
            elif a.width >= 1080:
                s += 10
                
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

        # Filter out used assets by composite asset_key
        unused = [a for a in assets if a.asset_key not in self.used_asset_keys]
        if not unused:
            unused = assets
            
        return sorted(unused, key=score, reverse=True)

    def select_assets_for_scenes(self, scenes: List[Dict[str, Any]], orientation: str = "landscape") -> List[Dict[str, Any]]:
        for scene in scenes:
            queries = scene.get("queries", [])
            if not queries:
                queries = [scene["text"]]
                
            candidates = []
            seen_keys = set()
            for query in queries:
                for provider in self.providers:
                    res = provider.search(query, orientation=orientation)
                    for a in res:
                        # Deduplicate by global composite asset_key
                        if a.asset_key not in seen_keys:
                            seen_keys.add(a.asset_key)
                            candidates.append(a)
                    if len(candidates) > 20:
                        break
                if len(candidates) > 20:
                    break
                    
            ranked = self.rank_assets(candidates, orientation)
            
            best_asset = None
            backup_asset = None
            
            for asset in ranked:
                provider = next(p for p in self.providers if p.name == asset.provider)
                local_path = provider.download(asset, self.cache_dir)
                
                if local_path:
                    if not best_asset:
                        best_asset = asset
                        self.used_asset_keys.add(asset.asset_key)
                    elif not backup_asset:
                        backup_asset = asset
                        break
                        
            scene["asset"] = best_asset.model_dump() if best_asset else None
            scene["backup_asset"] = backup_asset.model_dump() if backup_asset else None
            
        return scenes
