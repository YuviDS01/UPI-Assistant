from pydantic import BaseModel


class ChatRequest(BaseModel):
    message: str
    thread_id: str | None = None


class ChatResponse(BaseModel):
    thread_id: str
    intent: str
    response: str
    requires_approval: bool = False
    tool_result: dict | None = None