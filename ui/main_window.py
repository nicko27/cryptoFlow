"""Application GUI PyQt6 - Crypto Bot v3.0"""
from datetime import datetime
from typing import Optional, List

from PyQt6.QtWidgets import (
    QMainWindow,
    QWidget,
    QVBoxLayout,
    QHBoxLayout,
    QPushButton,
    QLabel,
    QComboBox,
    QTextEdit,
    QGroupBox,
    QGridLayout,
    QScrollArea,
    QMessageBox,
)
from PyQt6.QtCore import QTimer, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QFont
import matplotlib

matplotlib.use("Qt5Agg")
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates

from core.models import BotConfiguration, MarketData, Prediction, Alert, AlertLevel
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from core.services.summary_service import SummaryService
from api.binance_api import BinanceAPI
from daemon.daemon_service import DaemonService


class MplCanvas(FigureCanvasQTAgg):
    def __init__(self, parent: Optional[QWidget] = None, width: int = 10, height: int = 6, dpi: int = 100):
        fig = Figure(figsize=(width, height), dpi=dpi, facecolor="#2b2b2b")
        self.axes = fig.add_subplot(111, facecolor="#2b2b2b")
        super().__init__(fig)


class MonitorThread(QThread):
    alert_signal = pyqtSignal(Alert)

    def __init__(self, config: BotConfiguration, market_service: MarketService,
                 alert_service: AlertService, telegram_api):
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
                except Exception as exc:  # pragma: no cover - logging only
                    print(f"Erreur surveillance {symbol}: {exc}")
            self.msleep(self.config.check_interval_seconds * 1000)

    def stop(self):
        self.running = False


class DaemonThread(QThread):
    started_signal = pyqtSignal()
    stopped_signal = pyqtSignal()

    def __init__(self, daemon_service: DaemonService):
        super().__init__()
        self.daemon_service = daemon_service

    def run(self):
        self.started_signal.emit()
        try:
            self.daemon_service.start()
        finally:
            self.stopped_signal.emit()

    def stop(self):
        self.daemon_service.stop()


