import uuid

from fastapi import APIRouter, Depends

from app.agent.graph import get_graph
from app.api.deps import get_current_user_id
from app.core.rate_limit import rate_limit
from app.schemas.chat import ChatRequest, ChatResponse

router = APIRouter(prefix="/api/chat", tags=["chat"])


@router.post("", response_model=ChatResponse, dependencies=[Depends(rate_limit("chat", max_requests=20, window_seconds=60))])
def chat(body: ChatRequest, user_id: uuid.UUID = Depends(get_current_user_id)) -> ChatResponse:
    thread_id = body.thread_id or str(uuid.uuid4())
    graph = get_graph()
    result = graph.invoke(
        {"user_id": str(user_id), "message": body.message},
        config={"configurable": {"thread_id": thread_id}},
    )
    return ChatResponse(
        thread_id=thread_id,
        intent=result.get("intent", "UNKNOWN"),
        response=result.get("response", ""),
        requires_approval=result.get("requires_approval", False),
        tool_result=result.get("tool_result"),
    )