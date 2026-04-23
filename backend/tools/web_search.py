"""
Tool: Web Search
Uses the Tavily Search API to fetch real-time information from the web.
The agent calls this automatically when the user asks about current events
or anything that isn't in the uploaded documents.
"""

import os
from langchain_community.tools.tavily_search import TavilySearchResults


def get_web_search_tool() -> TavilySearchResults:
    """
    Returns a configured Tavily search tool.
    TAVILY_API_KEY must be set in the environment.
    """
    return TavilySearchResults(
        max_results=3,                     # Keep context concise
        name="web_search",
        description=(
            "Search the web for current information. "
            "Use this when the user asks about recent events, news, "
            "or topics not covered by the uploaded documents."
        ),
    )