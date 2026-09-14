from typing import Any, Dict, List

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

def segment_into_scenes(words: List[Dict[str, Any]], max_duration: float = 6.0, pause_threshold: float = 0.8) -> List[Dict[str, Any]]:  # noqa: E501
    """
    Groups words into logical scenes based on sentence boundaries and pauses.
    Strictly enforces max_duration. Multi-word scenes will never exceed max_duration.
    Single-word scenes may exceed it only if the word itself is longer than max_duration.
    """
    if not words:
        return []
        
    scenes = []
    current_scene = []
    
    for word in words:
        if not current_scene:
            current_scene.append(word)
            # A single word that is a sentence end
            if any(word["word"].endswith(p) for p in ['.', '?', '!', '\n']):
                scenes.append(_build_scene(current_scene))
                current_scene = []
            continue
            
        # 1. Check for pause boundary *before* adding the current word
        gap = word["start"] - current_scene[-1]["end"]
        if gap >= pause_threshold:
            scenes.append(_build_scene(current_scene))
            current_scene = []
            
        current_scene.append(word)
        
        # 2. Enforce max_duration invariant iteratively
        while len(current_scene) > 1 and (current_scene[-1]["end"] - current_scene[0]["start"]) > max_duration:
            # Look for soft boundary in all but the last word
            split_idx = -1
            for j in range(len(current_scene)-2, -1, -1):
                if any(current_scene[j]["word"].endswith(p) for p in [',', ';', ':', '-']):
                    split_idx = j
                    break
            
            if split_idx != -1:
                # Split at soft boundary
                left = current_scene[:split_idx+1]
                scenes.append(_build_scene(left))
                current_scene = current_scene[split_idx+1:]
            else:
                # No soft boundary, hard split right before the last added word
                left = current_scene[:-1]
                scenes.append(_build_scene(left))
                current_scene = [current_scene[-1]]
                
        # 3. Check for sentence end *after* max_duration enforcement
        if current_scene and any(current_scene[-1]["word"].endswith(p) for p in ['.', '?', '!', '\n']):
            scenes.append(_build_scene(current_scene))
            current_scene = []
            
    # Final flush
    if current_scene:
        scenes.append(_build_scene(current_scene))
        
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

def _call_llm_chat(messages: List[Dict], temperature: float = 0.3) -> str:
    """Helper to send a chat completion request to the configured LLM."""
    provider = (settings.LLM_PROVIDER or "").lower()
    base_url = settings.LLM_BASE_URL
    model = settings.LLM_MODEL or "gpt-3.5-turbo"
    
    if not base_url:
        if provider == "openai":
            base_url = "https://api.openai.com/v1"
        elif provider == "groq":
            base_url = "https://api.groq.com/openai/v1"
            model = settings.LLM_MODEL or "llama3-8b-8192"
        elif provider == "openrouter":
            base_url = "https://openrouter.ai/api/v1"
        elif provider == "ollama":
            base_url = f"{settings.OLLAMA_URL.rstrip('/')}/v1"
            model = settings.LLM_MODEL or "llama3"
        else:
            base_url = "https://api.openai.com/v1"

    headers = {"Content-Type": "application/json"}
    if settings.LLM_API_KEY:
        headers["Authorization"] = f"Bearer {settings.LLM_API_KEY}"
        
    response = httpx.post(
        f"{base_url.rstrip('/')}/chat/completions",
        headers=headers,
        json={
            "model": model, 
            "messages": messages,
            "temperature": temperature
        },
        timeout=12.0
    )
    response.raise_for_status()
    data = response.json()
    return data["choices"][0]["message"]["content"]

def analyze_transcript_topic(full_text: str) -> str:
    """
    Uses the configured LLM to concisely describe the video's overall subject, setting, and visual world.
    """
    prompt = f"Analyze this transcript and describe its overall subject, setting, and visual world concisely (under 40 words).\nTranscript: {full_text}"  # noqa: E501
    try:
        content = _call_llm_chat([{"role": "user", "content": prompt}], temperature=0.7)
        return content.strip()
    except Exception as e:
        logger.warning(f"LLM topic analysis failed ({e}). Returning empty topic.")
        return ""

def extract_visual_queries_with_llm(text: str, topic_context: str = "") -> List[str]:
    """
    Uses an optional LLM to generate visual search queries, optionally guided by a transcript topic.
    """
    if topic_context:
        prompt = f"The overall video topic is: {topic_context}. For this line, return 1-3 short, CONCRETE stock-footage search queries that fit BOTH the line AND the overall topic. Stay literal and on-topic; do NOT use metaphors or generic motivational imagery. Line: '{text}'. Return ONLY comma-separated queries, nothing else."  # noqa: E501
    else:
        prompt = f"Extract 1 to 3 short visual search queries for a stock footage site that best represent this scene: '{text}'. Return ONLY comma-separated queries, nothing else."  # noqa: E501
    
    try:
        content = _call_llm_chat([
            {"role": "system", "content": "You are a visual search query generator. Return only comma-separated queries."},  # noqa: E501
            {"role": "user", "content": prompt}
        ], temperature=0.3)
        
        queries = [q.strip() for q in content.split(",") if q.strip()]
        return queries[:3] if queries else extract_keywords(text)
    except Exception as e:
        logger.warning(f"LLM extraction failed ({e}). Falling back to NLP extraction.")
        return extract_keywords(text)

def process_script_to_scenes(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    End-to-end pipeline to convert timed words into scenes with visual queries.
    """
    scenes = segment_into_scenes(words)
    
    use_llm = bool(settings.LLM_API_KEY) or ((settings.LLM_PROVIDER or "").lower() == "ollama")
    
    topic = ""
    if use_llm:
        full_text = " ".join(w["word"] for w in words).strip()
        topic = analyze_transcript_topic(full_text)
        
    for scene in scenes:
        scene["topic"] = topic
        if use_llm:
            scene["queries"] = extract_visual_queries_with_llm(scene["text"], topic_context=topic)
        else:
            scene["queries"] = extract_keywords(scene["text"])
            
    return scenes
