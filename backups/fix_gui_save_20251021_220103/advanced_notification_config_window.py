"""
Interface de configuration avancée des notifications
Interface ultra-intuitive adaptée pour être comprise par un enfant
"""

import copy

from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QCheckBox, QSpinBox, QLineEdit, QTextEdit, QGroupBox,
    QTabWidget, QScrollArea, QComboBox, QSlider, QFrame,
    QTimeEdit, QListWidget, QListWidgetItem, QMessageBox,
    QDialog, QFormLayout, QColorDialog
)
from PyQt6.QtCore import Qt, QTime
from PyQt6.QtGui import QFont, QColor, QPalette
from typing import Dict, List, Optional, Any

from core.models.notification_config import (
    ScheduledNotificationConfig,
    CoinNotificationProfile,
    GlobalNotificationSettings,
    PriceBlock, PredictionBlock, OpportunityBlock,
    ChartBlock, BrokersBlock, FearGreedBlock,
    GainLossBlock, InvestmentSuggestionBlock, GlossaryBlock,
)


class SimpleNotificationScheduleWidget(QWidget):
    """Widget simplifié pour configurer les horaires de notification"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.selected_hours = [9, 12, 18]  # Horaires par défaut
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre avec grand emoji
        title = QLabel("🕐 Quand veux-tu recevoir tes notifications ?")
        title_font = QFont()
        title_font.setPointSize(14)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Description simple
        desc = QLabel("Clique sur les heures où tu veux être informé :")
        layout.addWidget(desc)
        
        # Grille de 24 boutons (1 par heure)
        hours_container = QWidget()
        hours_layout = QHBoxLayout(hours_container)
        hours_layout.setSpacing(5)
        
        self.hour_buttons = {}
        
        # Créer les boutons par tranches de 6h
        for row in range(4):  # 4 lignes de 6 heures
            row_widget = QWidget()
            row_layout = QHBoxLayout(row_widget)
            row_layout.setSpacing(3)
            
            for col in range(6):
                hour = row * 6 + col
                btn = QPushButton(f"{hour}h")
                btn.setCheckable(True)
                btn.setMinimumWidth(50)
                btn.setMinimumHeight(40)
                
                # Colorer selon moment de la journée
                if 7 <= hour < 12:
                    btn.setStyleSheet("QPushButton { background-color: #FFE4B5; }")  # Matin
                elif 12 <= hour < 18:
                    btn.setStyleSheet("QPushButton { background-color: #87CEEB; }")  # Après-midi
                elif 18 <= hour < 23:
                    btn.setStyleSheet("QPushButton { background-color: #FFB6C1; }")  # Soir
                else:
                    btn.setStyleSheet("QPushButton { background-color: #4B0082; color: white; }")  # Nuit
                
                # Pré-sélectionner les heures par défaut
                if hour in self.selected_hours:
                    btn.setChecked(True)
                    btn.setStyleSheet(btn.styleSheet() + " QPushButton:checked { border: 3px solid green; font-weight: bold; }")
                
                btn.clicked.connect(lambda checked, h=hour: self._toggle_hour(h))
                self.hour_buttons[hour] = btn
                row_layout.addWidget(btn)
            
            layout.addWidget(row_widget)
        
        # Légende
        legend_layout = QHBoxLayout()
        legend_layout.addWidget(QLabel("🌅 Matin (7h-11h)"))
        legend_layout.addWidget(QLabel("☀️ Après-midi (12h-17h)"))
        legend_layout.addWidget(QLabel("🌆 Soir (18h-22h)"))
        legend_layout.addWidget(QLabel("🌙 Nuit (23h-6h)"))
        layout.addLayout(legend_layout)
        
        # Boutons rapides
        quick_layout = QHBoxLayout()
        quick_layout.addWidget(QLabel("Raccourcis :"))
        
        btn_morning = QPushButton("☀️ Matin (9h)")
        btn_morning.clicked.connect(lambda: self.set_hours([9]))
        quick_layout.addWidget(btn_morning)
        
        btn_standard = QPushButton("⏰ Standard (9h, 12h, 18h)")
        btn_standard.clicked.connect(lambda: self.set_hours([9, 12, 18]))
        quick_layout.addWidget(btn_standard)
        
        btn_frequent = QPushButton("📱 Fréquent (9h, 12h, 15h, 18h, 21h)")
        btn_frequent.clicked.connect(lambda: self.set_hours([9, 12, 15, 18, 21]))
        quick_layout.addWidget(btn_frequent)
        
        btn_clear = QPushButton("❌ Tout effacer")
        btn_clear.clicked.connect(lambda: self.set_hours([]))
        quick_layout.addWidget(btn_clear)
        
        layout.addLayout(quick_layout)
        
        # Compteur
        self.counter_label = QLabel()
        self._update_counter()
        layout.addWidget(self.counter_label)
    
    def _toggle_hour(self, hour: int):
        """Active/désactive une heure"""
        if hour in self.selected_hours:
            self.selected_hours.remove(hour)
        else:
            self.selected_hours.append(hour)
        self.selected_hours.sort()
        self._update_counter()
    
    def set_hours(self, hours: List[int]):
        """Définit les heures sélectionnées"""
        self.selected_hours = sorted(hours)
        # Mettre à jour l'affichage
        for hour, btn in self.hour_buttons.items():
            btn.setChecked(hour in hours)
        self._update_counter()
    
    def get_hours(self) -> List[int]:
        """Retourne les heures sélectionnées"""
        return self.selected_hours
    
    def _update_counter(self):
        """Met à jour le compteur de notifications"""
        count = len(self.selected_hours)
        if count == 0:
            text = "⚠️ Aucune notification ne sera envoyée"
            color = "red"
        elif count <= 3:
            text = f"✅ {count} notification(s) par jour - Parfait !"
            color = "green"
        elif count <= 6:
            text = f"⚠️ {count} notifications par jour - Peut-être un peu beaucoup ?"
            color = "orange"
        else:
            text = f"❗ {count} notifications par jour - Attention, ça fait beaucoup !"
            color = "red"
        
        self.counter_label.setText(text)
        self.counter_label.setStyleSheet(f"color: {color}; font-weight: bold; font-size: 12pt;")


class BlockConfigWidget(QGroupBox):
    """Widget générique pour configurer un bloc de notification"""
    
    def __init__(self, block_name: str, block_icon: str, parent=None):
        super().__init__(f"{block_icon} {block_name}", parent)
        self.block_name = block_name
        self.enabled_checkbox = None
        self.options = {}
        
    def add_enable_checkbox(self, default: bool = True):
        """Ajoute une case à cocher pour activer/désactiver le bloc"""
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout()
            self.setLayout(layout)
        
        self.enabled_checkbox = QCheckBox("✅ Afficher ce bloc dans les notifications")
        self.enabled_checkbox.setChecked(default)
        self.enabled_checkbox.setStyleSheet("font-weight: bold; font-size: 11pt;")
        layout.addWidget(self.enabled_checkbox)
        
        # Ligne de séparation
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Sunken)
        layout.addWidget(line)
    
    def add_checkbox_option(self, key: str, label: str, tooltip: str = "", default: bool = True):
        """Ajoute une option checkbox"""
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout()
            self.setLayout(layout)
        
        checkbox = QCheckBox(label)
        checkbox.setChecked(default)
        if tooltip:
            checkbox.setToolTip(tooltip)
        
        self.options[key] = checkbox
        layout.addWidget(checkbox)
    
    def add_slider_option(self, key: str, label: str, min_val: int, max_val: int, default: int, tooltip: str = ""):
        """Ajoute une option slider avec valeur"""
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout()
            self.setLayout(layout)
        
        container = QWidget()
        h_layout = QHBoxLayout(container)
        
        label_widget = QLabel(label)
        h_layout.addWidget(label_widget)
        
        slider = QSlider(Qt.Orientation.Horizontal)
        slider.setMinimum(min_val)
        slider.setMaximum(max_val)
        slider.setValue(default)
        if tooltip:
            slider.setToolTip(tooltip)
        
        value_label = QLabel(str(default))
        value_label.setMinimumWidth(30)
        
        slider.valueChanged.connect(lambda v: value_label.setText(str(v)))
        
        h_layout.addWidget(slider)
        h_layout.addWidget(value_label)
        
        self.options[key] = slider
        layout.addWidget(container)
    
    def add_text_option(self, key: str, label: str, default: str = "", multiline: bool = False, tooltip: str = ""):
        """Ajoute une option texte"""
        layout = self.layout()
        if layout is None:
            layout = QVBoxLayout()
            self.setLayout(layout)
        
        layout.addWidget(QLabel(label))
        
        if multiline:
            text_widget = QTextEdit()
            text_widget.setPlainText(default)
            text_widget.setMaximumHeight(80)
        else:
            text_widget = QLineEdit()
            text_widget.setText(default)
        
        if tooltip:
            text_widget.setToolTip(tooltip)
        
        self.options[key] = text_widget
        layout.addWidget(text_widget)
    
    def is_enabled(self) -> bool:
        """Retourne si le bloc est activé"""
        if self.enabled_checkbox:
            return self.enabled_checkbox.isChecked()
        return True
    
    def set_enabled(self, enabled: bool):
        """Active/désactive la case principale du bloc"""
        if self.enabled_checkbox:
            self.enabled_checkbox.setChecked(bool(enabled))
    
    def set_option_value(self, key: str, value: Any):
        """Affecte une valeur à une option si le widget associé existe"""
        if key not in self.options or value is None:
            return
        
        widget = self.options[key]
        if isinstance(widget, QCheckBox):
            widget.setChecked(bool(value))
        elif isinstance(widget, QSlider):
            widget.setValue(int(value))
        elif isinstance(widget, QLineEdit):
            widget.setText(str(value))
        elif isinstance(widget, QTextEdit):
            widget.setPlainText(str(value))

    def get_option_value(self, key: str):
        """Récupère la valeur d'une option"""
        widget = self.options.get(key)
        if isinstance(widget, QCheckBox):
            return widget.isChecked()
        elif isinstance(widget, QSlider):
            return widget.value()
        elif isinstance(widget, QLineEdit):
            return widget.text()
        elif isinstance(widget, QTextEdit):
            return widget.toPlainText()
        return None


