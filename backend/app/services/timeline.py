import json
import jsonschema
from typing import List, Dict, Any, Optional
from pathlib import Path
from backend.app.core.logger import logger

# Assuming SHARED is accessible, we can construct the path.
# Let's import BASE_DIR and construct it, or just use a relative path if needed.
from backend.app.core.paths import ROOT
SCHEMA_PATH = ROOT / "shared" / "timeline.schema.json"

class TimelineAssembler:
    def __init__(self, schema_path: Path = None):
        path_to_load = schema_path or SCHEMA_PATH
        with open(path_to_load, "r", encoding="utf-8") as f:
            self.schema = json.load(f)
            
    def _map_asset(self, asset_meta: Optional[Dict[str, Any]]) -> Optional[Dict[str, Any]]:
        if not asset_meta:
            return None
        return {
            "type": asset_meta["media_type"],
            "path": str(asset_meta["local_path"]) if asset_meta.get("local_path") else None,
            "source": asset_meta["provider"],
            "author": asset_meta["author"],
            "license": asset_meta["license_name"],
            "url": asset_meta.get("source_page_url") or asset_meta.get("media_url", ""),
            "asset_key": asset_meta.get("asset_key", ""),
            "provider_asset_id": asset_meta.get("provider_asset_id", ""),
            "license_url": asset_meta.get("license_url"),
            "attribution_required": asset_meta.get("attribution_required", False),
            "attribution_text": asset_meta.get("attribution_text")
        }

    def assemble(self, audio_path: str, audio_duration: float, words: List[Dict[str, Any]], scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        timeline_scenes = []
        for i, scene in enumerate(scenes):
            asset_meta = scene.get("asset")
            backup_meta = scene.get("backup_asset")
            
            timeline_asset = self._map_asset(asset_meta)
            timeline_backup = self._map_asset(backup_meta)
                
            transition = None
            if i < len(scenes) - 1:
                dur = scene["end"] - scene["start"]
                if dur > 1.0:
                    transition = {"type": "crossfade", "duration": 0.4}
                    
            timeline_scene = {
                "id": f"s{i+1}",
                "start": scene["start"],
                "end": scene["end"],
                "text": scene["text"],
                "asset": timeline_asset,
                "backup_asset": timeline_backup,
                "motion": "kenburns_in",
            }
            if transition:
                timeline_scene["transition_out"] = transition
                
            timeline_scenes.append(timeline_scene)
            
        captions = []
        for w in words:
            captions.append({
                "word": w["word"],
                "start": w["start"],
                "end": w["end"]
            })
            
        timeline = {
            "version": 1,
            "resolution": {"width": 1080, "height": 1920, "fps": 30},
            "audio": {"path": str(audio_path), "duration": audio_duration},
            "scenes": timeline_scenes,
            "captions": captions,
            "popups": []
        }
        
        # Schema Validation
        try:
            jsonschema.validate(instance=timeline, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Timeline validation failed: {e.message}")
            raise ValueError(f"Invalid timeline generated: {e.message}")
            
        # Semantic Validation
        last_scene_end = 0.0
        for i, sc in enumerate(timeline_scenes):
            if sc["start"] > sc["end"]:
                raise ValueError(f"Scene {sc['id']} has start > end ({sc['start']} > {sc['end']})")
            if sc["start"] < last_scene_end and i != 0:
                raise ValueError(f"Scene {sc['id']} is not chronological")
            if sc["end"] > audio_duration:
                raise ValueError(f"Scene {sc['id']} end ({sc['end']}) exceeds audio_duration ({audio_duration})")
                
            last_scene_end = max(last_scene_end, sc["end"])
            
            # Transition check
            if "transition_out" in sc:
                t_dur = sc["transition_out"]["duration"]
                s_dur = sc["end"] - sc["start"]
                if t_dur >= s_dur:
                    raise ValueError(f"Scene {sc['id']} transition duration ({t_dur}) must be less than scene duration ({s_dur})")

        last_word_end = 0.0
        for i, w in enumerate(captions):
            if w["start"] > w["end"]:
                raise ValueError(f"Caption word '{w['word']}' has start > end")
            if w["start"] < last_word_end and i != 0:
                raise ValueError(f"Caption word '{w['word']}' is not chronological")
            if w["end"] > audio_duration:
                raise ValueError(f"Caption word '{w['word']}' end exceeds audio_duration")
            last_word_end = max(last_word_end, w["end"])
            
        return timeline
