"""Configuration Manager - Gestion de la configuration"""
import yaml
from pathlib import Path
from typing import Optional, Dict, Any
from core.models import BotConfiguration

class ConfigManager:
    def __init__(self, config_path: str = "config/config.yaml"):
        self.config_path = Path(config_path)
        self.config_dir = self.config_path.parent
    
    def config_exists(self) -> bool:
        return self.config_path.exists()
    
    def load_config(self) -> BotConfiguration:
        if not self.config_exists():
            raise FileNotFoundError(f"Configuration non trouvée : {self.config_path}")
        with open(self.config_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return self._dict_to_config(data)
    
    def save_config(self, config: BotConfiguration):
        self.config_dir.mkdir(parents=True, exist_ok=True)
        data = self._config_to_dict(config)
        with open(self.config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
    
    def _dict_to_config(self, data: Dict[str, Any]) -> BotConfiguration:
        telegram_cfg = data.get("telegram", {})
        display_cfg = telegram_cfg.get("display", {})
        thresholds_cfg = telegram_cfg.get("thresholds", {})

        return BotConfiguration(
            telegram_bot_token=telegram_cfg.get("bot_token", ""),
            telegram_chat_id=telegram_cfg.get("chat_id", ""),
            crypto_symbols=data.get("crypto", {}).get("symbols", ["BTC"]),
            investment_amount=data.get("crypto", {}).get("investment_amount", 100.0),
            enable_alerts=data.get("alerts", {}).get("enable", True),
            price_lookback_minutes=data.get("alerts", {}).get("lookback_minutes", 120),
            price_drop_threshold=data.get("alerts", {}).get("drop_threshold", 10.0),
            price_spike_threshold=data.get("alerts", {}).get("spike_threshold", 10.0),
            enable_price_levels=data.get("price_levels", {}).get("enable", True),
            price_levels=data.get("price_levels", {}).get("levels", {}),
            level_buffer_eur=data.get("price_levels", {}).get("buffer_eur", 2.0),
            level_cooldown_minutes=data.get("price_levels", {}).get("cooldown_minutes", 30),
            check_interval_seconds=data.get("timing", {}).get("check_interval", 900),
            log_file=data.get("logging", {}).get("file", "logs/crypto_bot.log"),
            log_level=data.get("logging", {}).get("level", "INFO"),
            telegram_show_prices=display_cfg.get("show_prices", True),
            telegram_show_trend_24h=display_cfg.get("show_trend_24h", True),
            telegram_show_trend_7d=display_cfg.get("show_trend_7d", True),
            telegram_show_recommendations=display_cfg.get("show_recommendations", True),
            telegram_message_delay=telegram_cfg.get("message_delay", 0.5),
            trend_buy_threshold_24h=thresholds_cfg.get("buy_24h", 2.0),
            trend_sell_threshold_24h=thresholds_cfg.get("sell_24h", -2.0),
            trend_buy_threshold_7d=thresholds_cfg.get("buy_7d", 5.0),
            trend_sell_threshold_7d=thresholds_cfg.get("sell_7d", -5.0)
        )

    def _config_to_dict(self, config: BotConfiguration) -> Dict[str, Any]:
        return {
            "telegram": {
                "bot_token": config.telegram_bot_token,
                "chat_id": config.telegram_chat_id,
                "message_delay": config.telegram_message_delay,
                "display": {
                    "show_prices": config.telegram_show_prices,
                    "show_trend_24h": config.telegram_show_trend_24h,
                    "show_trend_7d": config.telegram_show_trend_7d,
                    "show_recommendations": config.telegram_show_recommendations,
                },
                "thresholds": {
                    "buy_24h": config.trend_buy_threshold_24h,
                    "sell_24h": config.trend_sell_threshold_24h,
                    "buy_7d": config.trend_buy_threshold_7d,
                    "sell_7d": config.trend_sell_threshold_7d,
                },
            },
            "crypto": {"symbols": config.crypto_symbols, "investment_amount": config.investment_amount},
            "alerts": {"enable": config.enable_alerts, "lookback_minutes": config.price_lookback_minutes},
            "price_levels": {"enable": config.enable_price_levels, "levels": config.price_levels},
            "timing": {"check_interval": config.check_interval_seconds},
            "logging": {"file": config.log_file, "level": config.log_level}
        }
