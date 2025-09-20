# Event Scraper
[![CI](https://github.com/masatoi/eventscraper/actions/workflows/ci.yml/badge.svg)](https://github.com/masatoi/eventscraper/actions/workflows/ci.yml) [![Coverage](coverage.svg)](coverage.svg)

Hacker NewsやReuters Japanなどのニュースサイトをスクレイピングし、機械学習モデルやデータ分析パイプラインで利用しやすいJSON/CSV形式に変換する非同期スクレイピングツールです。TyperベースのCLIから複数サイトを並列に処理し、データ検証やエクスポートまで一括で実行できます。

## 主な特徴

- **非同期スクレイピング**: `aiohttp`を使った並列HTTPリクエストで高速にデータ取得。
- **統一的なデータモデル**: Pydanticモデルで定義されたスキーマに沿ってデータを整形。
- **設定ファイルによる制御**: `config/settings.yaml`からサイト別設定や出力パラメータを管理可能。
- **CLIバリデーション**: `--validate`オプションでスクレイパーの健全性とサイト接続状況を診断。
- **柔軟なエクスポート**: JSON/CSVのどちらか、または両方のフォーマットを選択し、出力先を指定可能。

## 対応環境

- Python 3.12
- [Poetry](https://python-poetry.org/) 1.8 以降（依存関係とツールチェーンの管理に使用）

> 互換性維持のための最低バージョンは `pyproject.toml` を参照してください。

## セットアップ

1. リポジトリをクローンします。
2. Poetryで依存関係をインストールします（開発ツールも含めてセットアップする場合）。

```bash
poetry install --with dev
```

3. 仮想環境に入る場合は `poetry shell` を実行するか、コマンドの前に `poetry run` を付けてください。

> ランタイムに必要な最小依存関係のみをpipでインストールしたい場合は `pip install -r requirements.txt` でも利用できますが、CIと同じ開発体験を得るにはPoetryの利用を推奨します。

## 使い方

まずはヘルプを確認します。

```bash
poetry run python main.py --help
```

### よく使うコマンド

| コマンド例 | 説明 |
| --- | --- |
| `poetry run python main.py --sites hackernews` | Hacker Newsから最新記事を取得（デフォルト30件）。 |
| `poetry run python main.py --sites hackernews --limit 10` | 取得件数を10件に限定。 |
| `poetry run python main.py --sites hackernews --output data.json` | 出力ファイルを指定。 |
| `poetry run python main.py --sites hackernews --format csv` | CSV形式でエクスポート。 |
| `poetry run python main.py --sites hackernews --format both` | JSONとCSVの両方で出力。 |
| `poetry run python main.py --list-sites` | 利用可能なスクレイパー一覧と有効/無効状態を表示。 |
| `poetry run python main.py --validate --sites hackernews reuters_japan` | 対象サイトの動作検証を実行。 |
| `poetry run python main.py --config-path custom.yaml` | 独自設定ファイルを使用。 |
| `poetry run python main.py --verbose` | ログレベルをDEBUGに上げて詳細ログを出力。 |

### サンプルスクリプト

簡単な実行例は `example.py` から確認できます。

```bash
poetry run python example.py
```

### バリデーションの活用

`--validate` フラグはスクレイパーの接続性、データ取得、サイト固有チェックを行い、結果を `ValidationResult` としてまとめます。稼働前の動作確認や、定期監視用のヘルスチェックとして活用してください。

## 設定ファイル

`config/settings.yaml` でスクレイピング対象サイトやログ設定、出力フォーマットを制御できます。

- `defaults.limit`: 取得件数のデフォルト値。
- `defaults.output_format`: `json` / `csv` / `both` を指定。
- `sites.<name>.enabled`: サイトごとの有効/無効切り替え。
- `logging`: ログ出力ファイルやフォーマットを管理。

CLIの `--config-path` オプションを使うと、任意の設定ファイルで上書きできます。複数環境で利用する場合は設定ファイルを分けておくと便利です。

## 開発フロー

Poetryで開発用依存関係をインストール済みであることを前提とします。

### テスト

```bash
poetry run pytest
poetry run pytest --cov=src tests/
```

特定のテストのみを実行したい場合は `-k` やパス指定を活用してください。

### 型チェック

```bash
poetry run mypy src/ main.py example.py
```

型スタブはPoetry経由で自動的にインストールされるため、追加の準備は不要です。

### コード品質

`ruff` をLintとフォーマッタの両方に利用しています。

```bash
poetry run ruff check src/ main.py example.py
poetry run ruff format src/ main.py example.py
```

CIと同じフォーマットかどうかを確認したい場合は `ruff format --check` を使用してください。

## プロジェクト構成

```
eventscraper/
├── config/              # 設定ファイル
│   └── settings.yaml
├── main.py              # TyperベースのCLIエントリーポイント
├── example.py           # サンプル実行スクリプト
├── src/
│   ├── scraper/         # 各サイトのスクレイパー実装
│   ├── models/          # Pydanticデータモデル
│   └── utils/           # 設定・エクスポート等のユーティリティ
├── tests/               # pytestベースのテストスイート
├── pyproject.toml       # Poetry設定とツールチェーン定義
├── poetry.lock          # 依存関係ロックファイル
└── requirements.txt     # ランタイム依存パッケージ（pip用）
```

## ライセンス

このプロジェクトのライセンス情報はリポジトリに含まれるファイルを参照してください。
