"""Hacker News用スクレイパー."""

from __future__ import annotations

import asyncio
import json
from datetime import datetime
from typing import Any

from loguru import logger
from pydantic import HttpUrl, ValidationError

from ..models.data_models import Article, Author
from .base import BaseScraper


class HackerNewsScraper(BaseScraper):
    """Hacker News用スクレイパー"""

    def __init__(self) -> None:
        super().__init__("hackernews", "https://news.ycombinator.com")
        self.api_base = "https://hacker-news.firebaseio.com/v0"

    async def get_top_stories(self, limit: int = 30) -> list[int]:
        """トップストーリーのIDリストを取得"""
        url = f"{self.api_base}/topstories.json"
        response_text = await self.fetch_page(url)

        if response_text:
            try:
                parsed_ids = json.loads(response_text)
            except json.JSONDecodeError as exc:
                logger.error("Error parsing top stories JSON: {}", exc)
                return []

            if isinstance(parsed_ids, list):
                story_ids: list[int] = [
                    int(item)
                    for item in parsed_ids
                    if isinstance(item, int | float | str) and str(item).isdigit()
                ]
                return story_ids[:limit]

            logger.error("Unexpected data type for top stories: {}", type(parsed_ids))
            return []
        return []

    async def get_story_details(self, story_id: int) -> dict[str, Any] | None:
        """ストーリーの詳細を取得"""
        url = f"{self.api_base}/item/{story_id}.json"
        response_text = await self.fetch_page(url)

        if response_text:
            try:
                parsed_data = json.loads(response_text)
            except json.JSONDecodeError as exc:
                logger.error("Error parsing story {} JSON: {}", story_id, exc)
                return None

            if isinstance(parsed_data, dict):
                return parsed_data

            logger.error(
                "Unexpected data type for story {} JSON: {}",
                story_id,
                type(parsed_data),
            )
            return None
        return None

    def parse_story_to_article(self, story_data: dict[str, Any]) -> Article | None:
        """ストーリーデータをArticleモデルに変換"""
        try:
            # 必須フィールドのチェック
            if not all(key in story_data for key in ["id", "title", "by", "time"]):
                logger.warning(
                    "Missing required fields in story {}",
                    story_data.get("id", "unknown"),
                )
                return None

            # 作者情報
            profile_url_str = f"https://news.ycombinator.com/user?id={story_data['by']}"
            try:
                profile_url: HttpUrl | None = HttpUrl(profile_url_str)
            except ValidationError:
                profile_url = None

            author = Author(username=story_data["by"], profile_url=profile_url)

            # タイムスタンプ変換
            timestamp = datetime.fromtimestamp(story_data["time"])

            # 記事URL（外部リンクまたはHN内のディスカッション）
            article_url_raw = story_data.get("url")
            if not article_url_raw:
                article_url_raw = (
                    f"https://news.ycombinator.com/item?id={story_data['id']}"
                )

            article_url: HttpUrl | None = None
            if article_url_raw:
                try:
                    article_url = HttpUrl(article_url_raw)
                except ValidationError:
                    logger.warning(
                        "Invalid article URL for story {}", story_data.get("id")
                    )

            # ソースURL（HNのディスカッションページ）
            source_url_str = f"https://news.ycombinator.com/item?id={story_data['id']}"
            try:
                source_url: HttpUrl = HttpUrl(source_url_str)
            except ValidationError:
                logger.error("Invalid source URL for story {}", story_data.get("id"))
                return None

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
            logger.error(
                "Error parsing story {}: {}",
                story_data.get("id", "unknown"),
                e,
            )
            return None

    async def scrape_articles(self, limit: int = 30) -> list[Article]:
        """記事をスクレイピング"""
        logger.info(f"Fetching top {limit} stories from Hacker News")

        # トップストーリーのIDを取得
        story_ids = await self.get_top_stories(limit)
        if not story_ids:
            logger.error("Failed to fetch story IDs")
            return []

        articles = []

        # 各ストーリーの詳細を並行取得
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

    def _connectivity_fallback_sample(self) -> str | None:
        """オフライン時の接続確認で利用するサンプルレスポンス."""
        return "<html><title>Hacker News</title></html>"

    async def _validate_site_specific(self) -> dict[str, Any]:
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
