import re

with open('backend/app/api/routes.py', 'r') as f:
    content = f.read()

# 1. Update GenerateRequest
content = content.replace('pace: str = "balanced"\n', 'pace: str = "balanced"\n    punchy_hook: bool = True\n')

# 2. Update run_job_pipeline_sync signature
content = content.replace('pace: str = "balanced"):  # noqa: E501', 'pace: str = "balanced", punchy_hook: bool = True):  # noqa: E501')

# 3. Update process_script_to_scenes call inside run_job_pipeline_sync
content = content.replace('scenes = process_script_to_scenes(words, pace=pace, job_state=job_state)', 'scenes = process_script_to_scenes(words, pace=pace, punchy_hook=punchy_hook, job_state=job_state)')

# 4. Update /generate/script task add
content = content.replace('background_tasks.add_task(run_job_pipeline_sync, job_id, loop, req.aspect_ratio, req.enable_motion, req.pace)', 'background_tasks.add_task(run_job_pipeline_sync, job_id, loop, req.aspect_ratio, req.enable_motion, req.pace, req.punchy_hook)')

# 5. Update /generate/audio signature
content = content.replace('pace: str = Form("balanced")):', 'pace: str = Form("balanced"), punchy_hook: bool = Form(True)):')

# 6. Update /generate/audio task add
content = content.replace('background_tasks.add_task(run_job_pipeline_sync, job_id, loop, aspect_ratio, enable_motion, pace)', 'background_tasks.add_task(run_job_pipeline_sync, job_id, loop, aspect_ratio, enable_motion, pace, punchy_hook)')

with open('backend/app/api/routes.py', 'w') as f:
    f.write(content)
