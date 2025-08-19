"""
Crawler Manager Service

Handles initialization and management of the Crawl4AI crawler instance.
This avoids circular imports by providing a service-level access to the crawler.
"""

import os
import sys
import asyncio
import httpx
import re
from typing import Optional
from bs4 import BeautifulSoup, NavigableString
from urllib.parse import urljoin, urlparse

# Windows event loop policy is now set in main.py

try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig
except ImportError:
    AsyncWebCrawler = None
    BrowserConfig = None

from ..config.logfire_config import get_logger, safe_logfire_error, safe_logfire_info

logger = get_logger(__name__)


class FallbackCrawler:
    """Simple HTTP-based crawler fallback for Windows when Playwright fails."""
    
    def __init__(self):
        self.client = None
        
    async def __aenter__(self):
        self.client = httpx.AsyncClient(
            timeout=30.0,
            headers={
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
            }
        )
        return self
        
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        if self.client:
            await self.client.aclose()
            
    async def arun(self, url: str, **kwargs):
        """Simple crawl implementation that returns basic text content."""
        try:
            response = await self.client.get(url)
            response.raise_for_status()
            
            # Parse HTML with BeautifulSoup
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()
                
            # Get text content
            text = soup.get_text()
            
            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = ' '.join(chunk for chunk in chunks if chunk)
            
            # Create a simple result object that mimics Crawl4AI's structure
            class SimpleResult:
                def __init__(self, markdown_content, url):
                    self.markdown = markdown_content
                    self.cleaned_html = markdown_content
                    self.html = markdown_content  # Add html attribute
                    self.url = url
                    self.success = True
                    self.status_code = response.status_code
                    
            return SimpleResult(text, url)
            
        except Exception as e:
            logger.error(f"Fallback crawler failed for {url}: {e}")
            class FailedResult:
                def __init__(self, url, error):
                    self.markdown = ""
                    self.cleaned_html = ""
                    self.html = ""  # Add html attribute
                    self.url = url
                    self.success = False
                    self.error = str(error)
                    self.status_code = 0
                    
            return FailedResult(url, e)


