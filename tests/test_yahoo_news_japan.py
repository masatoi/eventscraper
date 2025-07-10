"""Yahoo News Japan スクレイパーのテスト"""

import pytest
from src.scraper.yahoo_news_japan import YahooNewsJapanScraper
import xml.etree.ElementTree as ET


class TestYahooNewsJapanScraper:
    """Yahoo News Japan スクレイパーのテストクラス"""

    def test_parse_item_to_article_success(self):
        scraper = YahooNewsJapanScraper()
        sample_item = """
        <item>
            <title>テストタイトル</title>
            <link>https://news.yahoo.co.jp/pickup/1234567?source=rss</link>
            <pubDate>Thu, 01 Jan 2024 00:00:00 GMT</pubDate>
        </item>
        """
        element = ET.fromstring(sample_item)
        article = scraper.parse_item_to_article(element)
        assert article is not None
        assert article.title == "テストタイトル"
        assert article.id == "1234567"
        assert article.source_site == "yahoo_news_japan"

    def test_parse_item_to_article_missing_fields(self):
        scraper = YahooNewsJapanScraper()
        incomplete = """
        <item>
            <title>テスト</title>
        </item>
        """
        element = ET.fromstring(incomplete)
        article = scraper.parse_item_to_article(element)
        assert article is None

    @pytest.mark.asyncio
    async def test_scraper_context_manager(self):
        scraper = YahooNewsJapanScraper()
        async with scraper:
            assert scraper.session is not None
        assert scraper.session.closed
