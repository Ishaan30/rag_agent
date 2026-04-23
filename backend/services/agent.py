"""
Agent Service
Builds a LangChain AgentExecutor that:
  1. Searches uploaded documents (RAG) for context
  2. Calls web_search or get_weather tools when needed
  3. Streams the final answer token-by-token

Architecture:
  User message
    → retrieve relevant doc chunks (RAG)
    → inject chunks into system context
    → AgentExecutor decides: answer directly OR call a tool
    → stream response back to the client
"""

import os
from typing import AsyncIterator

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.agents import AgentExecutor, create_tool_calling_agent
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage

import state
from tools import get_web_search_tool, get_weather

# ─── System Prompt ────────────────────────────────────────────────────────────

SYSTEM_PROMPT = """You are a helpful, knowledgeable assistant. You are concise, friendly, and clear.

When answering:
- If the user asks about previous questions or conversation history, look at the chat_history provided to you and answer directly from it.
- If the user's question relates to an uploaded document, use the provided document context.
- If the document context does not contain the answer, say so clearly, then try the web_search tool.
- For weather questions, always use the get_weather tool.
- For current events or real-time information, use the web_search tool.
- Never make up facts. If you don't know something, say so.

Document context (may be empty if no document has been uploaded):
{doc_context}
"""

# ─── LLM Setup ────────────────────────────────────────────────────────────────

def _build_llm() -> ChatGoogleGenerativeAI:
    """Create the Gemini LLM instance used by the agent."""
    return ChatGoogleGenerativeAI(
        model="gemini-2.5-flash",          # Fast, capable, cost-effective
        google_api_key=os.environ["GOOGLE_API_KEY"],
        temperature=0.3,                   # Low temp → factual and consistent
        streaming=True,
    )


# ─── RAG Context Retrieval ────────────────────────────────────────────────────

def _retrieve_doc_context(query: str, k: int = 5) -> str:
    """
    Query the vector store for the most relevant document chunks.
    Returns a formatted string to inject into the system prompt.
    Returns an empty string if no document has been uploaded yet.
    """
    if state.vector_store is None:
        return ""  # No document uploaded yet

    docs = state.vector_store.similarity_search(query, k=k)
    if not docs:
        return ""

    # Format each chunk with a separator for clarity
    chunks = "\n\n---\n\n".join(doc.page_content for doc in docs)
    return f"Relevant excerpts from the uploaded document:\n\n{chunks}"


# ─── Agent Builder ────────────────────────────────────────────────────────────

def _build_agent_executor(doc_context: str) -> AgentExecutor:
    """
    Construct a fresh AgentExecutor for each request.
    Injecting doc_context into the system message keeps the prompt dynamic.
    """
    llm = _build_llm()
    tools = [get_web_search_tool(), get_weather]

    # Prompt template expected by create_tool_calling_agent
    prompt = ChatPromptTemplate.from_messages([
        ("system", SYSTEM_PROMPT),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "{input}"),
        MessagesPlaceholder(variable_name="agent_scratchpad"),  # tool call scratch space
    ])

    agent = create_tool_calling_agent(llm, tools, prompt)
    return AgentExecutor(
        agent=agent,
        tools=tools,
        verbose=True,          # Logs tool calls to the server console
        return_intermediate_steps=False,
        max_iterations=5,      # Prevent runaway tool loops
    )


# ─── History Helpers ──────────────────────────────────────────────────────────

def _get_history(session_id: str):
    """Return the LangChain message list for a session, creating it if needed."""
    return state.conversation_history.setdefault(session_id, [])


def _save_turn(session_id: str, human_msg: str, ai_msg: str):
    """Append a human/AI turn to the session history."""
    history = _get_history(session_id)
    history.append(HumanMessage(content=human_msg))
    history.append(AIMessage(content=ai_msg))


# ─── Public Interface ─────────────────────────────────────────────────────────

async def stream_agent_response(
    session_id: str,
    user_message: str,
) -> AsyncIterator[str]:
    """
    Run the agent and yield response tokens as they arrive.
    Saves the completed turn to session history when done.
    """
    history = _get_history(session_id)
    print(f"Session {session_id} history length: {len(history)}")
    doc_context = _retrieve_doc_context(user_message)
    executor = _build_agent_executor(doc_context)

    full_response = ""

    # astream_events gives us granular token-level events
    async for event in executor.astream_events(
        {
            "input": user_message,
            "chat_history": history,
            "doc_context": doc_context,
        },
        version="v2",
    ):
        kind = event["event"]

        # Stream tokens from the final LLM response (not intermediate tool calls)
        if kind == "on_chat_model_stream":
            chunk = event["data"]["chunk"]
            token = chunk.content
            if token:
                full_response += token
                yield token

    # Persist the completed turn so future requests have context
    _save_turn(session_id, user_message, full_response)


def clear_session(session_id: str):
    """Wipe the conversation history for a session."""
    state.conversation_history.pop(session_id, None)