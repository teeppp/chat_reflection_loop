# %%
from pydantic_ai import Agent, RunContext
from pydantic import BaseModel
from typing import List, Optional
import aiohttp
import json
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
import google.auth
import os

credentials, project = google.auth.default()
print(credentials)
print(project)
# %%
if __name__ == "__main__":
    from dotenv import load_dotenv    
    load_dotenv()
if os.getenv("LOGFIRE_TOKEN", None):
    import logfire
    logfire.configure(send_to_logfire='if-token-present')

# %%

model = VertexAIModel(
    os.getenv('VERTEXAI_LLM_DEPLOYMENT','gemini-2.0-pro-exp-02-05'),
)
# %%
agent = Agent(
    model,
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
async def tavily_websearch(ctx: RunContext[str]) -> str:
    """Search the web for the answer."""
    api_key = os.getenv("TAVILY_API_KEY")
    tavily_client = AsyncTavilyClient(api_key)
    # print("Prompt:")
    # print(ctx.prompt)
    # print("Messages:")
    # print(ctx.messages)
    ## ユーザーの素の質問がそのままクエリに使われてしまう
    search_results = await tavily_client.search(query=ctx.prompt,include_answer=True,include_raw_content=True)
    
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
    result = agent.run_sync("AIエージェントフレームワークのはやりを検索して", deps=True)
    print(result.data)
# %%
if __name__ == "__main__":
    original = result.new_messages()
    print(original)
# %%
if __name__ == "__main__":
    from pydantic_ai.messages import (
        ModelMessage,
        ModelMessagesTypeAdapter,
        ModelRequest,
        ModelResponse,
        TextPart,
        UserPromptPart,
    )
    new_message_json = result.new_messages_json()
    new_message = ModelMessagesTypeAdapter.validate_json(new_message_json)
    print(new_message)
# %%
