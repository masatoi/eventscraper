"""データエクスポート用ユーティリティ."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

import pandas as pd
from loguru import logger

from ..models.data_models import ScrapingResult


class DataExporter:
    """データエクスポート用クラス"""

    @staticmethod
    def export_to_json(results: list[ScrapingResult], output_path: str | Path) -> bool:
        """JSONファイルにエクスポート"""
        try:
            output_path = Path(output_path)

            # Pydanticモデルを辞書に変換
            export_data: dict[str, Any] = {
                "exported_at": datetime.now().isoformat(),
                "sites": [],
            }

            for result in results:
                site_data = {
                    "site": result.site,
                    "scraped_at": result.scraped_at.isoformat(),
                    "total_count": result.total_count,
                    "success_count": result.success_count,
                    "error_count": result.error_count,
                    "errors": result.errors,
                    "articles": [],
                }

                articles_data = []
                for article in result.articles:
                    article_data = {
                        "id": article.id,
                        "title": article.title,
                        "url": str(article.url) if article.url else None,
                        "content": article.content,
                        "author": {
                            "username": article.author.username,
                            "profile_url": (
                                str(article.author.profile_url)
                                if article.author.profile_url
                                else None
                            ),
                            "karma": article.author.karma,
                        },
                        "timestamp": article.timestamp.isoformat(),
                        "score": article.score,
                        "comments_count": article.comments_count,
                        "tags": article.tags,
                        "source_site": article.source_site,
                        "source_url": str(article.source_url),
                        "metadata": article.metadata,
                    }
                    articles_data.append(article_data)

                site_data["articles"] = articles_data

                export_data["sites"].append(site_data)

            # JSONファイルに書き込み
            with open(output_path, "w", encoding="utf-8") as f:
                json.dump(export_data, f, ensure_ascii=False, indent=2)

            logger.info(f"Data exported to JSON: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to JSON: {e}")
            return False

    @staticmethod
    def export_to_csv(results: list[ScrapingResult], output_path: str | Path) -> bool:
        """CSVファイルにエクスポート"""
        try:
            output_path = Path(output_path)

            # 全記事を平坦化
            all_articles = []
            for result in results:
                for article in result.articles:
                    article_row = {
                        "site": result.site,
                        "scraped_at": result.scraped_at.isoformat(),
                        "article_id": article.id,
                        "title": article.title,
                        "url": str(article.url) if article.url else "",
                        "content": article.content or "",
                        "author_username": article.author.username,
                        "author_profile_url": (
                            str(article.author.profile_url)
                            if article.author.profile_url
                            else ""
                        ),
                        "author_karma": article.author.karma or 0,
                        "timestamp": article.timestamp.isoformat(),
                        "score": article.score or 0,
                        "comments_count": article.comments_count,
                        "tags": ",".join(article.tags),
                        "source_site": article.source_site,
                        "source_url": str(article.source_url),
                        "metadata": json.dumps(article.metadata),
                    }
                    all_articles.append(article_row)

            # DataFrameに変換してCSV出力
            df = pd.DataFrame(all_articles)
            df.to_csv(output_path, index=False, encoding="utf-8")

            logger.info(f"Data exported to CSV: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting to CSV: {e}")
            return False

    @staticmethod
    def export_summary(results: list[ScrapingResult], output_path: str | Path) -> bool:
        """サマリー情報をテキストファイルにエクスポート"""
        try:
            output_path = Path(output_path)

            with open(output_path, "w", encoding="utf-8") as f:
                f.write("Event Scraper - Scraping Summary\n")
                f.write("=" * 40 + "\n\n")
                f.write(f"Export Time: {datetime.now().isoformat()}\n\n")

                total_articles = 0
                total_errors = 0

                for result in results:
                    f.write(f"Site: {result.site}\n")
                    f.write(f"Scraped At: {result.scraped_at.isoformat()}\n")
                    f.write(f"Success Count: {result.success_count}\n")
                    f.write(f"Error Count: {result.error_count}\n")

                    if result.errors:
                        f.write("Errors:\n")
                        for error in result.errors:
                            f.write(f"  - {error}\n")

                    f.write("\n" + "-" * 30 + "\n\n")

                    total_articles += result.success_count
                    total_errors += result.error_count

                f.write(f"Total Articles: {total_articles}\n")
                f.write(f"Total Errors: {total_errors}\n")

            logger.info(f"Summary exported to: {output_path}")
            return True

        except Exception as e:
            logger.error(f"Error exporting summary: {e}")
            return False
