import re

with open('backend/app/services/verification.py', 'r') as f:
    content = f.read()

replacement = r'''def verify_scene_candidates(
    scene_text: str,
    topic: str,
    candidates: List[AssetMetadata],
    job_state: Optional[Dict] = None
) -> Optional[Dict]:
    """
    Calls OpenRouter vision model to score and pick the best image candidate for a scene.
    Returns: {"best_index": int, "score": float, "reason": str} or None on any failure.
    """
    if not candidates:
        return None

    # Filter candidates to only those with previews
    verifiable = [c for c in candidates if c.preview_image_url]
    if not verifiable:
        return None

    system_prompt = (
        "You are an AI video editor selecting the best stock footage for a video scene. "
        "You will be given the overall video topic, the specific scene text, and several image thumbnails "
        "representing video/image candidates.\n\n"
        "Your task: evaluate which image BEST visually matches the meaning and tone of the scene text. "
        "Return STRICTLY a JSON object with this exact schema (no markdown, no quotes around the json):\n"
        "{\n"
        '  "best_index": <int>,\n'
        '  "score": <float between 0.0 and 1.0, where 1.0 is perfect match>,\n'
        '  "reason": "<str: brief 1-sentence explanation of why it fits>"\n'
        "}"
    )
    # We will base64 all verifiable thumbnails so they work for Gemini as well as any other provider.
    content_payload = [
        {"type": "text", "text": f"Video Topic: {topic}\nScene Text: {scene_text}\n\nCandidates:"}
    ]

    for i, c in enumerate(verifiable):
        content_payload.append({"type": "text", "text": f"Candidate {i}:"})
        img_url = c.preview_image_url
        b64_url = _fetch_image_base64(c.preview_image_url)
        if b64_url:
            img_url = b64_url
        content_payload.append({"type": "image_url", "image_url": {"url": img_url}})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content_payload}
    ]

    from backend.app.services.nlp import call_llm, AllProvidersFailed
    
    try:
        result_text = call_llm(messages, temperature=0.1, require_vision=True, job_state=job_state)
        
        # Strip potential markdown blocks if the model ignored response_format
        result_text = result_text.strip()
        if result_text.startswith("`json"):
            result_text = result_text[7:]
        if result_text.startswith("`"):
            result_text = result_text[3:]
        if result_text.endswith("`"):
            result_text = result_text[:-3]
            
        result = json.loads(result_text.strip())
        
        best_index = int(result.get("best_index", 0))
        score = float(result.get("score", 0.0))
        reason = str(result.get("reason", ""))
        
        # Map verifiable index back to original candidates index
        if 0 <= best_index < len(verifiable):
            orig_candidate = verifiable[best_index]
            actual_index = candidates.index(orig_candidate)
            return {
                "best_index": actual_index,
                "score": score,
                "reason": reason
            }
            
        return None
        
    except AllProvidersFailed:
        return None
    except Exception as e:
        logger.warning(f"Exception during vision verification: {type(e).__name__} - {e}")
        return None
'''

start_pattern = r'def verify_scene_candidates\(.*?\)\s*->\s*Optional\[Dict\]:'
new_content = re.sub(start_pattern + r'.*?return None', replacement, content, flags=re.DOTALL)

with open('backend/app/services/verification.py', 'w') as f:
    f.write(new_content)
