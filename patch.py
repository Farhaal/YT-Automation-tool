import re

with open('backend/app/api/routes.py', 'r') as f:
    content = f.read()

replacement = '''class LLMProviderConfig(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""
    enabled: bool = True

class SettingsUpdate(BaseModel):
    pexels_key: Optional[str] = None
    pixabay_key: Optional[str] = None
    llm_providers: Optional[List[LLMProviderConfig]] = None
    enable_visual_verification: Optional[bool] = None
    vision_model: Optional[str] = None

class TestLLMRequest(BaseModel):
    provider: str
    api_key: str = ""
    model: str = ""

def load_settings():
    base_settings = {
        "pexels_key": settings.PEXELS_API_KEY or "",
        "pixabay_key": settings.PIXABAY_API_KEY or "",
        "enable_visual_verification": settings.ENABLE_VISUAL_VERIFICATION,
        "vision_model": settings.VISION_MODEL,
        "llm_providers": settings.LLM_PROVIDERS or []
    }
    if SETTINGS_PATH.exists():
        try:
            with open(SETTINGS_PATH, "r") as f:
                saved = json.load(f)
                
                if "llm_provider" in saved and "llm_providers" not in saved:
                    prov_list = []
                    if saved.get("llm_provider"):
                        prov_list.append({
                            "provider": saved.get("llm_provider", ""),
                            "api_key": saved.get("llm_api_key", ""),
                            "model": saved.get("llm_model", ""),
                            "enabled": True
                        })
                    saved["llm_providers"] = prov_list
                    
                if "llm_providers" in saved:
                    base_settings["llm_providers"] = saved["llm_providers"]
                    
                base_settings["pexels_key"] = saved.get("pexels_key", base_settings["pexels_key"])
                base_settings["pixabay_key"] = saved.get("pixabay_key", base_settings["pixabay_key"])
                base_settings["enable_visual_verification"] = saved.get("enable_visual_verification", base_settings["enable_visual_verification"])
                base_settings["vision_model"] = saved.get("vision_model", base_settings["vision_model"])
        except:
            pass
    return base_settings

def apply_settings_to_env():
    s = load_settings()
    settings.PEXELS_API_KEY = s.get("pexels_key", settings.PEXELS_API_KEY)
    settings.PIXABAY_API_KEY = s.get("pixabay_key", settings.PIXABAY_API_KEY)
    settings.LLM_PROVIDERS = s.get("llm_providers", settings.LLM_PROVIDERS)
    settings.ENABLE_VISUAL_VERIFICATION = s.get("enable_visual_verification", settings.ENABLE_VISUAL_VERIFICATION)
    settings.VISION_MODEL = s.get("vision_model", settings.VISION_MODEL)

@router.get("/settings")
def get_settings():
    s = load_settings()
    masked = []
    for p in s.get("llm_providers", []):
        masked.append({
            "provider": p.get("provider", ""),
            "model": p.get("model", ""),
            "enabled": p.get("enabled", True),
            "status": "Configured" if p.get("api_key") else "Not configured"
        })
    return {
        "pexels": "Configured" if s.get("pexels_key") else "Not configured",
        "pixabay": "Configured" if s.get("pixabay_key") else "Not configured",
        "openverse": "No key required",
        "wikimedia": "No key required",
        "llm_providers": masked,
        "enable_visual_verification": s.get("enable_visual_verification", False),
        "vision_model": s.get("vision_model", "")
    }

@router.post("/settings")
def update_settings(req: SettingsUpdate):
    s = load_settings()
    if req.pexels_key is not None and req.pexels_key != "": s["pexels_key"] = req.pexels_key
    if req.pixabay_key is not None and req.pixabay_key != "": s["pixabay_key"] = req.pixabay_key
    if req.llm_providers is not None:
        s["llm_providers"] = [p.dict() for p in req.llm_providers]
    if req.enable_visual_verification is not None: s["enable_visual_verification"] = req.enable_visual_verification
    if req.vision_model is not None: s["vision_model"] = req.vision_model
    
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    apply_settings_to_env()
    return get_settings()

@router.delete("/settings/{provider}")
def delete_setting(provider: str):
    s = load_settings()
    if provider.lower() == "pexels":
        s["pexels_key"] = ""
    elif provider.lower() == "pixabay":
        s["pixabay_key"] = ""
    elif provider.lower() == "llm":
        s["llm_providers"] = []
        
    with open(SETTINGS_PATH, "w") as f:
        json.dump(s, f)
    apply_settings_to_env()
    return get_settings()

@router.post("/settings/test-llm")
def test_llm_settings(req: TestLLMRequest):
    import httpx
    
    provider = req.provider.lower()
    base_url = "https://api.openai.com/v1"
    model = req.model or "gpt-3.5-turbo"
    
    if provider == "groq":
        base_url = "https://api.groq.com/openai/v1"
        model = req.model or "llama3-8b-8192"
    elif provider == "openrouter":
        base_url = "https://openrouter.ai/api/v1"
    elif provider == "ollama":
        base_url = "http://localhost:11434/v1"
        model = req.model or "llama3"
    elif provider in ["gemini", "google"]:
        base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
        model = req.model or "gemini-2.0-flash"
        
    headers = {"Content-Type": "application/json"}
    if req.api_key:
        headers["Authorization"] = f"Bearer {req.api_key}"
        
    try:
        resp = httpx.post(
            f"{base_url.rstrip('/')}/chat/completions",
            headers=headers,
            json={
                "model": model,
                "messages": [{"role": "user", "content": "Hi"}],
                "max_tokens": 5
            },
            timeout=10.0
        )
        resp.raise_for_status()
        return {"ok": True}
    except Exception as e:
        msg = str(e)
        if isinstance(e, httpx.HTTPStatusError):
            try:
                msg = e.response.json().get("error", {}).get("message", msg)
            except:
                msg = e.response.text or msg
        return {"ok": False, "status": getattr(e, "response", None) and getattr(e.response, "status_code", None), "message": msg}
'''

start_pattern = r'class SettingsUpdate\(BaseModel\):'
end_pattern = r'from fastapi\.responses import FileResponse'

new_content = re.sub(start_pattern + r'.*?' + end_pattern, replacement + '\nfrom fastapi.responses import FileResponse', content, flags=re.DOTALL)

with open('backend/app/api/routes.py', 'w') as f:
    f.write(new_content)
