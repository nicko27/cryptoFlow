"""Application GUI PyQt6 - Crypto Bot v3.0"""
from PyQt6.QtWidgets import (QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, QComboBox, QTextEdit, QGroupBox, QGridLayout, QScrollArea, QMessageBox)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib
matplotlib.use('Qt5Agg')
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
import sys
from core.models import BotConfiguration, MarketData, Prediction, Alert, AlertLevel
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI

class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent=None, width=10, height=6, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor='#2b2b2b')
        self.axes = fig.add_subplot(111, facecolor='#2b2b2b')
        super().__init__(fig)

class MonitorThread(QThread):
    alert_signal = pyqtSignal(Alert)
    def __init__(self, config, market_service, alert_service, telegram_api):
        super().__init__()
        self.config = config
        self.market_service = market_service
        self.alert_service = alert_service
        self.telegram_api = telegram_api
        self.running = False
    def run(self):
        self.running = True
        while self.running:
            for symbol in self.config.crypto_symbols:
                if not self.running:
                    break
                try:
                    market_data = self.market_service.get_market_data(symbol)
                    if market_data:
                        prediction = self.market_service.predict_price_movement(market_data)
                        alerts = self.alert_service.check_alerts(market_data, prediction)
                        for alert in alerts:
                            self.alert_signal.emit(alert)
                            if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                                self.telegram_api.send_alert(alert, include_metadata=True)
                except Exception as e:
                    print(f"Erreur surveillance {symbol}: {e}")
            self.msleep(self.config.check_interval_seconds * 1000)
    def stop(self):
        self.running = False

