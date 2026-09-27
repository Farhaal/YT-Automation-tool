import json
import httpx
import base64
from typing import List, Optional, Dict

from backend.app.core.logger import logger
from backend.app.services.assets import AssetMetadata
from backend.app.core.config import settings

def _fetch_image_base64(url: str) -> Optional[str]:
    try:
        resp = httpx.get(url, timeout=5.0)
        if resp.status_code == 200:
            ctype = resp.headers.get("content-type", "image/jpeg")
            b64 = base64.b64encode(resp.content).decode("utf-8")
            return f"data:{ctype};base64,{b64}"
    except Exception:
        pass
    return None

def verify_scene_candidates(
    scene_text: str,
    topic: str,
    candidates: List[AssetMetadata],
    api_key: str,
    vision_model: str
) -> Optional[Dict]:
    """
    Calls OpenRouter vision model to score and pick the best image candidate for a scene.
    Returns: {"best_index": int, "score": float, "reason": str} or None on any failure.
    """
    if not api_key or not vision_model or not candidates:
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

    provider = (settings.LLM_PROVIDER or "").lower()
    is_gemini = provider in ["gemini", "google"]
    
    content = [
        {"type": "text", "text": f"Video Topic: {topic}\nScene Text: {scene_text}\n\nCandidates:"}
    ]

    for i, c in enumerate(verifiable):
        content.append({"type": "text", "text": f"Candidate {i}:"})
        img_url = c.preview_image_url
        if is_gemini:
            b64_url = _fetch_image_base64(c.preview_image_url)
            if b64_url:
                img_url = b64_url
        content.append({"type": "image_url", "image_url": {"url": img_url}})

    messages = [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": content}
    ]

    try:
        base_url = "https://openrouter.ai/api/v1/chat/completions"
        if is_gemini:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai/chat/completions"
        elif provider == "openai":
            base_url = "https://api.openai.com/v1/chat/completions"
        elif provider == "groq":
            base_url = "https://api.groq.com/openai/v1/chat/completions"
        elif provider == "ollama":
            base_url = f"{settings.OLLAMA_URL.rstrip('/')}/v1/chat/completions"
        elif settings.LLM_BASE_URL:
            base_url = f"{settings.LLM_BASE_URL.rstrip('/')}/chat/completions"

        headers = {
            "Authorization": f"Bearer {api_key}",
            "HTTP-Referer": "https://github.com/Farhaal/YT-Automation-tool",
            "X-Title": "OpenReel",
            "Content-Type": "application/json"
        }

        resp = httpx.post(
            base_url,
            headers=headers,
            json={
                "model": vision_model,
                "messages": messages,
                "response_format": {"type": "json_object"},
                "temperature": 0.1
            },
            timeout=15.0
        )
        
        if resp.status_code != 200:
            logger.warning(f"Vision verification failed (HTTP {resp.status_code}): {resp.text}")
            return None

        result_text = resp.json()["choices"][0]["message"]["content"]
        
        # Strip potential markdown blocks if the model ignored response_format
        result_text = result_text.strip()
        if result_text.startswith("```json"):
            result_text = result_text[7:]
        if result_text.startswith("```"):
            result_text = result_text[3:]
        if result_text.endswith("```"):
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
        
    except Exception as e:
        logger.warning(f"Exception during vision verification: {type(e).__name__} - {e}")
        return None
