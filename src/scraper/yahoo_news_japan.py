"""Yahoo!ニュース(日本)用スクレイパー"""

from datetime import datetime
import re
from typing import List, Optional, Dict, Any
from xml.etree import ElementTree
from urllib.parse import urlparse

from loguru import logger
from pydantic import HttpUrl

from .base import BaseScraper
from ..models.data_models import Article, Author


class YahooNewsJapanScraper(BaseScraper):
    """Yahoo!ニュース(日本)用スクレイパー"""

    RSS_URL = "https://news.yahoo.co.jp/rss/topics/top-picks.xml"

    def __init__(self) -> None:
        super().__init__("yahoo_news_japan", "https://news.yahoo.co.jp")

    def parse_item_to_article(self, item: ElementTree.Element) -> Optional[Article]:
        """RSSアイテムをArticleモデルに変換"""
        try:
            title = item.findtext("title")
            link = item.findtext("link")
            pub_date = item.findtext("pubDate")

            if not title or not link or not pub_date:
                logger.warning("Missing required fields in RSS item")
                return None

            # IDをURLのパスから抽出
            parsed = urlparse(link)
            segments = [seg for seg in parsed.path.split("/") if seg]
            item_id = segments[-1] if segments else link

            timestamp = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %Z")

            url_obj: HttpUrl = HttpUrl(link)
            author = Author(username="Yahoo!ニュース")

            article = Article(
                id=item_id,
                title=title,
                url=url_obj,
                content=None,
                author=author,
                timestamp=timestamp,
                score=None,
                comments_count=0,
                source_site="yahoo_news_japan",
                source_url=url_obj,
                metadata={},
            )

            return article
        except Exception as e:
            logger.error(f"Error parsing RSS item: {e}")
            return None

    async def scrape_articles(self, limit: int = 30) -> List[Article]:
        """記事をスクレイピング"""
        logger.info(f"Fetching Yahoo News Japan RSS (limit: {limit})")

        rss_text = await self.fetch_page(self.RSS_URL)
        if not rss_text:
            return []

        try:
            root = ElementTree.fromstring(rss_text)
        except ElementTree.ParseError as e:
            logger.error(f"Error parsing RSS XML: {e}")
            return []

        items = root.findall(".//item")
        articles: List[Article] = []
        for item in items[:limit]:
            article = self.parse_item_to_article(item)
            if article:
                articles.append(article)

        logger.info(f"Successfully parsed {len(articles)} Yahoo News Japan articles")
        return articles

    async def _validate_site_specific(self) -> Dict[str, Any]:
        """Yahooニュース固有の検証"""
        try:
            rss_text = await self.fetch_page(self.RSS_URL)
            if not rss_text:
                return {
                    "success": False,
                    "error": "RSS feed not accessible",
                    "critical": True,
                }

            try:
                root = ElementTree.fromstring(rss_text)
            except ElementTree.ParseError:
                return {"success": False, "error": "Invalid RSS XML", "critical": True}

            items = root.findall(".//item")
            if not items:
                return {
                    "success": False,
                    "error": "No items in RSS feed",
                    "critical": True,
                }

            sample_article = self.parse_item_to_article(items[0])
            if not sample_article:
                return {
                    "success": False,
                    "error": "Failed to parse sample item",
                    "critical": True,
                }

            return {
                "success": True,
                "items_count": len(items),
                "sample_id": sample_article.id,
            }
        except Exception as e:
            return {"success": False, "error": str(e), "critical": True}
