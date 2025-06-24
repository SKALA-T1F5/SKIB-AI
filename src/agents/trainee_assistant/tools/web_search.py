from typing import List
import aiohttp
from src.agents.trainee_assistant.models import SearchResult
from .base import BaseTool

class WebSearchTool(BaseTool):
    def __init__(self, api_key: str, cx: str):
        self.api_key = api_key
        self.cx = cx
        self.base_url = "https://www.googleapis.com/customsearch/v1"

    async def search(self, query: str, num_results: int = 5, **kwargs) -> List[SearchResult]:
        params = {
            "key": self.api_key,
            "cx": self.cx,
            "q": query,
            "num": num_results
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(self.base_url, params=params) as resp:
                    if resp.status != 200:
                        print(f"Web search failed: {resp.status}")
                        return []

                    data = await resp.json()
                    items = data.get("items", [])

                    search_results = []
                    for item in items:
                        search_results.append(SearchResult(
                            content=f"{item.get('title')}: {item.get('snippet')}",
                            source="web_search",
                            score=0.8,
                            metadata={"url": item.get("link"), "title": item.get("title")}
                        ))

                    return search_results

        except Exception as e:
            print(f"Web search error: {e}")
            return []