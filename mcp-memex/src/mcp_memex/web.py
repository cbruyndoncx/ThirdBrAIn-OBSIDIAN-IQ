from firecrawl import FirecrawlApp
from pathlib import Path
import os

async def scrape_url(cache_dir: Path, url: str) -> str:
    """Fetch page content from FireCrawl API"""
    firecrawl_api_key = os.getenv("FIRECRAWL_API_KEY")
    if not firecrawl_api_key:
        raise Exception("FIRECRAWL_API_KEY environment variable is required")
    
    app = FirecrawlApp(api_key=firecrawl_api_key)
    response = app.scrape_url(url)
    content = response['markdown']

    # Cache the response
    output_path = get_url_cache_path(cache_dir, url)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, "w") as f:
        f.write(content)

    return content

def get_url_cache_path(cache_dir: Path, url: str) -> Path:
    """Get the cache URL for a given URL"""
    return cache_dir / f"{url.replace('://', '/')}.md"

def fetch_cached_page(cache_dir: Path, url: str) -> str | None:
    """Get cached page content"""
    path = get_url_cache_path(cache_dir, url)
    if not path.exists():
        return None
    return path.read_text()

async def fetch_page(cache_dir: Path, url: str) -> str:
    """Get cached page content or scrape if not found"""
    # Check if URL is already scraped
    content = fetch_cached_page(cache_dir, url)
    if content:
        return content
    content = await scrape_url(cache_dir, url)
    return content