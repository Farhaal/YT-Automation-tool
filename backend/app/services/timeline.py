import json
import jsonschema
from typing import List, Dict, Any
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
            
    def assemble(self, audio_path: str, audio_duration: float, words: List[Dict[str, Any]], scenes: List[Dict[str, Any]]) -> Dict[str, Any]:
        timeline_scenes = []
        for i, scene in enumerate(scenes):
            asset_meta = scene.get("asset")
            timeline_asset = None
            if asset_meta:
                timeline_asset = {
                    "type": asset_meta["media_type"],
                    "path": str(asset_meta["local_path"]),
                    "source": asset_meta["provider"],
                    "author": asset_meta["author"],
                    "license": asset_meta["license_name"],
                    "url": asset_meta.get("source_page_url") or asset_meta.get("media_url", "")
                }
                
            transition = None
            # Only add a transition if it's not the last scene
            if i < len(scenes) - 1:
                # Add crossfade unless scene is very short
                dur = scene["end"] - scene["start"]
                if dur > 1.0:
                    transition = {"type": "crossfade", "duration": 0.4}
                    
            timeline_scene = {
                "id": f"s{i+1}",
                "start": scene["start"],
                "end": scene["end"],
                "text": scene["text"],
                "asset": timeline_asset,
                "motion": "kenburns_in",
            }
            if transition:
                timeline_scene["transition_out"] = transition
                
            timeline_scenes.append(timeline_scene)
            
        # Ensure words have only the required fields for captions
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
        
        # Validate against schema
        try:
            jsonschema.validate(instance=timeline, schema=self.schema)
        except jsonschema.exceptions.ValidationError as e:
            logger.error(f"Timeline validation failed: {e.message}")
            raise ValueError(f"Invalid timeline generated: {e.message}")
            
        return timeline
