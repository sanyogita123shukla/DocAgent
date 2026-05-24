from typing import Annotated, Sequence, TypedDict
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages

class AgentState(TypedDict):
    """The state of the document analysis agent."""
    messages: Annotated[Sequence[BaseMessage], add_messages]
    file_path: str            # Path to uploaded file
    file_type: str            # MIME type from router
