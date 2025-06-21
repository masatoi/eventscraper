"""
Reuters Japan用スクレイパー
"""

import json
import re
from typing import List, Optional, Dict, Any
from datetime import datetime
from loguru import logger
from bs4 import BeautifulSoup
from pydantic import HttpUrl

from .base import BaseScraper
from ..models.data_models import Article, Author


class ReutersJapanScraper(BaseScraper):
    """Reuters Japan用スクレイパー"""

    def __init__(self) -> None:
        super().__init__("reuters_japan", "https://jp.reuters.com")

    async def extract_fusion_data(self, html_content: str) -> Optional[Dict[str, Any]]:
        """HTMLからFusion.globalContentデータを抽出"""
        try:
            # BeautifulSoupでscriptタグを探す
            soup = BeautifulSoup(html_content, "html.parser")
            script_tags = soup.find_all("script")

            for script in script_tags:
                if script.string and "Fusion.globalContent" in script.string:
                    # FusionオブジェクトからglobalContentを抽出
                    script_content = script.string

                    # 正規表現でglobalContentの部分を抽出
                    pattern = r"Fusion\.globalContent\s*=\s*({.*?});"
                    match = re.search(pattern, script_content, re.DOTALL)

                    if match:
                        json_str = match.group(1)
                        return json.loads(json_str)

            logger.warning("Fusion.globalContent not found in HTML")
            return None

        except Exception as e:
            logger.error(f"Error extracting Fusion data: {e}")
            return None

    async def get_articles_from_page(self, url: str) -> List[Dict[str, Any]]:
        """ページから記事データを取得"""
        html_content = await self.fetch_page(url)
        if not html_content:
            return []

        fusion_data = await self.extract_fusion_data(html_content)
        if not fusion_data:
            return []

        # 記事リストを抽出
        articles: List[Dict[str, Any]] = []

        # resultの中のarticlesを探す
        if "result" in fusion_data and isinstance(fusion_data["result"], dict):
            result = fusion_data["result"]

            # 複数の可能な構造を試す
            possible_paths = [
                ["articles"],
                ["content", "articles"],
                ["items"],
                ["content", "items"],
            ]

            for path in possible_paths:
                current = result
                try:
                    for key in path:
                        if isinstance(current, dict) and key in current:
                            current = current[key]
                        else:
                            break
                    else:
                        if isinstance(current, list):
                            articles = current
                            break
                except (KeyError, TypeError):
                    continue

        # 直接resultがリストの場合もチェック
        if not articles and isinstance(fusion_data.get("result"), list):
            articles = fusion_data["result"]

        logger.info(f"Found {len(articles)} articles in Fusion data")
        return articles

    def parse_reuters_article(self, article_data: Dict[str, Any]) -> Optional[Article]:
        """Reuters記事データをArticleモデルに変換"""
        try:
            # 必須フィールドのチェック
            if not article_data.get("id") or not article_data.get("basic_headline"):
                logger.warning(
                    f"Missing required fields in article {article_data.get('id', 'unknown')}"
                )
                return None

            # タイトル
            title = article_data.get("basic_headline") or article_data.get("title", "")
            if not title:
                return None

            # URL構築
            canonical_url = article_data.get("canonical_url", "")
            article_url: Optional[str] = None
            if canonical_url:
                if canonical_url.startswith("/"):
                    article_url = f"{self.base_url}{canonical_url}"
                else:
                    article_url = canonical_url
            else:
                # URLがない場合はスキップ
                logger.warning(f"No URL found for article {article_data.get('id')}")
                return None

            # 作者情報
            authors = article_data.get("authors", [])
            if authors and isinstance(authors, list) and len(authors) > 0:
                author_data = authors[0]
                author_name = (
                    author_data.get("name")
                    or author_data.get("byline")
                    or f"{author_data.get('first_name', '')} {author_data.get('last_name', '')}".strip()
                    or "Reuters"
                )
            else:
                author_name = "Reuters"

            author = Author(username=author_name)

            # タイムスタンプ
            timestamp_str = (
                article_data.get("display_date")
                or article_data.get("first_publish_date")
                or article_data.get("publish_date")
            )

            if timestamp_str:
                try:
                    # ISO形式の日付をパース
                    if "T" in timestamp_str:
                        timestamp = datetime.fromisoformat(
                            timestamp_str.replace("Z", "+00:00")
                        )
                    else:
                        timestamp = datetime.fromisoformat(timestamp_str)
                except ValueError:
                    timestamp = datetime.now()
            else:
                timestamp = datetime.now()

            # 記事内容（概要）
            content = article_data.get("description", "")

            # article_urlは既にOptional[str]で、Noneでないことを確認済み
            assert article_url is not None

            # HttpUrlオブジェクトに変換
            url_obj: HttpUrl = HttpUrl(article_url)
            source_url_obj: HttpUrl = HttpUrl(article_url)

            article = Article(
                id=str(article_data["id"]),
                title=title,
                url=url_obj,
                content=content,
                author=author,
                timestamp=timestamp,
                score=None,  # Reutersにはスコアがない
                comments_count=0,  # コメント数は取得しない
                source_site="reuters_japan",
                source_url=source_url_obj,
                metadata={
                    "section": article_data.get("taxonomy", {}).get("sections", []),
                    "reuters_id": article_data.get("id"),
                    "type": article_data.get("type", "article"),
                },
            )

            return article

        except Exception as e:
            logger.error(
                f"Error parsing Reuters article {article_data.get('id', 'unknown')}: {e}"
            )
            return None

    async def scrape_articles(self, limit: int = 30) -> List[Article]:
        """記事をスクレイピング"""
        logger.info(f"Fetching articles from Reuters Japan (limit: {limit})")

        # マーケット記事を取得
        market_url = f"{self.base_url}/markets/"
        articles_data = await self.get_articles_from_page(market_url)

        if not articles_data:
            logger.error("Failed to fetch articles from Reuters Japan")
            return []

        articles = []
        processed = 0

        for article_data in articles_data:
            if processed >= limit:
                break

            if isinstance(article_data, dict):
                article = self.parse_reuters_article(article_data)
                if article:
                    articles.append(article)
                    processed += 1

        logger.info(f"Successfully parsed {len(articles)} articles from Reuters Japan")
        return articles

    async def _validate_site_specific(self) -> Dict[str, Any]:
        """Reuters Japan固有の検証"""
        try:
            issues = []

            # マーケットページの基本チェック
            market_url = f"{self.base_url}/markets/"
            market_page = await self.fetch_page(market_url)
            if market_page is None:
                return {
                    "success": False,
                    "error": "Reuters Japan markets page not accessible",
                    "critical": True,
                }

            # ページにReutersブランドが含まれているかチェック
            if "Reuters" not in market_page and "ロイター" not in market_page:
                issues.append("Reuters Japan page content appears to have changed")

            # Fusion.globalContentの存在チェック
            if "Fusion.globalContent" not in market_page:
                return {
                    "success": False,
                    "error": "Fusion.globalContent not found in page",
                    "critical": True,
                }

            # Fusionデータの抽出テスト
            fusion_data = await self.extract_fusion_data(market_page)
            if fusion_data is None:
                return {
                    "success": False,
                    "error": "Failed to extract Fusion data",
                    "critical": True,
                }

            # 記事データの存在確認
            articles_data: List[Dict[str, Any]] = []
            if "result" in fusion_data and isinstance(fusion_data["result"], dict):
                result = fusion_data["result"]
                possible_paths = [
                    ["articles"],
                    ["content", "articles"],
                    ["items"],
                    ["content", "items"],
                ]

                for path in possible_paths:
                    current = result
                    try:
                        for key in path:
                            if isinstance(current, dict) and key in current:
                                current = current[key]
                            else:
                                break
                        else:
                            if isinstance(current, list):
                                articles_data = current
                                break
                    except (KeyError, TypeError):
                        continue

            if not articles_data and isinstance(fusion_data.get("result"), list):
                articles_data = fusion_data["result"]

            if not articles_data:
                return {
                    "success": False,
                    "error": "No article data found in Fusion structure",
                    "critical": True,
                }

            if len(articles_data) < 5:
                issues.append(f"Unusually few articles found: {len(articles_data)}")

            # サンプル記事のデータ構造チェック
            if articles_data:
                sample_article = articles_data[0]
                required_fields = ["id", "basic_headline", "canonical_url"]
                missing_fields = [
                    field for field in required_fields if not sample_article.get(field)
                ]
                if missing_fields:
                    issues.append(
                        f"Sample article missing required fields: {missing_fields}"
                    )

            # ベースURLの動作確認
            base_check = await self.fetch_page(self.base_url)
            if base_check is None:
                issues.append("Reuters Japan base URL not accessible")

            if issues:
                return {
                    "success": False,
                    "error": "; ".join(issues),
                    "critical": any(
                        "critical" in issue.lower() or "Critical" in issue
                        for issue in issues
                    ),
                }

            return {
                "success": True,
                "fusion_data_found": fusion_data is not None,
                "articles_count": len(articles_data),
                "sample_article_id": articles_data[0].get("id")
                if articles_data
                else None,
                "markets_page_accessible": market_page is not None,
            }

        except Exception as e:
            return {"success": False, "error": str(e), "critical": True}
