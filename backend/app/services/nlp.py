import spacy
import yake
import httpx
from typing import List, Dict, Any
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
        "start": words[0]["start"],
        "end": words[-1]["end"],
        "words": words
    }

def segment_into_scenes(words: List[Dict[str, Any]], max_duration: float = 6.0) -> List[Dict[str, Any]]:
    """
    Groups words into logical scenes based on sentence boundaries and pauses.
    Splits long sentences if they exceed max_duration.
    """
    scenes = []
    current_scene_words = []
    
    for word_data in words:
        current_scene_words.append(word_data)
        
        start = current_scene_words[0]["start"]
        end = current_scene_words[-1]["end"]
        duration = end - start
        
        word_text = word_data["word"]
        
        is_sentence_end = any(word_text.endswith(punc) for punc in ['.', '?', '!', '\n'])
        is_pause = is_sentence_end or any(word_text.endswith(punc) for punc in [',', ';', ':'])
        
        # Split if it's the end of a sentence OR if it's getting too long and there's a natural pause
        if is_sentence_end or (duration >= max_duration and is_pause):
            scenes.append(_build_scene(current_scene_words))
            current_scene_words = []
            
    if current_scene_words:
        scenes.append(_build_scene(current_scene_words))
        
    return scenes

def extract_keywords(text: str) -> List[str]:
    """
    Extracts 1-3 visual search queries using YAKE and spaCy.
    """
    doc = nlp(text)
    entities = [ent.text for ent in doc.ents if ent.label_ not in ['CARDINAL', 'ORDINAL', 'DATE', 'TIME', 'PERCENT', 'MONEY', 'QUANTITY']]
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

def extract_visual_queries_with_llm(text: str) -> List[str]:
    """
    Uses a local LLM via Ollama to generate visual search queries.
    """
    prompt = f"Extract 1 to 3 short visual search queries for a stock footage site that best represent this scene: '{text}'. Return ONLY comma-separated queries, nothing else."
    
    try:
        response = httpx.post(
            f"{settings.OLLAMA_URL}/api/generate",
            json={
                "model": "llama3", 
                "prompt": prompt,
                "stream": False
            },
            timeout=5.0
        )
        response.raise_for_status()
        data = response.json()
        queries = [q.strip() for q in data.get("response", "").split(",") if q.strip()]
        return queries[:3] if queries else extract_keywords(text)
    except Exception as e:
        logger.warning(f"Ollama extraction failed ({e}). Falling back to NLP extraction.")
        return extract_keywords(text)

def process_script_to_scenes(words: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    End-to-end pipeline to convert timed words into scenes with visual queries.
    """
    scenes = segment_into_scenes(words)
    
    for scene in scenes:
        if settings.USE_OLLAMA:
            scene["queries"] = extract_visual_queries_with_llm(scene["text"])
        else:
            scene["queries"] = extract_keywords(scene["text"])
            
    return scenes
