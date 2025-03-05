from datetime import datetime
from enum import Enum
import json
from pathlib import Path
from typing import Sequence


from mcp.server import Server
from mcp.server.stdio import stdio_server
from mcp.types import Tool, TextContent, ImageContent, EmbeddedResource
from mcp.shared.exceptions import McpError

from pydantic import BaseModel

from mcp_memex.analysis import analyze_content
from mcp_memex.web import fetch_page
from mcp_memex.notes import add_artifact, get_topics, add_note, add_journal_entry

from .vector_store import VectorDB


class MemexTools(str, Enum):
    ANALYZE ="analyze_web_content"
    SEARCH = "search_knowledge_base"
    SAVE = "save_artifact"


class AnalyzeInput(BaseModel):
    query: str
    urls: str


class QueryInput(BaseModel):
    query: str


class SaveInput(BaseModel):
    name: str
    content: str


class SearchResult(BaseModel):
    url: str
    content: str
    similarity: float


class MemexServer:
    def __init__(self, index_dir: str, workspace_dir: str):
        
        self.index_dir = Path(index_dir)
        self.cache_dir = self.index_dir / "cache"
        self.workspace_dir = Path(workspace_dir)
        self.vector_db = VectorDB(self.index_dir)

    def write_analysis(self, query: str, urls: list[str], title: str, content: str) -> None:
        """Write the analysis to the workspace"""
        front_matter = f"""---
query: {query}
sources: {", ".join(urls)}
created: {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}
---
"""
        add_note(title, front_matter + content, self.workspace_dir)

    def write_analysis_journal_entry(self, query: str, urls: list[str], title: str, content: str) -> None:
        """Write a journal entry to the workspace"""
        journal_entry = f"- Added [[{title}]]\n"
        for url in urls:
            journal_entry += f"  - {url}\n"
        add_journal_entry(journal_entry, self.workspace_dir)

    def write_artifact_journal_entry(self, name: str, content: str) -> None:
        """Write a journal entry to the workspace"""
        journal_entry = f"- Saved [[{name}]]\n"
        add_journal_entry(journal_entry, self.workspace_dir)
    
    async def analyze(self, query: str, urls: list[str]) -> str:
        """Analyze a query and a list of URLs"""
        topics = get_topics(self.workspace_dir)
        results = []
        for url in urls:
            content = await fetch_page(self.cache_dir, url)
            title, result = await analyze_content(query, content, url, topics)
            results.append(result)

        # TODO: Add more advanced merging of results
        analysis = "\n\n".join(results)

        self.write_analysis(query, urls, title, analysis)
        self.write_analysis_journal_entry(query, urls, title, analysis)
        
        analysis_path = self.workspace_dir / "Notes" / f"{title}.md"
        self.vector_db.add_document(title, analysis_path)
        self.vector_db.save_db()

        return analysis
    
    def query(self, query_text: str) -> str:
        """Search for relevant content"""
        results = self.vector_db.search(query_text)

        formatted_results = ""

        results_by_path = {}
        for result in results:
            path = result['metadata'].path
            results_by_path[path] = results_by_path.get(path, []) + [result]

        for path, results in results_by_path.items():
            formatted_results += f"PATH: {path}\n\n"
            results.sort(key=lambda x: x['metadata'].index)
            for result in results:
                formatted_results += f"## {result['metadata'].header}\n\n"
                formatted_results += f"{result['metadata'].content}\n\n"

        return formatted_results
    
    def save_artifact(self, name: str, content: str) -> None:
        """Save an artifact to the knowledge base"""
        add_artifact(name, content, self.workspace_dir)
        self.write_artifact_journal_entry(name, content)
        artifact_path = self.workspace_dir / "Artifacts" / f"{name}.md"
        self.vector_db.add_document(content, artifact_path)
        self.vector_db.save_db()


async def serve(index_dir: str, workspace_dir: str) -> None:
    """Start the memex server"""

    server = Server("mcp-memex")
    memex_server = MemexServer(index_dir, workspace_dir)

    @server.list_tools()
    async def list_tools() -> list[Tool]:
        """List available memex tools."""
        return [
            Tool(
                name=MemexTools.ANALYZE.value,
                description="Analyze multiple web pages and extract relevant information based on your query. This tool fetches and processes the content from provided URLs to answer your specific questions.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "What you want to learn or understand from these web pages",
                        },
                        "urls": {
                            "type": "string",
                            "description": "A comma-separated list of web page URLs you want to analyze",
                        }
                    },
                    "required": ["query", "urls"],
                },
            ),
            Tool(
                name=MemexTools.SEARCH.value,
                description="Search through previously analyzed content in the knowledge base using natural language. This tool helps you find relevant information from your stored content.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "query": {
                            "type": "string", 
                            "description": "What information you're looking for in your knowledge base",
                        }
                    },
                    "required": ["query"],
                },
            ),
            Tool(
                name=MemexTools.SAVE.value,
                description="Save an artifact to the knowledge base",
                inputSchema={
                    "type": "object",
                    "properties": {"content": {"type": "string", "description": "The complete content of the artifact to save"}},
                    "required": ["content"],
                },
            ),
        ]

    @server.call_tool()
    async def call_tool(
        name: str, arguments: dict
    ) -> Sequence[TextContent | ImageContent | EmbeddedResource]:
        """Handle tool calls for memex operations."""
        try:
            match name:
                case MemexTools.ANALYZE.value:
                    input_data = AnalyzeInput(**arguments)
                    urls = input_data.urls.split(",")
                    result = await memex_server.analyze(input_data.query, urls)

                case MemexTools.SEARCH.value:
                    input_data = QueryInput(**arguments)
                    result = memex_server.query(input_data.query)

                case MemexTools.SAVE.value:
                    input_data = SaveInput(**arguments)
                    memex_server.save_artifact(input_data.name, input_data.content)
                    result = "Artifact saved"

                case _:
                    raise ValueError(f"Unknown tool: {name}")

            return [
                TextContent(type="text", text=json.dumps(result, indent=2))
            ]

        except Exception as e:
            raise McpError(f"Error processing memex query: {str(e)}")

    options = server.create_initialization_options()
    async with stdio_server() as (read_stream, write_stream):
        await server.run(read_stream, write_stream, options)
