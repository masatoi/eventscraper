"""
スクレイパー検証機能のテスト
"""

import pytest
from datetime import datetime
from unittest.mock import patch
from src.scraper.hackernews import HackerNewsScraper
from src.scraper.reuters_japan import ReutersJapanScraper
from src.scraper.manager import ScraperManager
from src.models.data_models import ValidationResult


class TestScraperValidation:
    """スクレイパー検証のテストクラス"""

    @pytest.mark.asyncio
    async def test_hackernews_validation_success(self):
        """HackerNewsスクレイパーの正常検証"""
        scraper = HackerNewsScraper()

        async with scraper:
            result = await scraper.validate()

        assert isinstance(result, ValidationResult)
        assert result.site == "hackernews"
        assert isinstance(result.is_valid, bool)
        assert result.validation_time_ms > 0
        assert "connectivity_check" in result.checks_performed
        assert "data_fetch_check" in result.checks_performed
        assert "site_specific_check" in result.checks_performed

    @pytest.mark.asyncio
    async def test_reuters_validation_success(self):
        """ReutersJapanスクレイパーの正常検証"""
        scraper = ReutersJapanScraper()

        async with scraper:
            result = await scraper.validate()

        assert isinstance(result, ValidationResult)
        assert result.site == "reuters_japan"
        assert isinstance(result.is_valid, bool)
        assert result.validation_time_ms > 0
        assert "connectivity_check" in result.checks_performed
        assert "data_fetch_check" in result.checks_performed
        assert "site_specific_check" in result.checks_performed

    @pytest.mark.asyncio
    async def test_validation_with_connection_failure(self):
        """接続失敗時の検証"""
        scraper = HackerNewsScraper()

        with patch.object(scraper, "fetch_page", return_value=None):
            async with scraper:
                result = await scraper.validate()

        assert not result.is_valid
        assert len(result.issues) > 0
        assert any("Connectivity failed" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_validation_with_data_fetch_failure(self):
        """データ取得失敗時の検証"""
        scraper = HackerNewsScraper()

        # 接続は成功、データ取得は失敗
        with patch.object(scraper, "fetch_page") as mock_fetch:
            mock_fetch.side_effect = [
                "<html>test</html>",  # connectivity check passes
                None,  # data fetch fails
                None,  # site specific checks fail
            ]

            async with scraper:
                result = await scraper.validate()

        assert not result.is_valid
        assert len(result.issues) > 0

    @pytest.mark.asyncio
    async def test_validation_with_invalid_data_structure(self):
        """データ構造が不正な場合の検証"""
        scraper = HackerNewsScraper()

        with patch.object(scraper, "scrape_articles", return_value=[]):
            async with scraper:
                result = await scraper.validate()

        assert not result.is_valid
        assert any("No articles retrieved" in issue for issue in result.issues)

    @pytest.mark.asyncio
    async def test_scraper_manager_validation(self):
        """ScraperManagerの検証機能"""
        manager = ScraperManager()

        # 存在しないサイトの検証
        result = await manager.validate_site("nonexistent")
        assert not result.is_valid
        assert result.site == "nonexistent"
        assert "Unknown site" in result.issues[0]

    @pytest.mark.asyncio
    async def test_multiple_sites_validation(self):
        """複数サイトの並行検証"""
        manager = ScraperManager()

        sites = ["hackernews", "reuters_japan"]
        results = await manager.validate_multiple_sites(sites)

        assert len(results) == 2
        assert all(isinstance(r, ValidationResult) for r in results)
        assert {r.site for r in results} == set(sites)

    def test_validation_result_structure(self):
        """ValidationResultの構造テスト"""
        result = ValidationResult(
            site="test",
            is_valid=True,
            validated_at=datetime.now(),
            validation_time_ms=100,
            checks_performed=["test_check"],
            issues=[],
            warnings=["test warning"],
            sample_data={"test": "data"},
        )

        assert result.site == "test"
        assert result.is_valid is True
        assert result.validation_time_ms == 100
        assert "test_check" in result.checks_performed
        assert "test warning" in result.warnings
        assert result.sample_data["test"] == "data"

    @pytest.mark.asyncio
    async def test_connectivity_validation_method(self):
        """接続性検証メソッドのテスト"""
        scraper = HackerNewsScraper()

        async with scraper:
            # 正常なケース
            result = await scraper._validate_connectivity()
            assert result["success"] is True
            assert "response_length" in result

            # 失敗ケース
            with patch.object(scraper, "fetch_page", return_value=None):
                result = await scraper._validate_connectivity()
                assert result["success"] is False
                assert "Failed to fetch base URL" in result["error"]

    @pytest.mark.asyncio
    async def test_data_structure_validation_method(self):
        """データ構造検証メソッドのテスト"""
        scraper = HackerNewsScraper()

        async with scraper:
            # 正常な記事データでテスト
            sample_articles = await scraper.scrape_articles(limit=1)
            if sample_articles:
                result = await scraper._validate_data_structure(sample_articles)
                assert result["success"] is True

            # 空のリストでテスト
            result = await scraper._validate_data_structure([])
            assert result["success"] is False
            assert result["critical"] is True
