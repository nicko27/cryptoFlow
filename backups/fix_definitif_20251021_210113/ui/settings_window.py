"""
PyQt Settings Dialog - Configuration complète du bot
FIXED: Problèmes 10, 18, 19 - Validation améliorée des heures et des paramètres
"""

import json
from dataclasses import replace
from typing import Optional, Callable, Dict, List, Any
from ui.unified_notification_dialog import UnifiedNotificationDialog
from PyQt6.QtCore import Qt
from PyQt6.QtWidgets import (
    QDialog,
    QVBoxLayout,
    QScrollArea,
    QWidget,
    QGroupBox,
    QGridLayout,
    QFormLayout,
    QLineEdit,
    QCheckBox,
    QDoubleSpinBox,
    QSpinBox,
    QLabel,
    QComboBox,
    QPushButton,
    QHBoxLayout,
    QMessageBox,
    QPlainTextEdit,
    QTabWidget,
)

from ui.crypto_manager_window import CryptoManagerWindow
from core.models import BotConfiguration


class SettingsDialog(QDialog):
    """Fenêtre de configuration basée sur PyQt."""

    def __init__(
        self,
        parent,
        config: BotConfiguration,
        on_save: Optional[Callable[[BotConfiguration], None]] = None,
    ):
        super().__init__(parent)

        self.setWindowTitle("⚙️ Configuration")
        self.resize(900, 720)

        self._original_config = config
        self._config = replace(config)
        self._on_save = on_save

        self._init_widgets()
        self._load_config(self._config)

    def _open_unified_config(self):
       dialog = UnifiedNotificationDialog("config/config.yaml", self)
       if dialog.exec() == QDialog.DialogCode.Accepted:
           self.config = self.config_manager.load_config()
           QMessageBox.information(self, "Succès", "Config appliquée !")

    def _init_widgets(self):
        self.main_layout = QVBoxLayout(self)

        scroll = QScrollArea(self)
        scroll.setWidgetResizable(True)
        self.main_layout.addWidget(scroll)

        container = QWidget()
        scroll.setWidget(container)
        self.content_layout = QVBoxLayout(container)
        self.content_layout.setAlignment(Qt.AlignmentFlag.AlignTop)

        # dictionnaires de widgets
        self._line_edits: Dict[str, QLineEdit] = {}
        self._check_boxes: Dict[str, QCheckBox] = {}
        self._double_spins: Dict[str, QDoubleSpinBox] = {}
        self._spin_boxes: Dict[str, QSpinBox] = {}
        self._combo_boxes: Dict[str, QComboBox] = {}
        self._text_edits: Dict[str, QPlainTextEdit] = {}
        self._coin_low_spins: Dict[str, QDoubleSpinBox] = {}
        self._coin_high_spins: Dict[str, QDoubleSpinBox] = {}

        self._create_telegram_section()
        self._create_crypto_section()
        self._create_alert_section()
        self._create_database_section()
        self._create_buttons()

    def _create_telegram_section(self):
        """Crée la section Telegram"""
        group = QGroupBox("📱 Configuration Telegram")
        layout = QFormLayout(group)

        self._line_edits["telegram_token"] = QLineEdit()
        self._line_edits["telegram_token"].setEchoMode(QLineEdit.EchoMode.Password)
        layout.addRow("Bot Token:", self._line_edits["telegram_token"])

        self._line_edits["telegram_chat"] = QLineEdit()
        layout.addRow("Chat ID:", self._line_edits["telegram_chat"])

        # FIXED: Problème 19 - Validation du délai message avec min/max
        self._spin_boxes["telegram_delay"] = QSpinBox()
        self._spin_boxes["telegram_delay"].setMinimum(1)  # Minimum 1 seconde
        self._spin_boxes["telegram_delay"].setMaximum(60)  # Maximum 60 secondes
        self._spin_boxes["telegram_delay"].setValue(2)
        self._spin_boxes["telegram_delay"].setSuffix(" s")
        layout.addRow("Délai entre messages:", self._spin_boxes["telegram_delay"])

        self._check_boxes["telegram_show_prices"] = QCheckBox()
        layout.addRow("Afficher prix:", self._check_boxes["telegram_show_prices"])

        self.content_layout.addWidget(group)

    def _create_crypto_section(self):
        """Crée la section des cryptos"""
        group = QGroupBox("💰 Cryptomonnaies")
        layout = QFormLayout(group)

        self._line_edits["crypto_symbols"] = QLineEdit()
        self._line_edits["crypto_symbols"].setPlaceholderText("Ex: BTC, ETH, SOL")
        layout.addRow("Symboles (séparés par virgule):", self._line_edits["crypto_symbols"])

        self._spin_boxes["check_interval"] = QSpinBox()
        self._spin_boxes["check_interval"].setMinimum(60)
        self._spin_boxes["check_interval"].setMaximum(3600)
        self._spin_boxes["check_interval"].setSuffix(" s")
        layout.addRow("Intervalle de vérification:", self._spin_boxes["check_interval"])

        self.content_layout.addWidget(group)

    def _create_alert_section(self):
        """Crée la section des alertes"""
        group = QGroupBox("🚨 Alertes")
        layout = QFormLayout(group)

        self._double_spins["price_drop"] = QDoubleSpinBox()
        self._double_spins["price_drop"].setMinimum(0.1)
        self._double_spins["price_drop"].setMaximum(50.0)
        self._double_spins["price_drop"].setSuffix(" %")
        layout.addRow("Seuil baisse de prix:", self._double_spins["price_drop"])

        self._double_spins["price_spike"] = QDoubleSpinBox()
        self._double_spins["price_spike"].setMinimum(0.1)
        self._double_spins["price_spike"].setMaximum(50.0)
        self._double_spins["price_spike"].setSuffix(" %")
        layout.addRow("Seuil hausse de prix:", self._double_spins["price_spike"])

        self._spin_boxes["rsi_oversold"] = QSpinBox()
        self._spin_boxes["rsi_oversold"].setMinimum(10)
        self._spin_boxes["rsi_oversold"].setMaximum(50)
        layout.addRow("RSI survente:", self._spin_boxes["rsi_oversold"])

        self._spin_boxes["rsi_overbought"] = QSpinBox()
        self._spin_boxes["rsi_overbought"].setMinimum(50)
        self._spin_boxes["rsi_overbought"].setMaximum(90)
        layout.addRow("RSI surachat:", self._spin_boxes["rsi_overbought"])

        self.content_layout.addWidget(group)

    def _create_database_section(self):
        """Crée la section base de données"""
        group = QGroupBox("💾 Base de données")
        layout = QFormLayout(group)

        self._line_edits["database_path"] = QLineEdit()
        layout.addRow("Chemin:", self._line_edits["database_path"])

        self._spin_boxes["keep_history"] = QSpinBox()
        self._spin_boxes["keep_history"].setMinimum(1)
        self._spin_boxes["keep_history"].setMaximum(365)
        self._spin_boxes["keep_history"].setSuffix(" jours")
        layout.addRow("Garder historique:", self._spin_boxes["keep_history"])

        self._line_edits["log_file"] = QLineEdit()
        layout.addRow("Fichier log:", self._line_edits["log_file"])

        self._combo_boxes["log_level"] = QComboBox()
        self._combo_boxes["log_level"].addItems(["DEBUG", "INFO", "WARNING", "ERROR"])
        layout.addRow("Niveau de log:", self._combo_boxes["log_level"])

        self.content_layout.addWidget(group)

    def _create_buttons(self):
        """Crée les boutons d'action"""
        button_layout = QHBoxLayout()

        btn = QPushButton("📋 Config unifiée pour toutes les cryptos")
        btn.clicked.connect(self._open_unified_config)
        # Ajoutez ce bouton dans votre layout


        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self._on_save_clicked)
        button_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(cancel_btn)

        self.main_layout.addLayout(button_layout)

    def _load_config(self, cfg: BotConfiguration):
        """Charge la configuration dans les widgets"""
        
        self._line_edits["telegram_token"].setText(cfg.telegram_bot_token)
        self._line_edits["telegram_chat"].setText(cfg.telegram_chat_id)
        self._spin_boxes["telegram_delay"].setValue(cfg.telegram_message_delay)
        self._check_boxes["telegram_show_prices"].setChecked(cfg.telegram_show_prices)

        self._line_edits["crypto_symbols"].setText(", ".join(cfg.crypto_symbols))
        self._spin_boxes["check_interval"].setValue(cfg.check_interval_seconds)

        self._double_spins["price_drop"].setValue(cfg.price_drop_threshold)
        self._double_spins["price_spike"].setValue(cfg.price_spike_threshold)
        self._spin_boxes["rsi_oversold"].setValue(cfg.rsi_oversold)
        self._spin_boxes["rsi_overbought"].setValue(cfg.rsi_overbought)

        self._line_edits["database_path"].setText(cfg.database_path)
        self._spin_boxes["keep_history"].setValue(cfg.keep_history_days)
        self._line_edits["log_file"].setText(cfg.log_file)
        
        if cfg.log_level in ["DEBUG", "INFO", "WARNING", "ERROR"]:
            self._combo_boxes["log_level"].setCurrentText(cfg.log_level)

    def _open_crypto_manager(self):
        """Ouvre le gestionnaire de cryptos"""
        dialog = CryptoManagerWindow(self.config, self)
        if dialog.exec():
            # Mettre à jour l'affichage
            self._line_edits["crypto_symbols"].setText(", ".join(self.config.crypto_symbols))
            QMessageBox.information(
                self,
                "Succès",
                "Configuration des cryptos mise à jour"
            )
    
    def _on_save_clicked(self):
        """Gère la sauvegarde de la configuration"""
        
        try:
            # Validation et récupération des valeurs
            telegram_token = self._line_edits["telegram_token"].text().strip()
            telegram_chat = self._line_edits["telegram_chat"].text().strip()
            
            if not telegram_token or not telegram_chat:
                raise ValueError("Le token Telegram et le Chat ID sont obligatoires")
            
            # FIXED: Problème 19 - Validation du délai
            telegram_delay = self._spin_boxes["telegram_delay"].value()
            if telegram_delay < 1 or telegram_delay > 60:
                raise ValueError("Le délai entre messages doit être entre 1 et 60 secondes")
            
            # Cryptos
            crypto_text = self._line_edits["crypto_symbols"].text().strip()
            if not crypto_text:
                raise ValueError("Au moins une cryptomonnaie doit être spécifiée")
            
            crypto_symbols = [s.strip().upper() for s in crypto_text.split(",") if s.strip()]
            if not crypto_symbols:
                raise ValueError("Format invalide pour les symboles de crypto")
            
            # Base de données
            database_path = self._line_edits["database_path"].text().strip()
            if not database_path:
                raise ValueError("Le chemin de la base de données est obligatoire")
            
            # FIXED: Problème 18 - Validation du chemin de fichier
            if not database_path.endswith('.db'):
                database_path += '.db'
            
            keep_history = self._spin_boxes["keep_history"].value()
            if keep_history < 1:
                raise ValueError("L'historique doit être conservé au moins 1 jour")
            
            log_file = self._line_edits["log_file"].text().strip()
            if not log_file:
                raise ValueError("Le fichier de log est obligatoire")
            
            # FIXED: Problème 18 - Validation du fichier log
            if not log_file.endswith('.log'):
                log_file += '.log'
            
            log_level = self._combo_boxes["log_level"].currentText()

            # Mettre à jour la configuration
            cfg = self._config
            cfg.telegram_bot_token = telegram_token
            cfg.telegram_chat_id = telegram_chat
            cfg.telegram_message_delay = telegram_delay
            cfg.telegram_show_prices = self._check_boxes["telegram_show_prices"].isChecked()

            cfg.crypto_symbols = crypto_symbols
            cfg.check_interval_seconds = self._spin_boxes["check_interval"].value()

            cfg.price_drop_threshold = self._double_spins["price_drop"].value()
            cfg.price_spike_threshold = self._double_spins["price_spike"].value()
            cfg.rsi_oversold = self._spin_boxes["rsi_oversold"].value()
            cfg.rsi_overbought = self._spin_boxes["rsi_overbought"].value()

            cfg.database_path = database_path
            cfg.keep_history_days = keep_history
            cfg.log_file = log_file
            cfg.log_level = log_level

            if self._on_save:
                self._on_save(cfg)

            self.accept()
            
        except ValueError as err:
            QMessageBox.critical(self, "Erreur de validation", str(err))
        except Exception as err:
            QMessageBox.critical(self, "Erreur", f"Erreur inattendue : {err}")

    @staticmethod
    def _parse_hours_list(text: str, label: str) -> List[int]:
        """
        Parse une liste d'heures depuis une chaîne (0-23)
        """
        if not text or not text.strip():
            return []
        
        result: List[int] = []
        normalized = text.replace(";", ",")
        
        for part in normalized.split(","):
            part = part.strip()
            if not part:
                continue
            
            # Ne plus accepter les signes +/-
            if not part.isdigit():
                raise ValueError(
                    f"{label} doit contenir uniquement des nombres entiers positifs (0-23)"
                )
            
            value = int(part)
            
            # Validation stricte 0-23
            if value < 0 or value > 23:
                raise ValueError(f"{label} : chaque heure doit être entre 0 et 23 (reçu: {value})")
            
            if value in result:
                raise ValueError(f"{label} : l'heure {value} est dupliquée")
            
            result.append(value)
        
        # Trier les heures
        result.sort()
        return result
