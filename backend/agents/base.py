# %%
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import List, Optional
import aiohttp
import json
import logfire
import os
from duckduckgo_search import DDGS
from dotenv import load_dotenv
from pydantic_ai.tools import ToolDefinition
from tavily import AsyncTavilyClient
import requests
from bs4 import BeautifulSoup
from urllib.parse import urlparse
from urllib.robotparser import RobotFileParser
from pydantic_ai.models.vertexai import VertexAIModel

# %%
model = VertexAIModel('gemini-2.0-flash-exp')
# model = VertexAIModel('gemini-2.0-flash-thingking-exp-1219')
logfire.configure(send_to_logfire='if-token-present')
# %%
# agent = Agent(
#     model,
#     deps_type=bool,
# )
agent = Agent(
    "openai:gpt-4o-mini",
    deps_type=bool,
)
async def check_authorization(ctx: RunContext[bool], tool_def: ToolDefinition):
    if ctx.deps:
        return tool_def

def check_robots_txt(url: str) -> bool:
    """Check if scraping is allowed by robots.txt"""
    parsed_url = urlparse(url)
    base_url = f"{parsed_url.scheme}://{parsed_url.netloc}"
    robots_url = f"{base_url}/robots.txt"
    
    rp = RobotFileParser()
    try:
        rp.set_url(robots_url)
        rp.read()
        return rp.can_fetch("*", url)
    except:
        return True  # If robots.txt is not accessible, assume scraping is allowed

def scrape_webpage(url: str) -> Optional[str]:
    """Scrape webpage content if allowed by robots.txt"""
    if not check_robots_txt(url):
        return None
        
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove unwanted elements
        for element in soup(['script', 'style', 'nav', 'footer']):
            element.decompose()
            
        return soup.get_text(separator='\n', strip=True)
    except:
        return None

@agent.tool(prepare=check_authorization)
async def tavily_websearch(ctx: RunContext, question) -> str:
    """Search the web for the answer to the question about technology topic."""
    api_key = os.getenv("Tavily_API_KEY")
    tavily_client = AsyncTavilyClient(api_key)
    search_results = await tavily_client.search(query=question,include_answer=True,include_raw_content=True)
    
    results = []
    for result in search_results['results']:
        content = scrape_webpage(result['url'])
        if content:
            results.append({
                'search_result': result,
                'scaraped_content': content[:2000]  # Limit content length
            })
        else:
            results.append({
                'search_result': result,
                'scaraped_content': "Content not available"
            })
    
    
    return json.dumps(results, ensure_ascii=False)


# %%
if __name__ == "__main__":
    import nest_asyncio
    nest_asyncio.apply()
    result = agent.run_sync("AIエージェントフレームワークのはやりを教えて", deps=True)
    print(result.data)
# %%