class SimpleCoinNotificationEditor(QWidget):
    """Éditeur simplifié de notification pour une crypto"""
    
    def __init__(self, symbol: str, parent=None):
        super().__init__(parent)
        self.symbol = symbol
        self.block_widgets = {}
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # En-tête avec nom de la crypto
        header = QLabel(f"💎 Configuration des notifications pour {self.symbol}")
        header_font = QFont()
        header_font.setPointSize(16)
        header_font.setBold(True)
        header.setFont(header_font)
        layout.addWidget(header)
        
        # Description
        desc = QLabel(
            "Personnalise ce qui sera affiché dans chaque notification pour cette crypto. "
            "Active ou désactive les blocs, et configure leur contenu !"
        )
        desc.setWordWrap(True)
        layout.addWidget(desc)
        
        # Zone scrollable pour les blocs
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        
        # Bloc Prix
        price_block = self._create_price_block()
        scroll_layout.addWidget(price_block)
        self.block_widgets["price"] = price_block
        
        # Bloc Graphique
        chart_block = self._create_chart_block()
        scroll_layout.addWidget(chart_block)
        self.block_widgets["chart"] = chart_block
        
        # Bloc Prédiction
        prediction_block = self._create_prediction_block()
        scroll_layout.addWidget(prediction_block)
        self.block_widgets["prediction"] = prediction_block
        
        # Bloc Opportunité
        opportunity_block = self._create_opportunity_block()
        scroll_layout.addWidget(opportunity_block)
        self.block_widgets["opportunity"] = opportunity_block
        
        # Bloc Courtiers
        brokers_block = self._create_brokers_block()
        scroll_layout.addWidget(brokers_block)
        self.block_widgets["brokers"] = brokers_block
        
        # Bloc Fear & Greed
        fg_block = self._create_fear_greed_block()
        scroll_layout.addWidget(fg_block)
        self.block_widgets["fear_greed"] = fg_block
        
        # Bloc Gain/Perte
        gain_block = self._create_gain_loss_block()
        scroll_layout.addWidget(gain_block)
        self.block_widgets["gain_loss"] = gain_block
        
        # 🆕 Bloc Suggestions d'investissement
        suggestions_block = self._create_investment_suggestions_block()
        scroll_layout.addWidget(suggestions_block)
        self.block_widgets["investment_suggestions"] = suggestions_block
        
        # Bloc Glossaire
        glossary_block = self._create_glossary_block()
        scroll_layout.addWidget(glossary_block)
        self.block_widgets["glossary"] = glossary_block
        
        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
    
    def load_from_profile(self, profile: CoinNotificationProfile):
        """Charge les paramètres existants pour ce profil."""
        if profile and profile.scheduled_notifications:
            base_config = profile.scheduled_notifications[0]
        elif profile and profile.default_config:
            base_config = profile.default_config
        else:
            base_config = ScheduledNotificationConfig()
        
        # Bloc prix
        price_widget = self.block_widgets.get("price")
        if price_widget:
            price_widget.set_enabled(base_config.price_block.enabled)
            price_widget.set_option_value("show_price_eur", base_config.price_block.show_price_eur)
            price_widget.set_option_value("show_variation_24h", base_config.price_block.show_variation_24h)
            price_widget.set_option_value("show_variation_7d", base_config.price_block.show_variation_7d)
            price_widget.set_option_value("show_volume", base_config.price_block.show_volume)
            price_widget.set_option_value("add_price_comment", base_config.price_block.add_price_comment)
            price_widget.set_option_value("message_prix_monte", base_config.price_block.message_prix_monte)
        
        chart_widget = self.block_widgets.get("chart")
        if chart_widget:
            chart_widget.set_enabled(base_config.chart_block.enabled)
            chart_widget.set_option_value("show_sparklines", base_config.chart_block.show_sparklines)
            chart_widget.set_option_value("send_full_chart", base_config.chart_block.send_full_chart)
            timeframes_text = ", ".join(str(tf) for tf in base_config.chart_block.timeframes)
            chart_widget.set_option_value("timeframes", timeframes_text)
        
        prediction_widget = self.block_widgets.get("prediction")
        if prediction_widget:
            prediction_widget.set_enabled(base_config.prediction_block.enabled)
            prediction_widget.set_option_value("show_prediction_type", base_config.prediction_block.show_prediction_type)
            prediction_widget.set_option_value("show_confidence", base_config.prediction_block.show_confidence)
            prediction_widget.set_option_value("show_explanation", base_config.prediction_block.show_explanation)
            prediction_widget.set_option_value("min_confidence", base_config.prediction_block.min_confidence_to_show)
        
        opportunity_widget = self.block_widgets.get("opportunity")
        if opportunity_widget:
            opportunity_widget.set_enabled(base_config.opportunity_block.enabled)
            opportunity_widget.set_option_value("show_score", base_config.opportunity_block.show_score)
            opportunity_widget.set_option_value("show_recommendation", base_config.opportunity_block.show_recommendation)
            opportunity_widget.set_option_value("show_reasons", base_config.opportunity_block.show_reasons)
            opportunity_widget.set_option_value("min_score", base_config.opportunity_block.min_score_to_show)
        
        brokers_widget = self.block_widgets.get("brokers")
        if brokers_widget:
            brokers_widget.set_enabled(base_config.brokers_block.enabled)
            brokers_widget.set_option_value("show_best_price", base_config.brokers_block.show_best_price)
            brokers_widget.set_option_value("show_all_brokers", base_config.brokers_block.show_all_brokers)
            brokers_widget.set_option_value("show_fees", base_config.brokers_block.show_fees)
            brokers_widget.set_option_value("max_brokers", base_config.brokers_block.max_brokers_displayed)
        
        fg_widget = self.block_widgets.get("fear_greed")
        if fg_widget:
            fg_widget.set_enabled(base_config.fear_greed_block.enabled)
            fg_widget.set_option_value("show_index", base_config.fear_greed_block.show_index)
            fg_widget.set_option_value("show_interpretation", base_config.fear_greed_block.show_interpretation)
        
        gain_widget = self.block_widgets.get("gain_loss")
        if gain_widget:
            gain_widget.set_enabled(base_config.gain_loss_block.enabled)
            gain_widget.set_option_value("show_gain_loss", base_config.gain_loss_block.show_gain_loss)
            gain_widget.set_option_value("show_percentage", base_config.gain_loss_block.show_percentage)
            gain_widget.set_option_value("investment_amount", f"{base_config.gain_loss_block.investment_amount:.2f}")
        
        suggestion_widget = self.block_widgets.get("investment_suggestions")
        if suggestion_widget:
            suggestion_widget.set_enabled(base_config.investment_suggestions_block.enabled)
            suggestion_widget.set_option_value("max_suggestions", base_config.investment_suggestions_block.max_suggestions)
            suggestion_widget.set_option_value("min_opportunity_score", base_config.investment_suggestions_block.min_opportunity_score)
            suggestion_widget.set_option_value("exclude_current", base_config.investment_suggestions_block.exclude_current)
            suggestion_widget.set_option_value("prefer_low_volatility", base_config.investment_suggestions_block.prefer_low_volatility)
            suggestion_widget.set_option_value("prefer_trending", base_config.investment_suggestions_block.prefer_trending)
            suggestion_widget.set_option_value("prefer_undervalued", base_config.investment_suggestions_block.prefer_undervalued)
            suggestion_widget.set_option_value("intro_message", base_config.investment_suggestions_block.intro_message)
        
        glossary_widget = self.block_widgets.get("glossary")
        if glossary_widget:
            glossary_widget.set_enabled(base_config.glossary_block.enabled)
            glossary_widget.set_option_value("auto_detect", base_config.glossary_block.auto_detect_terms)
            if base_config.glossary_block.custom_terms:
                lines = [f"{term}={definition}" for term, definition in base_config.glossary_block.custom_terms.items()]
                glossary_widget.set_option_value("custom_terms", "\n".join(lines))
            else:
                glossary_widget.set_option_value("custom_terms", "")
    
    def _create_price_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc prix"""
        block = BlockConfigWidget("Prix et variation", "💰")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_price_eur", "💶 Afficher le prix en euros", default=True)
        block.add_checkbox_option("show_variation_24h", "📊 Afficher la variation sur 24h", default=True)
        block.add_checkbox_option("show_variation_7d", "📈 Afficher la variation sur 7 jours", default=True)
        block.add_checkbox_option("show_volume", "🔊 Afficher le volume d'échanges", default=True)
        block.add_checkbox_option("add_price_comment", "💬 Ajouter un commentaire pédagogique", default=True)
        
        block.add_text_option(
            "message_prix_monte",
            "Message quand le prix monte :",
            "📈 Super ! Le prix monte. Si tu possèdes déjà cette crypto, tu gagnes de l'argent !",
            multiline=True
        )
        
        return block
    
    def _create_chart_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc graphique"""
        block = BlockConfigWidget("Graphiques", "📊")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_sparklines", "✨ Afficher mini-graphiques (sparklines)", default=True)
        block.add_checkbox_option("send_full_chart", "🖼️ Envoyer une image graphique complète", default=False)
        
        block.add_text_option(
            "timeframes",
            "Périodes à afficher (en heures, séparées par des virgules) :",
            "24, 168",
            tooltip="24 = 1 jour, 168 = 1 semaine, etc."
        )
        
        return block
    
    def _create_prediction_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc prédiction"""
        block = BlockConfigWidget("Prédiction IA", "🔮")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_prediction_type", "🎯 Afficher la tendance prédite", default=True)
        block.add_checkbox_option("show_confidence", "📊 Afficher le niveau de confiance", default=True)
        block.add_checkbox_option("show_explanation", "💡 Ajouter une explication simple", default=True)
        
        block.add_slider_option(
            "min_confidence",
            "Confiance minimum pour afficher :",
            0, 100, 50,
            "Ne pas afficher si l'IA est moins sûre que ce pourcentage"
        )
        
        return block
    
    def _create_opportunity_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc opportunité"""
        block = BlockConfigWidget("Score d'opportunité", "⭐")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_score", "🎯 Afficher le score sur 10", default=True)
        block.add_checkbox_option("show_recommendation", "💡 Afficher la recommandation", default=True)
        block.add_checkbox_option("show_reasons", "📝 Expliquer les raisons du score", default=True)
        
        block.add_slider_option(
            "min_score",
            "Score minimum pour afficher :",
            0, 10, 0,
            "Ne pas afficher si le score est inférieur"
        )
        
        return block
    
    def _create_brokers_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc courtiers"""
        block = BlockConfigWidget("Comparaison courtiers", "💱")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_best_price", "🏆 Afficher le meilleur prix", default=True)
        block.add_checkbox_option("show_all_brokers", "📋 Afficher tous les courtiers", default=True)
        block.add_checkbox_option("show_fees", "💰 Afficher les frais", default=True)
        
        block.add_slider_option(
            "max_brokers",
            "Nombre maximum de courtiers à afficher :",
            1, 10, 3
        )
        
        return block
    
    def _create_fear_greed_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc Fear & Greed"""
        block = BlockConfigWidget("Humeur du marché (Fear & Greed)", "😨😁")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_index", "📊 Afficher l'indice", default=True)
        block.add_checkbox_option("show_interpretation", "💭 Expliquer ce que ça signifie", default=True)
        
        return block
    
    def _create_gain_loss_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc gain/perte"""
        block = BlockConfigWidget("Simulation d'investissement", "💵")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option("show_gain_loss", "💰 Afficher gain ou perte", default=True)
        block.add_checkbox_option("show_percentage", "📊 Afficher le pourcentage", default=True)
        
        block.add_text_option(
            "investment_amount",
            "Montant de référence pour la simulation (en €) :",
            "100",
            tooltip="Ex: Si tu avais investi 100€, combien aurais-tu gagné/perdu ?"
        )
        
        return block
    
    def _create_investment_suggestions_block(self) -> BlockConfigWidget:
        """🆕 Crée le widget de configuration du bloc suggestions d'investissement"""
        block = BlockConfigWidget("Suggestions d'autres cryptos", "💡")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        
        block.add_slider_option(
            "max_suggestions",
            "Nombre de suggestions :",
            1, 5, 3,
            "Combien d'autres cryptos suggérer"
        )
        
        block.add_slider_option(
            "min_opportunity_score",
            "Score minimum pour suggérer :",
            5, 10, 7,
            "Ne suggérer que les cryptos avec ce score minimum"
        )
        
        block.add_checkbox_option(
            "exclude_current",
            "🚫 Ne pas suggérer la crypto actuelle",
            default=True
        )
        
        block.add_checkbox_option(
            "prefer_low_volatility",
            "🛡️ Préférer les cryptos stables",
            tooltip="Suggérer plutôt des cryptos avec peu de variations",
            default=False
        )
        
        block.add_checkbox_option(
            "prefer_trending",
            "📈 Préférer les cryptos en hausse",
            tooltip="Suggérer plutôt des cryptos qui montent",
            default=True
        )
        
        block.add_checkbox_option(
            "prefer_undervalued",
            "💎 Préférer les bonnes affaires",
            tooltip="Suggérer plutôt des cryptos avec un prix attractif",
            default=True
        )
        
        block.add_text_option(
            "intro_message",
            "Message d'introduction :",
            "🔍 D'autres cryptos qui pourraient t'intéresser :",
            multiline=True
        )
        
        return block
    
    def _create_glossary_block(self) -> BlockConfigWidget:
        """Crée le widget de configuration du bloc glossaire"""
        block = BlockConfigWidget("Glossaire pédagogique", "📚")
        block_layout = QVBoxLayout()
        block.setLayout(block_layout)
        
        block.add_enable_checkbox(default=True)
        block.add_checkbox_option(
            "auto_detect",
            "🔍 Détecter automatiquement les mots à expliquer",
            default=True
        )
        
        block.add_text_option(
            "custom_terms",
            "Ajouter des mots spécifiques à expliquer (un par ligne, format: mot=explication) :",
            "",
            multiline=True,
            tooltip="Ex:\nATH=Plus haut historique\nDCA=Dollar Cost Averaging"
        )
        
        return block
    
    def get_config(self) -> ScheduledNotificationConfig:
        """Génère la configuration à partir des widgets"""
        config = ScheduledNotificationConfig()
        config.hours = []
        
        # Configuration de chaque bloc
        if "price" in self.block_widgets:
            price_widget = self.block_widgets["price"]
            config.price_block.enabled = price_widget.is_enabled()
            config.price_block.show_price_eur = price_widget.get_option_value("show_price_eur")
            config.price_block.show_variation_24h = price_widget.get_option_value("show_variation_24h")
            config.price_block.show_variation_7d = price_widget.get_option_value("show_variation_7d")
            config.price_block.show_volume = price_widget.get_option_value("show_volume")
            config.price_block.add_price_comment = price_widget.get_option_value("add_price_comment")
            message_up = price_widget.get_option_value("message_prix_monte") or ""
            config.price_block.message_prix_monte = message_up.strip() or config.price_block.message_prix_monte
        
        if "chart" in self.block_widgets:
            chart_widget = self.block_widgets["chart"]
            config.chart_block.enabled = chart_widget.is_enabled()
            config.chart_block.show_sparklines = chart_widget.get_option_value("show_sparklines")
            config.chart_block.send_full_chart = chart_widget.get_option_value("send_full_chart")
            raw_timeframes = chart_widget.get_option_value("timeframes") or ""
            timeframes: List[int] = []
            for part in raw_timeframes.replace(";", ",").split(","):
                part = part.strip()
                if part.isdigit():
                    value = int(part)
                    if value > 0:
                        timeframes.append(value)
            config.chart_block.timeframes = timeframes or config.chart_block.timeframes
        
        if "prediction" in self.block_widgets:
            prediction_widget = self.block_widgets["prediction"]
            config.prediction_block.enabled = prediction_widget.is_enabled()
            config.prediction_block.show_prediction_type = prediction_widget.get_option_value("show_prediction_type")
            config.prediction_block.show_confidence = prediction_widget.get_option_value("show_confidence")
            config.prediction_block.show_explanation = prediction_widget.get_option_value("show_explanation")
            config.prediction_block.min_confidence_to_show = int(prediction_widget.get_option_value("min_confidence") or 0)
        
        if "opportunity" in self.block_widgets:
            opportunity_widget = self.block_widgets["opportunity"]
            config.opportunity_block.enabled = opportunity_widget.is_enabled()
            config.opportunity_block.show_score = opportunity_widget.get_option_value("show_score")
            config.opportunity_block.show_recommendation = opportunity_widget.get_option_value("show_recommendation")
            config.opportunity_block.show_reasons = opportunity_widget.get_option_value("show_reasons")
            config.opportunity_block.min_score_to_show = int(opportunity_widget.get_option_value("min_score") or 0)
        
        if "brokers" in self.block_widgets:
            brokers_widget = self.block_widgets["brokers"]
            config.brokers_block.enabled = brokers_widget.is_enabled()
            config.brokers_block.show_best_price = brokers_widget.get_option_value("show_best_price")
            config.brokers_block.show_all_brokers = brokers_widget.get_option_value("show_all_brokers")
            config.brokers_block.show_fees = brokers_widget.get_option_value("show_fees")
            config.brokers_block.max_brokers_displayed = int(brokers_widget.get_option_value("max_brokers") or 3)
        
        if "fear_greed" in self.block_widgets:
            fg_widget = self.block_widgets["fear_greed"]
            config.fear_greed_block.enabled = fg_widget.is_enabled()
            config.fear_greed_block.show_index = fg_widget.get_option_value("show_index")
            config.fear_greed_block.show_interpretation = fg_widget.get_option_value("show_interpretation")
        
        if "gain_loss" in self.block_widgets:
            gain_widget = self.block_widgets["gain_loss"]
            config.gain_loss_block.enabled = gain_widget.is_enabled()
            config.gain_loss_block.show_gain_loss = gain_widget.get_option_value("show_gain_loss")
            config.gain_loss_block.show_percentage = gain_widget.get_option_value("show_percentage")
            investment_amount = gain_widget.get_option_value("investment_amount") or "0"
            try:
                config.gain_loss_block.investment_amount = float(investment_amount.replace(",", "."))
            except ValueError:
                pass
        
        if "investment_suggestions" in self.block_widgets:
            suggestion_widget = self.block_widgets["investment_suggestions"]
            config.investment_suggestions_block.enabled = suggestion_widget.is_enabled()
            config.investment_suggestions_block.max_suggestions = int(suggestion_widget.get_option_value("max_suggestions") or 3)
            config.investment_suggestions_block.min_opportunity_score = int(suggestion_widget.get_option_value("min_opportunity_score") or 7)
            config.investment_suggestions_block.exclude_current = suggestion_widget.get_option_value("exclude_current")
            config.investment_suggestions_block.prefer_low_volatility = suggestion_widget.get_option_value("prefer_low_volatility")
            config.investment_suggestions_block.prefer_trending = suggestion_widget.get_option_value("prefer_trending")
            config.investment_suggestions_block.prefer_undervalued = suggestion_widget.get_option_value("prefer_undervalued")
            intro_message = suggestion_widget.get_option_value("intro_message")
            if isinstance(intro_message, str) and intro_message.strip():
                config.investment_suggestions_block.intro_message = intro_message.strip()
        
        if "glossary" in self.block_widgets:
            glossary_widget = self.block_widgets["glossary"]
            config.glossary_block.enabled = glossary_widget.is_enabled()
            config.glossary_block.auto_detect_terms = glossary_widget.get_option_value("auto_detect")
            custom_terms_text = glossary_widget.get_option_value("custom_terms") or ""
            custom_terms: Dict[str, str] = {}
            for line in custom_terms_text.splitlines():
                if "=" not in line:
                    continue
                term, definition = line.split("=", 1)
                term = term.strip()
                definition = definition.strip()
                if term and definition:
                    custom_terms[term] = definition
            if custom_terms:
                config.glossary_block.custom_terms = custom_terms
        
        return config
    
    def apply_to_profile(self, profile: CoinNotificationProfile, default_hours: List[int]):
        """Applique la configuration actuelle aux notifications du profil."""
        default_hours = sorted({int(h) for h in default_hours if isinstance(h, int) and 0 <= h <= 23}) or [9]
        base_config = self.get_config()
        base_config.hours = list(default_hours)
        
        profile.default_config = copy.deepcopy(base_config)
        profile.scheduled_notifications = []
        
        for hour in default_hours:
            notif_config = copy.deepcopy(base_config)
            notif_config.hours = [hour]
            notif_config.name = f"Notification {hour}h"
            profile.scheduled_notifications.append(notif_config)


