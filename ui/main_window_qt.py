"""
Application GUI PyQt6 - Crypto Bot v3.0
Interface graphique moderne avec PyQt6
"""

import sys
import threading
import time
from datetime import datetime
from typing import Dict, Optional

from PyQt6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QVBoxLayout, QHBoxLayout,
    QPushButton, QLabel, QComboBox, QFrame, QScrollArea, QGroupBox,
    QGridLayout, QMessageBox, QTabWidget
)
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QThread, pyqtSlot
from PyQt6.QtGui import QFont, QColor, QPalette

import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from core.models import (
    BotConfiguration, MarketData, Prediction, Alert, 
    AlertLevel, OpportunityScore
)
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI

import logging

logger = logging.getLogger("CryptoBot.GUI")


class WorkerSignals:
    """Signaux pour communication thread-safe"""
    pass


class MonitorWorker(QThread):
    """Worker thread pour surveillance en arrière-plan"""
    
    alert_triggered = pyqtSignal(Alert)
    data_updated = pyqtSignal(str, MarketData, Prediction, OpportunityScore)
    error_occurred = pyqtSignal(str, str)
    
    def __init__(self, config: BotConfiguration, market_service: MarketService, 
                 alert_service: AlertService, telegram_api: TelegramAPI):
        super().__init__()
        self.config = config
        self.market_service = market_service
        self.alert_service = alert_service
        self.telegram_api = telegram_api
        self.running = False
    
    def run(self):
        """Boucle principale de surveillance"""
        self.running = True
        logger.info("Monitor worker started")
        
        while self.running:
            for symbol in self.config.crypto_symbols:
                if not self.running:
                    break
                
                try:
                    # Récupérer données
                    market_data = self.market_service.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Prédiction
                    prediction = self.market_service.predict_price_movement(market_data)
                    
                    # Score opportunité
                    opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
                    
                    # Émettre signal de mise à jour
                    self.data_updated.emit(symbol, market_data, prediction, opportunity)
                    
                    # Vérifier alertes
                    alerts = self.alert_service.check_alerts(market_data, prediction)
                    
                    # Envoyer alertes importantes
                    for alert in alerts:
                        self.alert_triggered.emit(alert)
                        
                        if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                            self.telegram_api.send_alert(alert, include_metadata=True)
                
                except Exception as e:
                    logger.error(f"Error monitoring {symbol}: {e}", exc_info=True)
                    self.error_occurred.emit(symbol, str(e))
            
            # Attendre avant prochain cycle
            if self.running:
                time.sleep(self.config.check_interval_seconds)
        
        logger.info("Monitor worker stopped")
    
    def stop(self):
        """Arrête le worker"""
        self.running = False


