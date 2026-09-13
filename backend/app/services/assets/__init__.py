from pydantic import BaseModel
from typing import Optional

class AssetMetadata(BaseModel):
    id: str
    provider: str
    url: str
    author: str
    license: str
    media_type: str  # 'video' or 'image'
    width: int
    height: int
    duration: float = 0.0  # For video
    local_path: Optional[str] = None
    attribution_required: bool = False
