"""
スクレイパーマネージャー - 複数サイトの並行スクレイピングを管理
"""

import asyncio
from typing import List, Dict, Type
from datetime import datetime
from loguru import logger

from .base import BaseScraper
from .hackernews import HackerNewsScraper
from .reuters_japan import ReutersJapanScraper
from ..models.data_models import ScrapingResult, ValidationResult


class ScraperManager:
    """スクレイパーマネージャー"""

    def __init__(self) -> None:
        self.scrapers: Dict[str, Type[BaseScraper]] = {
            "hackernews": HackerNewsScraper,
            "reuters_japan": ReutersJapanScraper,
            # 将来的に他のサイトを追加
            # 'reddit': RedditScraper,
            # 'techcrunch': TechCrunchScraper,
        }

    def get_available_sites(self) -> List[str]:
        """利用可能なサイト一覧を取得"""
        return list(self.scrapers.keys())

    async def scrape_site(self, site_name: str, limit: int = 30) -> ScrapingResult:
        """単一サイトをスクレイピング"""
        if site_name not in self.scrapers:
            logger.error(f"Unknown site: {site_name}")
            return ScrapingResult(
                site=site_name,
                scraped_at=datetime.now(),
                articles=[],
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[f"Unknown site: {site_name}"],
            )

        scraper_class = self.scrapers[site_name]

        try:
            scraper_instance: BaseScraper = scraper_class()  # type: ignore
            async with scraper_instance as scraper:
                result = await scraper.scrape(limit)
                return result
        except Exception as e:
            logger.error(f"Error scraping {site_name}: {e}")
            return ScrapingResult(
                site=site_name,
                scraped_at=datetime.now(),
                articles=[],
                total_count=0,
                success_count=0,
                error_count=1,
                errors=[str(e)],
            )

    async def scrape_multiple_sites(
        self, sites: List[str], limit: int = 30
    ) -> List[ScrapingResult]:
        """複数サイトを並行スクレイピング"""
        logger.info(f"Starting parallel scraping for sites: {sites}")

        # 並行実行用のタスクを作成
        tasks = [self.scrape_site(site, limit) for site in sites]

        # 全てのタスクを並行実行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外が発生したタスクの処理
        final_results: List[ScrapingResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in scraping {sites[i]}: {result}")
                final_results.append(
                    ScrapingResult(
                        site=sites[i],
                        scraped_at=datetime.now(),
                        articles=[],
                        total_count=0,
                        success_count=0,
                        error_count=1,
                        errors=[str(result)],
                    )
                )
            else:
                # result is ScrapingResult at this point
                final_results.append(result)  # type: ignore

        # 結果のサマリーをログ出力
        total_articles = sum(r.success_count for r in final_results)
        total_errors = sum(r.error_count for r in final_results)
        logger.info(
            f"Scraping completed. Total articles: {total_articles}, Total errors: {total_errors}"
        )

        return final_results

    async def validate_site(self, site_name: str) -> ValidationResult:
        """単一サイトの検証"""
        if site_name not in self.scrapers:
            logger.error(f"Unknown site: {site_name}")
            return ValidationResult(
                site=site_name,
                is_valid=False,
                validated_at=datetime.now(),
                validation_time_ms=0,
                issues=[f"Unknown site: {site_name}"],
            )

        scraper_class = self.scrapers[site_name]

        try:
            scraper_instance: BaseScraper = scraper_class()  # type: ignore
            async with scraper_instance as scraper:
                result = await scraper.validate()
                return result
        except Exception as e:
            logger.error(f"Error validating {site_name}: {e}")
            return ValidationResult(
                site=site_name,
                is_valid=False,
                validated_at=datetime.now(),
                validation_time_ms=0,
                issues=[str(e)],
            )

    async def validate_multiple_sites(self, sites: List[str]) -> List[ValidationResult]:
        """複数サイトを並行検証"""
        logger.info(f"Starting parallel validation for sites: {sites}")

        # 並行実行用のタスクを作成
        tasks = [self.validate_site(site) for site in sites]

        # 全てのタスクを並行実行
        results = await asyncio.gather(*tasks, return_exceptions=True)

        # 例外が発生したタスクの処理
        final_results: List[ValidationResult] = []
        for i, result in enumerate(results):
            if isinstance(result, Exception):
                logger.error(f"Exception in validating {sites[i]}: {result}")
                final_results.append(
                    ValidationResult(
                        site=sites[i],
                        is_valid=False,
                        validated_at=datetime.now(),
                        validation_time_ms=0,
                        issues=[str(result)],
                    )
                )
            else:
                # result is ValidationResult at this point
                final_results.append(result)  # type: ignore

        # 結果のサマリーをログ出力
        valid_count = sum(1 for r in final_results if r.is_valid)
        invalid_count = len(final_results) - valid_count
        logger.info(
            f"Validation completed. Valid: {valid_count}, Invalid: {invalid_count}"
        )

        return final_results
