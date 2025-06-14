#!/usr/bin/env python3
"""
Event Scraper の使用例
"""
import asyncio
import sys
from pathlib import Path

# プロジェクトのsrcディレクトリをパスに追加
sys.path.insert(0, str(Path(__file__).parent / "src"))

from src.scraper.manager import ScraperManager
from src.utils.export import DataExporter


async def main():
    """サンプル実行"""
    print("Event Scraper - 使用例")
    print("=" * 40)
    
    # スクレイパーマネージャーを作成
    manager = ScraperManager()
    
    # 利用可能なサイトを表示
    available_sites = manager.get_available_sites()
    print(f"利用可能なサイト: {available_sites}")
    
    # Hacker Newsから5記事を取得
    print("\nHacker Newsから5記事を取得中...")
    results = await manager.scrape_multiple_sites(['hackernews'], limit=5)
    
    # 結果を表示
    for result in results:
        print(f"\nサイト: {result.site}")
        print(f"取得記事数: {result.success_count}")
        print(f"エラー数: {result.error_count}")
        
        print("\n記事一覧:")
        for i, article in enumerate(result.articles[:3], 1):  # 最初の3記事のみ表示
            print(f"{i}. {article.title}")
            print(f"   作者: {article.author.username}")
            print(f"   スコア: {article.score}")
            print(f"   URL: {article.url}")
            print()
    
    # JSONファイルに出力
    output_dir = Path("output")
    output_dir.mkdir(exist_ok=True)
    
    exporter = DataExporter()
    json_file = output_dir / "example_output.json"
    
    if exporter.export_to_json(results, json_file):
        print(f"結果をJSONファイルに出力しました: {json_file}")
    
    # サマリーファイルに出力
    summary_file = output_dir / "example_summary.txt"
    if exporter.export_summary(results, summary_file):
        print(f"サマリーをファイルに出力しました: {summary_file}")


if __name__ == '__main__':
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n実行が中断されました。")
    except Exception as e:
        print(f"エラーが発生しました: {e}")
