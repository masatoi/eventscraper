"""
設定管理ユーティリティ
"""
import yaml
from pathlib import Path
from typing import Dict, Any, Optional, Union, List
from loguru import logger


class Config:
    """設定管理クラス"""
    
    def __init__(self, config_path: Optional[Union[str, Path]] = None):
        if config_path is None:
            config_path = Path(__file__).parent.parent.parent / "config" / "settings.yaml"
        
        self.config_path = Path(config_path)
        self._config: Dict[str, Any] = {}
        self.load_config()
    
    def load_config(self) -> None:
        """設定ファイルを読み込み"""
        try:
            if self.config_path.exists():
                with open(self.config_path, 'r', encoding='utf-8') as f:
                    self._config = yaml.safe_load(f) or {}
                logger.info(f"Configuration loaded from {self.config_path}")
            else:
                logger.warning(f"Configuration file not found: {self.config_path}")
                self._config = self._get_default_config()
        except Exception as e:
            logger.error(f"Error loading configuration: {e}")
            self._config = self._get_default_config()
    
    def _get_default_config(self) -> Dict[str, Any]:
        """デフォルト設定を返す"""
        return {
            'defaults': {
                'limit': 30,
                'timeout': 30,
                'concurrent_requests': 10,
                'output_format': 'json',
                'output_dir': 'output'
            },
            'sites': {
                'hackernews': {
                    'enabled': True,
                    'api_base': 'https://hacker-news.firebaseio.com/v0',
                    'web_base': 'https://news.ycombinator.com',
                    'rate_limit': 1.0
                }
            },
            'logging': {
                'level': 'INFO',
                'format': '{time:YYYY-MM-DD HH:mm:ss} | {level} | {name}:{function}:{line} - {message}',
                'file': 'logs/scraper.log',
                'rotation': '1 day',
                'retention': '7 days'
            },
            'export': {
                'include_metadata': True,
                'include_content': True,
                'include_comments': False,
                'timestamp_format': 'iso'
            }
        }
    
    def get(self, key: str, default: Any = None) -> Any:
        """設定値を取得（ドット記法対応）"""
        keys = key.split('.')
        value = self._config
        
        try:
            for k in keys:
                value = value[k]
            return value
        except (KeyError, TypeError):
            return default
    
    def get_defaults(self) -> Dict[str, Any]:
        """デフォルト設定を取得"""
        result = self.get('defaults', {})
        return result if isinstance(result, dict) else {}
    
    def get_site_config(self, site_name: str) -> Dict[str, Any]:
        """サイト別設定を取得"""
        result = self.get(f'sites.{site_name}', {})
        return result if isinstance(result, dict) else {}
    
    def get_logging_config(self) -> Dict[str, Any]:
        """ログ設定を取得"""
        result = self.get('logging', {})
        return result if isinstance(result, dict) else {}
    
    def get_export_config(self) -> Dict[str, Any]:
        """エクスポート設定を取得"""
        result = self.get('export', {})
        return result if isinstance(result, dict) else {}
    
    def is_site_enabled(self, site_name: str) -> bool:
        """サイトが有効かチェック"""
        result = self.get(f'sites.{site_name}.enabled', False)
        return bool(result)
    
    def get_enabled_sites(self) -> List[str]:
        """有効なサイト一覧を取得"""
        sites = self.get('sites', {})
        if not isinstance(sites, dict):
            return []
        return [name for name, config in sites.items() 
                if isinstance(config, dict) and config.get('enabled', False)]


# グローバル設定インスタンス
config = Config()
