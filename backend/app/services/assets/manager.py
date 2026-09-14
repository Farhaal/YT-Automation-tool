from pathlib import Path
from typing import Any, Dict, List, Optional

from backend.app.core.paths import DATA
from backend.app.services.assets import AssetMetadata
from backend.app.services.assets.openverse import OpenverseProvider
from backend.app.services.assets.pexels import PexelsProvider
from backend.app.services.assets.pixabay import PixabayProvider
from backend.app.services.assets.wikimedia import WikimediaProvider


class AssetManager:
    def __init__(self, cache_dir: Optional[Path] = None):
        self.fast_tier = [PexelsProvider(), PixabayProvider()]
        self.slow_tier = [OpenverseProvider(), WikimediaProvider()]
        self.providers = self.fast_tier + self.slow_tier
        self.used_asset_keys = set()
        self.cache_dir = cache_dir or (DATA / "assets")
        self.cache_dir.mkdir(parents=True, exist_ok=True)

    def rank_assets(self, assets: List[AssetMetadata], orientation: str, scene_duration: float, scene_query: str = "") -> List[AssetMetadata]:  # noqa: E501
        import re
        
        query_tokens = set(re.findall(r'\w+', scene_query.lower()))
        
        def score(a: AssetMetadata) -> tuple:
            # 0. Relevance Score (higher is better)
            # Compare scene query tokens against asset fields
            asset_text = " ".join([
                a.title or "",
                a.description or "",
                a.query or "",
                " ".join(a.tags or [])
            ]).lower()
            asset_tokens = set(re.findall(r'\w+', asset_text))
            
            pri_relevance = len(query_tokens.intersection(asset_tokens)) if query_tokens else 1
            
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
            
            # If zero overlap, rank it absolutely last by negating the relevance score or putting a huge penalty
            if pri_relevance == 0:
                return (-1, pri_query, pri_pos, pri_media, pri_orientation, pri_res, pri_dur, pri_attr)
                
            return (pri_relevance, pri_query, pri_pos, pri_media, pri_orientation, pri_res, pri_dur, pri_attr)

        # Filter out used assets by composite asset_key
        unused = [a for a in assets if a.asset_key not in self.used_asset_keys]
        if not unused:
            unused = assets
            
        return sorted(unused, key=score, reverse=True)

    def _concurrent_search(self, providers, query: str, query_idx: int, orientation: str) -> List[AssetMetadata]:
        import concurrent.futures
        import logging
        
        candidates = []
        seen_keys = set()

        def _search_provider(provider):
            try:
                return provider.search(query, orientation=orientation)
            except Exception as e:
                logging.warning(f"Provider {provider.name} search failed: {e}")
                return []

        if not providers:
            return []

        with concurrent.futures.ThreadPoolExecutor(max_workers=len(providers)) as executor:
            future_to_prov = {executor.submit(_search_provider, p): p for p in providers}
            for future in concurrent.futures.as_completed(future_to_prov):
                res = future.result()
                for pos_idx, a in enumerate(res):
                    a.query = query
                    a.query_priority = query_idx
                    a.result_position = pos_idx
                    if a.asset_key not in seen_keys:
                        seen_keys.add(a.asset_key)
                        candidates.append(a)
        return candidates

    def _rank_and_download(self, candidates, orientation, scene_duration, full_scene_query, scene_text="", topic=""):
        from backend.app.core.config import settings
        from backend.app.services.verification import verify_scene_candidates
        
        ranked = self.rank_assets(candidates, orientation, scene_duration, full_scene_query)
        best_asset = None
        backup_asset = None
        
        # --- VERIFICATION STEP ---
        if settings.ENABLE_VISUAL_VERIFICATION and settings.LLM_API_KEY:
            top_k = [c for c in ranked if c.preview_image_url][:4]
            if top_k:
                verification_result = verify_scene_candidates(
                    scene_text=scene_text,
                    topic=topic,
                    candidates=top_k,
                    openrouter_key=settings.LLM_API_KEY,
                    vision_model=settings.VISION_MODEL
                )
                if verification_result:
                    best_idx = verification_result["best_index"]
                    verified_best = top_k[best_idx]
                    verified_best.match_score = verification_result["score"]
                    verified_best.match_reason = verification_result["reason"]
                    
                    # Move verified best to the front of ranked list
                    ranked.remove(verified_best)
                    ranked.insert(0, verified_best)
                else:
                    # Mark top ranked as needing review if verification fails
                    if ranked:
                        ranked[0].match_score = 0.0
                        ranked[0].match_reason = "Verification failed or skipped."
        # -------------------------
        
        for asset in ranked:
            provider = next((p for p in self.providers if p.name == asset.provider), None)
            if not provider:
                continue
            
            local_path = provider.download(asset, self.cache_dir)
            if local_path:
                if not best_asset:
                    best_asset = asset
                    self.used_asset_keys.add(asset.asset_key)
                elif not backup_asset:
                    backup_asset = asset
                    break
        return best_asset, backup_asset

    def select_assets_for_scenes(self, scenes: List[Dict[str, Any]], orientation: str = "landscape") -> List[Dict[str, Any]]:  # noqa: E501
        for scene in scenes:
            queries = scene.get("queries", [])
            if not queries:
                queries = [scene["text"]]
                
            # Cap at 2 queries max
            queries = queries[:2]
            scene_duration = scene.get("end", 0.0) - scene.get("start", 0.0)
            full_scene_query = " ".join(queries)
            
            best_asset = None
            backup_asset = None
            
            for query_idx, query in enumerate(queries):
                # Phase 1: Fast Tier
                candidates = self._concurrent_search(self.fast_tier, query, query_idx, orientation)
                if candidates:
                    best_asset, backup_asset = self._rank_and_download(
                        candidates, orientation, scene_duration, full_scene_query,
                        scene_text=scene.get("text", ""), topic=scene.get("topic", "")
                    )
                
                # Phase 2: Slow Tier (only if fast tier yielded nothing usable)
                if not best_asset:
                    slow_candidates = self._concurrent_search(self.slow_tier, query, query_idx, orientation)
                    if slow_candidates:
                        best_asset, backup_asset = self._rank_and_download(
                            slow_candidates, orientation, scene_duration, full_scene_query,
                            scene_text=scene.get("text", ""), topic=scene.get("topic", "")
                        )
                
                # Early exit if we found a good asset
                if best_asset:
                    break
                        
            scene["asset"] = best_asset.model_dump() if best_asset else None
            scene["backup_asset"] = backup_asset.model_dump() if backup_asset else None
            
            # Carry over verification flags if they exist
            if best_asset:
                score = getattr(best_asset, "match_score", None)
                if score is not None:
                    scene["match_score"] = score
                    scene["match_reason"] = getattr(best_asset, "match_reason", None)
                    scene["needs_review"] = (score < 0.5)
            
        return scenes
