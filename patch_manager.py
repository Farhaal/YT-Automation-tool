import re

with open('backend/app/services/assets/manager.py', 'r') as f:
    content = f.read()

content = content.replace(
    'def select_assets_for_scenes(self, scenes: List[Dict[str, Any]], orientation: str = "landscape") -> List[Dict[str, Any]]:',
    'def select_assets_for_scenes(self, scenes: List[Dict[str, Any]], orientation: str = "landscape", job_state: Optional[Dict] = None) -> List[Dict[str, Any]]:'
)

content = content.replace(
    'def _rank_and_download(self, candidates, orientation, scene_duration, full_scene_query, scene_text="", topic=""):',
    'def _rank_and_download(self, candidates, orientation, scene_duration, full_scene_query, scene_text="", topic="", job_state=None):'
)

content = content.replace(
    'best_asset, backup_asset = self._rank_and_download(\n                        candidates, orientation, scene_duration, full_scene_query,\n                        scene_text=scene.get("text", ""), topic=scene.get("topic", "")\n                    )',
    'best_asset, backup_asset = self._rank_and_download(\n                        candidates, orientation, scene_duration, full_scene_query,\n                        scene_text=scene.get("text", ""), topic=scene.get("topic", ""), job_state=job_state\n                    )'
)
content = content.replace(
    'best_asset, backup_asset = self._rank_and_download(\n                            slow_candidates, orientation, scene_duration, full_scene_query,\n                            scene_text=scene.get("text", ""), topic=scene.get("topic", "")\n                        )',
    'best_asset, backup_asset = self._rank_and_download(\n                            slow_candidates, orientation, scene_duration, full_scene_query,\n                            scene_text=scene.get("text", ""), topic=scene.get("topic", ""), job_state=job_state\n                        )'
)

# Replace the enable_visual_verification check
old_check = '''        if settings.ENABLE_VISUAL_VERIFICATION and settings.LLM_API_KEY:
            top_k = [c for c in ranked if c.preview_image_url][:4]
            if top_k:
                verification_result = verify_scene_candidates(
                    scene_text=scene_text,
                    topic=topic,
                    candidates=top_k,
                    api_key=settings.LLM_API_KEY,
                    vision_model=settings.VISION_MODEL
                )'''
new_check = '''        if settings.ENABLE_VISUAL_VERIFICATION:
            top_k = [c for c in ranked if c.preview_image_url][:4]
            if top_k:
                verification_result = verify_scene_candidates(
                    scene_text=scene_text,
                    topic=topic,
                    candidates=top_k,
                    job_state=job_state
                )'''
content = content.replace(old_check, new_check)

with open('backend/app/services/assets/manager.py', 'w') as f:
    f.write(content)