class CryptoBotGUI(ctk.CTk):
    def __init__(self, config, db_service, portfolio_service, dca_service,
                 report_service, chart_service, telegram_api, summary_service):
        super().__init__()
        
        # Services
        self.config = config
        self.db_service = db_service
        self.portfolio_service = portfolio_service
        self.dca_service = dca_service
        self.report_service = report_service
        self.chart_service = chart_service
        self.telegram_api = telegram_api
        self.summary_service = summary_service
        
        # ... reste du code ...
    
    def _update_stats(self):
        """Met à jour les statistiques - IMPLÉMENTÉE"""
        stats = self.db_service.get_stats_summary(days=7)
        
        self.stats_labels["Checks"].configure(text=str(stats["total_checks"]))
        self.stats_labels["Alertes envoyées"].configure(text=str(stats["total_alerts"]))
        self.stats_labels["Dernière vérification"].configure(
            text=datetime.now().strftime('%H:%M:%S')
        )
    
    def _generate_report(self):
        """Génère un rapport complet - IMPLÉMENTÉE"""
        # Collecter données
        markets_data = {}
        predictions = {}
        opportunities = {}
        
        for symbol in self.config.crypto_symbols:
            market = self.market_service.get_market_data(symbol)
            if market:
                markets_data[symbol] = market
                predictions[symbol] = self.market_service.predict_price_movement(market)
                opportunities[symbol] = self.market_service.calculate_opportunity_score(
                    market, predictions[symbol]
                )
        
        # Générer rapport
        stats = self.db_service.get_stats_summary()
        report = self.report_service.generate_complete_report(
            markets_data, predictions, opportunities, stats
        )
        
        # Sauvegarder
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"report_{timestamp}.txt"
        
        with open(f"/tmp/{filename}", "w") as f:
            f.write(report)
        
        self._show_info("Rapport", f"Rapport sauvegardé : {filename}")
    
    def _open_settings(self):
        """Ouvre la fenêtre de configuration - IMPLÉMENTÉE"""
        from settings_window import SettingsWindow
        
        def on_save(new_config):
            self.config = new_config
            self._show_info("Configuration", "Configuration mise à jour !")
        
        settings = SettingsWindow(self, self.config, on_save)
    
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.addWidget(self.create_sidebar(), stretch=1)
        main_layout.addWidget(self.create_charts_area(), stretch=4)
        main_layout.addWidget(self.create_info_panel(), stretch=1)
    
    def create_sidebar(self):
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)
        title = QLabel("🚀 Crypto Bot v3.0")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)
        self.status_label = QLabel("● Arrêté")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        self.start_btn = QPushButton("▶ Démarrer")
        self.start_btn.setStyleSheet("background-color: green; color: white; padding: 10px;")
        self.start_btn.clicked.connect(self.start_monitoring)
        layout.addWidget(self.start_btn)
        self.stop_btn = QPushButton("⏸ Arrêter")
        self.stop_btn.setStyleSheet("background-color: red; color: white; padding: 10px;")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)
        layout.addWidget(QLabel("Crypto:"))
        self.crypto_combo = QComboBox()
        self.crypto_combo.addItems(self.config.crypto_symbols)
        self.crypto_combo.currentTextChanged.connect(self.update_display)
        layout.addWidget(self.crypto_combo)
        layout.addWidget(QLabel("Niveau:"))
        self.detail_combo = QComboBox()
        self.detail_combo.addItems(["Simple", "Normal", "Expert"])
        self.detail_combo.setCurrentText("Normal")
        layout.addWidget(self.detail_combo)
        test_btn = QPushButton("📤 Test Telegram")
        test_btn.clicked.connect(self.test_telegram)
        layout.addWidget(test_btn)
        layout.addStretch()
        version = QLabel("v3.0 PyQt6")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: gray;")
        layout.addWidget(version)
        return sidebar
    
    def create_charts_area(self):
        charts = QWidget()
        layout = QVBoxLayout(charts)
        self.price_canvas = MplCanvas(self, width=10, height=6)
        layout.addWidget(self.price_canvas, stretch=3)
        indicators = QWidget()
        ind_layout = QGridLayout(indicators)
        self.price_label = self.create_indicator_card("💰 Prix", "0.00 €")
        ind_layout.addWidget(self.price_label, 0, 0)
        self.change_label = self.create_indicator_card("📊 24h", "0.00%")
        ind_layout.addWidget(self.change_label, 0, 1)
        self.rsi_label = self.create_indicator_card("📈 RSI", "50")
        ind_layout.addWidget(self.rsi_label, 0, 2)
        self.opp_label = self.create_indicator_card("⭐ Opportunité", "5/10")
        ind_layout.addWidget(self.opp_label, 0, 3)
        layout.addWidget(indicators, stretch=1)
        return charts
    
    def create_indicator_card(self, title, value):
        card = QGroupBox(title)
        layout = QVBoxLayout(card)
        label = QLabel(value)
        label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return card
    
    def create_info_panel(self):
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.addWidget(QLabel("🔮 Prédiction"))
        self.prediction_text = QTextEdit()
        self.prediction_text.setReadOnly(True)
        self.prediction_text.setMaximumHeight(200)
        layout.addWidget(self.prediction_text)
        layout.addWidget(QLabel("🚨 Alertes"))
        self.alerts_scroll = QScrollArea()
        self.alerts_widget = QWidget()
        self.alerts_layout = QVBoxLayout(self.alerts_widget)
        self.alerts_scroll.setWidget(self.alerts_widget)
        self.alerts_scroll.setWidgetResizable(True)
        layout.addWidget(self.alerts_scroll)
        return panel
    
    def update_display(self):
        symbol = self.crypto_combo.currentText()
        try:
            market_data = self.market_service.get_market_data(symbol)
            if not market_data:
                return
            prediction = self.market_service.predict_price_movement(market_data)
            opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
            self.update_chart(market_data)
            self.update_indicators(market_data, prediction, opportunity)
            self.update_prediction(prediction, opportunity)
        except Exception as e:
            print(f"Erreur: {e}")
    
    def update_chart(self, market_data: MarketData):
        if not market_data.price_history:
            return
        self.price_canvas.axes.clear()
        timestamps = [p.timestamp for p in market_data.price_history]
        prices = [p.price_eur for p in market_data.price_history]
        self.price_canvas.axes.plot(timestamps, prices, linewidth=2, color='#2196F3')
        if self.config.enable_price_levels and market_data.symbol in self.config.price_levels:
            levels = self.config.price_levels[market_data.symbol]
            if "low" in levels:
                self.price_canvas.axes.axhline(y=levels["low"], color='green', linestyle=':', linewidth=2, alpha=0.7)
            if "high" in levels:
                self.price_canvas.axes.axhline(y=levels["high"], color='red', linestyle=':', linewidth=2, alpha=0.7)
        self.price_canvas.axes.set_xlabel('Temps', color='white')
        self.price_canvas.axes.set_ylabel('Prix (€)', color='white')
        self.price_canvas.axes.set_title(f'{market_data.symbol} - Prix temps réel', color='white', fontsize=14, fontweight='bold')
        self.price_canvas.axes.tick_params(colors='white')
        self.price_canvas.axes.grid(True, alpha=0.3, color='gray')
        self.price_canvas.axes.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.price_canvas.figure.autofmt_xdate()
        self.price_canvas.draw()
    
    def update_indicators(self, market_data, prediction, opportunity):
        self.price_label.findChild(QLabel).setText(f"{market_data.current_price.price_eur:.2f} €")
        change = market_data.current_price.change_24h
        color = "green" if change > 0 else "red"
        change_label = self.change_label.findChild(QLabel)
        change_label.setText(f"{change:+.2f}%")
        change_label.setStyleSheet(f"color: {color};")
        rsi = market_data.technical_indicators.rsi
        rsi_color = "green" if rsi < 40 else "red" if rsi > 60 else "white"
        rsi_label = self.rsi_label.findChild(QLabel)
        rsi_label.setText(f"{rsi:.0f}")
        rsi_label.setStyleSheet(f"color: {rsi_color};")
        score = opportunity.score
        opp_color = "green" if score >= 7 else "orange" if score >= 5 else "red"
        opp_label = self.opp_label.findChild(QLabel)
        opp_label.setText(f"{score}/10 ⭐")
        opp_label.setStyleSheet(f"color: {opp_color};")
    
    def update_prediction(self, prediction, opportunity):
        detail = self.detail_combo.currentText()
        if detail == "Simple":
            text = f"{prediction.direction} {prediction.prediction_type.value}\\n\\nConfiance: {prediction.confidence}%\\n\\nScore: {opportunity.score}/10\\n{opportunity.recommendation}"
        else:
            text = f"{prediction.direction} {prediction.prediction_type.value}\\nConfiance: {prediction.confidence}%\\nTrend: {prediction.trend_score}\\n\\nOpportunité: {opportunity.score}/10\\n{opportunity.recommendation}\\n\\nRaisons:\\n"
            for reason in opportunity.reasons[:3]:
                text += f"• {reason}\\n"
        self.prediction_text.setText(text)
    
    def start_monitoring(self):
        self.start_btn.setEnabled(False)
        self.stop_btn.setEnabled(True)
        self.status_label.setText("● En cours")
        self.status_label.setStyleSheet("color: green;")
        self.monitor_thread = MonitorThread(self.config, self.market_service, self.alert_service, self.telegram_api)
        self.monitor_thread.alert_signal.connect(self.add_alert)
        self.monitor_thread.start()
    
    def stop_monitoring(self):
        if self.monitor_thread:
            self.monitor_thread.stop()
            self.monitor_thread.wait()
        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● Arrêté")
        self.status_label.setStyleSheet("color: gray;")
    
    def add_alert(self, alert: Alert):
        colors = {"INFO": "#2196F3", "WARNING": "#FF9800", "IMPORTANT": "#FF5722", "CRITICAL": "#F44336"}
        alert_widget = QGroupBox(f"{alert.symbol} - {alert.alert_type.value}")
        alert_widget.setStyleSheet(f"background-color: {colors.get(alert.alert_level.value.upper(), 'gray')};")
        layout = QVBoxLayout(alert_widget)
        msg = QLabel(alert.message)
        msg.setWordWrap(True)
        layout.addWidget(msg)
        time_label = QLabel(alert.timestamp.strftime('%H:%M:%S'))
        time_label.setStyleSheet("color: lightgray;")
        layout.addWidget(time_label)
        self.alerts_layout.addWidget(alert_widget)
    
    def test_telegram(self):
        success = self.telegram_api.send_message("🚀 Test - Crypto Bot v3.0 PyQt6")
        if success:
            QMessageBox.information(self, "Telegram", "Message envoyé!")
        else:
            QMessageBox.critical(self, "Telegram", "Échec envoi")
    
    def closeEvent(self, event):
        self.stop_monitoring()
        event.accept()
