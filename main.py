#!/usr/bin/env python3
"""Event Scraper - TyperベースのCLIエントリーポイント."""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import Annotated

import typer
from loguru import logger

from src.scraper.manager import ScraperManager
from src.utils.config import Config, config
from src.utils.export import DataExporter

app = typer.Typer(add_completion=False, help="WebサイトをスクレイピングするCLIツール")


class OutputFormat(str, Enum):
    """出力フォーマットの選択肢."""

    JSON = "json"
    CSV = "csv"
    BOTH = "both"


SitesOption = Annotated[
    list[str] | None,
    typer.Option(
        None,
        "--sites",
        "-s",
        help="スクレイピング対象サイト (例: hackernews)",
    ),
]
LimitOption = Annotated[
    int | None,
    typer.Option(None, "--limit", "-l", help="取得する記事数"),
]
OutputPathOption = Annotated[
    Path | None,
    typer.Option(None, "--output", "-o", help="出力ファイルパス"),
]
OutputFormatOption = Annotated[
    OutputFormat | None,
    typer.Option(
        None,
        "--format",
        "-f",
        help="出力フォーマット",
        case_sensitive=False,
    ),
]
ListSitesFlag = Annotated[
    bool,
    typer.Option(
        False,
        "--list-sites",
        help="利用可能なサイト一覧を表示",
        is_flag=True,
    ),
]
ValidateFlag = Annotated[
    bool,
    typer.Option(
        False,
        "--validate",
        help="スクレイパーの動作を検証",
        is_flag=True,
    ),
]
ConfigPathOption = Annotated[
    Path | None,
    typer.Option(None, "--config-path", help="設定ファイルのパス"),
]
VerboseFlag = Annotated[
    bool,
    typer.Option(
        False,
        "--verbose",
        "-v",
        help="詳細ログを出力",
        is_flag=True,
    ),
]


def setup_logging(verbose: bool) -> None:
    """ログ設定を初期化."""
    if verbose:
        logger.remove()
        logger.add(sys.stderr, level="DEBUG")
        return

    log_config = config.get_logging_config()
    logger.remove()
    logger.add(
        sys.stderr,
        level=log_config.get("level", "INFO"),
        format=log_config.get("format", "{time} | {level} | {message}"),
    )

    log_file = Path(log_config.get("file", "logs/scraper.log"))
    log_file.parent.mkdir(parents=True, exist_ok=True)

    logger.add(
        log_file,
        level=log_config.get("level", "INFO"),
        format=log_config.get("format", "{time} | {level} | {message}"),
        rotation=log_config.get("rotation", "1 day"),
        retention=log_config.get("retention", "7 days"),
        encoding="utf-8",
    )


@app.command()
def main(
    sites: SitesOption = None,
    limit: LimitOption = None,
    output: OutputPathOption = None,
    output_format: OutputFormatOption = None,
    list_sites: ListSitesFlag = False,
    validate: ValidateFlag = False,
    config_path: ConfigPathOption = None,
    verbose: VerboseFlag = False,
) -> None:
    """Event Scraperのメインコマンド."""
    selected_sites = list(sites or [])

    if config_path is not None:
        global config
        config = Config(config_path)

    setup_logging(verbose)

    if list_sites:
        manager = ScraperManager()
        available_sites = manager.get_available_sites()
        enabled_sites = set(config.get_enabled_sites())
        typer.echo("利用可能なサイト:")
        for site in available_sites:
            status = "有効" if site in enabled_sites else "無効"
            typer.echo(f"  - {site} ({status})")
        raise typer.Exit()

    if validate:
        if not selected_sites:
            selected_sites = config.get_enabled_sites()
        if not selected_sites:
            typer.echo("エラー: 検証対象サイトが指定されていません。", err=True)
            typer.echo(
                (
                    "--sites オプションでサイトを指定するか、--list-sites で"
                    "利用可能なサイトを確認してください。"
                ),
                err=True,
            )
            raise typer.Exit(code=1)

        try:
            asyncio.run(run_validation(selected_sites))
        except RuntimeError as exc:
            typer.echo(str(exc), err=True)
            raise typer.Exit(code=1) from exc
        raise typer.Exit()

    if not selected_sites:
        selected_sites = config.get_enabled_sites()
    if not selected_sites:
        typer.echo("エラー: スクレイピング対象サイトが指定されていません。", err=True)
        typer.echo(
            (
                "--sites オプションでサイトを指定するか、--list-sites で"
                "利用可能なサイトを確認してください。"
            ),
            err=True,
        )
        raise typer.Exit(code=1)

    defaults = config.get_defaults()
    resolved_limit = limit if limit is not None else int(defaults.get("limit", 30))

    resolved_format = output_format
    if resolved_format is None:
        try:
            resolved_format = OutputFormat(str(defaults.get("output_format", "json")))
        except ValueError:
            resolved_format = OutputFormat.JSON

    output_dir = Path(defaults.get("output_dir", "output"))
    output_dir.mkdir(parents=True, exist_ok=True)

    if output is None:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        sites_str = "_".join(selected_sites)
        if resolved_format is OutputFormat.JSON:
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}.json"
        elif resolved_format is OutputFormat.CSV:
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}.csv"
        else:
            output_path = output_dir / f"scraped_{sites_str}_{timestamp}"
    else:
        output_path = output

    try:
        asyncio.run(
            run_scraping(selected_sites, resolved_limit, output_path, resolved_format)
        )
    except RuntimeError as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(code=1) from exc


