"""統一的なデータフォーマットのためのPydanticモデル定義."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field, HttpUrl


class Author(BaseModel):
    """投稿者情報."""

    username: str
    profile_url: HttpUrl | None = None
    karma: int | None = None


class Comment(BaseModel):
    """コメント情報."""

    id: str
    author: Author
    content: str
    timestamp: datetime
    score: int | None = None
    parent_id: str | None = None
    replies: list[Comment] = Field(default_factory=list)


class Article(BaseModel):
    """記事/投稿の統一データモデル."""

    id: str
    title: str
    url: HttpUrl | None = None
    content: str | None = None  # 記事本文（ある場合）
    author: Author
    timestamp: datetime
    score: int | None = None
    comments_count: int = 0
    comments: list[Comment] = Field(default_factory=list)
    tags: list[str] = Field(default_factory=list)
    source_site: str  # 'hackernews', 'reddit', etc.
    source_url: HttpUrl
    metadata: dict[str, Any] = Field(default_factory=dict)


class ScrapingResult(BaseModel):
    """スクレイピング結果の全体."""

    site: str
    scraped_at: datetime
    articles: list[Article]
    total_count: int
    success_count: int
    error_count: int
    errors: list[str] = Field(default_factory=list)


class ValidationResult(BaseModel):
    """スクレイパー検証結果."""

    site: str
    is_valid: bool
    validated_at: datetime
    validation_time_ms: int
    checks_performed: list[str] = Field(default_factory=list)
    issues: list[str] = Field(default_factory=list)
    warnings: list[str] = Field(default_factory=list)
    sample_data: dict[str, Any] = Field(default_factory=dict)


# Forward reference resolution
Comment.model_rebuild()