class CryptoBotGUI(QMainWindow):
    def __init__(
        self,
        config: BotConfiguration,
        db_service,
        portfolio_service,
        dca_service,
        report_service,
        chart_service,
        telegram_api,
        summary_service,
    ):
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

        self.binance_api = BinanceAPI()
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(self.config)

        # Threads
        self.monitor_thread: Optional[MonitorThread] = None
        self.daemon_thread: Optional[DaemonThread] = None
        self.daemon_service: Optional[DaemonService] = None

        # Fenêtre
        self.setWindowTitle("Crypto Bot v3.0 - Dashboard PyQt6")
        self.setGeometry(100, 100, 1400, 900)

        self.setup_ui()

        # Rafraîchissement périodique
        self.update_timer = QTimer(self)
        self.update_timer.timeout.connect(self.update_display)
        self.update_timer.start(5000)
        self.update_display()

    # ------------------------------------------------------------------
    # UI helpers
    # ------------------------------------------------------------------
    def setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QHBoxLayout(central)
        main_layout.addWidget(self.create_sidebar(), stretch=1)
        main_layout.addWidget(self.create_charts_area(), stretch=4)
        main_layout.addWidget(self.create_info_panel(), stretch=1)

    def create_sidebar(self) -> QWidget:
        sidebar = QWidget()
        layout = QVBoxLayout(sidebar)

        title = QLabel("🚀 Crypto Bot v3.0")
        title.setFont(QFont("Arial", 20, QFont.Weight.Bold))
        title.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(title)

        self.status_label = QLabel("● Arrêté")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)

        self.daemon_status_label = QLabel("Daemon: arrêté")
        self.daemon_status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.daemon_status_label.setStyleSheet("color: gray;")
        layout.addWidget(self.daemon_status_label)

        self.start_btn = QPushButton("▶ Démarrer")
        self.start_btn.setStyleSheet("background-color: green; color: white; padding: 10px;")
        self.start_btn.clicked.connect(self.start_monitoring)
        layout.addWidget(self.start_btn)

        self.stop_btn = QPushButton("⏸ Arrêter")
        self.stop_btn.setStyleSheet("background-color: red; color: white; padding: 10px;")
        self.stop_btn.clicked.connect(self.stop_monitoring)
        self.stop_btn.setEnabled(False)
        layout.addWidget(self.stop_btn)

        self.daemon_start_btn = QPushButton("🟢 Lancer le daemon")
        self.daemon_start_btn.setStyleSheet("background-color: #1565C0; color: white; padding: 10px;")
        self.daemon_start_btn.clicked.connect(self.start_daemon)
        layout.addWidget(self.daemon_start_btn)

        self.daemon_stop_btn = QPushButton("⛔ Arrêter le daemon")
        self.daemon_stop_btn.setStyleSheet("background-color: #B71C1C; color: white; padding: 10px;")
        self.daemon_stop_btn.clicked.connect(self.stop_daemon)
        self.daemon_stop_btn.setEnabled(False)
        layout.addWidget(self.daemon_stop_btn)

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

        report_btn = QPushButton("📝 Générer un rapport")
        report_btn.clicked.connect(self._generate_report)
        layout.addWidget(report_btn)

        summary_btn = QPushButton("🧾 Résumé Telegram")
        summary_btn.clicked.connect(self._send_summary_to_telegram)
        layout.addWidget(summary_btn)

        dca_btn = QPushButton("💡 Plan DCA Telegram")
        dca_btn.clicked.connect(self._send_dca_plan_to_telegram)
        layout.addWidget(dca_btn)

        chart_btn = QPushButton("📈 Graphique Telegram")
        chart_btn.clicked.connect(self._send_price_chart_to_telegram)
        layout.addWidget(chart_btn)

        telegram_report_btn = QPushButton("📄 Rapport Telegram")
        telegram_report_btn.clicked.connect(self._send_report_to_telegram)
        layout.addWidget(telegram_report_btn)

        status_btn = QPushButton("📊 Statut du daemon")
        status_btn.clicked.connect(self._show_daemon_status)
        layout.addWidget(status_btn)

        settings_btn = QPushButton("⚙️ Paramètres")
        settings_btn.clicked.connect(self._open_settings)
        layout.addWidget(settings_btn)

        layout.addStretch()

        version = QLabel("v3.0 PyQt6")
        version.setAlignment(Qt.AlignmentFlag.AlignCenter)
        version.setStyleSheet("color: gray;")
        layout.addWidget(version)

        return sidebar

    def create_charts_area(self) -> QWidget:
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

    def create_indicator_card(self, title: str, value: str) -> QGroupBox:
        card = QGroupBox(title)
        layout = QVBoxLayout(card)
        label = QLabel(value)
        label.setFont(QFont("Arial", 18, QFont.Weight.Bold))
        label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(label)
        return card

    def create_info_panel(self) -> QWidget:
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

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def update_display(self):
        if not self.config.crypto_symbols:
            return

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
        except Exception as exc:  # pragma: no cover - logging only
            print(f"Erreur: {exc}")

    def update_chart(self, market_data: MarketData):
        if not market_data.price_history:
            return

        self.price_canvas.axes.clear()
        timestamps = [p.timestamp for p in market_data.price_history]
        prices = [p.price_eur for p in market_data.price_history]
        self.price_canvas.axes.plot(timestamps, prices, linewidth=2, color="#2196F3")

        if self.config.enable_price_levels and market_data.symbol in self.config.price_levels:
            levels = self.config.price_levels[market_data.symbol]
            if "low" in levels:
                self.price_canvas.axes.axhline(
                    y=levels["low"], color="green", linestyle=":", linewidth=2, alpha=0.7
                )
            if "high" in levels:
                self.price_canvas.axes.axhline(
                    y=levels["high"], color="red", linestyle=":", linewidth=2, alpha=0.7
                )

        self.price_canvas.axes.set_xlabel("Temps", color="white")
        self.price_canvas.axes.set_ylabel("Prix (€)", color="white")
        self.price_canvas.axes.set_title(
            f"{market_data.symbol} - Prix temps réel",
            color="white",
            fontsize=14,
            fontweight="bold",
        )
        self.price_canvas.axes.tick_params(colors="white")
        self.price_canvas.axes.grid(True, alpha=0.3, color="gray")
        self.price_canvas.axes.xaxis.set_major_formatter(mdates.DateFormatter("%H:%M"))
        self.price_canvas.figure.autofmt_xdate()
        self.price_canvas.draw()

    def update_indicators(self, market_data: MarketData, prediction: Prediction, opportunity):
        price_label = self.price_label.findChild(QLabel)
        if price_label and market_data.current_price and market_data.current_price.price_eur is not None:
            price_label.setText(f"{market_data.current_price.price_eur:.2f} €")

        change_label = self.change_label.findChild(QLabel)
        change = market_data.current_price.change_24h if market_data.current_price else None
        if change_label:
            if change is not None:
                color = "green" if change > 0 else "red"
                change_label.setText(f"{change:+.2f}%")
                change_label.setStyleSheet(f"color: {color};")
            else:
                change_label.setText("N/A")
                change_label.setStyleSheet("color: gray;")

        rsi_value = market_data.technical_indicators.rsi if market_data.technical_indicators else None
        rsi_label = self.rsi_label.findChild(QLabel)
        if rsi_label:
            if rsi_value is not None:
                rsi_color = "green" if rsi_value < 40 else "red" if rsi_value > 60 else "white"
                rsi_label.setText(f"{rsi_value:.0f}")
                rsi_label.setStyleSheet(f"color: {rsi_color};")
            else:
                rsi_label.setText("N/A")
                rsi_label.setStyleSheet("color: gray;")

        opp_label = self.opp_label.findChild(QLabel)
        if opp_label:
            score = opportunity.score if opportunity else 0
            opp_color = "green" if score >= 7 else "orange" if score >= 5 else "red"
            opp_label.setText(f"{score}/10 ⭐")
            opp_label.setStyleSheet(f"color: {opp_color};")

    def update_prediction(self, prediction: Prediction, opportunity):
        if not prediction or not opportunity:
            self.prediction_text.setText("Données indisponibles")
            return

        detail = self.detail_combo.currentText()
        if detail == "Simple":
            text = (
                f"{prediction.direction} {prediction.prediction_type.value}\n\n"
                f"Confiance: {prediction.confidence}%\n\n"
                f"Score: {opportunity.score}/10\n{opportunity.recommendation}"
            )
        else:
            text = (
                f"{prediction.direction} {prediction.prediction_type.value}\n"
                f"Confiance: {prediction.confidence}%\n"
                f"Trend: {prediction.trend_score}\n\n"
                f"Opportunité: {opportunity.score}/10\n{opportunity.recommendation}\n"
            )
            reasons = getattr(opportunity, "reasons", []) or []
            if reasons:
                text += "\nRaisons:\n"
                for reason in reasons[:3]:
                    text += f"• {reason}\n"

        self.prediction_text.setText(text)

    def _collect_market_context(self, symbols: Optional[List[str]] = None, refresh: bool = True):
        markets = {}
        predictions = {}
        opportunities = {}

        for symbol in symbols or self.config.crypto_symbols:
            try:
                market = self.market_service.get_market_data(symbol, refresh=refresh)
                if not market:
                    continue
                prediction = self.market_service.predict_price_movement(market)
                opportunity = self.market_service.calculate_opportunity_score(market, prediction)
                markets[symbol] = market
                predictions[symbol] = prediction
                opportunities[symbol] = opportunity
            except Exception as exc:  # pragma: no cover - logging only
                print(f"Erreur collecte données {symbol}: {exc}")

        return markets, predictions, opportunities

    def _send_large_telegram_message(self, text: str, chunk_size: int = 3500) -> bool:
        if not text:
            return False

        total_length = len(text)
        for start in range(0, total_length, chunk_size):
            chunk = text[start:start + chunk_size]
            prefix = "" if start == 0 else "…\n"
            sent = self.telegram_api.send_message(prefix + chunk)
            if not sent:
                return False
        return True

    def _send_price_chart_to_telegram(self):
        symbols = self.config.crypto_symbols or []
        if not symbols:
            symbol = self.crypto_combo.currentText()
            if not symbol:
                self._show_error("Graphique", "Aucun symbole sélectionné.")
                return
            symbols = [symbol]

        markets, predictions, opportunities = self._collect_market_context(symbols=symbols, refresh=False)
        if hasattr(self.report_service, "configure"):
            self.report_service.configure(self.config)

        success_count = 0
        failure_count = 0
        notification_success = 0

        for symbol in symbols:
            market = markets.get(symbol)
            prediction = predictions.get(symbol)
            opportunity = opportunities.get(symbol)

            sent_message = False
            if hasattr(self.report_service, "generate_coin_notification"):
                message = self.report_service.generate_coin_notification(symbol, market, prediction, opportunity)
                if message:
                    try:
                        if self.telegram_api.send_message(message, use_queue=False):
                            notification_success += 1
                            sent_message = True
                    except Exception as exc:
                        self._show_error("Notification", f"Erreur message {symbol}: {exc}")

            notif_options = self.report_service.get_notification_options(symbol)
            show_curves = notif_options.get(
                "show_curves",
                self.config.notification_include_chart,
            )
            if not show_curves or not sent_message:
                continue

            timeframes = self.report_service.get_notification_timeframes(symbol)
            for timeframe in timeframes:
                prices = self.market_service.get_price_history(symbol, hours=timeframe)
                if not prices:
                    failure_count += 1
                    continue

                chart_buffer = self.chart_service.generate_price_chart(
                    symbol,
                    prices,
                    show_levels=self.config.show_levels_on_graph,
                    price_levels=self.config.price_levels.get(symbol) if self.config.price_levels else None,
                )
                if not chart_buffer:
                    failure_count += 1
                    continue

                caption = f"{symbol} — Graphique {timeframe}h"
                try:
                    sent = self.telegram_api.send_photo(chart_buffer, caption, use_queue=False)
                    chart_buffer.close()
                    if sent:
                        success_count += 1
                    else:
                        failure_count += 1
                except Exception as exc:
                    chart_buffer.close()
                    failure_count += 1
                    self._show_error("Graphique", f"Erreur {symbol} ({timeframe}h): {exc}")

        messages = []
        if notification_success:
            messages.append(f"{notification_success} notification(s) texte envoyée(s)")
        if success_count:
            messages.append(f"{success_count} graphique(s) envoyé(s)")
        if failure_count:
            messages.append(f"{failure_count} graphique(s) en échec")

        if messages:
            self._show_info("Graphique", "; ".join(messages))
        else:
            self._show_error("Graphique", "Aucune notification ni graphique n'a pu être envoyé.")

    def start_monitoring(self):
        if self.monitor_thread and self.monitor_thread.isRunning():
            return

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
            self.monitor_thread = None

        self.start_btn.setEnabled(True)
        self.stop_btn.setEnabled(False)
        self.status_label.setText("● Arrêté")
        self.status_label.setStyleSheet("color: gray;")

    def start_daemon(self):
        if self.daemon_thread and self.daemon_thread.isRunning():
            self._show_info("Daemon", "Le daemon est déjà en cours d'exécution.")
            return

        self.daemon_service = DaemonService(self.config)
        self.daemon_thread = DaemonThread(self.daemon_service)
        self.daemon_thread.started_signal.connect(lambda: self._update_daemon_status(True))
        self.daemon_thread.stopped_signal.connect(lambda: self._update_daemon_status(False))
        self.daemon_thread.start()

    def stop_daemon(self):
        if self.daemon_thread and self.daemon_thread.isRunning():
            self.daemon_thread.stop()
            self.daemon_thread.wait(5000)
            self.daemon_thread = None
            self.daemon_service = None
            self._update_daemon_status(False)

    def _update_daemon_status(self, running: bool):
        if running:
            self.daemon_status_label.setText("Daemon: en cours")
            self.daemon_status_label.setStyleSheet("color: green;")
            self.daemon_start_btn.setEnabled(False)
            self.daemon_stop_btn.setEnabled(True)
        else:
            self.daemon_status_label.setText("Daemon: arrêté")
            self.daemon_status_label.setStyleSheet("color: gray;")
            self.daemon_start_btn.setEnabled(True)
            self.daemon_stop_btn.setEnabled(False)

    def add_alert(self, alert: Alert):
        colors = {
            "INFO": "#2196F3",
            "WARNING": "#FF9800",
            "IMPORTANT": "#FF5722",
            "CRITICAL": "#F44336",
        }
        alert_widget = QGroupBox(f"{alert.symbol} - {alert.alert_type.value}")
        alert_widget.setStyleSheet(f"background-color: {colors.get(alert.alert_level.value.upper(), 'gray')};")
        layout = QVBoxLayout(alert_widget)

        msg = QLabel(alert.message)
        msg.setWordWrap(True)
        layout.addWidget(msg)

        time_label = QLabel(alert.timestamp.strftime("%H:%M:%S"))
        time_label.setStyleSheet("color: lightgray;")
        layout.addWidget(time_label)

        self.alerts_layout.addWidget(alert_widget)

    def test_telegram(self):
        success = self.telegram_api.send_message("🚀 Test - Crypto Bot v3.0 PyQt6")
        if success:
            self._show_info("Telegram", "Message envoyé !")
        else:
            self._show_error("Telegram", "Échec de l'envoi du message.")

    def _generate_report(self):
        markets_data, predictions, opportunities = self._collect_market_context()
        if not markets_data and not opportunities:
            self._show_error("Rapport", "Impossible de générer un rapport sans données.")
            return

        stats = self.db_service.get_stats_summary() if self.db_service else {}
        report = self.report_service.generate_complete_report(markets_data, predictions, opportunities, stats)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"/tmp/report_{timestamp}.txt"
        with open(filename, "w", encoding="utf-8") as handle:
            handle.write(report)

        self._show_info("Rapport", f"Rapport sauvegardé : {filename}")

    def _open_settings(self):
        from ui.settings_window import SettingsDialog

        def on_save(new_config: BotConfiguration):
            self.config = new_config
            self.alert_service = AlertService(self.config)
            # Refresh dependent services
            self.summary_service = SummaryService(self.config)
            self.report_service.configure(self.config)
            self.telegram_api.message_delay = self.config.telegram_message_delay
            self.crypto_combo.clear()
            self.crypto_combo.addItems(self.config.crypto_symbols)
            if self.monitor_thread:
                self.monitor_thread.config = self.config
                self.monitor_thread.alert_service = self.alert_service
            if self.daemon_service:
                if hasattr(self.daemon_service, "update_configuration"):
                    self.daemon_service.update_configuration(self.config)
                else:
                    self.daemon_service.config = self.config
            message = "Configuration mise à jour !"
            if self.daemon_service and getattr(self.daemon_service, "is_running", False):
                message += "\nRedémarrez le daemon pour appliquer toutes les modifications."
            self._show_info("Configuration", message)

        dialog = SettingsDialog(self, self.config, on_save)
        dialog.exec()

    # ------------------------------------------------------------------
    # Utilitaires
    # ------------------------------------------------------------------
    def _show_info(self, title: str, message: str):
        QMessageBox.information(self, title, message)

    def _show_error(self, title: str, message: str):
        QMessageBox.critical(self, title, message)

    # ------------------------------------------------------------------
    # Telegram helpers
    # ------------------------------------------------------------------

    def _send_summary_to_telegram(self):
        markets, predictions, opportunities = self._collect_market_context(refresh=False)
        if not markets and not opportunities:
            self._show_error("Résumé Telegram", "Aucune donnée disponible pour générer un résumé.")
            return

        summary = self.summary_service.generate_summary(
            markets,
            predictions,
            opportunities,
            simple=self.config.use_simple_language
        )
        if self.telegram_api.send_message(summary):
            self._show_info("Résumé Telegram", "Résumé envoyé avec succès.")
        else:
            self._show_error("Résumé Telegram", "Impossible d'envoyer le résumé.")

    def _send_report_to_telegram(self):
        markets, predictions, opportunities = self._collect_market_context(refresh=False)
        if not markets and not opportunities:
            self._show_error("Rapport Telegram", "Aucune donnée disponible pour générer un rapport.")
            return

        stats = self.db_service.get_stats_summary() if self.db_service else {}
        report = self.report_service.generate_complete_report(markets, predictions, opportunities, stats)
        if not report.strip():
            self._show_error("Rapport Telegram", "Rapport vide, envoi annulé.")
            return

        if self._send_large_telegram_message(report):
            self._show_info("Rapport Telegram", "Rapport envoyé sur Telegram.")
        else:
            self._show_error("Rapport Telegram", "Échec de l'envoi du rapport sur Telegram.")

        if self.config.notification_per_coin:
            notifications = self.report_service.generate_coin_notifications(markets, predictions, opportunities)
            for message in notifications:
                try:
                    self.telegram_api.send_message(message, use_queue=False)
                except Exception as exc:
                    self._show_error("Rapport Telegram", f"Erreur notification individuelle: {exc}")

    def _send_dca_plan_to_telegram(self):
        symbol = self.crypto_combo.currentText() or (self.config.crypto_symbols[0] if self.config.crypto_symbols else None)
        if not symbol:
            self._show_error("Plan DCA", "Aucun symbole sélectionné.")
            return

        markets, predictions, opportunities = self._collect_market_context(symbols=[symbol], refresh=False)
        market = markets.get(symbol)
        prediction = predictions.get(symbol)
        opportunity = opportunities.get(symbol)
        if not (market and prediction and opportunity):
            self._show_error("Plan DCA", "Données insuffisantes pour générer un plan DCA.")
            return

        plan = self.dca_service.generate_dca_plan(
            symbol,
            self.config.investment_amount,
            market.current_price.price_eur,
            market,
            prediction,
            opportunity
        )
        message = self.dca_service.format_dca_message(plan, simple=self.config.use_simple_language)
        if self.telegram_api.send_message(message):
            self._show_info("Plan DCA", "Plan DCA envoyé sur Telegram.")
        else:
            self._show_error("Plan DCA", "Impossible d'envoyer le plan DCA.")

    def _show_daemon_status(self):
        if not self.daemon_service:
            self._show_info("Daemon", "Le daemon n'est pas démarré.")
            return

        if not hasattr(self.daemon_service, "get_status"):
            self._show_error("Daemon", "La fonction de statut n'est pas disponible.")
            return

        status = self.daemon_service.get_status()

        def fmt_dt(value: Optional[datetime]) -> str:
            return value.strftime("%d/%m %H:%M:%S") if value else "—"

        queue_stats = status.get("queue", {})
        message = (
            f"En cours: {'Oui' if status.get('is_running') else 'Non'}\n"
            f"Dernière vérification: {fmt_dt(status.get('last_check_time'))}\n"
            f"Dernier résumé: {fmt_dt(status.get('last_summary_sent'))}\n"
            f"Vérifications: {status.get('checks_count', 0)}\n"
            f"Alertes envoyées: {status.get('alerts_sent', 0)}\n"
            f"Erreurs: {status.get('errors_count', 0)}\n"
            f"Uptime (s): {status.get('uptime_seconds', 0)}\n"
            f"Queue Telegram: {queue_stats.get('queue_size', 0)} en attente"
        )
        if status.get("last_error"):
            message += f"\nDernière erreur: {status['last_error']}"

        self._show_info("Statut du daemon", message)

    def closeEvent(self, event):
        self.stop_monitoring()
        self.stop_daemon()
        event.accept()