class CryptoBotGUI(QMainWindow):
    """Application principale PyQt6"""
    
    def __init__(self, config: BotConfiguration):
        super().__init__()
        
        self.config = config
        self.is_running = False
        self.worker = None
        
        # Services
        self.binance_api = BinanceAPI()
        self.telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        
        # Cache données
        self.market_data_cache: Dict[str, MarketData] = {}
        self.predictions_cache: Dict[str, Prediction] = {}
        self.opportunity_cache: Dict[str, OpportunityScore] = {}
        
        # Configuration fenêtre
        self.setWindowTitle("Crypto Bot v3.0 - Dashboard")
        self.setGeometry(100, 100, 1600, 900)
        
        # Appliquer thème sombre
        self._apply_dark_theme()
        
        # Créer interface
        self._create_ui()
        
        # Timer pour mise à jour initiale
        QTimer.singleShot(500, self._initial_load)
    
    def _apply_dark_theme(self):
        """Applique un thème sombre moderne"""
        palette = QPalette()
        palette.setColor(QPalette.ColorRole.Window, QColor(43, 43, 43))
        palette.setColor(QPalette.ColorRole.WindowText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Base, QColor(33, 33, 33))
        palette.setColor(QPalette.ColorRole.AlternateBase, QColor(43, 43, 43))
        palette.setColor(QPalette.ColorRole.Text, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ColorRole.ButtonText, Qt.GlobalColor.white)
        palette.setColor(QPalette.ColorRole.Highlight, QColor(33, 150, 243))
        palette.setColor(QPalette.ColorRole.HighlightedText, Qt.GlobalColor.white)
        
        QApplication.instance().setPalette(palette)
        
        # Style additionnel
        QApplication.instance().setStyleSheet("""
            QMainWindow {
                background-color: #2b2b2b;
            }
            QPushButton {
                background-color: #3d5afe;
                color: white;
                border: none;
                padding: 8px 16px;
                border-radius: 4px;
                font-weight: bold;
            }
            QPushButton:hover {
                background-color: #5c6bc0;
            }
            QPushButton:pressed {
                background-color: #3949ab;
            }
            QPushButton:disabled {
                background-color: #555;
                color: #888;
            }
            QLabel {
                color: white;
            }
            QComboBox {
                background-color: #3d3d3d;
                color: white;
                border: 1px solid #555;
                padding: 5px;
                border-radius: 3px;
            }
            QComboBox::drop-down {
                border: none;
            }
            QGroupBox {
                border: 1px solid #555;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
                color: white;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
            QScrollArea {
                border: none;
            }
        """)
    
    def _create_ui(self):
        """Crée l'interface utilisateur"""
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        
        main_layout = QHBoxLayout(central_widget)
        main_layout.setSpacing(10)
        main_layout.setContentsMargins(10, 10, 10, 10)
        
        # Sidebar (gauche)
        sidebar = self._create_sidebar()
        main_layout.addWidget(sidebar, stretch=0)
        
        # Zone centrale (graphiques et données)
        center_widget = self._create_center_area()
        main_layout.addWidget(center_widget, stretch=3)
        
        # Panneau droit (alertes et prédictions)
        right_panel = self._create_right_panel()
        main_layout.addWidget(right_panel, stretch=1)
    
    def _create_sidebar(self) -> QWidget:
        """Crée la sidebar"""
        sidebar = QFrame()
        sidebar.setFixedWidth(250)
        sidebar.setFrameStyle(QFrame.Shape.StyledPanel)
        
        layout = QVBoxLayout(sidebar)
        
        # Titre
        title = QLabel("🚀 Crypto Bot v3.0")
        title.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        
        # Statut
        self.status_label = QLabel("● Arrêté")
        self.status_label.setFont(QFont("Arial", 12))
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.status_label)
        
        layout.addSpacing(20)
        
        # Boutons Start/Stop
        self.start_button = QPushButton("▶ Démarrer")
        self.start_button.setStyleSheet("background-color: #4caf50;")
        self.start_button.clicked.connect(self._start_monitoring)
        layout.addWidget(self.start_button)
        
        self.stop_button = QPushButton("⏸ Arrêter")
        self.stop_button.setStyleSheet("background-color: #f44336;")
        self.stop_button.clicked.connect(self._stop_monitoring)
        self.stop_button.setEnabled(False)
        layout.addWidget(self.stop_button)
        
        layout.addSpacing(20)
        
        # Sélecteur crypto
        layout.addWidget(QLabel("Cryptomonnaie:"))
        self.crypto_selector = QComboBox()
        self.crypto_selector.addItems(self.config.crypto_symbols)
        self.crypto_selector.currentTextChanged.connect(self._on_crypto_changed)
        layout.addWidget(self.crypto_selector)
        
        layout.addSpacing(10)
        
        # Niveau de détail
        layout.addWidget(QLabel("Niveau de détail:"))
        self.detail_selector = QComboBox()
        self.detail_selector.addItems(["Simple", "Normal", "Expert"])
        self.detail_selector.setCurrentText("Normal")
        self.detail_selector.currentTextChanged.connect(self._on_detail_changed)
        layout.addWidget(self.detail_selector)
        
        layout.addSpacing(30)
        
        # Boutons actions
        test_btn = QPushButton("📤 Test Telegram")
        test_btn.clicked.connect(self._test_telegram)
        layout.addWidget(test_btn)
        
        refresh_btn = QPushButton("🔄 Rafraîchir")
        refresh_btn.clicked.connect(self._refresh_data)
        layout.addWidget(refresh_btn)
        
        layout.addStretch()
        
        # Version
        version_label = QLabel("v3.0 | PyQt6")
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version_label.setStyleSheet("color: gray; font-size: 10px;")
        layout.addWidget(version_label)
        
        return sidebar
    
    def _create_center_area(self) -> QWidget:
        """Crée la zone centrale"""
        center = QWidget()
        layout = QVBoxLayout(center)
        
        # Tabs
        tabs = QTabWidget()
        
        # Tab 1: Graphique prix
        graph_widget = self._create_price_chart()
        tabs.addTab(graph_widget, "📊 Graphique")
        
        # Tab 2: Indicateurs
        indicators_widget = self._create_indicators()
        tabs.addTab(indicators_widget, "📈 Indicateurs")
        
        layout.addWidget(tabs)
        
        return center
    
    def _create_price_chart(self) -> QWidget:
        """Crée le widget graphique"""
        widget = QWidget()
        layout = QVBoxLayout(widget)
        
        # Créer figure matplotlib
        self.figure = Figure(figsize=(10, 6), facecolor='#2b2b2b')
        self.canvas = FigureCanvas(self.figure)
        self.ax = self.figure.add_subplot(111, facecolor='#2b2b2b')
        
        layout.addWidget(self.canvas)
        
        return widget
    
    def _create_indicators(self) -> QWidget:
        """Crée les cartes d'indicateurs"""
        widget = QWidget()
        layout = QGridLayout(widget)
        
        # Prix actuel
        self.price_card = self._create_indicator_card("💰 Prix", "0.00 €")
        layout.addWidget(self.price_card, 0, 0)
        
        # Changement 24h
        self.change_card = self._create_indicator_card("📊 Variation 24h", "0.00%")
        layout.addWidget(self.change_card, 0, 1)
        
        # RSI
        self.rsi_card = self._create_indicator_card("📈 RSI", "50")
        layout.addWidget(self.rsi_card, 1, 0)
        
        # Score opportunité
        self.opportunity_card = self._create_indicator_card("⭐ Opportunité", "5/10")
        layout.addWidget(self.opportunity_card, 1, 1)
        
        # Fear & Greed
        self.fgi_card = self._create_indicator_card("😱 Fear & Greed", "N/A")
        layout.addWidget(self.fgi_card, 2, 0)
        
        # Funding Rate
        self.funding_card = self._create_indicator_card("💸 Funding Rate", "N/A")
        layout.addWidget(self.funding_card, 2, 1)
        
        layout.setRowStretch(3, 1)
        
        return widget
    
    def _create_indicator_card(self, title: str, value: str) -> QGroupBox:
        """Crée une carte indicateur"""
        card = QGroupBox(title)
        layout = QVBoxLayout(card)
        
        value_label = QLabel(value)
        value_label.setFont(QFont("Arial", 24, QFont.Weight.Bold))
        value_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        value_label.setObjectName("value")
        
        layout.addWidget(value_label)
        
        return card
    
    def _create_right_panel(self) -> QWidget:
        """Crée le panneau droit"""
        panel = QWidget()
        layout = QVBoxLayout(panel)
        
        # Prédiction
        pred_group = QGroupBox("🔮 Prédiction")
        pred_layout = QVBoxLayout(pred_group)
        
        self.prediction_label = QLabel("Chargement...")
        self.prediction_label.setWordWrap(True)
        self.prediction_label.setAlignment(Qt.AlignmentFlag.AlignTop | Qt.AlignmentFlag.AlignLeft)
        
        pred_scroll = QScrollArea()
        pred_scroll.setWidget(self.prediction_label)
        pred_scroll.setWidgetResizable(True)
        pred_scroll.setFixedHeight(250)
        pred_layout.addWidget(pred_scroll)
        
        layout.addWidget(pred_group)
        
        # Alertes
        alerts_group = QGroupBox("🚨 Alertes actives")
        alerts_layout = QVBoxLayout(alerts_group)
        
        self.alerts_scroll = QScrollArea()
        self.alerts_widget = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_widget)
        self.alerts_layout.addStretch()
        
        self.alerts_scroll.setWidget(self.alerts_widget)
        self.alerts_scroll.setWidgetResizable(True)
        alerts_layout.addWidget(self.alerts_scroll)
        
        layout.addWidget(alerts_group)
        
        return panel
    
    def _initial_load(self):
        """Chargement initial"""
        self._refresh_data()
    
    def _refresh_data(self):
        """Rafraîchit les données"""
        symbol = self.crypto_selector.currentText()
        
        try:
            # Récupérer données
            market_data = self.market_service.get_market_data(symbol)
            if not market_data:
                return
            
            prediction = self.market_service.predict_price_movement(market_data)
            opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
            
            # Mettre à jour cache
            self.market_data_cache[symbol] = market_data
            self.predictions_cache[symbol] = prediction
            self.opportunity_cache[symbol] = opportunity
            
            # Mettre à jour UI
            self._update_display(symbol, market_data, prediction, opportunity)
        
        except Exception as e:
            logger.error(f"Error refreshing data: {e}", exc_info=True)
            QMessageBox.warning(self, "Erreur", f"Impossible de rafraîchir les données:\n{e}")
    
    @pyqtSlot(str, MarketData, Prediction, OpportunityScore)
    def _update_display(self, symbol: str, market_data: MarketData, 
                       prediction: Prediction, opportunity: OpportunityScore):
        """Met à jour l'affichage"""
        if symbol != self.crypto_selector.currentText():
            return
        
        # Mise à jour graphique
        self._update_chart(market_data)
        
        # Mise à jour indicateurs
        self._update_indicators(market_data, prediction, opportunity)
        
        # Mise à jour prédiction
        self._update_prediction_panel(prediction, opportunity)
    
    def _update_chart(self, market_data: MarketData):
        """Met à jour le graphique"""
        self.ax.clear()
        
        if not market_data.price_history:
            return
        
        timestamps = [p.timestamp for p in market_data.price_history]
        prices = [p.price_eur for p in market_data.price_history]
        
        # Tracer prix
        self.ax.plot(timestamps, prices, linewidth=2, color='#2196F3', label='Prix')
        
        # Ajouter niveaux
        if self.config.enable_price_levels and market_data.symbol in self.config.price_levels:
            levels = self.config.price_levels[market_data.symbol]
            if "low" in levels:
                self.ax.axhline(y=levels["low"], color='green', linestyle=':', 
                              linewidth=2, label=f'Niveau BAS ({levels["low"]}€)', alpha=0.7)
            if "high" in levels:
                self.ax.axhline(y=levels["high"], color='red', linestyle=':', 
                              linewidth=2, label=f'Niveau HAUT ({levels["high"]}€)', alpha=0.7)
        
        # Styling
        self.ax.set_xlabel('Temps', color='white')
        self.ax.set_ylabel('Prix (€)', color='white')
        self.ax.set_title(f'{market_data.symbol} - Prix en temps réel', 
                         color='white', fontsize=14, fontweight='bold')
        self.ax.legend(loc='upper left', facecolor='#2b2b2b', 
                      edgecolor='white', labelcolor='white')
        self.ax.grid(True, alpha=0.3, color='gray')
        self.ax.tick_params(colors='white')
        self.ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.figure.autofmt_xdate()
        
        self.canvas.draw()
    
    def _update_indicators(self, market_data: MarketData, 
                          prediction: Prediction, opportunity: OpportunityScore):
        """Met à jour les indicateurs"""
        # Prix
        price = market_data.current_price.price_eur
        price_label = self.price_card.findChild(QLabel, "value")
        price_label.setText(f"{price:.2f} €")
        
        # Changement 24h
        change = market_data.current_price.change_24h
        change_label = self.change_card.findChild(QLabel, "value")
        change_label.setText(f"{change:+.2f}%")
        change_label.setStyleSheet(f"color: {'#4caf50' if change > 0 else '#f44336'};")
        
        # RSI
        rsi = market_data.technical_indicators.rsi
        rsi_label = self.rsi_card.findChild(QLabel, "value")
        rsi_label.setText(f"{rsi:.0f}")
        if rsi < 40:
            rsi_label.setStyleSheet("color: #4caf50;")
        elif rsi > 60:
            rsi_label.setStyleSheet("color: #f44336;")
        else:
            rsi_label.setStyleSheet("color: white;")
        
        # Opportunité
        score = opportunity.score
        opp_label = self.opportunity_card.findChild(QLabel, "value")
        opp_label.setText(f"{score}/10 ⭐")
        if score >= 7:
            opp_label.setStyleSheet("color: #4caf50;")
        elif score >= 5:
            opp_label.setStyleSheet("color: #ff9800;")
        else:
            opp_label.setStyleSheet("color: #f44336;")
        
        # Fear & Greed
        fgi_label = self.fgi_card.findChild(QLabel, "value")
        if market_data.fear_greed_index:
            fgi_label.setText(f"{market_data.fear_greed_index}/100")
            if market_data.fear_greed_index <= 30:
                fgi_label.setStyleSheet("color: #4caf50;")
            elif market_data.fear_greed_index >= 70:
                fgi_label.setStyleSheet("color: #f44336;")
            else:
                fgi_label.setStyleSheet("color: white;")
        else:
            fgi_label.setText("N/A")
            fgi_label.setStyleSheet("color: gray;")
        
        # Funding Rate
        funding_label = self.funding_card.findChild(QLabel, "value")
        if market_data.funding_rate is not None:
            funding_label.setText(f"{market_data.funding_rate:.4f}%")
            funding_label.setStyleSheet("color: #4caf50;" if market_data.funding_rate < 0 else "color: white;")
        else:
            funding_label.setText("N/A")
            funding_label.setStyleSheet("color: gray;")
    
    def _update_prediction_panel(self, prediction: Prediction, opportunity: OpportunityScore):
        """Met à jour le panneau de prédiction"""
        detail = self.detail_selector.currentText()
        
        if detail == "Simple":
            text = self._format_prediction_simple(prediction, opportunity)
        elif detail == "Expert":
            text = self._format_prediction_expert(prediction, opportunity)
        else:
            text = self._format_prediction_normal(prediction, opportunity)
        
        self.prediction_label.setText(text)
    
    def _format_prediction_simple(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format simple"""
        text = f"<h3>{prediction.direction} {prediction.prediction_type.value}</h3>"
        text += f"<p>Je suis sûr à <b>{prediction.confidence}%</b></p>"
        
        if opportunity.score >= 7:
            text += "<p style='color: #4caf50;'>💡 C'est un BON moment pour acheter !</p>"
        elif opportunity.score >= 5:
            text += "<p style='color: #ff9800;'>💡 C'est pas mal, tu peux acheter</p>"
        else:
            text += "<p style='color: #f44336;'>💡 Attends un peu avant d'acheter</p>"
        
        text += f"<p>Note : <b>{opportunity.score}/10 ⭐</b></p>"
        
        return text
    
    def _format_prediction_normal(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format normal"""
        text = f"<h3>{prediction.direction} {prediction.prediction_type.value}</h3>"
        text += f"<p>Confiance: <b>{prediction.confidence}%</b></p>"
        
        text += f"<p>Score opportunité: <b>{opportunity.score}/10</b><br>"
        text += f"{opportunity.recommendation}</p>"
        
        if opportunity.reasons:
            text += "<p><b>Raisons:</b><br>"
            for reason in opportunity.reasons[:3]:
                text += f"• {reason}<br>"
            text += "</p>"
        
        return text
    
    def _format_prediction_expert(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format expert"""
        text = f"<h3>{prediction.direction} {prediction.prediction_type.value}</h3>"
        text += f"<p>Confiance: <b>{prediction.confidence}%</b><br>"
        text += f"Trend Score: <b>{prediction.trend_score}</b></p>"
        
        text += "<p><b>Objectifs:</b><br>"
        text += f"• Haut: {prediction.target_high:.2f}€<br>"
        text += f"• Bas: {prediction.target_low:.2f}€</p>"
        
        text += "<p><b>Timeline:</b><br>"
        text += f"• 2-6h: {prediction.timeframe_short:.2f}€<br>"
        text += f"• 1-2j: {prediction.timeframe_medium:.2f}€<br>"
        text += f"• 1 sem: {prediction.timeframe_long:.2f}€</p>"
        
        text += f"<p><b>Opportunité:</b> {opportunity.score}/10</p>"
        
        if prediction.signals:
            text += "<p><b>Signaux:</b><br>"
            for signal in prediction.signals[:3]:
                text += f"• {signal}<br>"
            text += "</p>"
        
        return text
    
    @pyqtSlot(Alert)
    def _on_alert_triggered(self, alert: Alert):
        """Callback alerte déclenchée"""
        logger.info(f"Alert received in GUI: {alert.message}")
        self._add_alert_card(alert)
    
    def _add_alert_card(self, alert: Alert):
        """Ajoute une carte d'alerte"""
        colors = {
            "info": "#2196F3",
            "warning": "#FF9800",
            "important": "#FF5722",
            "critical": "#F44336"
        }
        
        card = QFrame()
        card.setFrameStyle(QFrame.Shape.StyledPanel)
        card.setStyleSheet(f"background-color: {colors.get(alert.alert_level.value, 'gray')}; "
                          "border-radius: 5px; padding: 10px;")
        
        layout = QVBoxLayout(card)
        
        # Header
        header_layout = QHBoxLayout()
        
        header_label = QLabel(f"<b>{alert.symbol} - {alert.alert_type.value}</b>")
        header_layout.addWidget(header_label)
        
        ack_btn = QPushButton("✓")
        ack_btn.setFixedSize(30, 30)
        ack_btn.clicked.connect(lambda: self._acknowledge_alert(alert, card))
        header_layout.addWidget(ack_btn)
        
        layout.addLayout(header_layout)
        
        # Message
        msg_label = QLabel(alert.message)
        msg_label.setWordWrap(True)
        layout.addWidget(msg_label)
        
        # Timestamp
        time_label = QLabel(alert.timestamp.strftime('%H:%M:%S'))
        time_label.setStyleSheet("color: lightgray; font-size: 10px;")
        layout.addWidget(time_label)
        
        # Ajouter au début de la liste
        self.alerts_layout.insertWidget(0, card)
    
    def _acknowledge_alert(self, alert: Alert, card: QFrame):
        """Acquitte une alerte"""
        self.alert_service.acknowledge_alert(alert.alert_id)
        card.deleteLater()
        logger.debug(f"Alert acknowledged: {alert.alert_id}")
    
    def _start_monitoring(self):
        """Démarre la surveillance"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_button.setEnabled(False)
        self.stop_button.setEnabled(True)
        self.status_label.setText("● En cours")
        self.status_label.setStyleSheet("color: #4caf50;")
        
        # Créer et démarrer worker
        self.worker = MonitorWorker(
            self.config, self.market_service, 
            self.alert_service, self.telegram_api
        )
        self.worker.alert_triggered.connect(self._on_alert_triggered)
        self.worker.data_updated.connect(self._update_display)
        self.worker.error_occurred.connect(self._on_error)
        self.worker.start()
        
        logger.info("Monitoring started")
        QMessageBox.information(self, "Démarré", "Surveillance démarrée avec succès !")
    
    def _stop_monitoring(self):
        """Arrête la surveillance"""
        if not self.is_running:
            return
        
        self.is_running = False
        
        if self.worker:
            self.worker.stop()
            self.worker.wait(5000)  # Attendre max 5 secondes
        
        self.start_button.setEnabled(True)
        self.stop_button.setEnabled(False)
        self.status_label.setText("● Arrêté")
        self.status_label.setStyleSheet("color: gray;")
        
        logger.info("Monitoring stopped")
        QMessageBox.information(self, "Arrêté", "Surveillance arrêtée")
    
    @pyqtSlot(str, str)
    def _on_error(self, symbol: str, error: str):
        """Gère les erreurs du worker"""
        logger.error(f"Worker error for {symbol}: {error}")
    
    def _on_crypto_changed(self, symbol: str):
        """Callback changement crypto"""
        self._refresh_data()
    
    def _on_detail_changed(self, detail: str):
        """Callback changement niveau de détail"""
        symbol = self.crypto_selector.currentText()
        if symbol in self.predictions_cache and symbol in self.opportunity_cache:
            self._update_prediction_panel(
                self.predictions_cache[symbol],
                self.opportunity_cache[symbol]
            )
    
    def _test_telegram(self):
        """Teste Telegram"""
        success = self.telegram_api.send_message("🚀 Test - Crypto Bot v3.0 (PyQt6)")
        
        if success:
            QMessageBox.information(self, "Telegram", 
                                   "Message de test envoyé avec succès !")
        else:
            QMessageBox.warning(self, "Telegram", 
                               "Échec de l'envoi du message de test")
    
    def closeEvent(self, event):
        """Gère la fermeture de l'application"""
        if self.is_running:
            reply = QMessageBox.question(
                self, "Confirmation",
                "La surveillance est en cours. Voulez-vous vraiment quitter ?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self._stop_monitoring()
                event.accept()
            else:
                event.ignore()
        else:
            event.accept()


def main():
    """Point d'entrée"""
    from core.models import BotConfiguration
    
    app = QApplication(sys.argv)
    
    # Configuration test
    config = BotConfiguration()
    config.crypto_symbols = ["BTC", "ETH", "SOL"]
    
    window = CryptoBotGUI(config)
    window.show()
    
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
