from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field


class Message(BaseModel):
    role: str = Field(..., description="Role: 'user' or 'model'/'assistant'")
    content: str = Field(..., description="Content of the message")


class ToolExecutionDetail(BaseModel):
    tool_name: str
    arguments: Dict[str, Any]
    result: Any


class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, description="User's incoming query")
    history: Optional[List[Message]] = Field(default=[], description="Previous conversation turns")
    customer_id: Optional[str] = Field(default="CUST-8801", description="Current logged in customer ID")


class ChatResponse(BaseModel):
    response: str
    tool_calls: List[ToolExecutionDetail] = []
    status: str = "success"


class HealthResponse(BaseModel):
    status: str
    service: str
    version: str
