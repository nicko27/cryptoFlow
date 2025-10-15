"""
Settings Window - Fenêtre de configuration GUI
"""

import customtkinter as ctk
from typing import Optional, Callable
from core.models import BotConfiguration
from config.config_manager import ConfigManager


class SettingsWindow(ctk.CTkToplevel):
    """Fenêtre de configuration"""
    
    def __init__(self, parent, config: BotConfiguration, 
                 on_save: Optional[Callable] = None):
        super().__init__(parent)
        
        self.config = config
        self.on_save_callback = on_save
        
        # Configuration fenêtre
        self.title("⚙️ Configuration")
        self.geometry("800x700")
        self.transient(parent)
        self.grab_set()
        
        # Variables
        self.telegram_token_var = ctk.StringVar(value=config.telegram_bot_token)
        self.telegram_chat_var = ctk.StringVar(value=config.telegram_chat_id)
        self.interval_var = ctk.IntVar(value=config.check_interval_seconds)
        self.enable_alerts_var = ctk.BooleanVar(value=config.enable_alerts)
        self.enable_predictions_var = ctk.BooleanVar(value=config.enable_predictions)
        self.enable_levels_var = ctk.BooleanVar(value=config.enable_price_levels)
        self.quiet_hours_var = ctk.BooleanVar(value=config.enable_quiet_hours)
        self.detail_level_var = ctk.StringVar(value=config.detail_level)
        self.show_prices_var = ctk.BooleanVar(value=config.telegram_show_prices)
        self.show_trend_24h_var = ctk.BooleanVar(value=config.telegram_show_trend_24h)
        self.show_trend_7d_var = ctk.BooleanVar(value=config.telegram_show_trend_7d)
        self.show_reco_var = ctk.BooleanVar(value=config.telegram_show_recommendations)
        self.telegram_delay_var = ctk.DoubleVar(value=config.telegram_message_delay)
        self.buy_24h_var = ctk.DoubleVar(value=config.trend_buy_threshold_24h)
        self.sell_24h_var = ctk.DoubleVar(value=config.trend_sell_threshold_24h)
        self.buy_7d_var = ctk.DoubleVar(value=config.trend_buy_threshold_7d)
        self.sell_7d_var = ctk.DoubleVar(value=config.trend_sell_threshold_7d)
        
        # UI
        self._create_ui()
    
    def _create_ui(self):
        """Crée l'interface"""
        
        # Container scrollable
        main_frame = ctk.CTkScrollableFrame(self)
        main_frame.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === TELEGRAM ===
        self._create_section(main_frame, "📱 Telegram", 0)
        
        ctk.CTkLabel(main_frame, text="Bot Token:").grid(
            row=1, column=0, padx=10, pady=5, sticky="w"
        )
        ctk.CTkEntry(main_frame, textvariable=self.telegram_token_var, width=400).grid(
            row=1, column=1, padx=10, pady=5, sticky="ew"
        )
        
        ctk.CTkLabel(main_frame, text="Chat ID:").grid(
            row=2, column=0, padx=10, pady=5, sticky="w"
        )
        ctk.CTkEntry(main_frame, textvariable=self.telegram_chat_var, width=400).grid(
            row=2, column=1, padx=10, pady=5, sticky="ew"
        )
        
        # === OPTIONS TELEGRAM ===
        self._create_section(main_frame, "📬 Contenu Telegram", 3)

        ctk.CTkCheckBox(main_frame, text="Afficher les prix",
                        variable=self.show_prices_var).grid(
            row=4, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkCheckBox(main_frame, text="Afficher la tendance 24h",
                        variable=self.show_trend_24h_var).grid(
            row=5, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkCheckBox(main_frame, text="Afficher la tendance 7j",
                        variable=self.show_trend_7d_var).grid(
            row=6, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkCheckBox(main_frame, text="Afficher la recommandation achat/vente",
                        variable=self.show_reco_var).grid(
            row=7, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkLabel(main_frame, text="Délai entre messages (s):").grid(
            row=8, column=0, padx=10, pady=5, sticky="w"
        )
        delay_frame = ctk.CTkFrame(main_frame)
        delay_frame.grid(row=8, column=1, padx=10, pady=5, sticky="w")
        ctk.CTkEntry(delay_frame, textvariable=self.telegram_delay_var, width=100).pack(side="left", padx=5)
        ctk.CTkLabel(delay_frame, text=">= 0.0").pack(side="left")

        # === SEUILS ===
        self._create_section(main_frame, "🎯 Seuils tendance", 9)

        thresholds_24h = ctk.CTkFrame(main_frame)
        thresholds_24h.grid(row=10, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        thresholds_24h.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(thresholds_24h, text="Achat 24h (%):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(thresholds_24h, textvariable=self.buy_24h_var, width=80).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(thresholds_24h, text="Vente 24h (%):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(thresholds_24h, textvariable=self.sell_24h_var, width=80).grid(row=0, column=3, padx=5, pady=5)

        thresholds_7d = ctk.CTkFrame(main_frame)
        thresholds_7d.grid(row=11, column=0, columnspan=2, padx=10, pady=5, sticky="ew")
        thresholds_7d.grid_columnconfigure((0, 1, 2, 3), weight=1)
        ctk.CTkLabel(thresholds_7d, text="Achat 7j (%):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(thresholds_7d, textvariable=self.buy_7d_var, width=80).grid(row=0, column=1, padx=5, pady=5)
        ctk.CTkLabel(thresholds_7d, text="Vente 7j (%):").grid(row=0, column=2, padx=5, pady=5, sticky="w")
        ctk.CTkEntry(thresholds_7d, textvariable=self.sell_7d_var, width=80).grid(row=0, column=3, padx=5, pady=5)

        # === SURVEILLANCE ===
        self._create_section(main_frame, "🔍 Surveillance", 12)

        ctk.CTkLabel(main_frame, text="Intervalle (secondes):").grid(
            row=13, column=0, padx=10, pady=5, sticky="w"
        )
        interval_frame = ctk.CTkFrame(main_frame)
        interval_frame.grid(row=13, column=1, padx=10, pady=5, sticky="w")

        ctk.CTkEntry(interval_frame, textvariable=self.interval_var, width=100).pack(side="left", padx=5)
        ctk.CTkLabel(interval_frame, text="(min: 60s)").pack(side="left")

        # === ALERTES ===
        self._create_section(main_frame, "🚨 Alertes", 14)

        ctk.CTkCheckBox(main_frame, text="Activer les alertes de prix",
                       variable=self.enable_alerts_var).grid(
            row=15, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkCheckBox(main_frame, text="Activer les niveaux de prix",
                       variable=self.enable_levels_var).grid(
            row=16, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        # === FONCTIONNALITÉS ===
        self._create_section(main_frame, "✨ Fonctionnalités", 17)

        ctk.CTkCheckBox(main_frame, text="Activer les prédictions",
                       variable=self.enable_predictions_var).grid(
            row=18, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        # === MODE NUIT ===
        self._create_section(main_frame, "🌙 Mode Nuit", 19)

        ctk.CTkCheckBox(main_frame, text="Activer le mode nuit",
                       variable=self.quiet_hours_var).grid(
            row=20, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        ctk.CTkLabel(main_frame, text=f"Heures silencieuses: {self.config.quiet_start_hour}h - {self.config.quiet_end_hour}h").grid(
            row=21, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )

        # === INTERFACE ===
        self._create_section(main_frame, "🎨 Interface", 22)

        ctk.CTkLabel(main_frame, text="Niveau de détail:").grid(
            row=23, column=0, padx=10, pady=5, sticky="w"
        )

        detail_menu = ctk.CTkOptionMenu(
            main_frame,
            variable=self.detail_level_var,
            values=["simple", "normal", "expert"]
        )
        detail_menu.grid(row=23, column=1, padx=10, pady=5, sticky="w")

        # === CRYPTOS ===
        self._create_section(main_frame, "💰 Cryptomonnaies surveillées", 24)

        crypto_text = ", ".join(self.config.crypto_symbols)
        ctk.CTkLabel(main_frame, text=crypto_text, wraplength=600).grid(
            row=25, column=0, columnspan=2, padx=10, pady=5, sticky="w"
        )
        
        # === BOUTONS ===
        button_frame = ctk.CTkFrame(self)
        button_frame.pack(fill="x", padx=10, pady=10)
        
        ctk.CTkButton(
            button_frame,
            text="💾 Sauvegarder",
            command=self._save_config,
            fg_color="green",
            hover_color="darkgreen",
            width=200
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="❌ Annuler",
            command=self.destroy,
            fg_color="gray",
            width=200
        ).pack(side="left", padx=5)
        
        ctk.CTkButton(
            button_frame,
            text="🔄 Réinitialiser",
            command=self._reset_config,
            width=200
        ).pack(side="right", padx=5)
    
    def _create_section(self, parent, title: str, row: int):
        """Crée une section"""
        label = ctk.CTkLabel(
            parent,
            text=title,
            font=ctk.CTkFont(size=14, weight="bold")
        )
        label.grid(row=row, column=0, columnspan=2, padx=10, pady=(15, 5), sticky="w")
    
    def _save_config(self):
        """Sauvegarde la configuration"""
        
        # Valider
        try:
            interval = self.interval_var.get()
            if interval < 60:
                self._show_error("L'intervalle doit être >= 60 secondes")
                return

            delay = float(self.telegram_delay_var.get())
            if delay < 0:
                self._show_error("Le délai Telegram doit être >= 0")
                return

            # Mettre à jour la config
            self.config.telegram_bot_token = self.telegram_token_var.get()
            self.config.telegram_chat_id = self.telegram_chat_var.get()
            self.config.check_interval_seconds = interval
            self.config.enable_alerts = self.enable_alerts_var.get()
            self.config.enable_predictions = self.enable_predictions_var.get()
            self.config.enable_price_levels = self.enable_levels_var.get()
            self.config.enable_quiet_hours = self.quiet_hours_var.get()
            self.config.detail_level = self.detail_level_var.get()
            self.config.telegram_show_prices = self.show_prices_var.get()
            self.config.telegram_show_trend_24h = self.show_trend_24h_var.get()
            self.config.telegram_show_trend_7d = self.show_trend_7d_var.get()
            self.config.telegram_show_recommendations = self.show_reco_var.get()
            self.config.telegram_message_delay = delay
            self.config.trend_buy_threshold_24h = self.buy_24h_var.get()
            self.config.trend_sell_threshold_24h = self.sell_24h_var.get()
            self.config.trend_buy_threshold_7d = self.buy_7d_var.get()
            self.config.trend_sell_threshold_7d = self.sell_7d_var.get()

            # Sauvegarder dans fichier
            config_manager = ConfigManager("config/config.yaml")
            config_manager.save_config(self.config)
            
            # Callback
            if self.on_save_callback:
                self.on_save_callback(self.config)
            
            self._show_success("Configuration sauvegardée avec succès !")
            self.destroy()
        
        except Exception as e:
            self._show_error(f"Erreur: {e}")
    
    def _reset_config(self):
        """Réinitialise la configuration"""
        if self._confirm("Réinitialiser toute la configuration ?"):
            self.config = BotConfiguration()
            self._refresh_vars()
    
    def _refresh_vars(self):
        """Rafraîchit les variables"""
        self.telegram_token_var.set(self.config.telegram_bot_token)
        self.telegram_chat_var.set(self.config.telegram_chat_id)
        self.interval_var.set(self.config.check_interval_seconds)
        self.enable_alerts_var.set(self.config.enable_alerts)
        self.enable_predictions_var.set(self.config.enable_predictions)
        self.enable_levels_var.set(self.config.enable_price_levels)
        self.quiet_hours_var.set(self.config.enable_quiet_hours)
        self.detail_level_var.set(self.config.detail_level)
        self.show_prices_var.set(self.config.telegram_show_prices)
        self.show_trend_24h_var.set(self.config.telegram_show_trend_24h)
        self.show_trend_7d_var.set(self.config.telegram_show_trend_7d)
        self.show_reco_var.set(self.config.telegram_show_recommendations)
        self.telegram_delay_var.set(self.config.telegram_message_delay)
        self.buy_24h_var.set(self.config.trend_buy_threshold_24h)
        self.sell_24h_var.set(self.config.trend_sell_threshold_24h)
        self.buy_7d_var.set(self.config.trend_buy_threshold_7d)
        self.sell_7d_var.set(self.config.trend_sell_threshold_7d)
    
    def _show_error(self, message: str):
        """Affiche une erreur"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Erreur")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"❌ {message}", wraplength=350, 
                    text_color="red").pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, 
                     fg_color="red").pack(pady=10)
    
    def _show_success(self, message: str):
        """Affiche un succès"""
        dialog = ctk.CTkToplevel(self)
        dialog.title("Succès")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"✅ {message}", wraplength=350, 
                    text_color="green").pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, 
                     fg_color="green").pack(pady=10)
    
    def _confirm(self, message: str) -> bool:
        """Dialogue de confirmation"""
        result = [False]
        
        dialog = ctk.CTkToplevel(self)
        dialog.title("Confirmation")
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=message, wraplength=350).pack(pady=20)
        
        button_frame = ctk.CTkFrame(dialog)
        button_frame.pack(pady=10)
        
        def on_yes():
            result[0] = True
            dialog.destroy()
        
        ctk.CTkButton(button_frame, text="Oui", command=on_yes, 
                     fg_color="green", width=100).pack(side="left", padx=5)
        ctk.CTkButton(button_frame, text="Non", command=dialog.destroy, 
                     fg_color="gray", width=100).pack(side="left", padx=5)
        
        dialog.wait_window()
        return result[0]
