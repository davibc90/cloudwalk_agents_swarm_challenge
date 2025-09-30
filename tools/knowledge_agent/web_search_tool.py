from langchain_core.tools import tool
from typing import List, Dict, Any
from tavily import TavilyClient
import os
from dotenv import load_dotenv
load_dotenv()

# Inicializa cliente Tavily
tavily_api_key = os.getenv("TAVILY_SEARCH_API_KEY")
tavily = TavilyClient(api_key=tavily_api_key)

@tool
def web_search_tool(query: str, max_results: int = 10) -> List[Dict[str, Any]]:
    """
    Web search tool using Tavily Search API
    Args:
        query: search query
        max_results: number of results should be returned (between 10 and 20)
    Returns:
        List of dicts with {title, url, content}
    """
    resp = tavily.search(query, max_results=max_results)
    results = []
    for r in resp.get("results", []):
        results.append({
            "title": r.get("title"),
            "url": r.get("url"),
            "content": r.get("content"),
        })
    return results