class CrawlerManager:
    """Manages the global crawler instance."""

    _instance: Optional["CrawlerManager"] = None
    _crawler: AsyncWebCrawler | FallbackCrawler | None = None
    _initialized: bool = False
    _using_fallback: bool = False

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    async def get_crawler(self) -> AsyncWebCrawler | FallbackCrawler:
        """Get or create the crawler instance."""
        if not self._initialized or self._crawler is None:
            await self.initialize()
        return self._crawler

    async def initialize(self):
        """Initialize the crawler if not already initialized."""
        if self._initialized and self._crawler is not None:
            safe_logfire_info("Crawler already initialized, skipping")
            return

        try:
            safe_logfire_info("Initializing Crawl4AI crawler...")
            logger.info("=== CRAWLER INITIALIZATION START ===")

            # Check if crawl4ai is available
            if not AsyncWebCrawler or not BrowserConfig:
                logger.error("ERROR: crawl4ai not available")
                logger.error(f"AsyncWebCrawler: {AsyncWebCrawler}")
                logger.error(f"BrowserConfig: {BrowserConfig}")
                raise ImportError("crawl4ai is not installed or available")

            # Check for Docker environment
            in_docker = os.path.exists("/.dockerenv") or os.getenv("DOCKER_CONTAINER", False)
            
            # Simple, working browser config for Windows compatibility
            if sys.platform.startswith('win'):
                logger.info("=== USING WINDOWS CRAWL4AI CONFIGURATION WITH SELENIUM FALLBACK ===")
                safe_logfire_info("Windows detected - attempting Selenium fallback")
                
                # For Windows, use environment variables to locate browsers
                try:
                    logger.info(f"PLAYWRIGHT_BROWSERS_PATH set to: {os.environ.get('PLAYWRIGHT_BROWSERS_PATH', 'Not set')}")
                    
                    browser_config = BrowserConfig(
                        headless=True,
                        browser_type="chromium",
                        verbose=True,
                        extra_args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu", 
                            "--disable-extensions",
                            "--disable-background-timer-throttling",
                            "--disable-backgrounding-occluded-windows",
                            "--disable-renderer-backgrounding"
                        ]
                    )
                    logger.info("Windows config with environment path created with args: %s", browser_config.extra_args)
                except Exception as selenium_e:
                    logger.warning(f"Selenium config failed, trying minimal Playwright: {selenium_e}")
                    # Fallback to minimal Playwright config
                    browser_config = BrowserConfig(
                        headless=True,
                        browser_type="chromium",
                        verbose=False,
                        extra_args=[
                            "--no-sandbox",
                            "--disable-dev-shm-usage",
                            "--disable-gpu", 
                            "--disable-extensions"
                        ]
                    )
                    logger.info("Windows minimal config created with args: %s", browser_config.extra_args)
            else:
                # More comprehensive config for non-Windows systems
                browser_config = BrowserConfig(
                    headless=True,
                    verbose=False,
                    viewport_width=1920,
                    viewport_height=1080,
                    user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
                    browser_type="chromium",
                    extra_args=[
                        "--disable-blink-features=AutomationControlled",
                        "--disable-dev-shm-usage",
                        "--no-sandbox",
                        "--disable-setuid-sandbox",
                        "--disable-web-security",
                        "--disable-gpu",
                        "--disable-extensions",
                        "--disable-plugins",
                        "--no-first-run"
                    ]
                )

            safe_logfire_info(f"Creating AsyncWebCrawler with config | in_docker={in_docker}")

            # Initialize crawler with the correct parameter name
            self._crawler = AsyncWebCrawler(config=browser_config)
            safe_logfire_info("AsyncWebCrawler instance created, entering context...")
            
            # Initialize crawler - should work on all platforms with proper config
            await self._crawler.__aenter__()
            self._initialized = True
            safe_logfire_info(f"Crawler entered context successfully | crawler={self._crawler}")

            safe_logfire_info("✅ Crawler initialized successfully")
            logger.info("=== CRAWLER INITIALIZATION SUCCESS ===")
            logger.info(f"Crawler instance: {self._crawler}")
            logger.info(f"Initialized: {self._initialized}")

        except Exception as e:
            safe_logfire_error(f"Failed to initialize Crawl4AI crawler, trying fallback: {e}")
            import traceback

            tb = traceback.format_exc()
            safe_logfire_error(f"Crawl4AI initialization traceback: {tb}")
            logger.error("=== CRAWL4AI INITIALIZATION ERROR ===")
            logger.error(f"Error: {e}")
            logger.error(f"Traceback:\n{tb}")
            logger.error("=== END CRAWL4AI ERROR ===")
            
            # Try fallback crawler for Windows
            try:
                logger.info("=== FALLBACK CRAWLER INITIALIZATION START ===")
                safe_logfire_info("Initializing fallback HTTP crawler...")
                
                self._crawler = FallbackCrawler()
                await self._crawler.__aenter__()
                self._initialized = True
                self._using_fallback = True
                
                logger.info("=== FALLBACK CRAWLER INITIALIZATION SUCCESS ===")
                safe_logfire_info("✅ Fallback crawler initialized successfully")
                logger.info(f"Fallback crawler instance: {self._crawler}")
                logger.info(f"Using fallback: {self._using_fallback}")
                
            except Exception as fallback_e:
                safe_logfire_error(f"Fallback crawler also failed: {fallback_e}")
                logger.error("=== FALLBACK CRAWLER ERROR ===")
                logger.error(f"Error: {fallback_e}")
                logger.error("=== END FALLBACK ERROR ===")
                
                self._crawler = None
                self._initialized = False
                self._using_fallback = False
                raise Exception(f"Both Crawl4AI and fallback crawler failed: {e}, {fallback_e}")

    async def cleanup(self):
        """Clean up the crawler resources."""
        if self._crawler and self._initialized:
            try:
                await self._crawler.__aexit__(None, None, None)
                safe_logfire_info("Crawler cleaned up successfully")
            except Exception as e:
                safe_logfire_error(f"Error cleaning up crawler: {e}")
            finally:
                self._crawler = None
                self._initialized = False


# Global instance
_crawler_manager = CrawlerManager()


async def get_crawler() -> AsyncWebCrawler | FallbackCrawler | None:
    """Get the global crawler instance."""
    global _crawler_manager
    crawler = await _crawler_manager.get_crawler()
    if crawler is None:
        logger.warning("get_crawler() returning None")
        logger.warning(f"_crawler_manager: {_crawler_manager}")
        logger.warning(
            f"_crawler_manager._crawler: {_crawler_manager._crawler if _crawler_manager else 'N/A'}"
        )
        logger.warning(
            f"_crawler_manager._initialized: {_crawler_manager._initialized if _crawler_manager else 'N/A'}"
        )
    return crawler


async def initialize_crawler():
    """Initialize the global crawler."""
    await _crawler_manager.initialize()


async def cleanup_crawler():
    """Clean up the global crawler."""
    await _crawler_manager.cleanup()
