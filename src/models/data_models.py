"""
統一的なデータフォーマットのためのPydanticモデル定義
"""

from datetime import datetime
from typing import List, Optional, Dict, Any
from pydantic import BaseModel, Field, HttpUrl


class Author(BaseModel):
    """投稿者情報"""

    username: str
    profile_url: Optional[HttpUrl] = None
    karma: Optional[int] = None


class Comment(BaseModel):
    """コメント情報"""

    id: str
    author: Author
    content: str
    timestamp: datetime
    score: Optional[int] = None
    parent_id: Optional[str] = None
    replies: List["Comment"] = Field(default_factory=list)


class Article(BaseModel):
    """記事/投稿の統一データモデル"""

    id: str
    title: str
    url: Optional[HttpUrl] = None
    content: Optional[str] = None  # 記事本文（ある場合）
    author: Author
    timestamp: datetime
    score: Optional[int] = None
    comments_count: int = 0
    comments: List[Comment] = Field(default_factory=list)
    tags: List[str] = Field(default_factory=list)
    source_site: str  # 'hackernews', 'reddit', etc.
    source_url: HttpUrl
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ScrapingResult(BaseModel):
    """スクレイピング結果の全体"""

    site: str
    scraped_at: datetime
    articles: List[Article]
    total_count: int
    success_count: int
    error_count: int
    errors: List[str] = Field(default_factory=list)


# Forward reference resolution
Comment.model_rebuild()
