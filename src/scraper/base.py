"""
スクレイパーの基底クラス
"""

from abc import ABC, abstractmethod
from typing import List, Optional, Any, Dict
import aiohttp
import time
from datetime import datetime
from loguru import logger

from ..models.data_models import Article, ScrapingResult, ValidationResult


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

    async def validate(self) -> ValidationResult:
        """スクレイパーの動作を検証"""
        logger.info(f"Starting validation for {self.site_name}")
        start_time = time.time()
        validation_start = datetime.now()

        checks_performed: List[str] = []
        issues: List[str] = []
        warnings: List[str] = []
        sample_data: Dict[str, Any] = {}
        is_valid = True

        try:
            # 基本的な接続チェック
            checks_performed.append("connectivity_check")
            connectivity_result = await self._validate_connectivity()
            if not connectivity_result["success"]:
                issues.append(f"Connectivity failed: {connectivity_result['error']}")
                is_valid = False
            else:
                sample_data["connectivity"] = connectivity_result

            # データ取得チェック
            checks_performed.append("data_fetch_check")
            data_result = await self._validate_data_fetch()
            if not data_result["success"]:
                issues.append(f"Data fetch failed: {data_result['error']}")
                is_valid = False
            else:
                sample_data["data_fetch"] = data_result

                # データ構造チェック
                checks_performed.append("data_structure_check")
                structure_result = await self._validate_data_structure(
                    data_result.get("sample_articles", [])
                )
                if not structure_result["success"]:
                    if structure_result.get("critical", False):
                        issues.append(
                            f"Data structure validation failed: {structure_result['error']}"
                        )
                        is_valid = False
                    else:
                        warnings.append(
                            f"Data structure warning: {structure_result['error']}"
                        )
                else:
                    sample_data["data_structure"] = structure_result

            # サイト固有の検証
            checks_performed.append("site_specific_check")
            site_result = await self._validate_site_specific()
            if not site_result["success"]:
                if site_result.get("critical", False):
                    issues.append(
                        f"Site-specific validation failed: {site_result['error']}"
                    )
                    is_valid = False
                else:
                    warnings.append(f"Site-specific warning: {site_result['error']}")
            else:
                sample_data["site_specific"] = site_result

        except Exception as e:
            logger.error(f"Validation error for {self.site_name}: {e}")
            issues.append(f"Validation exception: {str(e)}")
            is_valid = False

        validation_time_ms = int((time.time() - start_time) * 1000)

        logger.info(
            f"Validation completed for {self.site_name}: "
            f"{'VALID' if is_valid else 'INVALID'} "
            f"({validation_time_ms}ms)"
        )

        return ValidationResult(
            site=self.site_name,
            is_valid=is_valid,
            validated_at=validation_start,
            validation_time_ms=validation_time_ms,
            checks_performed=checks_performed,
            issues=issues,
            warnings=warnings,
            sample_data=sample_data,
        )

    async def _validate_connectivity(self) -> Dict[str, Any]:
        """基本的な接続性を検証"""
        try:
            response_text = await self.fetch_page(self.base_url)
            if response_text is None:
                return {"success": False, "error": "Failed to fetch base URL"}

            return {
                "success": True,
                "response_length": len(response_text),
                "has_content": len(response_text) > 0,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _validate_data_fetch(self) -> Dict[str, Any]:
        """データ取得の検証（少量のサンプルデータで）"""
        try:
            # 少量のサンプルデータを取得
            sample_articles = await self.scrape_articles(limit=3)

            if not sample_articles:
                return {"success": False, "error": "No articles retrieved"}

            return {
                "success": True,
                "articles_count": len(sample_articles),
                "sample_articles": sample_articles,
            }
        except Exception as e:
            return {"success": False, "error": str(e)}

    async def _validate_data_structure(
        self, sample_articles: List[Article]
    ) -> Dict[str, Any]:
        """データ構造の検証"""
        try:
            if not sample_articles:
                return {
                    "success": False,
                    "error": "No sample articles to validate",
                    "critical": True,
                }

            issues = []

            for i, article in enumerate(sample_articles):
                # 必須フィールドのチェック
                if not article.id:
                    issues.append(f"Article {i}: Missing ID")
                if not article.title:
                    issues.append(f"Article {i}: Missing title")
                if not article.author or not article.author.username:
                    issues.append(f"Article {i}: Missing author")
                if article.source_site != self.site_name:
                    issues.append(f"Article {i}: Incorrect source_site")

            if issues:
                return {
                    "success": False,
                    "error": "; ".join(issues),
                    "critical": len(issues)
                    > len(sample_articles)
                    // 2,  # Critical if more than half have issues
                }

            return {
                "success": True,
                "validated_articles": len(sample_articles),
                "sample_titles": [article.title for article in sample_articles[:2]],
            }
        except Exception as e:
            return {"success": False, "error": str(e), "critical": True}

    @abstractmethod
    async def _validate_site_specific(self) -> Dict[str, Any]:
        """サイト固有の検証（サブクラスで実装）"""
        pass
