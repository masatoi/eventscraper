#!/usr/bin/env python3
"""
Event Scraper - メインエントリーポイント
"""
import asyncio
import sys
from pathlib import Path
from datetime import datetime
from typing import List, Optional

import click
from loguru import logger

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper.manager import ScraperManager
from src.utils.export import DataExporter
from src.utils.config import config


def setup_logging():
    """ログ設定を初期化"""
    log_config = config.get_logging_config()

    # 既存のハンドラーを削除
    logger.remove()

    # コンソール出力
    logger.add(
        sys.stderr,
        level=log_config.get("level", "INFO"),
        format=log_config.get("format", "{time} | {level} | {message}"),
    )

    # ファイル出力
    log_file = log_config.get("file", "logs/scraper.log")
    log_dir = Path(log_file).parent
    log_dir.mkdir(exist_ok=True)

    logger.add(
        log_file,
        level=log_config.get("level", "INFO"),
        format=log_config.get("format", "{time} | {level} | {message}"),
        rotation=log_config.get("rotation", "1 day"),
        retention=log_config.get("retention", "7 days"),
        encoding="utf-8",
    )


@click.command()
@click.option("--sites", "-s", multiple=True, help="スクレイピング対象サイト (例: hackernews)")
@click.option("--limit", "-l", default=None, type=int, help="取得する記事数")
@click.option("--output", "-o", help="出力ファイルパス")
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "csv", "both"]),
    help="出力フォーマット",
)
@click.option("--list-sites", is_flag=True, help="利用可能なサイト一覧を表示")
@click.option("--config-path", help="設定ファイルのパス")
@click.option("--verbose", "-v", is_flag=True, help="詳細ログを出力")
def main(
    sites: tuple,
    limit: Optional[int],
    output: Optional[str],
    output_format: Optional[str],
    list_sites: bool,
    config_path: Optional[str],
    verbose: bool,
):
    """
    Event Scraper - Webサイトから記事をスクレイピングして統一フォーマットで出力

    例:
    \b
    python main.py --sites hackernews --limit 10 --output data.json
    python main.py --sites hackernews --format both
    python main.py --list-sites
    """

    # 設定ファイルの再読み込み（カスタムパスが指定された場合）
    if config_path:
        from src.utils.config import Config

        global config
        config = Config(config_path)

    # ログ設定
    if verbose:
        # 詳細モードの場合はDEBUGレベルに設定
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
    else:
        setup_logging()

    # 利用可能サイト一覧表示
    if list_sites:
        manager = ScraperManager()
        available_sites = manager.get_available_sites()
        enabled_sites = config.get_enabled_sites()

        click.echo("利用可能なサイト:")
        for site in available_sites:
            status = "有効" if site in enabled_sites else "無効"
            click.echo(f"  - {site} ({status})")
        return

    # サイトが指定されていない場合は有効なサイトを使用
    if not sites:
        sites = tuple(config.get_enabled_sites())
        if not sites:
            click.echo("エラー: スクレイピング対象サイトが指定されていません。", err=True)
            click.echo(
                "--sites オプションでサイトを指定するか、--list-sites で利用可能なサイトを確認してください。",
                err=True,
            )
            sys.exit(1)

    # デフォルト値の設定
    defaults = config.get_defaults()
    if limit is None:
        limit = defaults.get("limit", 30)
    if output_format is None:
        output_format = defaults.get("output_format", "json")

    # 出力ディレクトリの作成
    output_dir = Path(defaults.get("output_dir", "output"))
    output_dir.mkdir(exist_ok=True)

    # 出力ファイル名の生成
    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sites_str = "_".join(sites)
        if output_format == "json":
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}.json"
        elif output_format == "csv":
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}.csv"
        else:  # both
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}"
    else:
        output_path = Path(output)

    # 非同期実行
    asyncio.run(
        run_scraping(list(sites), limit or 30, output_path, output_format or "json")
    )


async def run_scraping(sites: List[str], limit: int, output: Path, output_format: str):
    """スクレイピングを実行"""
    logger.info(f"Starting scraping for sites: {sites}")
    logger.info(f"Limit: {limit}, Output: {output}, Format: {output_format}")

    try:
        # スクレイピング実行
        manager = ScraperManager()
        results = await manager.scrape_multiple_sites(sites, limit)

        # 結果の出力
        exporter = DataExporter()

        if output_format == "json":
            success = exporter.export_to_json(results, output)
            if success:
                click.echo(f"データをJSONファイルに出力しました: {output}")

        elif output_format == "csv":
            success = exporter.export_to_csv(results, output)
            if success:
                click.echo(f"データをCSVファイルに出力しました: {output}")

        elif output_format == "both":
            json_file = output.with_suffix(".json")
            csv_file = output.with_suffix(".csv")
            summary_file = output.with_suffix(".txt")

            json_success = exporter.export_to_json(results, json_file)
            csv_success = exporter.export_to_csv(results, csv_file)
            summary_success = exporter.export_summary(results, summary_file)

            if json_success:
                click.echo(f"JSONファイルに出力: {json_file}")
            if csv_success:
                click.echo(f"CSVファイルに出力: {csv_file}")
            if summary_success:
                click.echo(f"サマリーファイルに出力: {summary_file}")

        # 結果サマリー
        total_articles = sum(r.success_count for r in results)
        total_errors = sum(r.error_count for r in results)

        click.echo(f"\nスクレイピング完了:")
        click.echo(f"  取得記事数: {total_articles}")
        click.echo(f"  エラー数: {total_errors}")

        for result in results:
            click.echo(f"  {result.site}: {result.success_count}記事")

    except Exception as e:
        logger.error(f"Scraping failed: {e}")
        click.echo(f"エラー: {e}", err=True)
        sys.exit(1)


if __name__ == "__main__":
    main()