async def run_scraping(
    sites: list[str], limit: int, output: Path, output_format: OutputFormat
) -> None:
    """スクレイピングを実行."""
    logger.info("Starting scraping for sites: {}", sites)
    logger.info(
        "Scraping parameters - limit: {}, output: {}, format: {}",
        limit,
        output,
        output_format.value,
    )

    manager = ScraperManager()
    results = await manager.scrape_multiple_sites(sites, limit)

    exporter = DataExporter()
    if output_format is OutputFormat.JSON:
        if exporter.export_to_json(results, output):
            typer.echo(f"データをJSONファイルに出力しました: {output}")
    elif output_format is OutputFormat.CSV:
        if exporter.export_to_csv(results, output):
            typer.echo(f"データをCSVファイルに出力しました: {output}")
    else:
        json_file = output.with_suffix(".json")
        csv_file = output.with_suffix(".csv")
        summary_file = output.with_suffix(".txt")
        if exporter.export_to_json(results, json_file):
            typer.echo(f"JSONファイルに出力: {json_file}")
        if exporter.export_to_csv(results, csv_file):
            typer.echo(f"CSVファイルに出力: {csv_file}")
        if exporter.export_summary(results, summary_file):
            typer.echo(f"サマリーファイルに出力: {summary_file}")

    total_articles = sum(r.success_count for r in results)
    total_errors = sum(r.error_count for r in results)

    typer.echo("\nスクレイピング完了:")
    typer.echo(f"  取得記事数: {total_articles}")
    typer.echo(f"  エラー数: {total_errors}")
    for result in results:
        typer.echo(f"  {result.site}: {result.success_count}記事")


async def run_validation(sites: list[str]) -> None:
    """検証を実行."""
    logger.info("Starting validation for sites: {}", sites)

    manager = ScraperManager()
    results = await manager.validate_multiple_sites(sites)

    typer.echo("\n検証結果:")
    typer.echo("=" * 50)

    all_valid = True
    for result in results:
        status_text = "✓ VALID" if result.is_valid else "✗ INVALID"
        status_color = "green" if result.is_valid else "red"

        typer.echo(f"\n{result.site}: ", nl=False)
        typer.secho(status_text, fg=status_color, bold=True)
        typer.echo(f"  検証時間: {result.validation_time_ms}ms")
        typer.echo(f"  実行チェック: {', '.join(result.checks_performed)}")

        if result.issues:
            typer.echo("  問題:")
            for issue in result.issues:
                typer.echo(f"    - {issue}")

        if result.warnings:
            typer.echo("  警告:")
            for warning in result.warnings:
                typer.echo(f"    - {warning}")

        if result.sample_data:
            typer.echo(f"  サンプルデータ: {len(result.sample_data)} 項目")

        if not result.is_valid:
            all_valid = False

    typer.echo("\n" + "=" * 50)
    if all_valid:
        typer.secho("全てのスクレイパーが正常に動作しています", fg="green", bold=True)
    else:
        typer.secho("一部のスクレイパーに問題があります", fg="red", bold=True)
        raise RuntimeError("一部のスクレイパーが検証に失敗しました")


if __name__ == "__main__":
    app()
