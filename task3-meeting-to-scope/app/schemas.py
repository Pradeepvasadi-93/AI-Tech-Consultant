from pydantic import BaseModel, Field

class ProjectCreate(BaseModel):
    client_name: str = Field(min_length=1, max_length=200)
    project_name: str = Field(min_length=1, max_length=200)
    transcript: str = Field(min_length=20, max_length=100000)
    meeting_id: str = "meeting-a"

class Approval(BaseModel):
    version: int = Field(ge=1)
    reviewer: str = Field(min_length=1, max_length=200)
    notes: str = ""

class FollowUp(BaseModel):
    transcript: str = Field(min_length=20, max_length=100000)
    meeting_id: str = "meeting-c"

class SimulatedSend(BaseModel):
    version: int = Field(ge=1)
    reviewer: str = Field(min_length=1, max_length=200)
