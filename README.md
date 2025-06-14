# Event Scraper

Hacker Newsなどの指定したサイトをスクレイピングして、機械学習モデルから利用できる統一的なデータフォーマットに変換するツールです。

## 特徴

- 非同期HTTPリクエストによる高速スクレイピング
- 統一的なデータフォーマット（JSON）への変換
- 複数サイトの同時処理
- 将来的にはLLMを使った柔軟なサイト構造解析

## 要件

- Python 3.8+
- 必要なライブラリは requirements.txt を参照

## インストール

```bash
pip install -r requirements.txt
```

## 使用方法

### 基本的な使用方法

```bash
# Hacker Newsから30記事を取得（デフォルト）
python main.py --sites hackernews

# 記事数を指定
python main.py --sites hackernews --limit 10

# 出力ファイルを指定
python main.py --sites hackernews --output my_data.json

# 複数フォーマットで出力
python main.py --sites hackernews --format both

# 利用可能なサイト一覧を表示
python main.py --list-sites

# 詳細ログを出力
python main.py --sites hackernews --verbose
```

### サンプル実行

```bash
python example.py
```

## 開発・テスト

### テストの実行

```bash
# 全テストを実行
pytest

# 特定のテストファイルを実行
pytest tests/test_hackernews.py

# カバレッジ付きでテスト実行
pytest --cov=src tests/

# 詳細な出力でテスト実行
pytest -v tests/
```

### 型検査

```bash
# 必要な型スタブをインストール
pip install pandas-stubs types-PyYAML types-beautifulsoup4

# mypyによる型検査
mypy src/ main.py example.py

# 厳密な型検査（一部の警告を無視）
mypy --strict src/ --ignore-missing-imports

# 特定のファイルのみ検査
mypy src/models/data_models.py
```

**注意**: 現在のバージョンでは、以下の型チェック警告が残っています：
- 相対インポートの警告（実際の動作には影響なし）
- PydanticのHttpUrl型の厳密チェック（実際の動作には影響なし）
- 一部のライブラリの型スタブ不足

これらは実際の動作には影響せず、将来のバージョンで改善予定です。

### コード品質チェック

```bash
# flake8によるコードスタイルチェック
pip install flake8
flake8 src/ main.py example.py

# blackによるコードフォーマット
pip install black
black src/ main.py example.py

# isortによるimport文の整理
pip install isort
isort src/ main.py example.py
```

## プロジェクト構造

```
eventscraper/
├── src/
│   ├── scraper/          # スクレイピング関連
│   ├── models/           # データモデル
│   └── utils/            # ユーティリティ
├── config/               # 設定ファイル
├── tests/                # テストファイル
├── requirements.txt      # 依存関係
└── main.py              # エントリーポイント
