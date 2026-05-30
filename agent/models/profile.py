from pydantic import BaseModel
from typing import Optional


class BrandProfile(BaseModel):
    name: str
    bpm: float
    avg_cut_duration: float
    color_tone: str        # warm | cool | neutral
    transition_style: str  # hard_cut | dissolve | whip_pan
    style_tag: str
    lut_file: Optional[str] = None
    created_at: str
