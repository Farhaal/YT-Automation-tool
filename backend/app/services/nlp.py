from typing import Any, Dict, List, Optional

import httpx
import spacy
import yake

from backend.app.core.config import settings
from backend.app.core.logger import logger

try:
    nlp = spacy.load("en_core_web_sm")
except OSError:
    logger.error("spaCy model 'en_core_web_sm' not found. Ensure it was downloaded.")
    raise

def _build_scene(words: List[Dict]) -> Dict:
    text = " ".join(w["word"] for w in words).strip()
    return {
        "text": text,
        "start": words[0]["start"] if words else 0.0,
        "end": words[-1]["end"] if words else 0.0,
        "words": words
    }

def segment_into_scenes(
    words: List[Dict[str, Any]], 
    max_duration: float = 3.5, 
    min_duration: float = 1.2
) -> List[Dict[str, Any]]:
    """
    Groups words into logical scenes based on sentence/clause boundaries and pauses.
    Enforces min_duration (except possibly the last scene) and max_duration.
    """
    if not words:
        return []
        
    scenes = []
    current_words = []
    
    clause_punct = {",", ";", ":", "-"}
    conjunctions = {"and", "but", "or", "so", "then", "while", "because"}
    sentence_ends = {".", "?", "!", "\n"}
    
    def _make_scene(w_list: List[Dict[str, Any]], sid: int) -> Dict[str, Any]:
        return {
            "id": f"s{sid}",
            "start": w_list[0]["start"],
            "end": w_list[-1]["end"],
            "text": " ".join(x["word"].strip() for x in w_list),
            "_words": w_list
        }
        
    for i, w in enumerate(words):
        current_words.append(w)
        dur = current_words[-1]["end"] - current_words[0]["start"]
        
        is_last_word = (i == len(words) - 1)
        if is_last_word:
            break
            
        next_w = words[i+1]
        pause = (next_w["start"] - w["end"] > 0.5)
        
        word_clean = w["word"].strip().lower()
        last_char = word_clean[-1] if word_clean else ""
        bare_word = "".join(c for c in word_clean if c.isalnum())
        
        is_sentence_end = last_char in sentence_ends
        is_clause = last_char in clause_punct or bare_word in conjunctions
        is_max_dur = dur >= max_duration
        
        if dur >= min_duration and (is_sentence_end or is_clause or pause or is_max_dur):
            scenes.append(_make_scene(current_words, len(scenes)+1))
            current_words = []
            
    if current_words:
        dur = current_words[-1]["end"] - current_words[0]["start"]
        if scenes and dur < min_duration:
            # Merge backward
            last_scene = scenes.pop()
            merged = last_scene["_words"] + current_words
            scenes.append(_make_scene(merged, len(scenes)+1))
        else:
            scenes.append(_make_scene(current_words, len(scenes)+1))
            
    # Cleanup _words and format correctly
    for idx, s in enumerate(scenes):
        s["id"] = f"s{idx+1}"
        s.pop("_words", None)
        
    return scenes

def extract_keywords(text: str) -> List[str]:
    """
    Extracts 1-3 visual search queries using YAKE and spaCy.
    """
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents if ent.label_ not in ['CARDINAL', 'ORDINAL', 'DATE', 'TIME', 'PERCENT', 'MONEY', 'QUANTITY']]  # noqa: E501
    nouns = [chunk.text for chunk in doc.noun_chunks]
    
    kw_extractor = yake.KeywordExtractor(lan="en", n=2, dedupLim=0.9, top=3, features=None)
    keywords = kw_extractor.extract_keywords(text)
    phrases = [kw[0] for kw in keywords]
    
    # Combine and prioritize: Entities > YAKE phrases > Noun chunks
    all_candidates = []
    for item in entities + phrases + nouns:
        # Simple cleanup
        clean_item = item.strip('.,;!?').lower()
        if clean_item and clean_item not in all_candidates:
            all_candidates.append(clean_item)
            
    return all_candidates[:3] if all_candidates else [text.strip('.,;!?')]

class AllProvidersFailed(Exception):
    def __init__(self, failures):
        self.failures = failures
        super().__init__("All LLM providers failed")

