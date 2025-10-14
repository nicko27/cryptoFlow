"""
Application GUI Principale - Crypto Bot v3.0
Interface graphique complète avec graphiques en temps réel
"""

import customtkinter as ctk
from tkinter import ttk
import matplotlib.pyplot as plt
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg
from matplotlib.figure import Figure
import matplotlib.dates as mdates
from typing import Dict, List, Optional
from datetime import datetime
import threading
import time

from core.models import *
from core.services.market_service import MarketService
from core.services.alert_service import AlertService
from api.binance_api import BinanceAPI
from api.telegram_api import TelegramAPI


# Configuration du thème
ctk.set_appearance_mode("dark")
ctk.set_default_color_theme("blue")


class CryptoBot GUI(ctk.CTk):
    """Application principale avec interface graphique"""
    
    def __init__(self, config: BotConfiguration):
        super().__init__()
        
        self.config = config
        self.is_running = False
        self.monitor_thread = None
        
        # Services
        self.binance_api = BinanceAPI()
        self.telegram_api = TelegramAPI(config.telegram_bot_token, config.telegram_chat_id)
        self.market_service = MarketService(self.binance_api)
        self.alert_service = AlertService(config)
        
        # Données
        self.market_data_cache: Dict[str, MarketData] = {}
        self.predictions_cache: Dict[str, Prediction] = {}
        
        # Configuration de la fenêtre
        self.title("Crypto Bot v3.0 - Dashboard")
        self.geometry("1400x900")
        
        # Créer l'interface
        self._create_ui()
        
        # Enregistrer callback alertes
        self.alert_service.register_callback(self._on_new_alert)
        
        # Charger les données initiales
        self.after(100, self._initial_load)
    
    def _create_ui(self):
        """Crée l'interface utilisateur"""
        
        # Layout principal : 3 colonnes
        self.grid_columnconfigure(0, weight=0)  # Sidebar
        self.grid_columnconfigure(1, weight=3)  # Graphiques
        self.grid_columnconfigure(2, weight=1)  # Infos/Alertes
        self.grid_rowconfigure(0, weight=1)
        
        # === SIDEBAR (Colonne 0) ===
        self._create_sidebar()
        
        # === GRAPHIQUES (Colonne 1) ===
        self._create_chart_area()
        
        # === INFOS & ALERTES (Colonne 2) ===
        self._create_info_panel()
    
    def _create_sidebar(self):
        """Crée la sidebar avec contrôles"""
        sidebar = ctk.CTkFrame(self, width=250, corner_radius=0)
        sidebar.grid(row=0, column=0, sticky="nsew", padx=0, pady=0)
        sidebar.grid_rowconfigure(10, weight=1)
        
        # Logo/Titre
        title_label = ctk.CTkLabel(
            sidebar,
            text="🚀 Crypto Bot v3.0",
            font=ctk.CTkFont(size=20, weight="bold")
        )
        title_label.grid(row=0, column=0, padx=20, pady=20)
        
        # Statut
        self.status_label = ctk.CTkLabel(
            sidebar,
            text="● Arrêté",
            text_color="gray",
            font=ctk.CTkFont(size=14)
        )
        self.status_label.grid(row=1, column=0, padx=20, pady=10)
        
        # Boutons Start/Stop
        self.start_button = ctk.CTkButton(
            sidebar,
            text="▶ Démarrer",
            command=self._start_monitoring,
            fg_color="green",
            hover_color="darkgreen"
        )
        self.start_button.grid(row=2, column=0, padx=20, pady=10, sticky="ew")
        
        self.stop_button = ctk.CTkButton(
            sidebar,
            text="⏸ Arrêter",
            command=self._stop_monitoring,
            fg_color="red",
            hover_color="darkred",
            state="disabled"
        )
        self.stop_button.grid(row=3, column=0, padx=20, pady=10, sticky="ew")
        
        # Sélection crypto
        ctk.CTkLabel(sidebar, text="Crypto:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=4, column=0, padx=20, pady=(20, 5), sticky="w"
        )
        
        self.crypto_selector = ctk.CTkOptionMenu(
            sidebar,
            values=self.config.crypto_symbols,
            command=self._on_crypto_changed
        )
        self.crypto_selector.grid(row=5, column=0, padx=20, pady=5, sticky="ew")
        
        # Intervalle
        ctk.CTkLabel(sidebar, text="Intervalle:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=6, column=0, padx=20, pady=(20, 5), sticky="w"
        )
        
        interval_values = ["5 min", "15 min", "30 min", "1h", "4h"]
        self.interval_selector = ctk.CTkOptionMenu(sidebar, values=interval_values)
        self.interval_selector.grid(row=7, column=0, padx=20, pady=5, sticky="ew")
        
        # Niveau de détail
        ctk.CTkLabel(sidebar, text="Détail:", font=ctk.CTkFont(size=12, weight="bold")).grid(
            row=8, column=0, padx=20, pady=(20, 5), sticky="w"
        )
        
        self.detail_level = ctk.CTkSegmentedButton(
            sidebar,
            values=["Simple", "Normal", "Expert"],
            command=self._on_detail_changed
        )
        self.detail_level.set("Normal")
        self.detail_level.grid(row=9, column=0, padx=20, pady=5, sticky="ew")
        
        # Boutons actions
        ctk.CTkButton(
            sidebar,
            text="📊 Rapport complet",
            command=self._generate_report
        ).grid(row=11, column=0, padx=20, pady=5, sticky="ew")
        
        ctk.CTkButton(
            sidebar,
            text="⚙️ Configuration",
            command=self._open_settings
        ).grid(row=12, column=0, padx=20, pady=5, sticky="ew")
        
        ctk.CTkButton(
            sidebar,
            text="📤 Test Telegram",
            command=self._test_telegram
        ).grid(row=13, column=0, padx=20, pady=5, sticky="ew")
        
        # Version/Credits
        ctk.CTkLabel(
            sidebar,
            text="v3.0 | by CryptoBot",
            font=ctk.CTkFont(size=10),
            text_color="gray"
        ).grid(row=14, column=0, padx=20, pady=20)
    
    def _create_chart_area(self):
        """Crée la zone de graphiques"""
        chart_frame = ctk.CTkFrame(self)
        chart_frame.grid(row=0, column=1, sticky="nsew", padx=10, pady=10)
        chart_frame.grid_rowconfigure(0, weight=2)
        chart_frame.grid_rowconfigure(1, weight=1)
        chart_frame.grid_columnconfigure(0, weight=1)
        
        # === GRAPHIQUE PRIX ===
        price_chart_frame = ctk.CTkFrame(chart_frame)
        price_chart_frame.grid(row=0, column=0, sticky="nsew", padx=5, pady=5)
        
        # Créer figure matplotlib
        self.price_figure = Figure(figsize=(10, 6), facecolor='#2b2b2b')
        self.price_ax = self.price_figure.add_subplot(111, facecolor='#2b2b2b')
        
        self.price_canvas = FigureCanvasTkAgg(self.price_figure, price_chart_frame)
        self.price_canvas.get_tk_widget().pack(fill="both", expand=True)
        
        # === INDICATEURS ===
        indicators_frame = ctk.CTkFrame(chart_frame)
        indicators_frame.grid(row=1, column=0, sticky="nsew", padx=5, pady=5)
        indicators_frame.grid_columnconfigure((0, 1, 2, 3), weight=1)
        
        # Prix actuel
        self.price_card = self._create_indicator_card(
            indicators_frame, "💰 Prix", "0.00 €", row=0, col=0
        )
        
        # Changement 24h
        self.change_card = self._create_indicator_card(
            indicators_frame, "📊 24h", "0.00%", row=0, col=1
        )
        
        # RSI
        self.rsi_card = self._create_indicator_card(
            indicators_frame, "📈 RSI", "50", row=0, col=2
        )
        
        # Score opportunité
        self.opportunity_card = self._create_indicator_card(
            indicators_frame, "⭐ Opportunité", "5/10", row=0, col=3
        )
    
    def _create_info_panel(self):
        """Crée le panneau d'informations et alertes"""
        info_frame = ctk.CTkFrame(self)
        info_frame.grid(row=0, column=2, sticky="nsew", padx=10, pady=10)
        info_frame.grid_rowconfigure(1, weight=1)
        info_frame.grid_rowconfigure(3, weight=1)
        info_frame.grid_columnconfigure(0, weight=1)
        
        # === PRÉDICTION ===
        ctk.CTkLabel(
            info_frame,
            text="🔮 Prédiction",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=0, column=0, padx=10, pady=10, sticky="w")
        
        self.prediction_frame = ctk.CTkScrollableFrame(info_frame, height=200)
        self.prediction_frame.grid(row=1, column=0, padx=10, pady=5, sticky="nsew")
        
        self.prediction_label = ctk.CTkLabel(
            self.prediction_frame,
            text="Aucune prédiction",
            justify="left",
            wraplength=250
        )
        self.prediction_label.pack(fill="both", expand=True, padx=10, pady=10)
        
        # === ALERTES ===
        ctk.CTkLabel(
            info_frame,
            text="🚨 Alertes actives",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=2, column=0, padx=10, pady=10, sticky="w")
        
        self.alerts_frame = ctk.CTkScrollableFrame(info_frame)
        self.alerts_frame.grid(row=3, column=0, padx=10, pady=5, sticky="nsew")
        
        # Placeholder
        self.no_alerts_label = ctk.CTkLabel(
            self.alerts_frame,
            text="Aucune alerte active",
            text_color="gray"
        )
        self.no_alerts_label.pack(pady=20)
        
        # === STATISTIQUES ===
        ctk.CTkLabel(
            info_frame,
            text="📈 Statistiques",
            font=ctk.CTkFont(size=16, weight="bold")
        ).grid(row=4, column=0, padx=10, pady=10, sticky="w")
        
        stats_frame = ctk.CTkFrame(info_frame)
        stats_frame.grid(row=5, column=0, padx=10, pady=5, sticky="ew")
        
        self.stats_labels = {}
        stats = [
            ("Checks", "0"),
            ("Alertes envoyées", "0"),
            ("Dernière vérification", "Jamais")
        ]
        
        for i, (label, value) in enumerate(stats):
            ctk.CTkLabel(stats_frame, text=f"{label}:", font=ctk.CTkFont(size=11)).grid(
                row=i, column=0, padx=10, pady=5, sticky="w"
            )
            self.stats_labels[label] = ctk.CTkLabel(
                stats_frame, text=value, font=ctk.CTkFont(size=11, weight="bold")
            )
            self.stats_labels[label].grid(row=i, column=1, padx=10, pady=5, sticky="e")
    
    def _create_indicator_card(self, parent, title, value, row, col):
        """Crée une carte indicateur"""
        card = ctk.CTkFrame(parent)
        card.grid(row=row, column=col, padx=5, pady=5, sticky="nsew")
        
        ctk.CTkLabel(
            card,
            text=title,
            font=ctk.CTkFont(size=12)
        ).pack(pady=(10, 5))
        
        value_label = ctk.CTkLabel(
            card,
            text=value,
            font=ctk.CTkFont(size=20, weight="bold")
        )
        value_label.pack(pady=(0, 10))
        
        return value_label
    
    def _initial_load(self):
        """Chargement initial des données"""
        self._update_display()
    
    def _update_display(self):
        """Met à jour l'affichage avec les dernières données"""
        selected_crypto = self.crypto_selector.get()
        
        # Récupérer données de marché
        market_data = self.market_service.get_market_data(selected_crypto)
        
        if market_data:
            self.market_data_cache[selected_crypto] = market_data
            
            # Prédiction
            prediction = self.market_service.predict_price_movement(market_data)
            self.predictions_cache[selected_crypto] = prediction
            
            # Score opportunité
            opportunity = self.market_service.calculate_opportunity_score(market_data, prediction)
            
            # Mise à jour UI
            self._update_price_chart(market_data)
            self._update_indicators(market_data, prediction, opportunity)
            self._update_prediction_panel(prediction, opportunity)
        
        # Planifier prochaine mise à jour si en cours d'exécution
        if self.is_running:
            interval_ms = self.config.check_interval_seconds * 1000
            self.after(interval_ms, self._update_display)
    
    def _update_price_chart(self, market_data: MarketData):
        """Met à jour le graphique de prix"""
        self.price_ax.clear()
        
        # Préparer données
        if not market_data.price_history:
            return
        
        timestamps = [p.timestamp for p in market_data.price_history]
        prices = [p.price_eur for p in market_data.price_history]
        
        # Tracer prix
        self.price_ax.plot(timestamps, prices, linewidth=2, color='#2196F3', label='Prix')
        
        # Ajouter niveaux de prix si configurés
        if self.config.enable_price_levels and market_data.symbol in self.config.price_levels:
            levels = self.config.price_levels[market_data.symbol]
            if "low" in levels:
                self.price_ax.axhline(y=levels["low"], color='green', linestyle=':', linewidth=2, label=f'Niveau BAS ({levels["low"]}€)', alpha=0.7)
            if "high" in levels:
                self.price_ax.axhline(y=levels["high"], color='red', linestyle=':', linewidth=2, label=f'Niveau HAUT ({levels["high"]}€)', alpha=0.7)
        
        # Styling
        self.price_ax.set_xlabel('Temps', color='white')
        self.price_ax.set_ylabel('Prix (€)', color='white')
        self.price_ax.set_title(f'{market_data.symbol} - Prix en temps réel', color='white', fontsize=14, fontweight='bold')
        self.price_ax.legend(loc='upper left', facecolor='#2b2b2b', edgecolor='white', labelcolor='white')
        self.price_ax.grid(True, alpha=0.3, color='gray')
        self.price_ax.tick_params(colors='white')
        self.price_ax.xaxis.set_major_formatter(mdates.DateFormatter('%H:%M'))
        self.price_figure.autofmt_xdate()
        
        self.price_canvas.draw()
    
    def _update_indicators(self, market_data: MarketData, prediction: Prediction, opportunity: OpportunityScore):
        """Met à jour les cartes indicateurs"""
        # Prix
        price = market_data.current_price.price_eur
        self.price_card.configure(text=f"{price:.2f} €")
        
        # Changement 24h
        change = market_data.current_price.change_24h
        color = "green" if change > 0 else "red"
        self.change_card.configure(text=f"{change:+.2f}%", text_color=color)
        
        # RSI
        rsi = market_data.technical_indicators.rsi
        rsi_color = "green" if rsi < 40 else "red" if rsi > 60 else "white"
        self.rsi_card.configure(text=f"{rsi:.0f}", text_color=rsi_color)
        
        # Opportunité
        score = opportunity.score
        score_color = "green" if score >= 7 else "orange" if score >= 5 else "red"
        self.opportunity_card.configure(text=f"{score}/10 ⭐", text_color=score_color)
    
    def _update_prediction_panel(self, prediction: Prediction, opportunity: OpportunityScore):
        """Met à jour le panneau de prédiction"""
        detail = self.detail_level.get()
        
        if detail == "Simple":
            text = self._format_prediction_simple(prediction, opportunity)
        elif detail == "Expert":
            text = self._format_prediction_expert(prediction, opportunity)
        else:
            text = self._format_prediction_normal(prediction, opportunity)
        
        self.prediction_label.configure(text=text)
    
    def _format_prediction_simple(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format simple pour enfant"""
        pred = prediction.prediction_type.value
        conf = prediction.confidence
        score = opportunity.score
        
        text = f"{prediction.direction} {pred}\n\n"
        text += f"Je suis sûr à {conf}%\n\n"
        
        if score >= 7:
            text += "💡 C'est un BON moment pour acheter !\n"
        elif score >= 5:
            text += "💡 C'est pas mal, tu peux acheter\n"
        else:
            text += "💡 Attends un peu avant d'acheter\n"
        
        text += f"\nNote : {score}/10 ⭐"
        
        return text
    
    def _format_prediction_normal(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format normal"""
        text = f"{prediction.direction} {prediction.prediction_type.value}\n"
        text += f"Confiance: {prediction.confidence}%\n\n"
        
        text += f"Score opportunité: {opportunity.score}/10\n"
        text += f"{opportunity.recommendation}\n\n"
        
        if opportunity.reasons:
            text += "Raisons:\n"
            for reason in opportunity.reasons[:3]:
                text += f"• {reason}\n"
        
        return text
    
    def _format_prediction_expert(self, prediction: Prediction, opportunity: OpportunityScore) -> str:
        """Format expert avec tous les détails"""
        text = f"{prediction.direction} {prediction.prediction_type.value}\n"
        text += f"Confiance: {prediction.confidence}%\n"
        text += f"Trend Score: {prediction.trend_score}\n\n"
        
        text += f"Objectifs:\n"
        text += f"• Haut: {prediction.target_high:.2f}€\n"
        text += f"• Bas: {prediction.target_low:.2f}€\n\n"
        
        text += f"Timeline:\n"
        text += f"• 2-6h: {prediction.timeframe_short:.2f}€\n"
        text += f"• 1-2j: {prediction.timeframe_medium:.2f}€\n"
        text += f"• 1 sem: {prediction.timeframe_long:.2f}€\n\n"
        
        text += f"Opportunité: {opportunity.score}/10\n"
        
        if prediction.signals:
            text += f"\nSignaux:\n"
            for signal in prediction.signals[:3]:
                text += f"• {signal}\n"
        
        return text
    
    def _on_new_alert(self, alert: Alert):
        """Callback pour nouvelle alerte"""
        self._add_alert_card(alert)
        
        # Cacher le placeholder si présent
        if self.no_alerts_label.winfo_exists():
            self.no_alerts_label.pack_forget()
    
    def _add_alert_card(self, alert: Alert):
        """Ajoute une carte d'alerte"""
        colors = {
            "INFO": "#2196F3",
            "WARNING": "#FF9800",
            "IMPORTANT": "#FF5722",
            "CRITICAL": "#F44336"
        }
        
        card = ctk.CTkFrame(self.alerts_frame, fg_color=colors.get(alert.alert_level.value.upper(), "gray"))
        card.pack(fill="x", padx=5, pady=5)
        
        # Header
        header = ctk.CTkFrame(card, fg_color="transparent")
        header.pack(fill="x", padx=10, pady=5)
        
        ctk.CTkLabel(
            header,
            text=f"{alert.symbol} - {alert.alert_type.value}",
            font=ctk.CTkFont(size=12, weight="bold")
        ).pack(side="left")
        
        ctk.CTkButton(
            header,
            text="✓",
            width=30,
            command=lambda: self._acknowledge_alert(alert, card)
        ).pack(side="right")
        
        # Message
        ctk.CTkLabel(
            card,
            text=alert.message,
            wraplength=250,
            justify="left"
        ).pack(fill="x", padx=10, pady=5)
        
        # Timestamp
        ctk.CTkLabel(
            card,
            text=alert.timestamp.strftime('%H:%M:%S'),
            font=ctk.CTkFont(size=10),
            text_color="lightgray"
        ).pack(fill="x", padx=10, pady=(0, 5))
    
    def _acknowledge_alert(self, alert: Alert, card: ctk.CTkFrame):
        """Acquitte une alerte"""
        self.alert_service.acknowledge_alert(alert.alert_id)
        card.destroy()
        
        # Réafficher placeholder si plus d'alertes
        if not self.alerts_frame.winfo_children():
            self.no_alerts_label.pack(pady=20)
    
    def _start_monitoring(self):
        """Démarre la surveillance"""
        if self.is_running:
            return
        
        self.is_running = True
        self.start_button.configure(state="disabled")
        self.stop_button.configure(state="normal")
        self.status_label.configure(text="● En cours", text_color="green")
        
        # Démarrer thread de surveillance
        self.monitor_thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self.monitor_thread.start()
        
        # Démarrer mise à jour UI
        self._update_display()
    
    def _stop_monitoring(self):
        """Arrête la surveillance"""
        self.is_running = False
        self.start_button.configure(state="normal")
        self.stop_button.configure(state="disabled")
        self.status_label.configure(text="● Arrêté", text_color="gray")
    
    def _monitor_loop(self):
        """Boucle de surveillance (thread séparé)"""
        while self.is_running:
            for symbol in self.config.crypto_symbols:
                if not self.is_running:
                    break
                
                try:
                    # Récupérer données
                    market_data = self.market_service.get_market_data(symbol)
                    if not market_data:
                        continue
                    
                    # Prédiction
                    prediction = self.market_service.predict_price_movement(market_data)
                    
                    # Vérifier alertes
                    alerts = self.alert_service.check_alerts(market_data, prediction)
                    
                    # Envoyer sur Telegram si alertes
                    for alert in alerts:
                        if alert.alert_level in [AlertLevel.IMPORTANT, AlertLevel.CRITICAL]:
                            self.telegram_api.send_alert(alert, include_metadata=True)
                    
                    # Mettre à jour stats
                    self._update_stats()
                
                except Exception as e:
                    print(f"Erreur surveillance {symbol}: {e}")
            
            # Attendre avant prochain cycle
            if self.is_running:
                time.sleep(self.config.check_interval_seconds)
    
    def _update_stats(self):
        """Met à jour les statistiques"""
        # TODO: Implémenter avec vraies stats
        pass
    
    def _on_crypto_changed(self, value):
        """Callback changement de crypto"""
        self._update_display()
    
    def _on_detail_changed(self, value):
        """Callback changement de niveau de détail"""
        self._update_display()
    
    def _test_telegram(self):
        """Teste la connexion Telegram"""
        success = self.telegram_api.send_message("🚀 Test de connexion - Crypto Bot v3.0")
        
        if success:
            self._show_info("Telegram", "Message de test envoyé avec succès !")
        else:
            self._show_error("Telegram", "Échec de l'envoi du message de test")
    
    def _generate_report(self):
        """Génère un rapport complet"""
        # TODO: Implémenter génération rapport
        self._show_info("Rapport", "Fonctionnalité en développement")
    
    def _open_settings(self):
        """Ouvre la fenêtre de configuration"""
        # TODO: Implémenter fenêtre settings
        self._show_info("Configuration", "Fonctionnalité en développement")
    
    def _show_info(self, title, message):
        """Affiche une info"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=message, wraplength=350).pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy).pack(pady=10)
    
    def _show_error(self, title, message):
        """Affiche une erreur"""
        dialog = ctk.CTkToplevel(self)
        dialog.title(title)
        dialog.geometry("400x150")
        dialog.transient(self)
        dialog.grab_set()
        
        ctk.CTkLabel(dialog, text=f"❌ {message}", wraplength=350, text_color="red").pack(pady=20)
        ctk.CTkButton(dialog, text="OK", command=dialog.destroy, fg_color="red").pack(pady=10)


def main():
    """Point d'entrée principal"""
    # Charger configuration
    # TODO: Charger depuis fichier config
    config = BotConfiguration()
    config.crypto_symbols = ["BTC", "ETH", "SOL"]
    
    # Lancer GUI
    app = CryptoBotGUI(config)
    app.mainloop()


if __name__ == "__main__":
    main()
