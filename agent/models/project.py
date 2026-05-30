from pydantic import BaseModel, Field
from typing import Optional, List
from datetime import datetime


class MediaFiles(BaseModel):
    clips: List[str] = []
    photos: List[str] = []
    music: Optional[str] = None
    logo: Optional[str] = None


class ProjectConfig(BaseModel):
    project_id: str
    name: str
    type: str         # product | event | social | travel
    style: str        # dark | fast | warm | corp
    music_choice: str
    reference: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class CommandMessage(BaseModel):
    type: str = "command"
    command: str = ""
    project_id: str
    files: Optional[MediaFiles] = None
    profile: Optional[str] = None
