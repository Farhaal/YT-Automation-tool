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

    def rank_assets(self, assets: List[AssetMetadata], orientation: str, scene_duration: float) -> List[AssetMetadata]:
        def score(a: AssetMetadata) -> tuple:
            # 1. Query priority (lower index is better, use negative to sort descending properly)
            pri_query = -a.query_priority
            
            # 2. Result position (lower index is better)
            pri_pos = -a.result_position
            
            # 3. Media Type
            pri_media = 1 if a.media_type == "video" else 0
            
            # 4. Orientation match
            is_landscape = a.width > a.height
            is_portrait = a.height > a.width
            is_square = a.width == a.height
            
            pri_orientation = 0
            if orientation == "landscape" and is_landscape:
                pri_orientation = 1
            elif orientation == "portrait" and is_portrait:
                pri_orientation = 1
            elif orientation == "square" and is_square:
                pri_orientation = 1
                
            # 5. Resolution (Width)
            pri_res = a.width
            
            # 6. Duration suitability
            pri_dur = 0
            if a.media_type == "video" and a.duration > 0:
                if a.duration >= scene_duration:
                    pri_dur = 1
                else:
                    pri_dur = -1
                    
            # 7. Attribution preference
            pri_attr = 1 if not a.attribution_required else 0
            
            return (pri_query, pri_pos, pri_media, pri_orientation, pri_res, pri_dur, pri_attr)

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
                
            scene_duration = scene.get("end", 0.0) - scene.get("start", 0.0)
            candidates = []
            seen_keys = set()
            
            for query_idx, query in enumerate(queries):
                for provider in self.providers:
                    res = provider.search(query, orientation=orientation)
                    for pos_idx, a in enumerate(res):
                        a.query = query
                        a.query_priority = query_idx
                        a.result_position = pos_idx
                        
                        # Deduplicate by global composite asset_key
                        if a.asset_key not in seen_keys:
                            seen_keys.add(a.asset_key)
                            candidates.append(a)
                            
                    if len(candidates) > 50:
                        break
                if len(candidates) > 50:
                    break
                    
            ranked = self.rank_assets(candidates, orientation, scene_duration)
            
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
