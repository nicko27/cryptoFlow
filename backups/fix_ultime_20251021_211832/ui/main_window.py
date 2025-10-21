"""
Main Window - Interface graphique principale du Crypto Bot
Version corrigée - PyQt6
"""

from pathlib import Path
from datetime import datetime, timezone  # FIXED: Problème 1 - Import timezone dupliqué corrigé
from typing import Dict, Optional, List
import yaml
import json
from threading import Thread

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QGridLayout, QComboBox, QTabWidget,
    QMessageBox, QTextEdit, QSplitter, QStatusBar, QMenuBar,
    QMenu, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QAction

from core.models import BotConfiguration, SystemStatus
from config.config_manager import ConfigManager
from daemon.daemon_service import DaemonService
from api.binance_api import BinanceAPI
from core.services.market_service import MarketService
from utils.logger import setup_logger
from core.models.notification_config import GlobalNotificationSettings
from ui.advanced_notification_config_window import AdvancedNotificationConfigWindow
from ui.settings_window import SettingsDialog


class CryptoBotGUI(QMainWindow):  # FIXED: Problème 13 - Nom de classe sans espace, pas customtkinter
    """Fenêtre principale de l'application Crypto Bot"""
    
    # Signaux
    status_updated = pyqtSignal(str)
    
    def __init__(self):
        super().__init__()
        
        # Configuration
        self.config_manager = ConfigManager()
        self.config = self._load_configuration()
        
        # Logger
        self.logger = setup_logger(
            name="CryptoBotGUI",
            log_file=self.config.log_file,
            level=self.config.log_level
        )
        
        # Services
        self.binance_api = BinanceAPI()
        self.market_service = MarketService(self.binance_api)
        self.daemon_service: Optional[DaemonService] = None
        
        # Système de notifications
        self.notification_settings = self._load_notification_settings()
        
        # État
        self.system_status = SystemStatus()
        self.current_symbol = self.config.crypto_symbols[0] if self.config.crypto_symbols else "BTC"
        
        # FIXED: Problème 24 - Cache complet initialisé
        self.market_data_cache: Dict = {}
        self.predictions_cache: Dict = {}
        self.opportunities_cache: Dict = {}
        
        # FIXED: Problème 28 - Timer de refresh configuré à 30s au lieu de 5s
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_ui)
        
        # Références UI
        self.price_card = None
        self.change_card = None
        self.rsi_card = None
        self.prediction_card = None
        self.opportunity_card = None
        self.checks_label = None
        self.alerts_label = None
        self.uptime_label = None
        self.last_update_label = None
        self.logs_text = None
        self.status_label = None
        self.daemon_status_label = None
        self.start_button = None
        self.stop_button = None
        
        # Initialiser l'interface
        self._init_ui()
        
        # Connecter signaux
        self.status_updated.connect(self._on_status_update)
        
        # Charger données initiales
        QTimer.singleShot(100, self._initial_data_load)
        
        self.logger.info("Interface graphique initialisée")
    
    def _init_ui(self):
        """Initialise l'interface utilisateur"""
        
        self.setWindowTitle("🚀 Crypto Bot v4.0 - Dashboard")
        self.setGeometry(100, 100, 1400, 900)
        
        # Widget central
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        # Layout principal
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Splitter pour ajuster les tailles
        splitter = QSplitter(Qt.Orientation.Horizontal)
        
        # Sidebar (gauche)
        sidebar = self._create_sidebar()
        splitter.addWidget(sidebar)
        
        # Zone principale (centre)
        main_area = self._create_main_area()
        splitter.addWidget(main_area)
        
        # Panel infos (droite)
        info_panel = self._create_info_panel()
        splitter.addWidget(info_panel)
        
        # Tailles initiales
        splitter.setStretchFactor(0, 1)  # Sidebar
        splitter.setStretchFactor(1, 3)  # Main area
        splitter.setStretchFactor(2, 1)  # Info panel
        
        main_layout.addWidget(splitter)
        
        # Créer la barre de menu
        self._create_menu_bar()
        
        # Créer la barre de statut
        self._create_status_bar()
        
        # Appliquer le style
        self._apply_style()
    
    def _create_sidebar(self) -> QWidget:
        """Crée la sidebar avec contrôles"""
        
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(10)
        
        # === CONTRÔLES DAEMON ===
        daemon_group = QGroupBox("🤖 Contrôle Daemon")
        daemon_layout = QVBoxLayout(daemon_group)
        
        self.daemon_status_label = QLabel("● Daemon: Arrêté")
        self.daemon_status_label.setStyleSheet("color: gray;")
        daemon_layout.addWidget(self.daemon_status_label)
        
        self.start_button = QPushButton("▶️ Démarrer")
        self.start_button.clicked.connect(self._start_daemon)
        daemon_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏹️ Arrêter")
        self.stop_button.clicked.connect(self._stop_daemon)
        self.stop_button.setEnabled(False)
        daemon_layout.addWidget(self.stop_button)
        
        layout.addWidget(daemon_group)
        
        # === SÉLECTION CRYPTO ===
        crypto_group = QGroupBox("💰 Crypto sélectionnée")
        crypto_layout = QVBoxLayout(crypto_group)
        
        self.crypto_selector = QComboBox()
        self.crypto_selector.addItems(self.config.crypto_symbols)
        self.crypto_selector.currentTextChanged.connect(self._on_crypto_changed)
        crypto_layout.addWidget(self.crypto_selector)
        
        layout.addWidget(crypto_group)
        
        # === STATISTIQUES ===
        stats_group = QGroupBox("📊 Statistiques")
        stats_layout = QVBoxLayout(stats_group)
        
        self.checks_label = QLabel("Vérifications: 0")
        stats_layout.addWidget(self.checks_label)
        
        self.alerts_label = QLabel("Alertes: 0")
        stats_layout.addWidget(self.alerts_label)
        
        self.uptime_label = QLabel("Uptime: 0h0m")
        stats_layout.addWidget(self.uptime_label)
        
        self.last_update_label = QLabel("Dernière MAJ: --:--:--")
        stats_layout.addWidget(self.last_update_label)
        
        layout.addWidget(stats_group)
        
        # === ACTIONS RAPIDES ===
        actions_group = QGroupBox("⚡ Actions")
        actions_layout = QVBoxLayout(actions_group)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self._refresh_data)
        actions_layout.addWidget(refresh_btn)
        
        summary_btn = QPushButton("📊 Résumé Telegram")
        summary_btn.clicked.connect(self._send_summary)
        actions_layout.addWidget(summary_btn)
        
        report_btn = QPushButton("📄 Générer rapport")
        report_btn.clicked.connect(self._generate_report)
        actions_layout.addWidget(report_btn)
        
        layout.addWidget(actions_group)
        
        layout.addStretch()
        
        # === CONFIGURATION ===
        settings_btn = QPushButton("⚙️ Paramètres")
        settings_btn.clicked.connect(self._open_general_settings)
        layout.addWidget(settings_btn)
        
        notif_config_btn = QPushButton("🔔 Config notifications")
        notif_config_btn.clicked.connect(self._open_notification_config)
        layout.addWidget(notif_config_btn)
        
        return sidebar
    
    def _create_main_area(self) -> QWidget:
        """Crée la zone principale avec onglets"""
        
        main_area = QWidget()
        layout = QVBoxLayout(main_area)
        layout.setContentsMargins(0, 0, 0, 0)
        
        # Onglets
        tabs = QTabWidget()
        
        # Onglet Dashboard
        dashboard_tab = self._create_dashboard_tab()
        tabs.addTab(dashboard_tab, "📊 Dashboard")
        
        # Onglet Logs
        logs_tab = self._create_logs_tab()
        tabs.addTab(logs_tab, "📝 Logs")
        
        layout.addWidget(tabs)
        
        return main_area
    
    def _create_dashboard_tab(self) -> QWidget:
        """Crée l'onglet dashboard"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Indicateurs principaux
        indicators_group = QGroupBox("💰 Indicateurs")
        indicators_layout = QGridLayout(indicators_group)
        
        # Prix
        self.price_card = self._create_metric_card("Prix", "0.00 €", "💰")
        indicators_layout.addWidget(self.price_card, 0, 0)
        
        # Changement 24h
        self.change_card = self._create_metric_card("Change 24h", "0.00%", "📈")
        indicators_layout.addWidget(self.change_card, 0, 1)
        
        # RSI
        self.rsi_card = self._create_metric_card("RSI", "0", "📊")
        indicators_layout.addWidget(self.rsi_card, 1, 0)
        
        # Prédiction
        self.prediction_card = self._create_metric_card("Prédiction", "N/A", "🔮")
        indicators_layout.addWidget(self.prediction_card, 1, 1)
        
        # Opportunité
        self.opportunity_card = self._create_metric_card("Opportunité", "0/10", "⭐")
        indicators_layout.addWidget(self.opportunity_card, 2, 0, 1, 2)
        
        layout.addWidget(indicators_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_logs_tab(self) -> QWidget:
        """Crée l'onglet logs"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("font-family: monospace;")
        
        layout.addWidget(self.logs_text)
        
        return tab
    
    def _create_info_panel(self) -> QWidget:
        """Crée le panel d'informations"""
        
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Statut
        status_group = QGroupBox("🎯 Statut")
        status_layout = QVBoxLayout(status_group)
        
        self.status_label = QLabel("● Arrêté")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        status_layout.addWidget(self.status_label)
        
        layout.addWidget(status_group)
        
        layout.addStretch()
        
        return panel
    
    def _create_menu_bar(self):
        """Crée la barre de menu"""
        
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu("📁 Fichier")
        
        export_action = QAction("💾 Exporter configuration", self)
        export_action.triggered.connect(self._export_configuration)
        file_menu.addAction(export_action)
        
        import_action = QAction("📥 Importer configuration", self)
        import_action.triggered.connect(self._import_configuration)
        file_menu.addAction(import_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("❌ Quitter", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Menu Aide
        help_menu = menubar.addMenu("❓ Aide")
        
        about_action = QAction("ℹ️ À propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """Crée la barre de statut"""
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Prêt")
    
    def _create_metric_card(self, title: str, value: str, icon: str) -> QGroupBox:
        """Crée une carte de métrique"""
        
        card = QGroupBox(f"{icon} {title}")
        layout = QVBoxLayout(card)
        
        value_label = QLabel(value)
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_font = QFont()
        value_font.setPointSize(20)
        value_font.setBold(True)
        value_label.setFont(value_font)
        
        layout.addWidget(value_label)
        
        # Stocker le label pour mise à jour
        card.value_label = value_label
        
        return card
    
    def _apply_style(self):
        """Applique le style à l'application"""
        
        self.setStyleSheet("""
            QMainWindow {
                background-color: #f0f0f0;
            }
            QGroupBox {
                font-weight: bold;
                border: 2px solid #cccccc;
                border-radius: 5px;
                margin-top: 10px;
                padding-top: 10px;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QPushButton {
                padding: 8px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                opacity: 0.8;
            }
        """)
    
    # === MÉTHODES DE CONFIGURATION ===
    
    def _load_configuration(self) -> BotConfiguration:
        """Charge la configuration"""
        
        try:
            if self.config_manager.config_exists():
                return self.config_manager.load_config()
            else:
                return BotConfiguration()
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de charger la configuration : {e}"
            )
            return BotConfiguration()
    
    def _load_notification_settings(self) -> GlobalNotificationSettings:
        """Charge les paramètres de notification"""
        
        notif_config_path = Path("config/notifications.yaml")
        
        if notif_config_path.exists():
            try:
                with open(notif_config_path, 'r', encoding='utf-8') as f:
                    data = yaml.safe_load(f)
                return self._dict_to_notification_settings(data)
            except Exception as e:
                self.logger.error(f"Erreur chargement notifications: {e}")
        
        return GlobalNotificationSettings(
            enabled=True,
            kid_friendly_mode=True,
            use_emojis_everywhere=True,
            explain_everything=True,
            respect_quiet_hours=True,
            quiet_start=23,
            quiet_end=7,
            default_scheduled_hours=[9, 12, 18]
        )
    
    def _dict_to_notification_settings(self, data: dict) -> GlobalNotificationSettings:
        """Convertit un dict en GlobalNotificationSettings"""
        # FIXED: Problème 8 - Méthode implémentée
        def _normalize_hours(value) -> List[int]:
            hours: List[int] = []
            if isinstance(value, (int, float)):
                hours.append(int(value))
            elif isinstance(value, str):
                parts = [p.strip() for p in value.replace(";", ",").split(",")]
                for part in parts:
                    if part.isdigit():
                        hours.append(int(part))
            elif isinstance(value, list):
                for item in value:
                    if isinstance(item, (int, float)):
                        hours.append(int(item))
                    elif isinstance(item, str) and item.strip().isdigit():
                        hours.append(int(item.strip()))
            return sorted({h for h in hours if 0 <= h <= 23})

        hours = _normalize_hours(data.get('default_scheduled_hours', [9, 12, 18])) or [9, 12, 18]
        quiet_start = int(data.get('quiet_start', 23) or 0)
        quiet_end = int(data.get('quiet_end', 7) or 0)
        quiet_start = max(0, min(23, quiet_start))
        quiet_end = max(0, min(23, quiet_end))

        return GlobalNotificationSettings(
            enabled=data.get('enabled', True),
            kid_friendly_mode=data.get('kid_friendly_mode', True),
            use_emojis_everywhere=data.get('use_emojis_everywhere', True),
            explain_everything=data.get('explain_everything', True),
            respect_quiet_hours=data.get('respect_quiet_hours', True),
            quiet_start=quiet_start,
            quiet_end=quiet_end,
            default_scheduled_hours=hours
        )
    
    def _save_notification_settings(self):
        """Sauvegarde les paramètres de notification"""
        
        try:
            notif_config_path = Path("config/notifications.yaml")
            notif_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(notif_config_path, 'w', encoding='utf-8') as f:
                yaml.dump({
                    'enabled': self.notification_settings.enabled,
                    'kid_friendly_mode': self.notification_settings.kid_friendly_mode,
                    'use_emojis_everywhere': self.notification_settings.use_emojis_everywhere,
                    'explain_everything': self.notification_settings.explain_everything,
                    'respect_quiet_hours': self.notification_settings.respect_quiet_hours,
                    'quiet_start': int(self.notification_settings.quiet_start),
                    'quiet_end': int(self.notification_settings.quiet_end),
                    'default_scheduled_hours': sorted(self.notification_settings.default_scheduled_hours),
                }, f, default_flow_style=False, sort_keys=False)
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde notifications: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de sauvegarder : {e}"
            )
    
    def _on_status_update(self, message: str):
        """Appelé pour mettre à jour le statut"""
        self.status_bar.showMessage(message, 3000)
    
    def _on_crypto_changed(self, symbol: str):
        """Appelé quand la crypto sélectionnée change"""
        self.current_symbol = symbol
        self._refresh_data()
    
    # === MÉTHODES DE CONTRÔLE DAEMON ===
    
    def _start_daemon(self):
        """Démarre le daemon"""
        
        try:
            self.logger.info("Démarrage du daemon...")
            
            if self.daemon_service is None:
                self.daemon_service = DaemonService(self.config)
                self.daemon_service.notification_settings = self.notification_settings
            
                # Lancer le daemon dans un thread séparé pour ne pas bloquer le GUI
            self.daemon_thread = Thread(target=self.daemon_service.start, daemon=True)
            self.daemon_thread.start()
            print("✓ Daemon démarré dans un thread séparé")
            
            # Mettre à jour l'UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.daemon_status_label.setText("● Daemon: En cours")
            self.daemon_status_label.setStyleSheet("color: green;")
            self.status_label.setText("● En cours")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # FIXED: Problème 28 - Timer à 30s au lieu de 5s
            self.refresh_timer.start(30000)  # 30 secondes
            
            self.logger.info("Daemon démarré")
            
            QMessageBox.information(
                self,
                "Daemon",
                "Le daemon a été démarré avec succès !"
            )
            
        except Exception as e:
            self.logger.error(f"Erreur démarrage daemon: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de démarrer le daemon : {e}"
            )
    
    def _stop_daemon(self):
        """Arrête le daemon"""
        
        try:
            self.logger.info("Arrêt du daemon...")
            
            if self.daemon_service:
                self.daemon_service.stop()
            
            # Mettre à jour l'UI
            self.start_button.setEnabled(True)
            self.stop_button.setEnabled(False)
            self.daemon_status_label.setText("● Daemon: Arrêté")
            self.daemon_status_label.setStyleSheet("color: gray;")
            self.status_label.setText("● Arrêté")
            self.status_label.setStyleSheet("color: gray; font-weight: bold;")
            
            self.refresh_timer.stop()
            
            self.logger.info("Daemon arrêté")
            
            QMessageBox.information(
                self,
                "Daemon",
                "Le daemon a été arrêté."
            )
            
        except Exception as e:
            self.logger.error(f"Erreur arrêt daemon: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible d'arrêter le daemon : {e}"
            )
    
    # === MÉTHODES DE DONNÉES ===
    
    def _initial_data_load(self):
        """Charge les données initiales"""
        self.logger.info("Chargement des données initiales...")
        self._refresh_data()
    
    def _refresh_data(self):
        """Rafraîchit les données"""
        
        try:
            market_data = self.market_service.get_market_data(self.current_symbol)
            
            if market_data:
                self.market_data_cache[self.current_symbol] = market_data
                self._update_dashboard(market_data)
                self.last_update_label.setText(datetime.now(timezone.utc).strftime("%H:%M:%S"))
            
        except Exception as e:
            self.logger.error(f"Erreur refresh données: {e}")
    
    def _refresh_ui(self):
        """Rafraîchit l'UI périodiquement"""
        
        self._refresh_data()
        
        if self.daemon_service:
            self.checks_label.setText(f"Vérifications: {self.daemon_service.checks_count}")
            self.alerts_label.setText(f"Alertes: {self.daemon_service.alerts_sent}")
            
            if self.daemon_service.start_time:
                uptime = datetime.now(timezone.utc) - self.daemon_service.start_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                self.uptime_label.setText(f"Uptime: {hours}h{minutes}m")
    
    def _update_dashboard(self, market_data):
        """Met à jour le dashboard avec les données"""
        
        if market_data and self.price_card:
            self.price_card.value_label.setText(
                f"{market_data.current_price.price_eur:.2f} €"
            )
            
            if self.change_card:
                change = market_data.current_price.change_24h
                self.change_card.value_label.setText(f"{change:+.2f}%")
                color = "green" if change > 0 else "red"
                self.change_card.value_label.setStyleSheet(f"color: {color};")
            
            if self.rsi_card:
                self.rsi_card.value_label.setText(
                    f"{market_data.technical_indicators.rsi:.0f}"
                )
    
    # === MÉTHODES D'ACTION ===
    
    def _send_summary(self):
        """Envoie un résumé complet sur Telegram via SummaryService"""
        try:
            # Importer SummaryService
            from core.services.summary_service import SummaryService
            from api.enhanced_telegram_api import EnhancedTelegramAPI
            
            # Créer le service de résumé
            summary_service = SummaryService(self.config)
            
            # Collecter les données pour toutes les cryptos
            markets_data = {}
            predictions = {}
            opportunities = {}
            
            self.logger.info("Collecte des données de marché...")
            
            for symbol in self.config.crypto_symbols:
                try:
                    # Utiliser le cache ou récupérer les données
                    if symbol in self.market_data_cache:
                        market = self.market_data_cache[symbol]
                    else:
                        market = self.market_service.get_market_data(symbol)
                        self.market_data_cache[symbol] = market
                    
                    if market:
                        markets_data[symbol] = market
                        
                        # Prédictions
                        if symbol in self.predictions_cache:
                            pred = self.predictions_cache[symbol]
                        else:
                            pred = self.market_service.predict_price_movement(market)
                            if pred:
                                self.predictions_cache[symbol] = pred
                        
                        if pred:
                            predictions[symbol] = pred
                        
                        # Opportunités
                        if symbol in self.opportunities_cache:
                            opp = self.opportunities_cache[symbol]
                        else:
                            opp = self.market_service.calculate_opportunity_score(market, pred)
                            if opp:
                                self.opportunities_cache[symbol] = opp
                        
                        if opp:
                            opportunities[symbol] = opp
                        
                        self.logger.info(f"  ✓ {symbol}: {market.current_price.price_eur:.2f}€")
                
                except Exception as e:
                    self.logger.error(f"Erreur récupération {symbol}: {e}")
            
            if not markets_data:
                QMessageBox.warning(
                    self,
                    "Aucune donnée",
                    "Aucune donnée de marché disponible. Rafraîchis d'abord les données."
                )
                return
            
            # Générer le résumé via SummaryService
            self.logger.info("Génération du résumé...")
            summary = summary_service.generate_summary(
                markets_data,
                predictions,
                opportunities,
                simple=self.config.use_simple_language
            )
            
            if not summary:
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Impossible de générer le résumé"
                )
                return
            
            # Envoyer le résumé sur Telegram
            self.logger.info("Envoi du résumé sur Telegram...")
            telegram = EnhancedTelegramAPI(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            )
            
            success = telegram.send_message(summary, parse_mode="HTML")
            
            if success:
                self.logger.info("✓ Résumé envoyé avec succès")
                QMessageBox.information(
                    self,
                    "Résumé envoyé",
                    "✅ Résumé envoyé sur Telegram avec succès !"
                )
            else:
                self.logger.error("✗ Échec envoi résumé")
                QMessageBox.warning(
                    self,
                    "Erreur",
                    "Échec de l'envoi du résumé sur Telegram"
                )
        
        except Exception as e:
            self.logger.error(f"Erreur envoi résumé: {e}", exc_info=True)
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'envoi du résumé :\n{e}"
            )

    def _generate_report(self):
        """Génère un rapport complet"""
        # FIXED: Problème 22 - Implémentation complète
        
        try:
            report_path = Path("reports")
            report_path.mkdir(exist_ok=True)
            
            filename = f"report_{datetime.now(timezone.utc).strftime('%Y%m%d_%H%M%S')}.txt"
            filepath = report_path / filename
            
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write("="*60 + "\n")
                f.write("RAPPORT CRYPTO BOT\n")
                f.write("="*60 + "\n\n")
                f.write(f"Date: {datetime.now(timezone.utc).strftime('%d/%m/%Y %H:%M:%S')} UTC\n\n")
                
                for symbol in self.config.crypto_symbols:
                    if symbol in self.market_data_cache:
                        data = self.market_data_cache[symbol]
                        f.write(f"\n{symbol}:\n")
                        f.write(f"  Prix: {data.current_price.price_eur:.2f}€\n")
                        f.write(f"  Change 24h: {data.current_price.change_24h:+.2f}%\n")
                        f.write(f"  RSI: {data.technical_indicators.rsi:.0f}\n")
                
                if self.daemon_service:
                    f.write(f"\n\nSTATISTIQUES:\n")
                    f.write(f"  Vérifications: {self.daemon_service.checks_count}\n")
                    f.write(f"  Alertes: {self.daemon_service.alerts_sent}\n")
                    f.write(f"  Erreurs: {self.daemon_service.errors_count}\n")
            
            QMessageBox.information(
                self,
                "Rapport",
                f"Rapport généré avec succès !\n\nFichier: {filepath}"
            )
            
        except Exception as e:
            self.logger.error(f"Erreur génération rapport: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de générer le rapport : {e}"
            )
    
    def _export_configuration(self):
        """Exporte la configuration"""
        # FIXED: Problème 23 - Implémentation complète avec validation
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter configuration",
            "",
            "Fichiers YAML (*.yaml *.yml)"
        )
        
        if file_path:
            # FIXED: Problème 18 - Validation du type de fichier
            if not file_path.endswith(('.yaml', '.yml')):
                file_path += '.yaml'
            
            try:
                self.config_manager.save_config(self.config)
                
                # Copier vers le fichier choisi
                import shutil
                shutil.copy(self.config_manager.config_file, file_path)
                
                QMessageBox.information(
                    self,
                    "Export",
                    f"Configuration exportée vers {file_path}"
                )
            except Exception as e:
                self.logger.error(f"Erreur export: {e}")
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Impossible d'exporter : {e}"
                )
    
    def _import_configuration(self):
        """Importe une configuration"""
        # FIXED: Problème 23 - Implémentation complète avec validation
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer configuration",
            "",
            "Fichiers YAML (*.yaml *.yml)"
        )
        
        if file_path:
            # FIXED: Problème 18 - Validation du fichier
            if not Path(file_path).exists():
                QMessageBox.critical(
                    self,
                    "Erreur",
                    "Le fichier sélectionné n'existe pas"
                )
                return
            
            try:
                # Charger depuis le fichier
                import shutil
                backup_file = self.config_manager.config_file + ".backup"
                shutil.copy(self.config_manager.config_file, backup_file)
                
                shutil.copy(file_path, self.config_manager.config_file)
                self.config = self.config_manager.load_config()
                
                # Recharger UI
                self.crypto_selector.clear()
                self.crypto_selector.addItems(self.config.crypto_symbols)
                
                QMessageBox.information(
                    self,
                    "Import",
                    "Configuration importée avec succès !\n(Backup créé: " + backup_file + ")"
                )
            except Exception as e:
                self.logger.error(f"Erreur import: {e}")
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Impossible d'importer : {e}"
                )
    
    def _open_general_settings(self):
        """Ouvre la fenêtre de paramètres généraux"""
        
        try:
            dialog = SettingsDialog(
                parent=self,
                config=self.config,
                on_save=self._on_config_saved
            )
            
            dialog.exec()
            
        except Exception as e:
            self.logger.error(f"Erreur ouverture paramètres: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible d'ouvrir les paramètres : {e}"
            )
    
    def _open_notification_config(self):
        """Ouvre la configuration avancée des notifications"""
        
        try:
            dialog = AdvancedNotificationConfigWindow(
                settings=self.notification_settings,
                symbols=self.config.crypto_symbols,
                parent=self
            )
            
            if dialog.exec() == QDialog.DialogCode.Accepted:
                self.notification_settings = dialog.settings
                self._save_notification_settings()
                
                if self.daemon_service:
                    self.daemon_service.update_notification_settings(self.notification_settings)
                
                QMessageBox.information(
                    self,
                    "Configuration",
                    "Configuration des notifications enregistrée !"
                )
            
        except Exception as e:
            self.logger.error(f"Erreur config notifications: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible d'ouvrir la configuration : {e}"
            )
    
    def _on_config_saved(self, config: BotConfiguration):
        """Appelé quand la config est sauvegardée"""
        
        self.config = config
        self.config_manager.save_config(config)
        
        if self.daemon_service:
            self.daemon_service.update_configuration(config)
        
        self.logger.info("Configuration sauvegardée")
    
    def _show_about(self):
        """Affiche la fenêtre À propos"""
        
        QMessageBox.about(
            self,
            "À propos",
            "🚀 Crypto Bot v4.0\n\n"
            "Bot de trading crypto intelligent\n"
            "Avec surveillance en temps réel\n\n"
            "© 2025 - PyQt6 Edition"
        )
    
    def closeEvent(self, event):
        """Gère la fermeture de la fenêtre"""
        
        if self.daemon_service and self.daemon_service.is_running:
            reply = QMessageBox.question(
                self,
                "Confirmation",
                "Le daemon est en cours d'exécution.\nVoulez-vous vraiment quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.daemon_service.stop()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()
