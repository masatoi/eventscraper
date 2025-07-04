"""
Hacker News用スクレイパー
"""

import json
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from pydantic import HttpUrl

from .base import BaseScraper
from ..models.data_models import Article, Author


class HackerNewsScraper(BaseScraper):
    """Hacker News用スクレイパー"""

    def __init__(self) -> None:
        super().__init__("hackernews", "https://news.ycombinator.com")
        self.api_base = "https://hacker-news.firebaseio.com/v0"

    async def get_top_stories(self, limit: int = 30) -> List[int]:
        """トップストーリーのIDリストを取得"""
        url = f"{self.api_base}/topstories.json"
        response_text = await self.fetch_page(url)

        if response_text:
            try:
                story_ids = json.loads(response_text)
                return story_ids[:limit]
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing top stories JSON: {e}")
                return []
        return []

    async def get_story_details(self, story_id: int) -> Optional[Dict[str, Any]]:
        """ストーリーの詳細を取得"""
        url = f"{self.api_base}/item/{story_id}.json"
        response_text = await self.fetch_page(url)

        if response_text:
            try:
                return json.loads(response_text)
            except json.JSONDecodeError as e:
                logger.error(f"Error parsing story {story_id} JSON: {e}")
                return None
        return None

    def parse_story_to_article(self, story_data: Dict[str, Any]) -> Optional[Article]:
        """ストーリーデータをArticleモデルに変換"""
        try:
            # 必須フィールドのチェック
            if not all(key in story_data for key in ["id", "title", "by", "time"]):
                logger.warning(
                    f"Missing required fields in story {story_data.get('id', 'unknown')}"
                )
                return None

            # 作者情報
            profile_url_str = f"https://news.ycombinator.com/user?id={story_data['by']}"
            profile_url: Optional[HttpUrl] = HttpUrl(profile_url_str)
            author = Author(username=story_data["by"], profile_url=profile_url)

            # タイムスタンプ変換
            timestamp = datetime.fromtimestamp(story_data["time"])

            # 記事URL（外部リンクまたはHN内のディスカッション）
            article_url_raw = story_data.get("url")
            if not article_url_raw:
                article_url_raw = (
                    f"https://news.ycombinator.com/item?id={story_data['id']}"
                )

            article_url: Optional[HttpUrl] = (
                HttpUrl(article_url_raw) if article_url_raw else None
            )

            # ソースURL（HNのディスカッションページ）
            source_url_str = f"https://news.ycombinator.com/item?id={story_data['id']}"
            source_url: HttpUrl = HttpUrl(source_url_str)

            article = Article(
                id=str(story_data["id"]),
                title=story_data["title"],
                url=article_url,
                content=story_data.get("text"),  # Ask HN posts may have text
                author=author,
                timestamp=timestamp,
                score=story_data.get("score", 0),
                comments_count=story_data.get("descendants", 0),
                source_site="hackernews",
                source_url=source_url,
                metadata={
                    "type": story_data.get("type", "story"),
                    "hn_id": story_data["id"],
                },
            )

            return article

        except Exception as e:
            logger.error(f"Error parsing story {story_data.get('id', 'unknown')}: {e}")
            return None

    async def scrape_articles(self, limit: int = 30) -> List[Article]:
        """記事をスクレイピング"""
        logger.info(f"Fetching top {limit} stories from Hacker News")

        # トップストーリーのIDを取得
        story_ids = await self.get_top_stories(limit)
        if not story_ids:
            logger.error("Failed to fetch story IDs")
            return []

        articles = []

        # 各ストーリーの詳細を並行取得
        import asyncio

        tasks = [self.get_story_details(story_id) for story_id in story_ids]
        story_details_list = await asyncio.gather(*tasks, return_exceptions=True)

        for i, story_details in enumerate(story_details_list):
            if isinstance(story_details, Exception):
                logger.error(f"Error fetching story {story_ids[i]}: {story_details}")
                continue

            if story_details and isinstance(story_details, dict):
                article = self.parse_story_to_article(story_details)
                if article:
                    articles.append(article)

        logger.info(f"Successfully parsed {len(articles)} articles from Hacker News")
        return articles

    async def _validate_site_specific(self) -> Dict[str, Any]:
        """Hacker News固有の検証"""
        try:
            issues = []

            # Firebase APIの動作確認
            api_check = await self.fetch_page(f"{self.api_base}/topstories.json")
            if api_check is None:
                return {
                    "success": False,
                    "error": "Firebase API not accessible",
                    "critical": True,
                }

            try:
                import json

                story_ids = json.loads(api_check)
                if not isinstance(story_ids, list) or len(story_ids) == 0:
                    issues.append("Firebase API returned invalid data format")
                elif len(story_ids) < 10:
                    issues.append(
                        f"Firebase API returned unusually few stories: {len(story_ids)}"
                    )
            except json.JSONDecodeError:
                return {
                    "success": False,
                    "error": "Firebase API returned invalid JSON",
                    "critical": True,
                }

            # 個別記事APIのチェック
            if story_ids and len(story_ids) > 0:
                sample_story_id = story_ids[0]
                story_detail = await self.fetch_page(
                    f"{self.api_base}/item/{sample_story_id}.json"
                )
                if story_detail is None:
                    issues.append("Individual story API not accessible")
                else:
                    try:
                        story_data = json.loads(story_detail)
                        required_fields = ["id", "title", "by", "time"]
                        missing_fields = [
                            field
                            for field in required_fields
                            if field not in story_data
                        ]
                        if missing_fields:
                            issues.append(
                                f"Story data missing fields: {missing_fields}"
                            )
                    except json.JSONDecodeError:
                        issues.append("Individual story API returned invalid JSON")

            # ウェブサイトの基本チェック
            web_check = await self.fetch_page("https://news.ycombinator.com")
            if web_check is None:
                issues.append("Hacker News website not accessible")
            elif "Hacker News" not in web_check:
                issues.append("Hacker News website content appears to have changed")

            if issues:
                return {
                    "success": False,
                    "error": "; ".join(issues),
                    "critical": any("critical" in issue.lower() for issue in issues),
                }

            return {
                "success": True,
                "api_stories_count": len(story_ids) if "story_ids" in locals() else 0,
                "sample_story_id": story_ids[0] if story_ids else None,
                "website_accessible": web_check is not None,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "critical": True}
