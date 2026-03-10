import os
import logging
from typing import Any, Dict, List, Optional, Tuple
from datetime import datetime
import json
from fastapi import FastAPI, HTTPException, WebSocket
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn
from dotenv import load_dotenv
import aiohttp
from tenacity import retry, stop_after_attempt, wait_exponential
import structlog
from enum import Enum

load_dotenv()

# Configure logging
structlog.configure(
    processors=[
        structlog.stdlib.filter_by_level,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso"),
        structlog.processors.StackInfoRenderer(),
        structlog.processors.format_exc_info,
        structlog.processors.UnicodeDecoder(),
        structlog.processors.JSONRenderer()
    ],
    context_class=dict,
    logger_factory=structlog.stdlib.LoggerFactory(),
    cache_logger_on_first_use=True,
)

logger = structlog.get_logger(__name__)

# Configuration
API_KEYS = {
    "google": os.getenv("GOOGLE_API_KEY"),
    "serper": os.getenv("SERPER_API_KEY"),
    "arxiv": os.getenv("ARXIV_API_KEY"),
}

class ResearchTool(str, Enum):
    WEB_SEARCH = "web_search"
    ACADEMIC = "academic"
    CODE_SEARCH = "code_search"
    DATABASE = "database"
    API_AGGREGATION = "api_aggregation"

class ResearchQuery(BaseModel):
    query: str = Field(..., min_length=1, max_length=1000)
    tools: List[ResearchTool] = Field(default=[ResearchTool.WEB_SEARCH])
    depth: int = Field(default=1, ge=1, le=5)
    max_results: int = Field(default=10, ge=1, le=100)

class ResearchResult(BaseModel):
    query: str
    tool: ResearchTool
    results: List[Dict[str, Any]]
    timestamp: str
    metadata: Dict[str, Any]

class MultiToolResearchAgent:
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self.search_history: List[ResearchQuery] = []
        self.cache: Dict[str, ResearchResult] = {}

    async def initialize(self):
        """Initialize HTTP session"""
        self.session = aiohttp.ClientSession()
        logger.info("Research agent initialized")

    async def close(self):
        """Close HTTP session"""
        if self.session:
            await self.session.close()

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def web_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Perform web search using Serper API"""
        url = "https://google.serper.dev/search"
        headers = {"X-API-KEY": API_KEYS["serper"]}
        payload = {"q": query, "num": max_results}
        
        try:
            async with self.session.post(url, json=payload, headers=headers) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Web search completed", query=query, results=len(data.get("organic", [])))
                    return data.get("organic", [])
                else:
                    logger.error(f"Web search failed", status=response.status)
                    return []
        except Exception as e:
            logger.error(f"Web search error: {str(e)}")
            raise

    @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
    async def academic_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search academic papers using arXiv API"""
        url = "http://export.arxiv.org/api/query"
        params = {"search_query": f"all:{query}", "start": 0, "max_results": max_results}
        
        try:
            async with self.session.get(url, params=params) as response:
                if response.status == 200:
                    import xml.etree.ElementTree as ET
                    content = await response.text()
                    root = ET.fromstring(content)
                    papers = []
                    for entry in root.findall("{http://www.w3.org/2005/Atom}entry"):
                        papers.append({
                            "title": entry.find("{http://www.w3.org/2005/Atom}title").text,
                            "summary": entry.find("{http://www.w3.org/2005/Atom}summary").text,
                            "published": entry.find("{http://www.w3.org/2005/Atom}published").text,
                        })
                    logger.info(f"Academic search completed", query=query, papers=len(papers))
                    return papers
                else:
                    logger.error(f"Academic search failed", status=response.status)
                    return []
        except Exception as e:
            logger.error(f"Academic search error: {str(e)}")
            raise

    async def code_search(self, query: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """Search code repositories using GitHub API"""
        url = "https://api.github.com/search/repositories"
        headers = {"Accept": "application/vnd.github.v3+json"}
        params = {"q": query, "sort": "stars", "order": "desc", "per_page": max_results}
        
        try:
            async with self.session.get(url, headers=headers, params=params) as response:
                if response.status == 200:
                    data = await response.json()
                    logger.info(f"Code search completed", query=query, repos=len(data.get("items", [])))
                    return data.get("items", [])
                else:
                    logger.error(f"Code search failed", status=response.status)
                    return []
        except Exception as e:
            logger.error(f"Code search error: {str(e)}")
            raise

    async def research(self, research_query: ResearchQuery) -> List[ResearchResult]:
        """Orchestrate multi-tool research"""
        results = []
        self.search_history.append(research_query)
        
        for tool in research_query.tools:
            cache_key = f"{research_query.query}:{tool}"
            if cache_key in self.cache:
                results.append(self.cache[cache_key])
                continue
            
            if tool == ResearchTool.WEB_SEARCH:
                search_results = await self.web_search(research_query.query, research_query.max_results)
            elif tool == ResearchTool.ACADEMIC:
                search_results = await self.academic_search(research_query.query, research_query.max_results)
            elif tool == ResearchTool.CODE_SEARCH:
                search_results = await self.code_search(research_query.query, research_query.max_results)
            else:
                search_results = []
            
            result = ResearchResult(
                query=research_query.query,
                tool=tool,
                results=search_results,
                timestamp=datetime.now().isoformat(),
                metadata={"depth": research_query.depth}
            )
            self.cache[cache_key] = result
            results.append(result)
        
        logger.info(f"Research completed", query=research_query.query, tools_used=len(research_query.tools))
        return results

app = FastAPI(title="Multi-Tool Research Agent")
agent = MultiToolResearchAgent()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.on_event("startup")
async def startup_event():
    await agent.initialize()
    logger.info("Application started")

@app.on_event("shutdown")
async def shutdown_event():
    await agent.close()
    logger.info("Application shutdown")

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now().isoformat()}

@app.post("/research")
async def perform_research(query: ResearchQuery) -> List[ResearchResult]:
    """Perform multi-tool research"""
    try:
        results = await agent.research(query)
        return results
    except Exception as e:
        logger.error(f"Research failed: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/history")
async def get_search_history():
    """Get search history"""
    return {"history": agent.search_history}

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    """WebSocket endpoint for real-time updates"""
    await websocket.accept()
    try:
        while True:
            data = await websocket.receive_text()
            query = ResearchQuery(**json.loads(data))
            results = await agent.research(query)
            await websocket.send_json({"results": [r.dict() for r in results]})
    except Exception as e:
        logger.error(f"WebSocket error: {str(e)}")
        await websocket.close(code=1000)

if __name__ == "__main__":
    uvicorn.run(
        app,
        host=os.getenv("HOST", "0.0.0.0"),
        port=int(os.getenv("PORT", 8000)),
        log_level=os.getenv("LOG_LEVEL", "info")
    )
