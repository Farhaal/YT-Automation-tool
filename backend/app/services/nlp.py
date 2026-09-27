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
        elif provider in ["gemini", "google"]:
            base_url = "https://generativelanguage.googleapis.com/v1beta/openai"
            model = settings.LLM_MODEL or "gemini-1.5-flash"
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

def process_script_to_scenes(words: List[Dict[str, Any]], pace: str = "balanced") -> List[Dict[str, Any]]:
    """
    End-to-end pipeline to convert timed words into scenes with visual queries.
    """
    if pace == "dynamic":
        max_d, min_d = 2.5, 1.2
    elif pace == "relaxed":
        max_d, min_d = 5.0, 1.2
    else:
        max_d, min_d = 3.5, 1.2
        
    scenes = segment_into_scenes(words, max_d, min_d)
    
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