class AdvancedNotificationConfigWindow(QDialog):
    """Fenêtre principale de configuration avancée des notifications"""
    
    def __init__(self, settings: GlobalNotificationSettings, symbols: List[str], parent=None):
        super().__init__(parent)
        self.settings = copy.deepcopy(settings)
        self.symbols = symbols
        self.coin_editors: Dict[str, SimpleCoinNotificationEditor] = {}
        self.coins_tab: Optional[QTabWidget] = None
        self.schedule_widget: Optional[SimpleNotificationScheduleWidget] = None
        self.global_enabled_checkbox: Optional[QCheckBox] = None
        self.global_kid_mode_checkbox: Optional[QCheckBox] = None
        self.global_emoji_checkbox: Optional[QCheckBox] = None
        self.global_explain_checkbox: Optional[QCheckBox] = None
        self.global_quiet_enable_checkbox: Optional[QCheckBox] = None
        self.global_quiet_start_time: Optional[QTimeEdit] = None
        self.global_quiet_end_time: Optional[QTimeEdit] = None
        self.setWindowTitle("⚙️ Configuration avancée des notifications")
        self.resize(1000, 700)
        self._init_ui()
    
    def _init_ui(self):
        layout = QVBoxLayout(self)
        
        # Titre
        title = QLabel("🔔 Configure tes notifications comme tu veux !")
        title_font = QFont()
        title_font.setPointSize(18)
        title_font.setBold(True)
        title.setFont(title_font)
        layout.addWidget(title)
        
        # Onglets
        tabs = QTabWidget()
        
        # Onglet 1: Horaires
        schedule_tab = QWidget()
        schedule_layout = QVBoxLayout(schedule_tab)
        self.schedule_widget = SimpleNotificationScheduleWidget()
        schedule_layout.addWidget(self.schedule_widget)
        tabs.addTab(schedule_tab, "🕐 Horaires")
        
        # Onglet 2: Configuration par crypto
        self.coins_tab = QTabWidget()
        for symbol in self.symbols:
            coin_editor = SimpleCoinNotificationEditor(symbol)
            self.coin_editors[symbol] = coin_editor
            self.coins_tab.addTab(coin_editor, f"💎 {symbol}")
        tabs.addTab(self.coins_tab, "💰 Par crypto")
        
        # Onglet 3: Paramètres globaux
        global_tab = self._create_global_settings_tab()
        tabs.addTab(global_tab, "⚙️ Paramètres généraux")
        
        layout.addWidget(tabs)
        
        # Boutons
        buttons_layout = QHBoxLayout()
        
        btn_preview = QPushButton("👁️ Prévisualiser")
        btn_preview.clicked.connect(self._preview_notification)
        buttons_layout.addWidget(btn_preview)
        
        btn_save = QPushButton("💾 Enregistrer")
        btn_save.clicked.connect(self.accept)
        buttons_layout.addWidget(btn_save)
        
        btn_cancel = QPushButton("❌ Annuler")
        btn_cancel.clicked.connect(self.reject)
        buttons_layout.addWidget(btn_cancel)
        
        layout.addLayout(buttons_layout)
        
        self._load_settings_into_ui()
    
    def _create_global_settings_tab(self) -> QWidget:
        """Crée l'onglet des paramètres globaux"""
        tab = QWidget()
        layout = QVBoxLayout(tab)
        
        self.global_enabled_checkbox = QCheckBox("✅ Activer les notifications")
        self.global_enabled_checkbox.setChecked(True)
        layout.addWidget(self.global_enabled_checkbox)
        
        # Mode enfant
        kid_mode_group = QGroupBox("👶 Mode adapté aux enfants")
        kid_layout = QVBoxLayout()
        
        kid_check = QCheckBox("✅ Activer le mode ultra-simple")
        kid_check.setChecked(True)
        kid_check.setToolTip("Utilise des mots simples et beaucoup d'explications")
        kid_layout.addWidget(kid_check)
        self.global_kid_mode_checkbox = kid_check
        
        emoji_check = QCheckBox("😀 Utiliser plein d'emojis")
        emoji_check.setChecked(True)
        kid_layout.addWidget(emoji_check)
        self.global_emoji_checkbox = emoji_check
        
        explain_check = QCheckBox("💡 Tout expliquer en détail")
        explain_check.setChecked(True)
        kid_layout.addWidget(explain_check)
        self.global_explain_checkbox = explain_check
        
        kid_mode_group.setLayout(kid_layout)
        layout.addWidget(kid_mode_group)
        
        # Heures silencieuses
        quiet_group = QGroupBox("🌙 Heures silencieuses (pour dormir)")
        quiet_layout = QVBoxLayout()
        
        quiet_enable = QCheckBox("Activer le mode nuit (pas de notifications)")
        quiet_enable.setChecked(True)
        quiet_layout.addWidget(quiet_enable)
        self.global_quiet_enable_checkbox = quiet_enable
        
        quiet_time_layout = QHBoxLayout()
        quiet_time_layout.addWidget(QLabel("De :"))
        quiet_start = QTimeEdit()
        quiet_start.setTime(QTime(23, 0))
        quiet_time_layout.addWidget(quiet_start)
        self.global_quiet_start_time = quiet_start
        quiet_time_layout.addWidget(QLabel("à :"))
        quiet_end = QTimeEdit()
        quiet_end.setTime(QTime(7, 0))
        quiet_time_layout.addWidget(quiet_end)
        self.global_quiet_end_time = quiet_end
        quiet_layout.addLayout(quiet_time_layout)
        
        quiet_group.setLayout(quiet_layout)
        layout.addWidget(quiet_group)
        
        layout.addStretch()
        
        return tab
    
    def _load_settings_into_ui(self):
        """Initialise l'UI avec les valeurs de configuration existantes"""
        if self.schedule_widget and self.settings.default_scheduled_hours:
            self.schedule_widget.set_hours(self.settings.default_scheduled_hours)
        
        if self.global_enabled_checkbox is not None:
            self.global_enabled_checkbox.setChecked(self.settings.enabled)
        
        if self.global_kid_mode_checkbox is not None:
            self.global_kid_mode_checkbox.setChecked(self.settings.kid_friendly_mode)
        
        if self.global_emoji_checkbox is not None:
            self.global_emoji_checkbox.setChecked(getattr(self.settings, "use_emojis_everywhere", True))
        
        if self.global_explain_checkbox is not None:
            self.global_explain_checkbox.setChecked(getattr(self.settings, "explain_everything", True))
        
        if self.global_quiet_enable_checkbox is not None:
            self.global_quiet_enable_checkbox.setChecked(getattr(self.settings, "respect_quiet_hours", True))
        
        if self.global_quiet_start_time is not None:
            start_hour = int(getattr(self.settings, "quiet_start", 23) or 0)
            start_hour = max(0, min(23, start_hour))
            self.global_quiet_start_time.setTime(QTime(start_hour, 0))
        
        if self.global_quiet_end_time is not None:
            end_hour = int(getattr(self.settings, "quiet_end", 7) or 0)
            end_hour = max(0, min(23, end_hour))
            self.global_quiet_end_time.setTime(QTime(end_hour, 0))
        
        for symbol, editor in self.coin_editors.items():
            profile = self.settings.get_coin_profile(symbol)
            editor.load_from_profile(profile)
    
    def _collect_settings_from_ui(self):
        """Valide et applique les valeurs saisies aux paramètres"""
        if not self.schedule_widget:
            return
        
        hours = sorted(set(self.schedule_widget.get_hours()))
        if not hours:
            raise ValueError("Veuillez sélectionner au moins une heure de notification.")
        self.settings.default_scheduled_hours = hours
        
        if self.global_enabled_checkbox is not None:
            self.settings.enabled = self.global_enabled_checkbox.isChecked()
        
        if self.global_kid_mode_checkbox is not None:
            self.settings.kid_friendly_mode = self.global_kid_mode_checkbox.isChecked()
        
        if self.global_emoji_checkbox is not None:
            self.settings.use_emojis_everywhere = self.global_emoji_checkbox.isChecked()
        
        if self.global_explain_checkbox is not None:
            self.settings.explain_everything = self.global_explain_checkbox.isChecked()
        
        if self.global_quiet_enable_checkbox is not None:
            self.settings.respect_quiet_hours = self.global_quiet_enable_checkbox.isChecked()
        
        if self.global_quiet_start_time is not None:
            self.settings.quiet_start = self.global_quiet_start_time.time().hour()
        
        if self.global_quiet_end_time is not None:
            self.settings.quiet_end = self.global_quiet_end_time.time().hour()
    
    def _collect_coin_settings_from_ui(self):
        """Met à jour les profils de notifications à partir des éditeurs."""
        hours = self.settings.default_scheduled_hours or [9]
        for symbol, editor in self.coin_editors.items():
            profile = self.settings.get_coin_profile(symbol)
            editor.apply_to_profile(profile, hours)
    

    def _save_to_file(self):
        """Sauvegarde les paramètres dans config/notifications.yaml"""
        import yaml
        from pathlib import Path
        
        notif_config_path = Path("config/notifications.yaml")
        notif_config_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Préparer les données à sauvegarder
        data = {
            'enabled': self.settings.enabled,
            'kid_friendly_mode': self.settings.kid_friendly_mode,
            'use_emojis_everywhere': self.settings.use_emojis_everywhere,
            'explain_everything': self.settings.explain_everything,
            'respect_quiet_hours': self.settings.respect_quiet_hours,
            'quiet_start': self.settings.quiet_start,
            'quiet_end': self.settings.quiet_end,
            'default_scheduled_hours': self.settings.default_scheduled_hours
        }
        
        # Sauvegarder dans le fichier
        with open(notif_config_path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        print(f"✅ Configuration des notifications sauvegardée dans {notif_config_path}")


    def _save_to_yaml(self):
        """Sauvegarde dans config/notifications.yaml"""
        import yaml
        from pathlib import Path
        
        path = Path("config/notifications.yaml")
        path.parent.mkdir(parents=True, exist_ok=True)
        
        data = {
            'enabled': self.settings.enabled,
            'kid_friendly_mode': self.settings.kid_friendly_mode,
            'use_emojis_everywhere': self.settings.use_emojis_everywhere,
            'explain_everything': self.settings.explain_everything,
            'respect_quiet_hours': self.settings.respect_quiet_hours,
            'quiet_start': self.settings.quiet_start,
            'quiet_end': self.settings.quiet_end,
            'default_scheduled_hours': self.settings.default_scheduled_hours
        }
        
        with open(path, 'w', encoding='utf-8') as f:
            yaml.dump(data, f, default_flow_style=False, sort_keys=False)
        
        print(f"✅ Sauvegardé: {path}")

    def accept(self):
        """Valide la saisie avant de fermer la fenêtre"""
        try:
            self._collect_settings_from_ui()
            self._collect_coin_settings_from_ui()
        except ValueError as err:
            QMessageBox.critical(self, "Erreur de validation", str(err))
            return
        self._save_to_file()
        super().accept()
    
    def _preview_notification(self):
        """Prévisualise une notification"""
        preview_dialog = QDialog(self)
        preview_dialog.setWindowTitle("👁️ Aperçu de notification")
        preview_dialog.resize(600, 800)
        
        layout = QVBoxLayout(preview_dialog)
        
        preview_text = QTextEdit()
        preview_text.setReadOnly(True)
        current_symbol = self.symbols[0] if self.symbols else "BTC"
        if self.coins_tab:
            current_index = self.coins_tab.currentIndex()
            if 0 <= current_index < len(self.symbols):
                current_symbol = self.symbols[current_index]

        tracked_set = {sym.upper() for sym in self.symbols}
        available_suggestions = [
            s for s in ["ADA", "XRP", "DOGE", "DOT", "LINK", "AVAX", "MATIC"]
            if s not in tracked_set
        ] or ["ADA", "XRP"]
        suggestion_lines = []
        for idx, sym in enumerate(available_suggestions[:2], start=1):
            emoji = "📈" if idx == 1 else "💎"
            suggestion_lines.append(
                f"{idx}. {emoji} {sym} montre des signaux intéressants"
            )
        suggestions_text = "\n".join(suggestion_lines)

        preview_text.setPlainText(
            f"🔔 Notification du matin - {current_symbol}\n\n"
            "💰 Prix actuel\n"
            f"Le prix actuel est affiché avec une explication simple.\n"
            "📈 Il a monté de +1.36% en 24h - C'est bien !\n"
            "🔊 Beaucoup de gens l'achètent aujourd'hui (volume élevé)\n\n"
            "🔮 Prédiction Intelligence Artificielle\n"
            "🚀 L'IA pense que le prix va monter\n"
            "Confiance: 75% - L'IA est plutôt sûre d'elle\n\n"
            "⭐ Score d'opportunité : 10/10\n"
            "🌟 Excellente opportunité ! À surveiller de près.\n\n"
            "💡 D'autres cryptos qui pourraient t'intéresser :\n"
            f"{suggestions_text}\n\n"
            "📚 Petit glossaire\n"
            "• Prix : Combien coûte 1 unité de cette crypto en euros\n"
            "• IA : Intelligence Artificielle = ordinateur qui essaie de prédire le futur\n"
            "• Score d'opportunité : Chance d'acheter au bon moment (sur 10)\n\n"
            "ℹ️ Ceci est une information, pas un conseil financier !"
        )
        layout.addWidget(preview_text)
        
        close_btn = QPushButton("Fermer")
        close_btn.clicked.connect(preview_dialog.close)
        layout.addWidget(close_btn)
        
        preview_dialog.exec()
