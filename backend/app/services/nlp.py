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
        "start": words[0]["start"] if words else 0.0,
        "end": words[-1]["end"] if words else 0.0,
        "words": words
    }

def segment_into_scenes(words: List[Dict[str, Any]], max_duration: float = 6.0, pause_threshold: float = 0.8) -> List[Dict[str, Any]]:
    """
    Groups words into logical scenes based on sentence boundaries and pauses.
    Enforces max_duration strictly. Splits at the best natural boundary (comma etc.)
    before the limit, or otherwise at the last word that fits.
    """
    if not words:
        return []
        
    scenes = []
    current_scene = []
    
    for word in words:
        if not current_scene:
            current_scene.append(word)
            continue
            
        prev_word = current_scene[-1]
        gap = word["start"] - prev_word["end"]
        
        # Hard boundaries: Sentence end or long pause
        is_sentence_end = any(prev_word["word"].endswith(p) for p in ['.', '?', '!', '\n'])
        is_pause = (gap >= pause_threshold)
        
        if is_sentence_end or is_pause:
            scenes.append(_build_scene(current_scene))
            current_scene = [word]
            continue
            
        # Max duration check
        scene_start = current_scene[0]["start"]
        if word["end"] - scene_start > max_duration:
            # Must split. Look for the last soft boundary in current_scene.
            split_idx = -1
            for j in range(len(current_scene)-1, -1, -1):
                if any(current_scene[j]["word"].endswith(p) for p in [',', ';', ':', '-']):
                    split_idx = j
                    break
            
            if split_idx != -1 and split_idx < len(current_scene) - 1:
                # Split at the last soft boundary
                scenes.append(_build_scene(current_scene[:split_idx+1]))
                current_scene = current_scene[split_idx+1:] + [word]
            else:
                # No natural boundary, split strictly before the current word
                scenes.append(_build_scene(current_scene))
                current_scene = [word]
        else:
            current_scene.append(word)
            
    if current_scene:
        scenes.append(_build_scene(current_scene))
        
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
