import re

with open('backend/app/api/routes.py', 'r') as f:
    content = f.read()

replacement = '''        update(40, "Segmenting scenes", log_msg="Analyzing transcript with NLP to segment scenes and extract visual search queries...")
        from backend.app.services.nlp import process_script_to_scenes
        job_state = {"dead_providers": set(), "llm_failover_log": [], "llm_warnings": []}
        scenes = process_script_to_scenes(words, pace=pace, job_state=job_state)
        
        update(60, "Finding assets", log_msg=f"Searching Pexels, Pixabay, Openverse, and Wikimedia for {len(scenes)} scenes...")
        from backend.app.services.assets.manager import AssetManager
        
        s = load_settings()
        import os
        if s.get("pexels_key"): os.environ["PEXELS_API_KEY"] = s["pexels_key"]
        if s.get("pixabay_key"): os.environ["PIXABAY_API_KEY"] = s["pixabay_key"]
        
        asset_manager = AssetManager(cache_dir=DATA / "assets")
        scenes = asset_manager.select_assets_for_scenes(scenes, orientation=aspect_ratio, job_state=job_state)
        
        # Determine llm_warning
        llm_warning = None
        if job_state["llm_warnings"]:
            # If all failed
            llm_warning = {
                "used_provider": job_state.get("used_provider"),
                "failed": job_state["llm_failover_log"]
            }
            job_manager.update_job(job_id, llm_warning=llm_warning)'''

start_pattern = r'        update\(40, "Segmenting scenes".*?scenes = asset_manager\.select_assets_for_scenes\(scenes, orientation=aspect_ratio\)'

new_content = re.sub(start_pattern, replacement, content, flags=re.DOTALL)

with open('backend/app/api/routes.py', 'w') as f:
    f.write(new_content)