def call_llm(messages: List[Dict], temperature: float = 0.3, require_vision: bool = False, job_state: Optional[Dict] = None) -> str:
    """Helper to send a chat completion request with multi-provider failover."""
    if job_state is None:
        job_state = {}
    if "dead_providers" not in job_state:
        job_state["dead_providers"] = set()
    if "llm_failover_log" not in job_state:
        job_state["llm_failover_log"] = []
        
    providers = [p for p in getattr(settings, "LLM_PROVIDERS", []) if p.get("enabled", True)]
    if not providers:
        raise AllProvidersFailed([{"provider": "none", "model": "", "status": "Not configured", "message": "No providers enabled"}])
        
    failures = []
    
    for p in providers:
        provider = p.get("provider", "").lower()
        base_url = "https://api.openai.com/v1"
        model = p.get("model") or "gpt-3.5-turbo"
        
        if provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            model = p.get("model") or "llama3-8b-8192"
        elif provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif provider == "ollama":
            base_url = "http://localhost:11434/v1"
            model = p.get("model") or "llama3"
        elif provider in ["gemini", "google"]:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            model = p.get("model") or "gemini-2.0-flash"
            
        prov_id = f"{provider}:{model}"
        
        if prov_id in job_state["dead_providers"]:
            continue
            
        headers = {"Content-Type": "application/json"}
        api_key = p.get("api_key", "")
        if api_key:
            headers["Authorization"] = f"Bearer {api_key}"
            
        # Try calling
        import time
        max_retries = 1
        success = False
        content = ""
        last_err_msg = ""
        last_status = None
        
        for attempt in range(max_retries + 1):
            try:
                # Need to use a fresh copy if messages contain generators, but here it's just lists/dicts
                response = httpx.post(
                    f"{base_url.rstrip('/')}/chat/completions",
                    headers=headers,
                    json={
                        "model": model, 
                        "messages": messages,
                        "temperature": temperature
                    },
                    timeout=15.0
                )
                response.raise_for_status()
                data = response.json()
                content = data["choices"][0]["message"]["content"]
                success = True
                break
            except Exception as e:
                msg = str(e)
                status = getattr(e, "response", None) and e.response.status_code
                if isinstance(e, httpx.HTTPStatusError):
                    try:
                        msg = e.response.json().get("error", {}).get("message", msg)
                    except Exception:
                        msg = e.response.text or msg
                        
                last_err_msg = msg
                last_status = status
                
                # Fail fast for 401, 403, 404
                if status in (401, 403, 404):
                    break
                
                if attempt < max_retries:
                    time.sleep(1)
                    
        if success:
            job_state["used_provider"] = prov_id
            return content
        else:
            job_state["dead_providers"].add(prov_id)
            failures.append({
                "provider": provider,
                "model": model,
                "status": last_status,
                "message": last_err_msg
            })
            job_state["llm_failover_log"].append(failures[-1])
            
    # If we get here, all enabled providers failed
    if "llm_warnings" not in job_state:
        job_state["llm_warnings"] = []
    job_state["llm_warnings"].append(failures)
    raise AllProvidersFailed(failures)

def analyze_transcript_topic(full_text: str, job_state: Optional[Dict] = None) -> str:
    """
    Uses the configured LLM to concisely describe the video's overall subject, setting, and visual world.
    """
    prompt = f"Analyze this transcript and describe its overall subject, setting, and visual world concisely (under 40 words).\nTranscript: {full_text}"  # noqa: E501
    try:
        content = call_llm([{"role": "user", "content": prompt}], temperature=0.7, job_state=job_state)
        return content.strip()
    except AllProvidersFailed:
        return ""
    except Exception as e:
        logger.warning(f"LLM topic analysis failed ({e}). Returning empty topic.")
        return ""

def extract_visual_queries_with_llm(text: str, topic_context: str = "", job_state: Optional[Dict] = None) -> List[str]:
    """
    Uses an optional LLM to generate visual search queries, optionally guided by a transcript topic.
    """
    if topic_context:
        prompt = f"The overall video topic is: {topic_context}. For this line, return 1-3 short, CONCRETE stock-footage search queries that fit BOTH the line AND the overall topic. Stay literal and on-topic; do NOT use metaphors or generic motivational imagery. Line: '{text}'. Return ONLY comma-separated queries, nothing else."  # noqa: E501
    else:
        prompt = f"Extract 1 to 3 short visual search queries for a stock footage site that best represent this scene: '{text}'. Return ONLY comma-separated queries, nothing else."  # noqa: E501
    
    try:
        content = call_llm([
            {"role": "system", "content": "You are a visual search query generator. Return only comma-separated queries."},  # noqa: E501
            {"role": "user", "content": prompt}
        ], temperature=0.3, job_state=job_state)
        
        queries = [q.strip() for q in content.split(",") if q.strip()]
        return queries[:3] if queries else extract_keywords(text)
    except AllProvidersFailed:
        return extract_keywords(text)
    except Exception as e:
        logger.warning(f"LLM extraction failed ({e}). Falling back to NLP extraction.")
        return extract_keywords(text)

HOOK_SECONDS = 30.0

def process_script_to_scenes(words: List[Dict[str, Any]], pace: str = "balanced", punchy_hook: bool = True, job_state: Optional[Dict] = None) -> List[Dict[str, Any]]:
    """
    End-to-end pipeline to convert timed words into scenes with visual queries.
    """
    if pace == "dynamic":
        max_d, min_d = 2.5, 1.2
    elif pace == "relaxed":
        max_d, min_d = 5.0, 1.2
    else:
        max_d, min_d = 3.5, 1.2
        
    if punchy_hook:
        hook_words = []
        rest_words = []
        for w in words:
            if w["start"] < HOOK_SECONDS:
                hook_words.append(w)
            else:
                rest_words.append(w)
                
        hook_scenes = segment_into_scenes(hook_words, max_duration=1.8, min_duration=1.0) if hook_words else []
        rest_scenes = segment_into_scenes(rest_words, max_duration=max_d, min_duration=min_d) if rest_words else []
        
        scenes = hook_scenes + rest_scenes
        for i, s in enumerate(scenes):
            s["id"] = f"s{i+1}"
    else:
        scenes = segment_into_scenes(words, max_d, min_d)
        
    use_llm = any(p.get("enabled", True) for p in getattr(settings, "LLM_PROVIDERS", []))
    
    topic = ""
    if use_llm:
        topic = analyze_transcript_topic(" ".join(w["word"] for w in words).strip(), job_state=job_state)
        
    for scene in scenes:
        scene["topic"] = topic
        if use_llm:
            scene["queries"] = extract_visual_queries_with_llm(scene["text"], topic_context=topic, job_state=job_state)
        else:
            scene["queries"] = extract_keywords(scene["text"])
            
    return scenes

