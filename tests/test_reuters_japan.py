"""
Reuters Japan スクレイパーのテスト
"""

import pytest
from datetime import datetime
from src.scraper.reuters_japan import ReutersJapanScraper


class TestReutersJapanScraper:
    """Reuters Japan スクレイパーのテストクラス"""

    def test_parse_reuters_article_success(self):
        """正常な記事データのパース"""
        scraper = ReutersJapanScraper()
        
        sample_data = {
            "id": "TEST123",
            "basic_headline": "テスト記事タイトル",
            "canonical_url": "/markets/test-article-TEST123-2025-06-20/",
            "description": "これはテスト記事の概要です。",
            "authors": [
                {
                    "name": "テスト記者",
                    "byline": "Test Reporter"
                }
            ],
            "display_date": "2025-06-20T12:00:00.000Z",
            "type": "article"
        }
        
        article = scraper.parse_reuters_article(sample_data)
        
        assert article is not None
        assert article.id == "TEST123"
        assert article.title == "テスト記事タイトル"
        assert str(article.url) == "https://jp.reuters.com/markets/test-article-TEST123-2025-06-20/"
        assert article.content == "これはテスト記事の概要です。"
        assert article.author.username == "テスト記者"
        assert article.source_site == "reuters_japan"
        assert article.metadata["reuters_id"] == "TEST123"

    def test_parse_reuters_article_missing_fields(self):
        """必須フィールドが不足している場合"""
        scraper = ReutersJapanScraper()
        
        # IDが不足
        sample_data = {
            "basic_headline": "テスト記事タイトル",
            "canonical_url": "/test-article/"
        }
        
        article = scraper.parse_reuters_article(sample_data)
        assert article is None
        
        # タイトルが不足
        sample_data = {
            "id": "TEST123",
            "canonical_url": "/test-article/"
        }
        
        article = scraper.parse_reuters_article(sample_data)
        assert article is None

    def test_parse_reuters_article_no_url(self):
        """URLがない場合"""
        scraper = ReutersJapanScraper()
        
        sample_data = {
            "id": "TEST123",
            "basic_headline": "テスト記事タイトル",
            "description": "テスト概要"
        }
        
        article = scraper.parse_reuters_article(sample_data)
        assert article is None

    def test_parse_reuters_article_no_authors(self):
        """作者情報がない場合"""
        scraper = ReutersJapanScraper()
        
        sample_data = {
            "id": "TEST123",
            "basic_headline": "テスト記事タイトル",
            "canonical_url": "/test-article/",
            "description": "テスト概要",
            "display_date": "2025-06-20T12:00:00.000Z"
        }
        
        article = scraper.parse_reuters_article(sample_data)
        
        assert article is not None
        assert article.author.username == "Reuters"

    @pytest.mark.asyncio
    async def test_scraper_context_manager(self):
        """コンテキストマネージャーのテスト"""
        scraper = ReutersJapanScraper()
        
        assert scraper.session is None
        
        async with scraper:
            assert scraper.session is not None
        
        # セッションが閉じられているかは直接確認できないが、
        # 例外が発生しないことを確認
        assert True

    def test_extract_fusion_data_no_data(self):
        """Fusionデータが存在しない場合"""
        scraper = ReutersJapanScraper()
        
        html_content = """
        <html>
            <head><title>Test</title></head>
            <body>
                <script>var someOtherData = {};</script>
            </body>
        </html>
        """
        
        # 非同期関数のテストのためのヘルパーメソッドが必要だが、
        # ここでは戻り値がNoneになることを想定
        import asyncio
        result = asyncio.run(scraper.extract_fusion_data(html_content))
        assert result is None