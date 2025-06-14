"""
Hacker News スクレイパーのテスト
"""
import pytest
import asyncio
from datetime import datetime
from unittest.mock import AsyncMock, patch

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.scraper.hackernews import HackerNewsScraper
from src.models.data_models import Article, Author


class TestHackerNewsScraper:
    """Hacker News スクレイパーのテストクラス"""
    
    @pytest.fixture
    def scraper(self):
        """スクレイパーインスタンスを作成"""
        return HackerNewsScraper()
    
    @pytest.fixture
    def sample_story_data(self):
        """サンプルストーリーデータ"""
        return {
            'id': 12345,
            'title': 'Test Article Title',
            'by': 'testuser',
            'time': 1640995200,  # 2022-01-01 00:00:00 UTC
            'score': 100,
            'descendants': 50,
            'url': 'https://example.com/article',
            'type': 'story'
        }
    
    def test_parse_story_to_article(self, scraper, sample_story_data):
        """ストーリーデータのパース機能をテスト"""
        article = scraper.parse_story_to_article(sample_story_data)
        
        assert article is not None
        assert article.id == '12345'
        assert article.title == 'Test Article Title'
        assert article.author.username == 'testuser'
        assert article.score == 100
        assert article.comments_count == 50
        assert article.source_site == 'hackernews'
        assert str(article.url) == 'https://example.com/article'
    
    def test_parse_story_missing_fields(self, scraper):
        """必須フィールドが不足している場合のテスト"""
        incomplete_data = {
            'id': 12345,
            'title': 'Test Title'
            # 'by' and 'time' are missing
        }
        
        article = scraper.parse_story_to_article(incomplete_data)
        assert article is None
    
    def test_parse_story_no_external_url(self, scraper):
        """外部URLがない場合のテスト（Ask HN等）"""
        story_data = {
            'id': 12345,
            'title': 'Ask HN: Test Question?',
            'by': 'testuser',
            'time': 1640995200,
            'score': 50,
            'descendants': 25,
            'text': 'This is the question content',
            'type': 'story'
        }
        
        article = scraper.parse_story_to_article(story_data)
        
        assert article is not None
        assert article.content == 'This is the question content'
        assert str(article.url) == 'https://news.ycombinator.com/item?id=12345'
    
    @pytest.mark.asyncio
    async def test_scraper_context_manager(self, scraper):
        """非同期コンテキストマネージャーのテスト"""
        async with scraper as s:
            assert s.session is not None
        
        # コンテキスト終了後はセッションがクローズされている
        assert scraper.session.closed
    
    @pytest.mark.asyncio
    async def test_get_top_stories_success(self, scraper):
        """トップストーリー取得の成功ケース"""
        mock_response = '[1, 2, 3, 4, 5]'
        
        with patch.object(scraper, 'fetch_page', return_value=mock_response):
            async with scraper:
                story_ids = await scraper.get_top_stories(3)
                assert story_ids == [1, 2, 3]
    
    @pytest.mark.asyncio
    async def test_get_top_stories_failure(self, scraper):
        """トップストーリー取得の失敗ケース"""
        with patch.object(scraper, 'fetch_page', return_value=None):
            async with scraper:
                story_ids = await scraper.get_top_stories(3)
                assert story_ids == []
    
    @pytest.mark.asyncio
    async def test_get_story_details_success(self, scraper, sample_story_data):
        """ストーリー詳細取得の成功ケース"""
        import json
        mock_response = json.dumps(sample_story_data)
        
        with patch.object(scraper, 'fetch_page', return_value=mock_response):
            async with scraper:
                details = await scraper.get_story_details(12345)
                assert details == sample_story_data
    
    @pytest.mark.asyncio
    async def test_get_story_details_failure(self, scraper):
        """ストーリー詳細取得の失敗ケース"""
        with patch.object(scraper, 'fetch_page', return_value=None):
            async with scraper:
                details = await scraper.get_story_details(12345)
                assert details is None


if __name__ == '__main__':
    pytest.main([__file__])
