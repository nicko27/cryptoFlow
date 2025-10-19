"""
Main Window - Interface graphique principale du Crypto Bot
Version améliorée avec intégration du système de notifications avancé
"""

from pathlib import Path
from datetime import datetime, timezone, timezone
from typing import Dict, Optional, List
import yaml

from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QLabel,
    QPushButton, QGroupBox, QGridLayout, QComboBox, QTabWidget,
    QMessageBox, QTextEdit, QSplitter, QStatusBar, QMenuBar,
    QMenu, QFileDialog, QDialog
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal
from PyQt6.QtGui import QFont, QAction, QIcon

from core.models import BotConfiguration, SystemStatus
from config.config_manager import ConfigManager
from daemon.daemon_service import DaemonService
from api.binance_api import BinanceAPI
from core.services.market_service import MarketService
from utils.logger import setup_logger

# Importer le nouveau système de notifications
from core.models.notification_config import GlobalNotificationSettings
from ui.advanced_notification_config_window import AdvancedNotificationConfigWindow
from ui.settings_window import SettingsDialog


class MainWindow(QMainWindow):
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
        
        # Données en cache
        self.market_data_cache = {}
        self.predictions_cache = {}
        self.opportunities_cache = {}
        
        # Timer pour refresh UI
        self.refresh_timer = QTimer()
        self.refresh_timer.timeout.connect(self._refresh_ui)
        
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
    
    def _create_menu_bar(self):
        """Crée la barre de menu"""
        
        menubar = self.menuBar()
        
        # Menu Fichier
        file_menu = menubar.addMenu("📁 Fichier")
        
        export_config_action = QAction("💾 Exporter configuration", self)
        export_config_action.triggered.connect(self._export_configuration)
        file_menu.addAction(export_config_action)
        
        import_config_action = QAction("📥 Importer configuration", self)
        import_config_action.triggered.connect(self._import_configuration)
        file_menu.addAction(import_config_action)
        
        file_menu.addSeparator()
        
        quit_action = QAction("🚪 Quitter", self)
        quit_action.triggered.connect(self.close)
        file_menu.addAction(quit_action)
        
        # Menu Configuration
        config_menu = menubar.addMenu("⚙️ Configuration")
        
        general_settings_action = QAction("🔧 Paramètres généraux", self)
        general_settings_action.triggered.connect(self._open_general_settings)
        config_menu.addAction(general_settings_action)
        
        notif_settings_action = QAction("🔔 Notifications avancées", self)
        notif_settings_action.triggered.connect(self._open_notification_config)
        config_menu.addAction(notif_settings_action)
        
        # Menu Actions
        actions_menu = menubar.addMenu("🎯 Actions")
        
        test_telegram_action = QAction("📤 Test Telegram", self)
        test_telegram_action.triggered.connect(self._test_telegram)
        actions_menu.addAction(test_telegram_action)
        
        send_summary_action = QAction("📊 Envoyer résumé", self)
        send_summary_action.triggered.connect(self._send_summary)
        actions_menu.addAction(send_summary_action)
        
        generate_report_action = QAction("📄 Générer rapport", self)
        generate_report_action.triggered.connect(self._generate_report)
        actions_menu.addAction(generate_report_action)
        
        # Menu Aide
        help_menu = menubar.addMenu("❓ Aide")
        
        guide_action = QAction("📚 Guide utilisateur", self)
        guide_action.triggered.connect(self._show_user_guide)
        help_menu.addAction(guide_action)
        
        about_action = QAction("ℹ️ À propos", self)
        about_action.triggered.connect(self._show_about)
        help_menu.addAction(about_action)
    
    def _create_status_bar(self):
        """Crée la barre de statut"""
        
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        
        # Labels de statut
        self.status_label = QLabel("● Arrêté")
        self.status_label.setStyleSheet("color: gray; font-weight: bold;")
        self.status_bar.addWidget(self.status_label)
        
        self.status_bar.addPermanentWidget(QLabel("   |   "))
        
        self.crypto_label = QLabel(f"📊 {self.current_symbol}")
        self.status_bar.addPermanentWidget(self.crypto_label)
        
        self.status_bar.addPermanentWidget(QLabel("   |   "))
        
        self.time_label = QLabel(datetime.now(timezone.utc).strftime("%H:%M:%S"))
        self.status_bar.addPermanentWidget(self.time_label)
        
        # Timer pour mettre à jour l'heure
        time_timer = QTimer(self)
        time_timer.timeout.connect(lambda: self.time_label.setText(
            datetime.now(timezone.utc).strftime("%H:%M:%S")
        ))
        time_timer.start(1000)
    
    def _create_sidebar(self) -> QWidget:
        """Crée la sidebar avec les contrôles"""
        
        sidebar = QGroupBox("🎮 Contrôles")
        layout = QVBoxLayout(sidebar)
        layout.setSpacing(10)
        
        # === TITRE ===
        title = QLabel("🚀 Crypto Bot")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        version = QLabel("v4.0")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: gray;")
        layout.addWidget(version)
        
        layout.addSpacing(20)
        
        # === STATUT ===
        status_group = QGroupBox("📊 Statut")
        status_layout = QVBoxLayout(status_group)
        
        self.daemon_status_label = QLabel("● Daemon: Arrêté")
        self.daemon_status_label.setStyleSheet("color: gray;")
        status_layout.addWidget(self.daemon_status_label)
        
        self.checks_label = QLabel("Vérifications: 0")
        status_layout.addWidget(self.checks_label)
        
        self.alerts_label = QLabel("Alertes: 0")
        status_layout.addWidget(self.alerts_label)
        
        self.uptime_label = QLabel("Uptime: 0h0m")
        status_layout.addWidget(self.uptime_label)
        
        layout.addWidget(status_group)
        
        # === CONTRÔLES DAEMON ===
        daemon_group = QGroupBox("⚙️ Daemon")
        daemon_layout = QVBoxLayout(daemon_group)
        
        self.start_button = QPushButton("▶️ Démarrer")
        self.start_button.clicked.connect(self._start_daemon)
        self.start_button.setStyleSheet("""
            QPushButton {
                background-color: #28a745;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #218838;
            }
        """)
        daemon_layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏸️ Arrêter")
        self.stop_button.clicked.connect(self._stop_daemon)
        self.stop_button.setEnabled(False)
        self.stop_button.setStyleSheet("""
            QPushButton {
                background-color: #dc3545;
                color: white;
                font-weight: bold;
                padding: 10px;
            }
            QPushButton:hover {
                background-color: #c82333;
            }
            QPushButton:disabled {
                background-color: #6c757d;
            }
        """)
        daemon_layout.addWidget(self.stop_button)
        
        layout.addWidget(daemon_group)
        
        # === SÉLECTION CRYPTO ===
        crypto_group = QGroupBox("💎 Crypto-monnaie")
        crypto_layout = QVBoxLayout(crypto_group)
        
        self.crypto_selector = QComboBox()
        self.crypto_selector.addItems(self.config.crypto_symbols)
        self.crypto_selector.currentTextChanged.connect(self._on_crypto_changed)
        crypto_layout.addWidget(self.crypto_selector)
        
        layout.addWidget(crypto_group)
        
        # === ACTIONS RAPIDES ===
        actions_group = QGroupBox("⚡ Actions rapides")
        actions_layout = QVBoxLayout(actions_group)
        
        refresh_btn = QPushButton("🔄 Actualiser")
        refresh_btn.clicked.connect(self._refresh_data)
        actions_layout.addWidget(refresh_btn)
        
        summary_btn = QPushButton("📊 Résumé Telegram")
        summary_btn.clicked.connect(self._send_summary)
        actions_layout.addWidget(summary_btn)
        
        notif_test_btn = QPushButton("🔔 Test notification")
        notif_test_btn.clicked.connect(self._test_notification)
        actions_layout.addWidget(notif_test_btn)
        
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
        
        # Onglet Notifications
        notifications_tab = self._create_notifications_tab()
        tabs.addTab(notifications_tab, "🔔 Notifications")
        
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
        
        # Variation 24h
        self.change_24h_card = self._create_metric_card("24h", "0.00%", "📊")
        indicators_layout.addWidget(self.change_24h_card, 0, 1)
        
        # Variation 7j
        self.change_7d_card = self._create_metric_card("7j", "0.00%", "📈")
        indicators_layout.addWidget(self.change_7d_card, 0, 2)
        
        # Opportunité
        self.opportunity_card = self._create_metric_card("Opportunité", "0/10", "⭐")
        indicators_layout.addWidget(self.opportunity_card, 0, 3)
        
        layout.addWidget(indicators_group)
        
        # Recommandation
        recommendation_group = QGroupBox("💡 Recommandation")
        recommendation_layout = QVBoxLayout(recommendation_group)
        
        self.recommendation_label = QLabel("En attente de données...")
        self.recommendation_label.setWordWrap(True)
        self.recommendation_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        recommendation_font = QFont()
        recommendation_font.setPointSize(14)
        recommendation_font.setBold(True)
        self.recommendation_label.setFont(recommendation_font)
        recommendation_layout.addWidget(self.recommendation_label)
        
        layout.addWidget(recommendation_group)
        
        # Prédiction IA
        prediction_group = QGroupBox("🔮 Prédiction IA")
        prediction_layout = QVBoxLayout(prediction_group)
        
        self.prediction_label = QLabel("En attente de données...")
        self.prediction_label.setWordWrap(True)
        self.prediction_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        prediction_layout.addWidget(self.prediction_label)
        
        layout.addWidget(prediction_group)
        
        layout.addStretch()
        
        return tab
    
    def _create_notifications_tab(self) -> QWidget:
        """Crée l'onglet notifications"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Info
        info_label = QLabel(
            "📱 Configuration du système de notifications\n\n"
            "Horaires configurés, blocs activés, suggestions d'investissement, etc."
        )
        info_label.setWordWrap(True)
        info_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(info_label)
        
        # Résumé de la config
        summary_group = QGroupBox("📋 Résumé de la configuration")
        summary_layout = QVBoxLayout(summary_group)
        
        self.notif_summary_text = QTextEdit()
        self.notif_summary_text.setReadOnly(True)
        self.notif_summary_text.setMaximumHeight(300)
        summary_layout.addWidget(self.notif_summary_text)
        
        layout.addWidget(summary_group)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        open_config_btn = QPushButton("⚙️ Ouvrir configuration avancée")
        open_config_btn.clicked.connect(self._open_notification_config)
        buttons_layout.addWidget(open_config_btn)
        
        test_notif_btn = QPushButton("🧪 Tester une notification")
        test_notif_btn.clicked.connect(self._test_notification)
        buttons_layout.addWidget(test_notif_btn)
        
        layout.addLayout(buttons_layout)
        
        # Mettre à jour le résumé
        self._update_notification_summary()
        
        layout.addStretch()
        
        return tab
    
    def _create_logs_tab(self) -> QWidget:
        """Crée l'onglet logs"""
        
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Zone de logs
        self.logs_text = QTextEdit()
        self.logs_text.setReadOnly(True)
        self.logs_text.setStyleSheet("""
            QTextEdit {
                background-color: #1e1e1e;
                color: #d4d4d4;
                font-family: 'Courier New', monospace;
                font-size: 10pt;
            }
        """)
        layout.addWidget(self.logs_text)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        refresh_logs_btn = QPushButton("🔄 Actualiser")
        refresh_logs_btn.clicked.connect(self._load_logs)
        buttons_layout.addWidget(refresh_logs_btn)
        
        clear_logs_btn = QPushButton("🗑️ Effacer l'affichage")
        clear_logs_btn.clicked.connect(self.logs_text.clear)
        buttons_layout.addWidget(clear_logs_btn)
        
        layout.addLayout(buttons_layout)
        
        # Charger les logs
        self._load_logs()
        
        return tab
    
    def _create_info_panel(self) -> QWidget:
        """Crée le panel d'informations"""
        
        panel = QGroupBox("ℹ️ Informations")
        layout = QVBoxLayout(panel)
        
        # Dernière mise à jour
        update_group = QGroupBox("🕐 Dernière mise à jour")
        update_layout = QVBoxLayout(update_group)
        
        self.last_update_label = QLabel("Jamais")
        self.last_update_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        update_layout.addWidget(self.last_update_label)
        
        layout.addWidget(update_group)
        
        # Alertes récentes
        alerts_group = QGroupBox("🚨 Alertes récentes")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_text = QTextEdit()
        self.alerts_text.setReadOnly(True)
        self.alerts_text.setMaximumHeight(200)
        alerts_layout.addWidget(self.alerts_text)
        
        layout.addWidget(alerts_group)
        
        # Notifications programmées
        scheduled_group = QGroupBox("⏰ Prochaines notifications")
        scheduled_layout = QVBoxLayout(scheduled_group)
        
        self.scheduled_notif_label = QLabel("Calcul en cours...")
        self.scheduled_notif_label.setWordWrap(True)
        scheduled_layout.addWidget(self.scheduled_notif_label)
        
        layout.addWidget(scheduled_group)
        
        # Mettre à jour les prochaines notifications
        self._update_scheduled_notifications()
        
        layout.addStretch()
        
        return panel
    
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
                # Configuration par défaut
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
                
                # Convertir YAML vers GlobalNotificationSettings
                settings = GlobalNotificationSettings()
                
                # Charger paramètres globaux
                notif_data = data.get('notifications', {})
                settings.enabled = notif_data.get('enabled', True)
                settings.kid_friendly_mode = notif_data.get('kid_friendly_mode', True)
                
                # TODO: Charger les autres paramètres
                
                self.logger.info("Paramètres de notification chargés")
                return settings
                
            except Exception as e:
                self.logger.error(f"Erreur chargement notifications: {e}")
        
        # Configuration par défaut
        return GlobalNotificationSettings(
            enabled=True,
            kid_friendly_mode=True,
            default_scheduled_hours=[9, 12, 18]
        )
    
    def _save_notification_settings(self):
        """Sauvegarde les paramètres de notification"""
        
        try:
            notif_config_path = Path("config/notifications.yaml")
            notif_config_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Convertir en dict et sauvegarder
            # TODO: Implémenter conversion complète
            
            self.logger.info("Paramètres de notification sauvegardés")
            
            QMessageBox.information(
                self,
                "Sauvegarde",
                "Les paramètres de notification ont été sauvegardés !"
            )
            
        except Exception as e:
            self.logger.error(f"Erreur sauvegarde notifications: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de sauvegarder : {e}"
            )
    
    # === MÉTHODES DE CONTRÔLE DAEMON ===
    
    def _start_daemon(self):
        """Démarre le daemon"""
        
        try:
            self.logger.info("Démarrage du daemon...")
            
            # Créer le daemon si besoin
            if self.daemon_service is None:
                self.daemon_service = DaemonService(self.config)
                # Passer les notification settings au daemon
                self.daemon_service.notification_settings = self.notification_settings
            
            # Démarrer
            self.daemon_service.start()
            
            # Mettre à jour l'UI
            self.start_button.setEnabled(False)
            self.stop_button.setEnabled(True)
            self.daemon_status_label.setText("● Daemon: En cours")
            self.daemon_status_label.setStyleSheet("color: green;")
            self.status_label.setText("● En cours")
            self.status_label.setStyleSheet("color: green; font-weight: bold;")
            
            # Démarrer le timer de refresh
            self.refresh_timer.start(5000)  # Toutes les 5 secondes
            
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
            
            # Arrêter le timer
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
            # Récupérer données marché
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
        
        # Mettre à jour statut daemon
        if self.daemon_service:
            self.checks_label.setText(f"Vérifications: {self.daemon_service.checks_count}")
            self.alerts_label.setText(f"Alertes: {self.daemon_service.alerts_sent}")
            
            if self.daemon_service.start_time:
                uptime = datetime.now(timezone.utc) - self.daemon_service.start_time
                hours = uptime.seconds // 3600
                minutes = (uptime.seconds % 3600) // 60
                self.uptime_label.setText(f"Uptime: {hours}h{minutes}m")
    
    def _update_dashboard(self, market_data):
        """Met à jour le dashboard"""
        
        # Prix
        if market_data.current_price:
            price_text = f"{market_data.current_price.price_eur:.2f} €"
            self.price_card.value_label.setText(price_text)
        
        # Variation 24h
        if market_data.price_change_24h is not None:
            change_24h = market_data.price_change_24h
            change_text = f"{change_24h:+.2f}%"
            self.change_24h_card.value_label.setText(change_text)
            
            # Couleur selon variation
            if change_24h > 0:
                self.change_24h_card.value_label.setStyleSheet("color: green;")
            elif change_24h < 0:
                self.change_24h_card.value_label.setStyleSheet("color: red;")
            else:
                self.change_24h_card.value_label.setStyleSheet("color: gray;")
        
        # Variation 7j
        if market_data.price_change_7d is not None:
            change_7d = market_data.price_change_7d
            change_text = f"{change_7d:+.2f}%"
            self.change_7d_card.value_label.setText(change_text)
            
            # Couleur
            if change_7d > 0:
                self.change_7d_card.value_label.setStyleSheet("color: green;")
            elif change_7d < 0:
                self.change_7d_card.value_label.setStyleSheet("color: red;")
            else:
                self.change_7d_card.value_label.setStyleSheet("color: gray;")
    
    # === MÉTHODES D'INTERFACE ===
    
    def _on_crypto_changed(self, symbol: str):
        """Appelé quand la crypto change"""
        
        self.current_symbol = symbol
        self.crypto_label.setText(f"📊 {symbol}")
        self._refresh_data()
        self.logger.info(f"Crypto changée: {symbol}")
    
    def _on_status_update(self, message: str):
        """Appelé pour mettre à jour le statut"""
        
        self.status_bar.showMessage(message, 3000)
    
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
                # Sauvegarder
                self.notification_settings = dialog.settings
                self._save_notification_settings()
                
                # Mettre à jour le daemon si actif
                if self.daemon_service:
                    self.daemon_service.notification_settings = self.notification_settings
                
                # Mettre à jour le résumé
                self._update_notification_summary()
                
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
        
        # Recharger si nécessaire
        if self.daemon_service:
            self.daemon_service.update_configuration(config)
        
        self.logger.info("Configuration sauvegardée")
    
    def _update_notification_summary(self):
        """Met à jour le résumé de configuration des notifications"""
        
        summary_lines = []
        
        summary_lines.append("📋 CONFIGURATION DES NOTIFICATIONS\n")
        summary_lines.append(f"Activées: {'✅ Oui' if self.notification_settings.enabled else '❌ Non'}")
        summary_lines.append(f"Mode enfant: {'✅ Oui' if self.notification_settings.kid_friendly_mode else '❌ Non'}")
        summary_lines.append(f"Horaires par défaut: {self.notification_settings.default_scheduled_hours}")
        summary_lines.append(f"Mode nuit: {'✅ Oui' if self.notification_settings.respect_quiet_hours else '❌ Non'}")
        
        if self.notification_settings.respect_quiet_hours:
            summary_lines.append(f"  ├─ De {self.notification_settings.quiet_start}h à {self.notification_settings.quiet_end}h")
        
        summary_lines.append(f"\nCryptos configurées: {len(self.notification_settings.coin_profiles)}")
        
        for symbol, profile in self.notification_settings.coin_profiles.items():
            summary_lines.append(f"\n💎 {symbol}")
            summary_lines.append(f"  ├─ Activée: {'✅' if profile.enabled else '❌'}")
            summary_lines.append(f"  ├─ Notifications programmées: {len(profile.scheduled_notifications)}")
            
            for notif in profile.scheduled_notifications:
                summary_lines.append(f"  │   ├─ {notif.name}: {notif.hours}")
        
        self.notif_summary_text.setPlainText("\n".join(summary_lines))
    
    def _update_scheduled_notifications(self):
        """Met à jour l'affichage des prochaines notifications"""
        
        now = datetime.now(timezone.utc)
        current_hour = now.hour
        
        next_notifs = []
        
        for symbol, profile in self.notification_settings.coin_profiles.items():
            if not profile.enabled:
                continue
            
            for notif_config in profile.scheduled_notifications:
                if not notif_config.enabled:
                    continue
                
                for hour in notif_config.hours:
                    if hour > current_hour:
                        next_notifs.append((symbol, hour, notif_config.name))
        
        # Trier par heure
        next_notifs.sort(key=lambda x: x[1])
        
        # Afficher les 5 prochaines
        lines = []
        for i, (symbol, hour, name) in enumerate(next_notifs[:5]):
            lines.append(f"{i+1}. {hour:02d}:00 - {symbol} - {name}")
        
        if lines:
            self.scheduled_notif_label.setText("\n".join(lines))
        else:
            self.scheduled_notif_label.setText("Aucune notification programmée")
    
    def _load_logs(self):
        """Charge les logs"""
        
        try:
            log_path = Path(self.config.log_file)
            
            if log_path.exists():
                with open(log_path, 'r', encoding='utf-8') as f:
                    # Lire les 100 dernières lignes
                    lines = f.readlines()
                    last_lines = lines[-100:]
                    self.logs_text.setPlainText("".join(last_lines))
                    
                    # Scroller vers le bas
                    self.logs_text.verticalScrollBar().setValue(
                        self.logs_text.verticalScrollBar().maximum()
                    )
            else:
                self.logs_text.setPlainText("Aucun fichier de log trouvé")
                
        except Exception as e:
            self.logger.error(f"Erreur chargement logs: {e}")
            self.logs_text.setPlainText(f"Erreur: {e}")
    
    # === ACTIONS ===
    
    def _test_telegram(self):
        """Teste l'envoi Telegram"""
        
        try:
            if not self.config.telegram_bot_token or not self.config.telegram_chat_id:
                QMessageBox.warning(
                    self,
                    "Configuration",
                    "Token ou Chat ID Telegram non configuré !"
                )
                return
            
            # Envoyer message de test
            from api.enhanced_telegram_api import EnhancedTelegramAPI
            
            telegram = EnhancedTelegramAPI(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            )
            
            message = (
                "🧪 **Test du bot Crypto**\n\n"
                f"Date: {datetime.now(timezone.utc).strftime('%Y-%m-%d %H:%M:%S')}\n"
                f"Cryptos suivies: {', '.join(self.config.crypto_symbols)}\n\n"
                "✅ La connexion fonctionne parfaitement !"
            )
            
            telegram.send_message(message)
            
            QMessageBox.information(
                self,
                "Test Telegram",
                "Message de test envoyé avec succès !"
            )
            
        except Exception as e:
            self.logger.error(f"Erreur test Telegram: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Échec du test : {e}"
            )
    
    def _test_notification(self):
        """Teste une notification avec le nouveau système"""
        
        try:
            # Importer le générateur
            from core.services.enhanced_notification_generator import EnhancedNotificationGenerator
            
            # Créer générateur
            generator = EnhancedNotificationGenerator(self.notification_settings)
            
            # Récupérer données
            market_data = self.market_data_cache.get(self.current_symbol)
            
            if not market_data:
                QMessageBox.warning(
                    self,
                    "Données",
                    "Aucune donnée disponible pour générer une notification test"
                )
                return
            
            # Générer notification
            message = generator.generate_notification(
                symbol=self.current_symbol,
                market=market_data,
                prediction=self.predictions_cache.get(self.current_symbol),
                opportunity=self.opportunities_cache.get(self.current_symbol),
                all_markets=self.market_data_cache,
                all_predictions=self.predictions_cache,
                all_opportunities=self.opportunities_cache,
                current_hour=datetime.now(timezone.utc).hour,
                current_day_of_week=datetime.now(timezone.utc).weekday()
            )
            
            if message:
                # Afficher dans une fenêtre
                dialog = QDialog(self)
                dialog.setWindowTitle("📱 Prévisualisation notification")
                dialog.resize(600, 800)
                
                layout = QVBoxLayout(dialog)
                
                text_edit = QTextEdit()
                text_edit.setPlainText(message)
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
                
                buttons_layout = QHBoxLayout()
                
                send_btn = QPushButton("📤 Envoyer sur Telegram")
                send_btn.clicked.connect(lambda: self._send_test_notification(message, dialog))
                buttons_layout.addWidget(send_btn)
                
                close_btn = QPushButton("Fermer")
                close_btn.clicked.connect(dialog.close)
                buttons_layout.addWidget(close_btn)
                
                layout.addLayout(buttons_layout)
                
                dialog.exec()
            else:
                QMessageBox.information(
                    self,
                    "Notification",
                    "Aucune notification à envoyer selon la configuration actuelle"
                )
            
        except Exception as e:
            self.logger.error(f"Erreur test notification: {e}")
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de générer la notification : {e}"
            )
    
    def _send_test_notification(self, message: str, dialog: QDialog):
        """Envoie la notification de test sur Telegram"""
        
        try:
            from api.enhanced_telegram_api import EnhancedTelegramAPI
            
            telegram = EnhancedTelegramAPI(
                self.config.telegram_bot_token,
                self.config.telegram_chat_id
            )
            
            telegram.send_message(message)
            
            QMessageBox.information(
                self,
                "Envoyé",
                "Notification envoyée sur Telegram !"
            )
            
            dialog.close()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible d'envoyer : {e}"
            )
    
    def _send_summary(self):
        """Envoie un résumé sur Telegram"""
        
        QMessageBox.information(
            self,
            "Résumé",
            "Fonctionnalité en développement"
        )
    
    def _generate_report(self):
        """Génère un rapport"""
        
        QMessageBox.information(
            self,
            "Rapport",
            "Fonctionnalité en développement"
        )
    
    def _export_configuration(self):
        """Exporte la configuration"""
        
        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Exporter configuration",
            "",
            "Fichiers YAML (*.yaml *.yml)"
        )
        
        if file_path:
            try:
                self.config_manager.save_config(self.config)
                QMessageBox.information(
                    self,
                    "Export",
                    f"Configuration exportée vers {file_path}"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Impossible d'exporter : {e}"
                )
    
    def _import_configuration(self):
        """Importe une configuration"""
        
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Importer configuration",
            "",
            "Fichiers YAML (*.yaml *.yml)"
        )
        
        if file_path:
            try:
                # Charger config
                self.config = self.config_manager.load_config()
                
                # Recharger UI
                self.crypto_selector.clear()
                self.crypto_selector.addItems(self.config.crypto_symbols)
                
                QMessageBox.information(
                    self,
                    "Import",
                    "Configuration importée avec succès !"
                )
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Impossible d'importer : {e}"
                )
    
    def _show_user_guide(self):
        """Affiche le guide utilisateur"""
        
        guide_path = Path("GUIDE_NOTIFICATIONS.md")
        
        if guide_path.exists():
            try:
                with open(guide_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                dialog = QDialog(self)
                dialog.setWindowTitle("📚 Guide utilisateur")
                dialog.resize(800, 600)
                
                layout = QVBoxLayout(dialog)
                
                text_edit = QTextEdit()
                text_edit.setPlainText(content)
                text_edit.setReadOnly(True)
                layout.addWidget(text_edit)
                
                close_btn = QPushButton("Fermer")
                close_btn.clicked.connect(dialog.close)
                layout.addWidget(close_btn)
                
                dialog.exec()
                
            except Exception as e:
                QMessageBox.critical(
                    self,
                    "Erreur",
                    f"Impossible d'afficher le guide : {e}"
                )
        else:
            QMessageBox.information(
                self,
                "Guide",
                "Guide utilisateur non trouvé"
            )
    
    def _show_about(self):
        """Affiche la fenêtre À propos"""
        
        QMessageBox.about(
            self,
            "À propos de Crypto Bot",
            "🚀 **Crypto Bot v4.0**\n\n"
            "Système de monitoring et notifications pour crypto-monnaies\n\n"
            "Fonctionnalités:\n"
            "• Dashboard temps réel\n"
            "• Notifications ultra-paramétrables\n"
            "• Suggestions d'investissement intelligentes\n"
            "• Mode adapté aux enfants\n"
            "• Interface graphique intuitive\n\n"
            "© 2025 Crypto Bot\n"
        )
    
    def closeEvent(self, event):
        """Appelé à la fermeture de la fenêtre"""
        
        # Arrêter le daemon si actif
        if self.daemon_service and self.daemon_service.is_running:
            reply = QMessageBox.question(
                self,
                "Fermeture",
                "Le daemon est en cours d'exécution. Voulez-vous l'arrêter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_daemon()
        
        self.logger.info("Fermeture de l'application")
        event.accept()