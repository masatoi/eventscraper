"""
スクレイパーの基底クラス
"""
from abc import ABC, abstractmethod
from typing import List, Optional, Any
import aiohttp
from datetime import datetime
from loguru import logger

from ..models.data_models import Article, ScrapingResult


class BaseScraper(ABC):
    """スクレイパーの基底クラス"""

    def __init__(self, site_name: str, base_url: str) -> None:
        self.site_name = site_name
        self.base_url = base_url
        self.session: Optional[aiohttp.ClientSession] = None

    async def __aenter__(self) -> "BaseScraper":
        """非同期コンテキストマネージャーの開始"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={"User-Agent": "EventScraper/1.0 (Educational Purpose)"},
        )
        return self

    async def __aexit__(self, exc_type: Any, exc_val: Any, exc_tb: Any) -> None:
        """非同期コンテキストマネージャーの終了"""
        if self.session:
            await self.session.close()

    async def fetch_page(self, url: str) -> Optional[str]:
        """ページのHTMLを取得"""
        if self.session is None:
            logger.error("Session is not initialized")
            return None

        try:
            async with self.session.get(url) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.warning(f"HTTP {response.status} for {url}")
                    return None
        except Exception as e:
            logger.error(f"Error fetching {url}: {e}")
            return None

    @abstractmethod
    async def scrape_articles(self, limit: int = 30) -> List[Article]:
        """記事をスクレイピング（サブクラスで実装）"""
        pass

    async def scrape(self, limit: int = 30) -> ScrapingResult:
        """スクレイピングを実行して結果を返す"""
        logger.info(f"Starting scraping for {self.site_name}")
        start_time = datetime.now()

        try:
            articles = await self.scrape_articles(limit)
            success_count = len(articles)
            error_count = 0
            errors: List[str] = []

            logger.info(f"Scraped {success_count} articles from {self.site_name}")

            return ScrapingResult(
                site=self.site_name,
                scraped_at=start_time,
                articles=articles,
                total_count=success_count,
                success_count=success_count,
                error_count=error_count,
                errors=errors,
            )

        except Exception as e:
            logger.error(f"Error scraping {self.site_name}: {e}")
            return ScrapingResult(
                site=self.site_name,
                scraped_at=start_time,
                articles=[],
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[str(e)],
            )
