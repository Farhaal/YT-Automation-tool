from pydantic import BaseModel
from typing import Optional

class AssetMetadata(BaseModel):
    provider: str
    provider_asset_id: str
    asset_key: str
    
    media_url: str
    source_page_url: Optional[str] = None
    
    author: str = "unknown"
    
    license_name: str = "unknown"
    license_url: Optional[str] = None
    
    attribution_required: bool = False
    attribution_text: Optional[str] = None
    
    media_type: str
    width: int = 0
    height: int = 0
    duration: float = 0.0
    
    query: Optional[str] = None
    query_priority: int = 0
    result_position: int = 0
    
    local_path: Optional[str] = None
    cache_key: Optional[str] = None
