"""
State Management
Holds in-memory session history and the shared vector store instance.
In production you'd swap these for Redis + a persistent vector DB.
"""

from typing import Dict, List
from langchain_core.messages import BaseMessage

# session_id → list of LangChain message objects
conversation_history: Dict[str, List[BaseMessage]] = {}

# Shared Chroma vector store (populated when a document is uploaded)
vector_store = None