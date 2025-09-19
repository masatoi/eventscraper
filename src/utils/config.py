"""設定管理ユーティリティ."""

from __future__ import annotations

from pathlib import Path
from typing import Any, TypeVar, cast

import yaml
from loguru import logger

T = TypeVar("T")


class Config:
    """設定管理クラス."""

    def __init__(self, config_path: str | Path | None = None) -> None:
        if config_path is None:
            config_path = (
                Path(__file__).parent.parent.parent / "config" / "settings.yaml"
            )

        self.config_path = Path(config_path)
        self._config: dict[str, Any] = {}
        self.load_config()

    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, encoding="utf-8") as file:
                    self._config = yaml.safe_load(file) or {}
                logger.info("Configuration loaded from {}", self.config_path)
            else:
                logger.warning("Configuration file not found: {}", self.config_path)
                self._config = self._get_default_config()
        except Exception as e:
            logger.error("Error loading configuration: {}", e)
            self._config = self._get_default_config()

    def _get_default_config(self) -> dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            "defaults": {
                "limit": 30,
                "timeout": 30,
                "concurrent_requests": 10,
                "output_format": "json",
                "output_dir": "output",
            },
            "sites": {
                "hackernews": {
                    "enabled": True,
                    "api_base": "https://hacker-news.firebaseio.com/v0",
                    "web_base": "https://news.ycombinator.com",
                    "rate_limit": 1.0,
                }
            },
            "logging": {
                "level": "INFO",
                "format": (
                    "{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line}"
                    " - {message}"
                ),
                "file": "logs/scraper.log",
                "rotation": "1 day",
                "retention": "7 days",
            },
            "export": {
                "include_metadata": True,
                "include_content": True,
                "include_comments": False,
                "timestamp_format": "iso",
            },
        }

    def get(self, key: str, default: T | None = None) -> T | None:
        """設定値を取得（ドット記法対応）"""
        keys = key.split(".")
        current: Any = self._config

        try:
            for k in keys:
                current = current[k]
            return cast(T | None, current)
        except (KeyError, TypeError):
            return default

    def get_defaults(self) -> dict[str, Any]:
        """デフォルト設定を取得"""
        defaults: Any = self.get("defaults", {})
        return defaults if isinstance(defaults, dict) else {}

    def get_site_config(self, site_name: str) -> dict[str, Any]:
        """サイト別設定を取得"""
        site_config: Any = self.get(f"sites.{site_name}", {})
        return site_config if isinstance(site_config, dict) else {}

    def get_logging_config(self) -> dict[str, Any]:
        """ログ設定を取得"""
        logging_config: Any = self.get("logging", {})
        return logging_config if isinstance(logging_config, dict) else {}

    def get_export_config(self) -> dict[str, Any]:
        """エクスポート設定を取得"""
        export_config: Any = self.get("export", {})
        return export_config if isinstance(export_config, dict) else {}

    def is_site_enabled(self, site_name: str) -> bool:
        """サイトが有効かチェック"""
        site_enabled: Any = self.get(f"sites.{site_name}.enabled", False)
        return bool(site_enabled)

    def get_enabled_sites(self) -> list[str]:
        """有効なサイト一覧を取得"""
        sites_config: Any = self.get("sites", {})
        if not isinstance(sites_config, dict):
            return []
        return [
            name
            for name, config in sites_config.items()
            if isinstance(config, dict) and config.get("enabled", False)
        ]


# グローバル設定インスタンス
config = Config()
