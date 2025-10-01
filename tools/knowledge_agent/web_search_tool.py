from langchain_core.tools import tool
from typing import List, Dict, Any
from tavily import TavilyClient
from config.env_config import env

# Get Tavily API key from environment variables and initialize Tavily client
tavily_api_key = env.tavily_search_api_key
tavily = TavilyClient(api_key=tavily_api_key)

@tool
def web_search_tool(query: str, max_results: int = 15) -> List[Dict[str, Any]]:
    """
    Web search tool using Tavily Search API
    Args:
        query: search query
        max_results: number of results should be returned (minimum: 15, maximum: 30)
    Returns:
        List of dicts with {title, url, content}
    """
    # Search using Tavily API
    response = tavily.search(query, max_results=max_results)
    results = []

    # Process search results
    for r in response.get("results", []):
        results.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
        })
    return results

