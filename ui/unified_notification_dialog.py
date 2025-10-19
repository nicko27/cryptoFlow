"""
Interface graphique pour appliquer la même configuration à toutes les cryptos
"""

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QGroupBox, QCheckBox, QSpinBox, QMessageBox, QTabWidget,
    QWidget, QTimeEdit, QListWidget, QListWidgetItem
)
from PyQt6.QtCore import Qt, QTime
from typing import List, Dict, Any
import yaml
from pathlib import Path


class UnifiedNotificationDialog(QDialog):
    """
    Dialog pour appliquer une configuration unique à toutes les cryptos
    """
    
    def __init__(self, config_path: str = "config/config.yaml", parent=None):
        super().__init__(parent)
        self.config_path = Path(config_path)
        self.config_data = None
        self.setWindowTitle("Configuration unifiée des notifications")
        self.setMinimumWidth(700)
        self.setMinimumHeight(600)
        
        self._load_config()
        self._init_ui()
    
    def _load_config(self):
        """Charge la configuration"""
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                self.config_data = yaml.safe_load(f) or {}
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Impossible de charger la configuration :\n{e}"
            )
            self.config_data = {}
    
    def _init_ui(self):
        """Initialise l'interface"""
        layout = QVBoxLayout(self)
        
        # Titre et description
        title = QLabel("📋 Configuration unifiée pour toutes les cryptos")
        title.setStyleSheet("font-size: 16px; font-weight: bold;")
        layout.addWidget(title)
        
        desc = QLabel(
            "Appliquez les mêmes paramètres de notification à toutes vos cryptos en un clic.\n"
            "Les modifications seront appliquées à : " + 
            ", ".join(self._get_crypto_symbols())
        )
        desc.setWordWrap(True)
        desc.setStyleSheet("color: #666; margin-bottom: 10px;")
        layout.addWidget(desc)
        
        # Tabs
        tabs = QTabWidget()
        tabs.addTab(self._create_hours_tab(), "⏰ Horaires")
        tabs.addTab(self._create_options_tab(), "⚙️ Options")
        tabs.addTab(self._create_presets_tab(), "🎨 Préréglages")
        layout.addWidget(tabs)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        btn_preview = QPushButton("👁️ Prévisualiser")
        btn_preview.clicked.connect(self._preview_changes)
        buttons_layout.addWidget(btn_preview)
        
        buttons_layout.addStretch()
        
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        btn_apply = QPushButton("✅ Appliquer")
        btn_apply.setStyleSheet("background-color: #4CAF50; color: white; font-weight: bold;")
        btn_apply.clicked.connect(self._apply_changes)
        buttons_layout.addWidget(btn_apply)
        
        layout.addLayout(buttons_layout)
    
    def _create_hours_tab(self) -> QWidget:
        """Crée l'onglet de configuration des horaires"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe horaires de notification
        notif_group = QGroupBox("📱 Horaires de notification")
        notif_layout = QVBoxLayout()
        
        notif_desc = QLabel(
            "Définissez les heures auxquelles vous souhaitez recevoir les notifications.\n"
            "Ces horaires seront appliqués à toutes vos cryptos."
        )
        notif_desc.setWordWrap(True)
        notif_layout.addWidget(notif_desc)
        
        # Liste des horaires
        self.notification_hours_list = QListWidget()
        self.notification_hours_list.setMaximumHeight(150)
        notif_layout.addWidget(self.notification_hours_list)
        
        # Boutons pour gérer les horaires
        hours_buttons = QHBoxLayout()
        
        self.hour_spin = QSpinBox()
        self.hour_spin.setRange(0, 23)
        self.hour_spin.setValue(9)
        self.hour_spin.setSuffix("h")
        hours_buttons.addWidget(self.hour_spin)
        
        btn_add_hour = QPushButton("➕ Ajouter")
        btn_add_hour.clicked.connect(self._add_notification_hour)
        hours_buttons.addWidget(btn_add_hour)
        
        btn_remove_hour = QPushButton("➖ Retirer")
        btn_remove_hour.clicked.connect(self._remove_notification_hour)
        hours_buttons.addWidget(btn_remove_hour)
        
        hours_buttons.addStretch()
        
        notif_layout.addLayout(hours_buttons)
        
        # Préréglages d'horaires
        presets_layout = QHBoxLayout()
        presets_layout.addWidget(QLabel("Préréglages :"))
        
        btn_morning = QPushButton("🌅 Matin (9h)")
        btn_morning.clicked.connect(lambda: self._set_preset_hours([9]))
        presets_layout.addWidget(btn_morning)
        
        btn_twice = QPushButton("📆 2x/jour (9h, 18h)")
        btn_twice.clicked.connect(lambda: self._set_preset_hours([9, 18]))
        presets_layout.addWidget(btn_twice)
        
        btn_three = QPushButton("📅 3x/jour (9h, 13h, 18h)")
        btn_three.clicked.connect(lambda: self._set_preset_hours([9, 13, 18]))
        presets_layout.addWidget(btn_three)
        
        presets_layout.addStretch()
        notif_layout.addLayout(presets_layout)
        
        notif_group.setLayout(notif_layout)
        layout.addWidget(notif_group)
        
        # Charger horaires actuels
        self._load_current_hours()
        
        layout.addStretch()
        return tab
    
    def _create_options_tab(self) -> QWidget:
        """Crée l'onglet des options de notification"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        # Groupe options de notification
        notif_group = QGroupBox("📱 Options de notification")
        notif_layout = QVBoxLayout()
        
        self.notif_checkboxes = {}
        
        options = [
            ("show_price", "💰 Afficher le prix", True),
            ("show_curves", "📈 Afficher les courbes", True),
            ("show_prediction", "🔮 Afficher la prédiction", True),
            ("show_opportunity", "⭐ Afficher le score d'opportunité", True),
            ("show_brokers", "🏦 Afficher les prix des courtiers", True),
            ("show_fear_greed", "😨 Afficher Fear & Greed", True),
            ("show_gain", "💸 Afficher les gains/pertes", True),
        ]
        
        for key, label, default in options:
            cb = QCheckBox(label)
            cb.setChecked(default)
            self.notif_checkboxes[key] = cb
            notif_layout.addWidget(cb)
        
        notif_group.setLayout(notif_layout)
        layout.addWidget(notif_group)
        
        # Groupe options de rapport
        report_group = QGroupBox("📊 Options de rapport")
        report_layout = QVBoxLayout()
        
        self.report_checkboxes = {}
        
        report_options = [
            ("show_price", "💰 Afficher le prix", True),
            ("show_volume", "📊 Afficher le volume", True),
            ("show_curves", "📈 Afficher les courbes", True),
            ("show_technicals", "🔧 Afficher les indicateurs techniques", True),
            ("show_prediction", "🔮 Afficher la prédiction", True),
            ("show_opportunity", "⭐ Afficher le score d'opportunité", True),
            ("show_brokers", "🏦 Afficher les prix des courtiers", True),
            ("show_fear_greed", "😨 Afficher Fear & Greed", True),
            ("show_gain", "💸 Afficher les gains/pertes", True),
        ]
        
        for key, label, default in report_options:
            cb = QCheckBox(label)
            cb.setChecked(default)
            self.report_checkboxes[key] = cb
            report_layout.addWidget(cb)
        
        report_group.setLayout(report_layout)
        layout.addWidget(report_group)
        
        layout.addStretch()
        return tab
    
    def _create_presets_tab(self) -> QWidget:
        """Crée l'onglet des préréglages"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        desc = QLabel(
            "Utilisez ces préréglages pour configurer rapidement toutes vos cryptos.\n"
            "Cliquez sur un préréglage pour l'appliquer immédiatement."
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Préréglage : Minimaliste
        minimal_group = QGroupBox("🎯 Minimaliste")
        minimal_layout = QVBoxLayout()
        minimal_layout.addWidget(QLabel("Notifications simples avec uniquement le prix et la prédiction"))
        btn_minimal = QPushButton("Appliquer le préréglage minimaliste")
        btn_minimal.clicked.connect(self._apply_minimal_preset)
        minimal_layout.addWidget(btn_minimal)
        minimal_group.setLayout(minimal_layout)
        layout.addWidget(minimal_group)
        
        # Préréglage : Complet
        full_group = QGroupBox("📊 Complet")
        full_layout = QVBoxLayout()
        full_layout.addWidget(QLabel("Toutes les options activées pour un maximum d'informations"))
        btn_full = QPushButton("Appliquer le préréglage complet")
        btn_full.clicked.connect(self._apply_full_preset)
        full_layout.addWidget(btn_full)
        full_group.setLayout(full_layout)
        layout.addWidget(full_group)
        
        # Préréglage : Trader
        trader_group = QGroupBox("💹 Trader")
        trader_layout = QVBoxLayout()
        trader_layout.addWidget(QLabel("Focus sur les indicateurs techniques et les opportunités"))
        btn_trader = QPushButton("Appliquer le préréglage trader")
        btn_trader.clicked.connect(self._apply_trader_preset)
        trader_layout.addWidget(btn_trader)
        trader_group.setLayout(trader_layout)
        layout.addWidget(trader_group)
        
        layout.addStretch()
        return tab
    
    def _get_crypto_symbols(self) -> List[str]:
        """Récupère la liste des cryptos"""
        crypto_cfg = self.config_data.get("crypto", {})
        symbols = crypto_cfg.get("symbols", ["BTC", "ETH", "SOL"])
        
        if isinstance(symbols, str):
            symbols = [s.strip().upper() for s in symbols.split(",")]
        elif isinstance(symbols, list):
            symbols = [str(s).strip().upper() for s in symbols]
        
        return symbols
    
    def _load_current_hours(self):
        """Charge les horaires actuels"""
        # Essayer de charger les horaires d'une crypto existante
        coins_cfg = self.config_data.get("coins", {})
        symbols = self._get_crypto_symbols()
        
        hours = [9, 18]  # Défaut
        
        if symbols and symbols[0] in coins_cfg:
            coin_hours = coins_cfg[symbols[0]].get("notification_hours", [9, 18])
            if isinstance(coin_hours, list):
                hours = coin_hours
        
        self.notification_hours_list.clear()
        for hour in sorted(hours):
            self.notification_hours_list.addItem(f"{hour}h")
    
    def _add_notification_hour(self):
        """Ajoute une heure de notification"""
        hour = self.hour_spin.value()
        
        # Vérifier si déjà dans la liste
        for i in range(self.notification_hours_list.count()):
            if self.notification_hours_list.item(i).text() == f"{hour}h":
                QMessageBox.warning(self, "Attention", f"L'heure {hour}h est déjà dans la liste")
                return
        
        self.notification_hours_list.addItem(f"{hour}h")
        self.notification_hours_list.sortItems()
    
    def _remove_notification_hour(self):
        """Retire une heure de notification"""
        current_item = self.notification_hours_list.currentItem()
        if current_item:
            self.notification_hours_list.takeItem(
                self.notification_hours_list.row(current_item)
            )
    
    def _set_preset_hours(self, hours: List[int]):
        """Définit des horaires préréglés"""
        self.notification_hours_list.clear()
        for hour in sorted(hours):
            self.notification_hours_list.addItem(f"{hour}h")
    
    def _get_selected_hours(self) -> List[int]:
        """Récupère les horaires sélectionnés"""
        hours = []
        for i in range(self.notification_hours_list.count()):
            text = self.notification_hours_list.item(i).text()
            hour = int(text.replace("h", ""))
            hours.append(hour)
        return sorted(hours)
    
    def _apply_minimal_preset(self):
        """Applique le préréglage minimaliste"""
        # Tout décocher sauf prix et prédiction
        for key, cb in self.notif_checkboxes.items():
            cb.setChecked(key in ["show_price", "show_prediction"])
        
        for key, cb in self.report_checkboxes.items():
            cb.setChecked(key in ["show_price", "show_prediction"])
        
        QMessageBox.information(self, "Préréglage", "Préréglage minimaliste appliqué")
    
    def _apply_full_preset(self):
        """Applique le préréglage complet"""
        # Tout cocher
        for cb in self.notif_checkboxes.values():
            cb.setChecked(True)
        
        for cb in self.report_checkboxes.values():
            cb.setChecked(True)
        
        QMessageBox.information(self, "Préréglage", "Préréglage complet appliqué")
    
    def _apply_trader_preset(self):
        """Applique le préréglage trader"""
        trader_options = ["show_price", "show_curves", "show_prediction", "show_opportunity", "show_technicals"]
        
        for key, cb in self.notif_checkboxes.items():
            cb.setChecked(key in trader_options)
        
        for key, cb in self.report_checkboxes.items():
            cb.setChecked(key in trader_options)
        
        QMessageBox.information(self, "Préréglage", "Préréglage trader appliqué")
    
    def _preview_changes(self):
        """Prévisualise les changements"""
        hours = self._get_selected_hours()
        symbols = self._get_crypto_symbols()
        
        message = f"Configuration qui sera appliquée à {len(symbols)} crypto(s) :\n\n"
        message += f"Cryptos concernées : {', '.join(symbols)}\n\n"
        message += f"Horaires de notification : {', '.join([f'{h}h' for h in hours])}\n\n"
        message += "Options de notification activées :\n"
        
        for key, cb in self.notif_checkboxes.items():
            if cb.isChecked():
                message += f"  ✓ {cb.text()}\n"
        
        QMessageBox.information(self, "Prévisualisation", message)
    
    def _apply_changes(self):
        """Applique les changements"""
        try:
            hours = self._get_selected_hours()
            
            if not hours:
                QMessageBox.warning(
                    self,
                    "Attention",
                    "Vous devez définir au moins un horaire de notification"
                )
                return
            
            symbols = self._get_crypto_symbols()
            
            # Confirmer
            reply = QMessageBox.question(
                self,
                "Confirmation",
                f"Appliquer cette configuration à {len(symbols)} crypto(s) ?\n\n"
                f"Cryptos : {', '.join(symbols)}\n"
                f"Horaires : {', '.join([f'{h}h' for h in hours])}",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply != QMessageBox.StandardButton.Yes:
                return
            
            # Appliquer les changements
            if "coins" not in self.config_data:
                self.config_data["coins"] = {}
            
            coins_cfg = self.config_data["coins"]
            
            for symbol in symbols:
                if symbol not in coins_cfg:
                    coins_cfg[symbol] = {}
                
                # Horaires
                coins_cfg[symbol]["notification_hours"] = hours
                coins_cfg[symbol]["report_hours"] = hours
                
                # Options de notification
                notif_options = {}
                for key, cb in self.notif_checkboxes.items():
                    notif_options[key] = cb.isChecked()
                coins_cfg[symbol]["notification_options"] = notif_options
                
                # Options de rapport
                report_options = {}
                for key, cb in self.report_checkboxes.items():
                    report_options[key] = cb.isChecked()
                coins_cfg[symbol]["report_options"] = report_options
            
            # Sauvegarder
            with open(self.config_path, 'w', encoding='utf-8') as f:
                yaml.dump(
                    self.config_data,
                    f,
                    default_flow_style=False,
                    allow_unicode=True,
                    sort_keys=False
                )
            
            QMessageBox.information(
                self,
                "Succès",
                f"✅ Configuration appliquée avec succès à {len(symbols)} crypto(s) !"
            )
            
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self,
                "Erreur",
                f"Erreur lors de l'application des changements :\n{e}"
            )


if __name__ == "__main__":
    from PyQt6.QtWidgets import QApplication
    import sys
    
    app = QApplication(sys.argv)
    dialog = UnifiedNotificationDialog()
    dialog.exec()
