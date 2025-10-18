"""PyQt Settings Dialog - Configuration complète du bot"""

import json
from dataclasses import replace
from typing import Optional, Callable, Dict, List, Any

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

    # ------------------------------------------------------------------
    # Construction UI
    # ------------------------------------------------------------------
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
        self._section_checks: Dict[str, QCheckBox] = {}
        self._metric_checks: Dict[str, QCheckBox] = {}
        self._text_edits: Dict[str, QPlainTextEdit] = {}
        self._coin_low_spins: Dict[str, QDoubleSpinBox] = {}
        self._coin_high_spins: Dict[str, QDoubleSpinBox] = {}
        self._coin_report_checkboxes: Dict[str, Dict[str, QCheckBox]] = {}
        self._coin_notification_checkboxes: Dict[str, Dict[str, QCheckBox]] = {}
        self._coin_report_hours_edit: Dict[str, QLineEdit] = {}
        self._coin_notification_hours_edit: Dict[str, QLineEdit] = {}
        self._coin_report_timeframes_edit: Dict[str, QLineEdit] = {}
        self._coin_notification_timeframes_edit: Dict[str, QLineEdit] = {}
        self._coin_notifications_tab: Optional[QTabWidget] = None
        self._coin_notification_title_edit: Dict[str, QLineEdit] = {}
        self._coin_notification_intro_edit: Dict[str, QPlainTextEdit] = {}
        self._coin_notification_outro_edit: Dict[str, QPlainTextEdit] = {}
        self._coin_notification_custom_lines_edit: Dict[str, QPlainTextEdit] = {}
        self._coin_glossary_enable_check: Dict[str, QCheckBox] = {}
        self._coin_glossary_title_edit: Dict[str, QLineEdit] = {}
        self._coin_glossary_intro_edit: Dict[str, QPlainTextEdit] = {}
        self._coin_glossary_entries_edit: Dict[str, QPlainTextEdit] = {}

        self._build_sections()

        # Boutons
        btn_layout = QHBoxLayout()
        self.main_layout.addLayout(btn_layout)

        save_btn = QPushButton("💾 Sauvegarder")
        save_btn.clicked.connect(self._save_config)
        btn_layout.addWidget(save_btn)

        cancel_btn = QPushButton("❌ Annuler")
        cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(cancel_btn)

        reset_btn = QPushButton("🔄 Réinitialiser")
        reset_btn.clicked.connect(self._reset_config)
        btn_layout.addWidget(reset_btn)

    def _build_sections(self):
        self._add_telegram_section()
        self._add_telegram_options_section()
        self._add_thresholds_section()
        self._add_alerts_section()
        self._add_monitoring_section()
        self._add_quiet_hours_section()
        self._add_summary_section()
        self._add_features_section()
        self._add_report_section()
        self._add_notifications_section()
        self._add_interface_section()
        self._add_budget_section()
        self._add_data_logs_section()

    def _add_group_box(self, title: str) -> QGroupBox:
        box = QGroupBox(title)
        box_layout = QGridLayout()
        box.setLayout(box_layout)
        self.content_layout.addWidget(box)
        return box

    def _add_telegram_section(self):
        box = self._add_group_box("📱 Telegram")
        layout = box.layout()
        layout.addWidget(QLabel("Bot Token:"), 0, 0)
        self._line_edits["telegram_token"] = QLineEdit()
        layout.addWidget(self._line_edits["telegram_token"], 0, 1)

        layout.addWidget(QLabel("Chat ID:"), 1, 0)
        self._line_edits["telegram_chat"] = QLineEdit()
        layout.addWidget(self._line_edits["telegram_chat"], 1, 1)

    def _add_telegram_options_section(self):
        box = self._add_group_box("📬 Contenu Telegram")
        layout = box.layout()

        self._check_boxes["telegram_show_prices"] = QCheckBox("Afficher les prix")
        layout.addWidget(self._check_boxes["telegram_show_prices"], 0, 0)

        self._check_boxes["telegram_show_trend_24h"] = QCheckBox("Afficher la tendance 24h")
        layout.addWidget(self._check_boxes["telegram_show_trend_24h"], 0, 1)

        self._check_boxes["telegram_show_trend_7d"] = QCheckBox("Afficher la tendance 7j")
        layout.addWidget(self._check_boxes["telegram_show_trend_7d"], 1, 0)

        self._check_boxes["telegram_show_recommendations"] = QCheckBox("Afficher la recommandation")
        layout.addWidget(self._check_boxes["telegram_show_recommendations"], 1, 1)

        layout.addWidget(QLabel("Délai entre messages (s)"), 2, 0)
        spin = QDoubleSpinBox()
        spin.setMinimum(0.0)
        spin.setMaximum(30.0)
        spin.setDecimals(2)
        spin.setSingleStep(0.1)
        self._double_spins["telegram_delay"] = spin
        layout.addWidget(spin, 2, 1)

    def _add_thresholds_section(self):
        box = self._add_group_box("🎯 Seuils de tendance")
        layout = box.layout()

        layout.addWidget(QLabel("Achat 24h (%)"), 0, 0)
        spin = QDoubleSpinBox()
        spin.setRange(-50.0, 50.0)
        spin.setDecimals(2)
        self._double_spins["buy_24h"] = spin
        layout.addWidget(spin, 0, 1)

        layout.addWidget(QLabel("Vente 24h (%)"), 0, 2)
        spin = QDoubleSpinBox()
        spin.setRange(-50.0, 50.0)
        spin.setDecimals(2)
        self._double_spins["sell_24h"] = spin
        layout.addWidget(spin, 0, 3)

        layout.addWidget(QLabel("Achat 7j (%)"), 1, 0)
        spin = QDoubleSpinBox()
        spin.setRange(-200.0, 200.0)
        spin.setDecimals(2)
        self._double_spins["buy_7d"] = spin
        layout.addWidget(spin, 1, 1)

        layout.addWidget(QLabel("Vente 7j (%)"), 1, 2)
        spin = QDoubleSpinBox()
        spin.setRange(-200.0, 200.0)
        spin.setDecimals(2)
        self._double_spins["sell_7d"] = spin
        layout.addWidget(spin, 1, 3)

    def _add_alerts_section(self):
        box = self._add_group_box("🚨 Alertes")
        layout = box.layout()

        self._check_boxes["enable_alerts"] = QCheckBox("Activer les alertes de prix")
        layout.addWidget(self._check_boxes["enable_alerts"], 0, 0, 1, 2)

        layout.addWidget(QLabel("Baisse alerte (%)"), 1, 0)
        spin = QDoubleSpinBox()
        spin.setRange(-100.0, 100.0)
        spin.setDecimals(2)
        self._double_spins["drop_threshold"] = spin
        layout.addWidget(spin, 1, 1)

        layout.addWidget(QLabel("Hausse alerte (%)"), 1, 2)
        spin = QDoubleSpinBox()
        spin.setRange(-100.0, 100.0)
        spin.setDecimals(2)
        self._double_spins["spike_threshold"] = spin
        layout.addWidget(spin, 1, 3)

        layout.addWidget(QLabel("Lookback (minutes)"), 2, 0)
        spin = QSpinBox()
        spin.setRange(1, 1440)
        self._spin_boxes["lookback_minutes"] = spin
        layout.addWidget(spin, 2, 1)

        layout.addWidget(QLabel("Funding négatif max"), 2, 2)
        spin = QDoubleSpinBox()
        spin.setRange(-10.0, 10.0)
        spin.setDecimals(3)
        self._double_spins["funding_threshold"] = spin
        layout.addWidget(spin, 2, 3)

        layout.addWidget(QLabel("Variation OI (%)"), 3, 0)
        spin = QDoubleSpinBox()
        spin.setRange(-100.0, 100.0)
        spin.setDecimals(2)
        self._double_spins["oi_delta"] = spin
        layout.addWidget(spin, 3, 1)

        layout.addWidget(QLabel("Fear & Greed max"), 3, 2)
        spin = QSpinBox()
        spin.setRange(0, 100)
        self._spin_boxes["fear_greed"] = spin
        layout.addWidget(spin, 3, 3)

        layout.addWidget(QLabel("Marge niveaux (EUR)"), 4, 0)
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1000.0)
        spin.setDecimals(2)
        self._double_spins["level_buffer"] = spin
        layout.addWidget(spin, 4, 1)

        layout.addWidget(QLabel("Cooldown niveaux (minutes)"), 4, 2)
        spin = QSpinBox()
        spin.setRange(1, 1440)
        self._spin_boxes["level_cooldown"] = spin
        layout.addWidget(spin, 4, 3)

        self._check_boxes["enable_price_levels"] = QCheckBox("Activer les niveaux de prix")
        layout.addWidget(self._check_boxes["enable_price_levels"], 5, 0, 1, 4)

        row = 6
        layout.addWidget(QLabel("Seuils par crypto"), row, 0, 1, 4)
        row += 1
        for symbol in sorted(self._config.crypto_symbols):
            layout.addWidget(QLabel(symbol), row, 0)
            low_spin = QDoubleSpinBox()
            low_spin.setRange(0.0, 1_000_000.0)
            low_spin.setDecimals(2)
            low_spin.setSuffix(" €")
            low_spin.setToolTip("Déclenche une alerte si le prix passe sous ce niveau")
            self._coin_low_spins[symbol] = low_spin
            layout.addWidget(low_spin, row, 1)

            high_spin = QDoubleSpinBox()
            high_spin.setRange(0.0, 1_000_000.0)
            high_spin.setDecimals(2)
            high_spin.setSuffix(" €")
            high_spin.setToolTip("Déclenche une alerte si le prix dépasse ce niveau")
            self._coin_high_spins[symbol] = high_spin
            layout.addWidget(high_spin, row, 2)

            helper = QLabel("Bas / Haut")
            helper.setStyleSheet("color: gray;")
            layout.addWidget(helper, row, 3)
            row += 1

    def _add_monitoring_section(self):
        box = self._add_group_box("🔍 Surveillance")
        layout = box.layout()

        layout.addWidget(QLabel("Intervalle de vérification (s)"), 0, 0)
        spin = QSpinBox()
        spin.setRange(60, 86400)
        self._spin_boxes["check_interval"] = spin
        layout.addWidget(spin, 0, 1)

    def _add_quiet_hours_section(self):
        box = self._add_group_box("🌙 Mode nuit")
        layout = box.layout()

        self._check_boxes["enable_quiet_hours"] = QCheckBox("Activer le mode nuit")
        layout.addWidget(self._check_boxes["enable_quiet_hours"], 0, 0, 1, 2)

        layout.addWidget(QLabel("Début (h)"), 1, 0)
        spin = QSpinBox()
        spin.setRange(0, 23)
        self._spin_boxes["quiet_start"] = spin
        layout.addWidget(spin, 1, 1)

        layout.addWidget(QLabel("Fin (h)"), 1, 2)
        spin = QSpinBox()
        spin.setRange(0, 23)
        self._spin_boxes["quiet_end"] = spin
        layout.addWidget(spin, 1, 3)

        self._check_boxes["quiet_allow_critical"] = QCheckBox("Autoriser alertes critiques")
        layout.addWidget(self._check_boxes["quiet_allow_critical"], 2, 0, 1, 4)

    def _add_summary_section(self):
        box = self._add_group_box("🕒 Résumés Telegram")
        layout = box.layout()

        layout.addWidget(QLabel("Heures (séparées par une virgule)"), 0, 0)
        edit = QLineEdit()
        self._line_edits["summary_hours"] = edit
        layout.addWidget(edit, 0, 1)

        self._check_boxes["use_simple_language"] = QCheckBox("Langage simple")
        layout.addWidget(self._check_boxes["use_simple_language"], 1, 0)

        self._check_boxes["enable_startup_summary"] = QCheckBox("Envoyer au démarrage")
        layout.addWidget(self._check_boxes["enable_startup_summary"], 1, 1)

    def _add_features_section(self):
        box = self._add_group_box("✨ Fonctionnalités")
        layout = box.layout()

        self._check_boxes["enable_predictions"] = QCheckBox("Activer les prédictions")
        layout.addWidget(self._check_boxes["enable_predictions"], 0, 0)

        self._check_boxes["enable_graphs"] = QCheckBox("Graphiques comparatifs")
        layout.addWidget(self._check_boxes["enable_graphs"], 0, 1)

        self._check_boxes["show_levels_on_graph"] = QCheckBox("Afficher niveaux sur graphiques")
        layout.addWidget(self._check_boxes["show_levels_on_graph"], 1, 0)

        self._check_boxes["enable_opportunity_score"] = QCheckBox("Score d'opportunité")
        layout.addWidget(self._check_boxes["enable_opportunity_score"], 1, 1)

        layout.addWidget(QLabel("Seuil opportunité"), 2, 0)
        spin = QSpinBox()
        spin.setRange(0, 10)
        self._spin_boxes["opportunity_threshold"] = spin
        layout.addWidget(spin, 2, 1)

        self._check_boxes["enable_timeline"] = QCheckBox("Timeline prédictive")
        layout.addWidget(self._check_boxes["enable_timeline"], 2, 2)

        self._check_boxes["enable_gain_loss_calc"] = QCheckBox("Calcul gains/pertes")
        layout.addWidget(self._check_boxes["enable_gain_loss_calc"], 3, 0)

        self._check_boxes["enable_dca_suggestions"] = QCheckBox("Suggestions DCA")
        layout.addWidget(self._check_boxes["enable_dca_suggestions"], 3, 1)

        self._check_boxes["educational_mode"] = QCheckBox("Mode éducatif")
        layout.addWidget(self._check_boxes["educational_mode"], 4, 0)

        self._check_boxes["send_summary_chart"] = QCheckBox("Envoyer un graphique 24h après chaque résumé automatique")
        layout.addWidget(self._check_boxes["send_summary_chart"], 4, 1)

        self._check_boxes["send_summary_dca"] = QCheckBox("Envoyer un plan DCA après chaque résumé automatique")
        layout.addWidget(self._check_boxes["send_summary_dca"], 5, 0)

    def _add_report_section(self):
        box = self._add_group_box("📄 Rapport Telegram")
        layout = box.layout()
        layout.setColumnStretch(1, 1)

        section_labels = [
            ("executive_summary", "Résumé exécutif"),
            ("per_crypto", "Analyse par crypto"),
            ("comparison", "Comparaison"),
            ("recommendations", "Recommandations"),
            ("advanced_analysis", "Analyses avancées"),
            ("statistics", "Statistiques système"),
        ]
        for idx, (key, label) in enumerate(section_labels):
            checkbox = QCheckBox(label)
            self._section_checks[key] = checkbox
            layout.addWidget(checkbox, idx, 0)

        metric_labels = [
            ("volatility", "Volatilité"),
            ("drawdown", "Drawdown"),
            ("trend_strength", "Force de tendance"),
            ("risk_score", "Profil de risque"),
            ("dca_projection", "Projection DCA"),
            ("correlation", "Corrélation"),
        ]
        for idx, (key, label) in enumerate(metric_labels):
            checkbox = QCheckBox(label)
            self._metric_checks[key] = checkbox
            layout.addWidget(checkbox, idx, 1)

        option_row = max(len(section_labels), (len(metric_labels) + 1) // 2)
        layout.addWidget(QLabel("Détail du rapport"), option_row, 0)
        combo = QComboBox()
        combo.addItems(["simple", "detailed"])
        self._combo_boxes["report_detail"] = combo
        layout.addWidget(combo, option_row, 1)

        option_row += 1
        self._check_boxes["report_include_summary"] = QCheckBox("Inclure le résumé Telegram")
        layout.addWidget(self._check_boxes["report_include_summary"], option_row, 0, 1, 2)

        option_row += 1
        self._check_boxes["report_include_telegram_report"] = QCheckBox("Inclure le rapport format Telegram")
        layout.addWidget(self._check_boxes["report_include_telegram_report"], option_row, 0, 1, 2)

        option_row += 1
        self._check_boxes["report_include_chart"] = QCheckBox("Ajouter un résumé texte du graphique 24h")
        layout.addWidget(self._check_boxes["report_include_chart"], option_row, 0, 1, 2)

        option_row += 1
        self._check_boxes["report_include_dca"] = QCheckBox("Ajouter le plan DCA dans le rapport")
        layout.addWidget(self._check_boxes["report_include_dca"], option_row, 0, 1, 2)

        option_row += 1
        self._check_boxes["report_include_broker_prices"] = QCheckBox("Afficher les prix achat/vente des courtiers")
        layout.addWidget(self._check_boxes["report_include_broker_prices"], option_row, 0, 1, 2)

        option_row += 1
        layout.addWidget(QLabel("Personnalisation par crypto"), option_row, 0, 1, 2)
        option_row += 1

        for symbol in sorted(self._config.crypto_symbols):
            coin_box = QGroupBox(symbol)
            coin_layout = QGridLayout(coin_box)
            self._coin_report_checkboxes[symbol] = {}

            include_cb = QCheckBox("Inclure cette crypto dans le rapport")
            self._coin_report_checkboxes[symbol]["include_report"] = include_cb
            coin_layout.addWidget(include_cb, 0, 0, 1, 2)

            show_price_cb = QCheckBox("Bloc prix / variation")
            self._coin_report_checkboxes[symbol]["show_price"] = show_price_cb
            coin_layout.addWidget(show_price_cb, 1, 0)

            show_volume_cb = QCheckBox("Afficher le volume")
            self._coin_report_checkboxes[symbol]["show_volume"] = show_volume_cb
            coin_layout.addWidget(show_volume_cb, 1, 1)

            show_curves_cb = QCheckBox("Afficher les courbes (sparklines)")
            self._coin_report_checkboxes[symbol]["show_curves"] = show_curves_cb
            coin_layout.addWidget(show_curves_cb, 2, 0)

            show_technicals_cb = QCheckBox("Afficher les indicateurs techniques")
            self._coin_report_checkboxes[symbol]["show_technicals"] = show_technicals_cb
            coin_layout.addWidget(show_technicals_cb, 2, 1)

            show_prediction_cb = QCheckBox("Afficher les prédictions")
            self._coin_report_checkboxes[symbol]["show_prediction"] = show_prediction_cb
            coin_layout.addWidget(show_prediction_cb, 3, 0)

            show_opportunity_cb = QCheckBox("Afficher le score d'opportunité")
            self._coin_report_checkboxes[symbol]["show_opportunity"] = show_opportunity_cb
            coin_layout.addWidget(show_opportunity_cb, 3, 1)

            show_brokers_cb = QCheckBox("Afficher les prix courtiers")
            self._coin_report_checkboxes[symbol]["show_brokers"] = show_brokers_cb
            coin_layout.addWidget(show_brokers_cb, 4, 0)

            show_fgi_cb = QCheckBox("Afficher l'indice Fear & Greed")
            self._coin_report_checkboxes[symbol]["show_fear_greed"] = show_fgi_cb
            coin_layout.addWidget(show_fgi_cb, 4, 1)

            show_gain_cb = QCheckBox("Afficher le gain/perte sur 24h")
            self._coin_report_checkboxes[symbol]["show_gain"] = show_gain_cb
            coin_layout.addWidget(show_gain_cb, 5, 0)

            coin_layout.addWidget(QLabel("Heures d'inclusion (ex: 9, 18)"), 6, 0)
            hours_edit = QLineEdit()
            self._coin_report_hours_edit[symbol] = hours_edit
            coin_layout.addWidget(hours_edit, 6, 1)

            coin_layout.addWidget(QLabel("Courbes (heures séparées par des virgules, défaut 24, 168)"), 7, 0)
            timeframes_edit = QLineEdit()
            self._coin_report_timeframes_edit[symbol] = timeframes_edit
            coin_layout.addWidget(timeframes_edit, 7, 1)

            layout.addWidget(coin_box, option_row, 0, 1, 2)
            option_row += 1

    def _add_notifications_section(self):
        box = self._add_group_box("🔔 Notifications")
        layout = box.layout()

        row = 0

        per_coin_cb = QCheckBox("Envoyer une notification dédiée par crypto")
        per_coin_cb.setToolTip("Active l'envoi d'un message spécifique pour chaque cryptomonnaie suivie.")
        self._check_boxes["notification_per_coin"] = per_coin_cb
        layout.addWidget(per_coin_cb, row, 0, 1, 2)
        row += 1

        include_chart_cb = QCheckBox("Inclure un graphique dans chaque notification")
        include_chart_cb.setToolTip("Ajoute un mini graphique (sparklines) pour visualiser l'évolution des cours.")
        self._check_boxes["notification_include_chart"] = include_chart_cb
        layout.addWidget(include_chart_cb, row, 0, 1, 2)
        row += 1

        layout.addWidget(QLabel("Périodes graphiques (heures, séparées par des virgules)"), row, 0)
        chart_tf_edit = QLineEdit("24,168")
        chart_tf_edit.setToolTip("Choisis les horizons temporels utilisés pour les graphiques (ex: 24 pour 24h, 168 pour 7 jours).")
        self._line_edits["notification_chart_timeframes"] = chart_tf_edit
        layout.addWidget(chart_tf_edit, row, 1)
        row += 1

        include_brokers_cb = QCheckBox("Afficher les prix achat/vente des courtiers")
        include_brokers_cb.setToolTip("Ajoute le détail des prix proposés par les courtiers configurés.")
        self._check_boxes["notification_include_brokers"] = include_brokers_cb
        layout.addWidget(include_brokers_cb, row, 0, 1, 2)
        row += 1

        send_glossary_cb = QCheckBox("Envoyer une notification glossaire globale")
        send_glossary_cb.setToolTip("Envoie un rappel pédagogique général après les notifications par crypto.")
        self._check_boxes["notification_send_glossary"] = send_glossary_cb
        layout.addWidget(send_glossary_cb, row, 0, 1, 2)
        row += 1

        layout.addWidget(QLabel("Courtiers actifs (slug, séparés par des virgules)"), row, 0)
        enabled_brokers_edit = QLineEdit("binance, revolut")
        enabled_brokers_edit.setToolTip("Liste des courtiers à interroger pour les prix (slug séparés par des virgules).")
        self._line_edits["enabled_brokers"] = enabled_brokers_edit
        layout.addWidget(enabled_brokers_edit, row, 1)
        row += 1

        layout.addWidget(QLabel("Overrides courtiers (JSON)"), row, 0)
        overrides_edit = QPlainTextEdit()
        overrides_edit.setPlaceholderText('{"revolut": {"spread_pct": 0.004}}')
        overrides_edit.setFixedHeight(80)
        overrides_edit.setToolTip("Permet de surcharger certains paramètres des courtiers (format JSON).")
        self._text_edits["broker_overrides"] = overrides_edit
        layout.addWidget(overrides_edit, row, 0, 1, 2)
        row += 1

        layout.addWidget(QLabel("Paramétrage détaillé par cryptomonnaie"), row, 0, 1, 2)
        row += 1

        self._coin_notifications_tab = QTabWidget()
        self._coin_notifications_tab.setTabPosition(QTabWidget.TabPosition.North)
        self._coin_notifications_tab.setDocumentMode(True)
        layout.addWidget(self._coin_notifications_tab, row, 0, 1, 2)
        row += 1

        for symbol in sorted(self._config.crypto_symbols):
            tab = QWidget()
            tab_layout = QVBoxLayout(tab)
            tab_layout.setSpacing(12)

            intro_label = QLabel(
                "Configure précisément le contenu envoyé pour cette monnaie. "
                "Les champs laissés vides utilisent les valeurs par défaut."
            )
            intro_label.setWordWrap(True)
            tab_layout.addWidget(intro_label)

            behaviour_group = QGroupBox("Bloc automatique")
            behaviour_layout = QGridLayout()
            self._coin_notification_checkboxes[symbol] = {}

            include_cb = QCheckBox("Activer l'envoi de cette notification")
            include_cb.setToolTip("Décoche pour désactiver totalement les alertes Telegram pour cette crypto.")
            self._coin_notification_checkboxes[symbol]["include"] = include_cb
            behaviour_layout.addWidget(include_cb, 0, 0, 1, 2)

            price_cb = QCheckBox("Inclure le bloc prix / variation / volume")
            price_cb.setToolTip("Affiche le prix actuel, la variation 24h et le volume.")
            self._coin_notification_checkboxes[symbol]["show_price"] = price_cb
            behaviour_layout.addWidget(price_cb, 1, 0)

            curves_cb = QCheckBox("Afficher les mini-courbes (sparklines)")
            curves_cb.setToolTip("Utilise les périodes définies ci-dessous pour tracer des micro-graphiques.")
            self._coin_notification_checkboxes[symbol]["show_curves"] = curves_cb
            behaviour_layout.addWidget(curves_cb, 1, 1)

            prediction_cb = QCheckBox("Mentionner la prédiction IA")
            prediction_cb.setToolTip("Ajoute un commentaire simplifié basé sur l'algorithme de prédiction.")
            self._coin_notification_checkboxes[symbol]["show_prediction"] = prediction_cb
            behaviour_layout.addWidget(prediction_cb, 2, 0)

            opportunity_cb = QCheckBox("Afficher le score d'opportunité")
            opportunity_cb.setToolTip("Résume la recommandation actuelle (score sur 10).")
            self._coin_notification_checkboxes[symbol]["show_opportunity"] = opportunity_cb
            behaviour_layout.addWidget(opportunity_cb, 2, 1)

            brokers_cb = QCheckBox("Lister les prix courtiers")
            brokers_cb.setToolTip("Affiche les meilleurs prix disponibles chez les courtiers actifs.")
            self._coin_notification_checkboxes[symbol]["show_brokers"] = brokers_cb
            behaviour_layout.addWidget(brokers_cb, 3, 0)

            fgi_cb = QCheckBox("Inclure l'indice Fear & Greed")
            fgi_cb.setToolTip("Indicateur de sentiment du marché (0 = peur, 100 = avidité).")
            self._coin_notification_checkboxes[symbol]["show_fear_greed"] = fgi_cb
            behaviour_layout.addWidget(fgi_cb, 3, 1)

            gain_cb = QCheckBox("Ajouter le gain/perte potentiel")
            gain_cb.setToolTip("Synthèse rapide du gain/perte estimé sur 24h.")
            self._coin_notification_checkboxes[symbol]["show_gain"] = gain_cb
            behaviour_layout.addWidget(gain_cb, 4, 0)

            behaviour_layout.addWidget(QLabel("Heures d'envoi (ex: 9, 21)"), 5, 0)
            notif_hours_edit = QLineEdit()
            notif_hours_edit.setToolTip("Limite l'envoi de messages à des heures précises (vide = à tout moment).")
            self._coin_notification_hours_edit[symbol] = notif_hours_edit
            behaviour_layout.addWidget(notif_hours_edit, 5, 1)

            behaviour_layout.addWidget(QLabel("Périodes graphiques personnalisées (heures)"), 6, 0)
            notif_tf_edit = QLineEdit()
            notif_tf_edit.setToolTip("Remplace les périodes globales pour les sparklines de cette crypto.")
            self._coin_notification_timeframes_edit[symbol] = notif_tf_edit
            behaviour_layout.addWidget(notif_tf_edit, 6, 1)

            behaviour_group.setLayout(behaviour_layout)
            tab_layout.addWidget(behaviour_group)

            content_group = QGroupBox("Texte personnalisé envoyé")
            content_form = QFormLayout()

            title_edit = QLineEdit()
            title_edit.setPlaceholderText("💎 {symbol} — Mise à jour dédiée")
            title_edit.setToolTip("Titre de la notification. Tu peux utiliser {symbol} pour injecter le ticker.")
            self._coin_notification_title_edit[symbol] = title_edit
            content_form.addRow("Titre personnalisé", title_edit)

            intro_edit = QPlainTextEdit()
            intro_edit.setPlaceholderText("Texte d'introduction spécifique à cette crypto (optionnel).")
            intro_edit.setToolTip("Explique en langage clair ce que représente cette notification pour cette monnaie.")
            intro_edit.setFixedHeight(70)
            self._coin_notification_intro_edit[symbol] = intro_edit
            content_form.addRow("Introduction", intro_edit)

            custom_lines_edit = QPlainTextEdit()
            custom_lines_edit.setPlaceholderText("Une ligne par explication supplémentaire.\nEx: ⚙️ Stratégie : On surveille le breakout des 30k.")
            custom_lines_edit.setToolTip("Chaque ligne ajoutée sera envoyée telle quelle à la suite des blocs automatiques.")
            custom_lines_edit.setFixedHeight(90)
            self._coin_notification_custom_lines_edit[symbol] = custom_lines_edit
            content_form.addRow("Lignes pédagogiques", custom_lines_edit)

            outro_edit = QPlainTextEdit()
            outro_edit.setPlaceholderText("Conclusion ou rappel (optionnel).")
            outro_edit.setToolTip("Utilise ce champ pour une synthèse finale ou un avertissement personnalisé.")
            outro_edit.setFixedHeight(60)
            self._coin_notification_outro_edit[symbol] = outro_edit
            content_form.addRow("Conclusion", outro_edit)

            content_group.setLayout(content_form)
            tab_layout.addWidget(content_group)

            glossary_group = QGroupBox("Glossaire ciblé")
            glossary_form = QFormLayout()

            glossary_enable = QCheckBox("Inclure un glossaire pour cette crypto")
            glossary_enable.setToolTip("Permet de rappeler les notions clés spécifiques à cette monnaie.")
            self._coin_glossary_enable_check[symbol] = glossary_enable
            glossary_form.addRow(glossary_enable)

            glossary_title_edit = QLineEdit()
            glossary_title_edit.setPlaceholderText("📘 Glossaire {symbol}")
            glossary_title_edit.setToolTip("Titre affiché en tête du glossaire individuel.")
            self._coin_glossary_title_edit[symbol] = glossary_title_edit
            glossary_form.addRow("Titre du glossaire", glossary_title_edit)

            glossary_intro_edit = QPlainTextEdit()
            glossary_intro_edit.setPlaceholderText("Quelques notions clés à retenir pour {symbol} :")
            glossary_intro_edit.setToolTip("Message d'introduction avant la liste des définitions.")
            glossary_intro_edit.setFixedHeight(70)
            self._coin_glossary_intro_edit[symbol] = glossary_intro_edit
            glossary_form.addRow("Introduction", glossary_intro_edit)

            glossary_entries_edit = QPlainTextEdit()
            glossary_entries_edit.setPlaceholderText('[{"term": "RSI", "definition": "Indicateur qui mesure la force du mouvement."}]')
            glossary_entries_edit.setToolTip("Liste JSON des couples terme / définition.")
            glossary_entries_edit.setFixedHeight(110)
            self._coin_glossary_entries_edit[symbol] = glossary_entries_edit
            glossary_form.addRow("Entrées (JSON)", glossary_entries_edit)

            glossary_group.setLayout(glossary_form)
            tab_layout.addWidget(glossary_group)

            tab_layout.addStretch(1)

            self._coin_notifications_tab.addTab(tab, symbol)

        layout.addWidget(QLabel("Seuils de notification (JSON optionnel)"), row, 0)
        thresholds_edit = QPlainTextEdit()
        thresholds_edit.setPlaceholderText('{"BTC": {"min_score": 6, "min_change_pct": -2}}')
        thresholds_edit.setFixedHeight(80)
        thresholds_edit.setToolTip("Permet de définir des seuils avancés par crypto pour déclencher ou bloquer une notification.")
        self._text_edits["notification_thresholds"] = thresholds_edit
        layout.addWidget(thresholds_edit, row, 0, 1, 2)

    def _add_interface_section(self):
        box = self._add_group_box("🎨 Interface")
        layout = box.layout()

        layout.addWidget(QLabel("Niveau de détail de l'interface"), 0, 0)
        combo = QComboBox()
        combo.addItems(["simple", "normal", "expert"])
        self._combo_boxes["detail_level"] = combo
        layout.addWidget(combo, 0, 1)

    def _add_budget_section(self):
        box = self._add_group_box("💰 Budget & Cryptos")
        layout = box.layout()

        layout.addWidget(QLabel("Montant d'investissement (EUR)"), 0, 0)
        spin = QDoubleSpinBox()
        spin.setRange(0.0, 1_000_000.0)
        spin.setDecimals(2)
        self._double_spins["investment_amount"] = spin
        layout.addWidget(spin, 0, 1)

        layout.addWidget(QLabel("Cryptos (séparées par une virgule)"), 1, 0)
        edit = QLineEdit()
        self._line_edits["crypto_symbols"] = edit
        layout.addWidget(edit, 1, 1)

    def _add_data_logs_section(self):
        box = self._add_group_box("💾 Données & Logs")
        layout = box.layout()

        layout.addWidget(QLabel("Chemin base de données"), 0, 0)
        edit = QLineEdit()
        self._line_edits["database_path"] = edit
        layout.addWidget(edit, 0, 1)

        layout.addWidget(QLabel("Conserver l'historique (jours)"), 1, 0)
        spin = QSpinBox()
        spin.setRange(1, 3650)
        self._spin_boxes["keep_history"] = spin
        layout.addWidget(spin, 1, 1)

        layout.addWidget(QLabel("Fichier log"), 2, 0)
        edit = QLineEdit()
        self._line_edits["log_file"] = edit
        layout.addWidget(edit, 2, 1)

        layout.addWidget(QLabel("Niveau de log"), 3, 0)
        combo = QComboBox()
        combo.addItems(["DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"])
        self._combo_boxes["log_level"] = combo
        layout.addWidget(combo, 3, 1)

    # ------------------------------------------------------------------
    # Chargement & reset
    # ------------------------------------------------------------------
    def _load_config(self, config: BotConfiguration) -> None:
        self._line_edits["telegram_token"].setText(config.telegram_bot_token)
        self._line_edits["telegram_chat"].setText(config.telegram_chat_id)
        self._double_spins["telegram_delay"].setValue(config.telegram_message_delay)

        self._check_boxes["telegram_show_prices"].setChecked(config.telegram_show_prices)
        self._check_boxes["telegram_show_trend_24h"].setChecked(config.telegram_show_trend_24h)
        self._check_boxes["telegram_show_trend_7d"].setChecked(config.telegram_show_trend_7d)
        self._check_boxes["telegram_show_recommendations"].setChecked(config.telegram_show_recommendations)

        self._double_spins["buy_24h"].setValue(config.trend_buy_threshold_24h)
        self._double_spins["sell_24h"].setValue(config.trend_sell_threshold_24h)
        self._double_spins["buy_7d"].setValue(config.trend_buy_threshold_7d)
        self._double_spins["sell_7d"].setValue(config.trend_sell_threshold_7d)

        self._check_boxes["enable_alerts"].setChecked(config.enable_alerts)
        self._check_boxes["enable_price_levels"].setChecked(config.enable_price_levels)
        self._double_spins["drop_threshold"].setValue(config.price_drop_threshold)
        self._double_spins["spike_threshold"].setValue(config.price_spike_threshold)
        self._spin_boxes["lookback_minutes"].setValue(config.price_lookback_minutes)
        self._double_spins["funding_threshold"].setValue(config.funding_negative_threshold)
        self._double_spins["oi_delta"].setValue(config.oi_delta_threshold)
        self._spin_boxes["fear_greed"].setValue(config.fear_greed_max)
        self._double_spins["level_buffer"].setValue(config.level_buffer_eur)
        self._spin_boxes["level_cooldown"].setValue(config.level_cooldown_minutes)
        for symbol, spin in self._coin_low_spins.items():
            value = float(config.price_levels.get(symbol, {}).get("low", 0.0)) if config.price_levels else 0.0
            spin.setValue(value)
        for symbol, spin in self._coin_high_spins.items():
            value = float(config.price_levels.get(symbol, {}).get("high", 0.0)) if config.price_levels else 0.0
            spin.setValue(value)

        coin_settings = {k.upper(): v for k, v in (config.coin_settings or {}).items()}
        for symbol, checkboxes in self._coin_report_checkboxes.items():
            options = coin_settings.get(symbol.upper(), {})
            report_opts = options.get("report_options", {})
            include_report = options.get("include_report", True)
            checkboxes["include_report"].setChecked(include_report)
            checkboxes["show_price"].setChecked(report_opts.get("show_price", True))
            checkboxes["show_volume"].setChecked(report_opts.get("show_volume", True))
            checkboxes["show_curves"].setChecked(report_opts.get("show_curves", True))
            checkboxes["show_technicals"].setChecked(report_opts.get("show_technicals", True))
            checkboxes["show_prediction"].setChecked(report_opts.get("show_prediction", True))
            checkboxes["show_opportunity"].setChecked(report_opts.get("show_opportunity", True))
            checkboxes["show_brokers"].setChecked(report_opts.get("show_brokers", self._config.report_include_broker_prices))
            checkboxes["show_fear_greed"].setChecked(report_opts.get("show_fear_greed", True))
            checkboxes["show_gain"].setChecked(report_opts.get("show_gain", True))

            report_hours = options.get("report_hours", []) or []
            self._coin_report_hours_edit[symbol].setText(
                ", ".join(str(int(h)) for h in report_hours)
            )
            report_timeframes = report_opts.get("chart_timeframes", []) or []
            self._coin_report_timeframes_edit[symbol].setText(
                ", ".join(str(int(tf)) for tf in report_timeframes)
            )

        notification_content_map = {
            (key if key == "default" else key.upper()): value
            for key, value in (config.notification_content_by_coin or {}).items()
            if isinstance(value, dict)
        }
        default_notification_content = notification_content_map.get("default", {})

        for symbol, checkboxes in self._coin_notification_checkboxes.items():
            options = coin_settings.get(symbol.upper(), {})
            notif_opts = options.get("notification_options", {})
            include_notif = options.get("include_notification", True)
            checkboxes["include"].setChecked(include_notif)
            checkboxes["show_price"].setChecked(notif_opts.get("show_price", True))
            checkboxes["show_curves"].setChecked(notif_opts.get("show_curves", self._config.notification_include_chart))
            checkboxes["show_prediction"].setChecked(notif_opts.get("show_prediction", True))
            checkboxes["show_opportunity"].setChecked(notif_opts.get("show_opportunity", True))
            checkboxes["show_brokers"].setChecked(notif_opts.get("show_brokers", self._config.notification_include_brokers))
            checkboxes["show_fear_greed"].setChecked(notif_opts.get("show_fear_greed", True))
            checkboxes["show_gain"].setChecked(notif_opts.get("show_gain", True))

            notif_hours = options.get("notification_hours", []) or []
            self._coin_notification_hours_edit[symbol].setText(
                ", ".join(str(int(h)) for h in notif_hours)
            )
            notif_timeframes = notif_opts.get("chart_timeframes", []) or []
            self._coin_notification_timeframes_edit[symbol].setText(
                ", ".join(str(int(tf)) for tf in notif_timeframes)
            )

            merged_content = dict(default_notification_content)
            merged_content.update(notification_content_map.get(symbol.upper(), {}))

            title_value = merged_content.get("title", "")
            self._coin_notification_title_edit[symbol].setText(title_value if isinstance(title_value, str) else "")

            intro_value = merged_content.get("intro", "")
            self._coin_notification_intro_edit[symbol].setPlainText(intro_value if isinstance(intro_value, str) else "")

            custom_lines_value = merged_content.get("custom_lines", [])
            if isinstance(custom_lines_value, list):
                custom_lines_text = "\n".join(str(line) for line in custom_lines_value if isinstance(line, str))
            elif isinstance(custom_lines_value, str):
                custom_lines_text = custom_lines_value
            else:
                custom_lines_text = ""
            self._coin_notification_custom_lines_edit[symbol].setPlainText(custom_lines_text)

            outro_value = merged_content.get("outro", "")
            self._coin_notification_outro_edit[symbol].setPlainText(outro_value if isinstance(outro_value, str) else "")

            glossary_data = merged_content.get("glossary") if isinstance(merged_content.get("glossary"), dict) else {}
            glossary_enabled = glossary_data.get("enabled")
            if glossary_enabled is None:
                glossary_enabled = config.notification_send_glossary
            self._coin_glossary_enable_check[symbol].setChecked(bool(glossary_enabled))

            glossary_title = glossary_data.get("title", "")
            self._coin_glossary_title_edit[symbol].setText(glossary_title if isinstance(glossary_title, str) else "")

            glossary_intro = glossary_data.get("intro", "")
            self._coin_glossary_intro_edit[symbol].setPlainText(glossary_intro if isinstance(glossary_intro, str) else "")

            glossary_entries = glossary_data.get("entries", [])
            entries_text = ""
            if isinstance(glossary_entries, list) and glossary_entries:
                try:
                    entries_text = json.dumps(glossary_entries, indent=2, ensure_ascii=False)
                except TypeError:
                    entries_text = ""
            self._coin_glossary_entries_edit[symbol].setPlainText(entries_text)

        self._spin_boxes["check_interval"].setValue(config.check_interval_seconds)

        self._check_boxes["enable_quiet_hours"].setChecked(config.enable_quiet_hours)
        self._spin_boxes["quiet_start"].setValue(config.quiet_start_hour)
        self._spin_boxes["quiet_end"].setValue(config.quiet_end_hour)
        self._check_boxes["quiet_allow_critical"].setChecked(config.quiet_allow_critical)

        self._line_edits["summary_hours"].setText(", ".join(str(h) for h in config.summary_hours)
                                                   if config.summary_hours else "")

        self._check_boxes["use_simple_language"].setChecked(config.use_simple_language)
        self._check_boxes["enable_startup_summary"].setChecked(config.enable_startup_summary)

        self._check_boxes["enable_predictions"].setChecked(config.enable_predictions)
        self._check_boxes["enable_graphs"].setChecked(config.enable_graphs)
        self._check_boxes["show_levels_on_graph"].setChecked(config.show_levels_on_graph)
        self._check_boxes["enable_opportunity_score"].setChecked(config.enable_opportunity_score)
        self._spin_boxes["opportunity_threshold"].setValue(config.opportunity_threshold)
        self._check_boxes["enable_timeline"].setChecked(config.enable_timeline)
        self._check_boxes["enable_gain_loss_calc"].setChecked(config.enable_gain_loss_calc)
        self._check_boxes["enable_dca_suggestions"].setChecked(config.enable_dca_suggestions)
        self._check_boxes["educational_mode"].setChecked(config.educational_mode)
        self._check_boxes["send_summary_chart"].setChecked(config.send_summary_chart)
        self._check_boxes["send_summary_dca"].setChecked(config.send_summary_dca)

        for key, checkbox in self._section_checks.items():
            checkbox.setChecked(config.report_enabled_sections.get(key, True))
        for key, checkbox in self._metric_checks.items():
            checkbox.setChecked(config.report_advanced_metrics.get(key, True))
        self._combo_boxes["report_detail"].setCurrentText(config.report_detail_level)
        self._check_boxes["report_include_summary"].setChecked(config.report_include_summary)
        self._check_boxes["report_include_telegram_report"].setChecked(config.report_include_telegram_report)
        self._check_boxes["report_include_chart"].setChecked(config.report_include_chart)
        self._check_boxes["report_include_dca"].setChecked(config.report_include_dca)
        self._check_boxes["report_include_broker_prices"].setChecked(config.report_include_broker_prices)

        self._check_boxes["notification_per_coin"].setChecked(config.notification_per_coin)
        self._check_boxes["notification_include_chart"].setChecked(config.notification_include_chart)
        self._line_edits["notification_chart_timeframes"].setText(
            ", ".join(str(v) for v in config.notification_chart_timeframes)
        )
        self._check_boxes["notification_include_brokers"].setChecked(config.notification_include_brokers)
        self._check_boxes["notification_send_glossary"].setChecked(config.notification_send_glossary)
        self._line_edits["enabled_brokers"].setText(
            ", ".join(config.enabled_brokers)
        )
        self._text_edits["broker_overrides"].setPlainText(
            json.dumps(config.broker_settings, indent=2, ensure_ascii=False)
            if config.broker_settings else ""
        )
        self._text_edits["notification_thresholds"].setPlainText(
            json.dumps(config.notification_thresholds, indent=2, ensure_ascii=False)
            if config.notification_thresholds else ""
        )

        self._combo_boxes["detail_level"].setCurrentText(config.detail_level)
        self._double_spins["investment_amount"].setValue(config.investment_amount)
        self._line_edits["crypto_symbols"].setText(", ".join(config.crypto_symbols))

        self._line_edits["database_path"].setText(config.database_path)
        self._spin_boxes["keep_history"].setValue(config.keep_history_days)
        self._line_edits["log_file"].setText(config.log_file)
        self._combo_boxes["log_level"].setCurrentText(config.log_level.upper())

    # ------------------------------------------------------------------
    # Actions
    # ------------------------------------------------------------------
    def _save_config(self):
        try:
            interval = self._spin_boxes["check_interval"].value()
            if interval < 60:
                raise ValueError("L'intervalle doit être >= 60 secondes")

            delay = self._double_spins["telegram_delay"].value()
            if delay < 0:
                raise ValueError("Le délai Telegram doit être >= 0")

            investment = self._double_spins["investment_amount"].value()
            if investment <= 0:
                raise ValueError("Le montant d'investissement doit être > 0")

            lookback = self._spin_boxes["lookback_minutes"].value()
            if lookback <= 0:
                raise ValueError("Le lookback doit être > 0")

            summary_hours_text = self._line_edits["summary_hours"].text().replace(";", ",")
            summary_hours = []
            if summary_hours_text.strip():
                for part in summary_hours_text.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    hour = int(part)
                    if hour < 0 or hour > 23:
                        raise ValueError("Les heures de résumé doivent être comprises entre 0 et 23")
                    summary_hours.append(hour)
            if not summary_hours:
                summary_hours = [9, 12, 18]

            crypto_symbols = [s.strip().upper() for s in self._line_edits["crypto_symbols"].text().split(",") if s.strip()]
            if not crypto_symbols:
                raise ValueError("Veuillez indiquer au moins une cryptomonnaie")

            quiet_start = self._spin_boxes["quiet_start"].value()
            quiet_end = self._spin_boxes["quiet_end"].value()
            for hour in (quiet_start, quiet_end):
                if hour < 0 or hour > 23:
                    raise ValueError("Les heures du mode nuit doivent être comprises entre 0 et 23")

            keep_history = self._spin_boxes["keep_history"].value()
            if keep_history <= 0:
                raise ValueError("La durée de conservation doit être positive")

            opportunity_threshold = self._spin_boxes["opportunity_threshold"].value()
            if opportunity_threshold < 0 or opportunity_threshold > 10:
                raise ValueError("Le seuil d'opportunité doit être compris entre 0 et 10")

            database_path = self._line_edits["database_path"].text().strip()
            if not database_path:
                raise ValueError("Le chemin de la base de données ne peut pas être vide")

            log_file = self._line_edits["log_file"].text().strip()
            if not log_file:
                raise ValueError("Le fichier de log ne peut pas être vide")

            log_level = self._combo_boxes["log_level"].currentText().upper()

            timeframes_text = self._line_edits["notification_chart_timeframes"].text().replace(";", ",")
            notification_timeframes: List[int] = []
            if timeframes_text.strip():
                for part in timeframes_text.split(","):
                    part = part.strip()
                    if not part:
                        continue
                    if not part.isdigit():
                        raise ValueError("Les périodes graphiques doivent être des nombres positifs")
                    value = int(part)
                    if value <= 0:
                        raise ValueError("Les périodes graphiques doivent être > 0")
                    notification_timeframes.append(value)
            if not notification_timeframes:
                notification_timeframes = [24, 168]

            enabled_brokers_input = self._line_edits["enabled_brokers"].text()
            enabled_brokers = [s.strip().lower() for s in enabled_brokers_input.split(",") if s.strip()]

            overrides_text = self._text_edits["broker_overrides"].toPlainText().strip()
            if overrides_text:
                try:
                    broker_overrides = json.loads(overrides_text)
                    if not isinstance(broker_overrides, dict):
                        raise ValueError
                except Exception:
                    raise ValueError("Les overrides courtiers doivent être un JSON valide (objet)")
            else:
                broker_overrides = {}

            thresholds_text = self._text_edits["notification_thresholds"].toPlainText().strip()
            if thresholds_text:
                try:
                    notification_thresholds = json.loads(thresholds_text)
                    if not isinstance(notification_thresholds, dict):
                        raise ValueError
                except Exception:
                    raise ValueError("Les seuils de notification doivent être un JSON valide (objet)")
            else:
                notification_thresholds = {}

            price_levels = {}
            if self._config.price_levels:
                price_levels = {
                    symbol.upper(): dict(levels)
                    for symbol, levels in self._config.price_levels.items()
                    if symbol.upper() not in self._coin_low_spins
                }
            for symbol in self._coin_low_spins:
                low_val = self._coin_low_spins[symbol].value()
                high_val = self._coin_high_spins[symbol].value()
                entry = {}
                if low_val > 0:
                    entry["low"] = low_val
                if high_val > 0:
                    entry["high"] = high_val
                if entry:
                    price_levels[symbol.upper()] = entry
                elif symbol.upper() in price_levels:
                    price_levels.pop(symbol.upper())

            # Mise à jour config
            cfg = self._config
            cfg.telegram_bot_token = self._line_edits["telegram_token"].text().strip()
            cfg.telegram_chat_id = self._line_edits["telegram_chat"].text().strip()
            cfg.telegram_message_delay = delay
            cfg.telegram_show_prices = self._check_boxes["telegram_show_prices"].isChecked()
            cfg.telegram_show_trend_24h = self._check_boxes["telegram_show_trend_24h"].isChecked()
            cfg.telegram_show_trend_7d = self._check_boxes["telegram_show_trend_7d"].isChecked()
            cfg.telegram_show_recommendations = self._check_boxes["telegram_show_recommendations"].isChecked()

            cfg.trend_buy_threshold_24h = self._double_spins["buy_24h"].value()
            cfg.trend_sell_threshold_24h = self._double_spins["sell_24h"].value()
            cfg.trend_buy_threshold_7d = self._double_spins["buy_7d"].value()
            cfg.trend_sell_threshold_7d = self._double_spins["sell_7d"].value()

            cfg.enable_alerts = self._check_boxes["enable_alerts"].isChecked()
            cfg.enable_price_levels = self._check_boxes["enable_price_levels"].isChecked()
            cfg.price_drop_threshold = self._double_spins["drop_threshold"].value()
            cfg.price_spike_threshold = self._double_spins["spike_threshold"].value()
            cfg.price_lookback_minutes = lookback
            cfg.funding_negative_threshold = self._double_spins["funding_threshold"].value()
            cfg.oi_delta_threshold = self._double_spins["oi_delta"].value()
            cfg.fear_greed_max = self._spin_boxes["fear_greed"].value()
            cfg.level_buffer_eur = self._double_spins["level_buffer"].value()
            cfg.level_cooldown_minutes = self._spin_boxes["level_cooldown"].value()
            cfg.price_levels = price_levels

            cfg.check_interval_seconds = interval

            cfg.enable_quiet_hours = self._check_boxes["enable_quiet_hours"].isChecked()
            cfg.quiet_start_hour = quiet_start
            cfg.quiet_end_hour = quiet_end
            cfg.quiet_allow_critical = self._check_boxes["quiet_allow_critical"].isChecked()

            cfg.summary_hours = summary_hours
            cfg.use_simple_language = self._check_boxes["use_simple_language"].isChecked()
            cfg.enable_startup_summary = self._check_boxes["enable_startup_summary"].isChecked()

            cfg.enable_predictions = self._check_boxes["enable_predictions"].isChecked()
            cfg.enable_graphs = self._check_boxes["enable_graphs"].isChecked()
            cfg.show_levels_on_graph = self._check_boxes["show_levels_on_graph"].isChecked()
            cfg.enable_opportunity_score = self._check_boxes["enable_opportunity_score"].isChecked()
            cfg.opportunity_threshold = opportunity_threshold
            cfg.enable_timeline = self._check_boxes["enable_timeline"].isChecked()
            cfg.enable_gain_loss_calc = self._check_boxes["enable_gain_loss_calc"].isChecked()
            cfg.enable_dca_suggestions = self._check_boxes["enable_dca_suggestions"].isChecked()
            cfg.educational_mode = self._check_boxes["educational_mode"].isChecked()
            cfg.send_summary_chart = self._check_boxes["send_summary_chart"].isChecked()
            cfg.send_summary_dca = self._check_boxes["send_summary_dca"].isChecked()

            cfg.report_enabled_sections = {key: cb.isChecked() for key, cb in self._section_checks.items()}
            cfg.report_advanced_metrics = {key: cb.isChecked() for key, cb in self._metric_checks.items()}
            cfg.report_detail_level = self._combo_boxes["report_detail"].currentText()
            cfg.report_include_summary = self._check_boxes["report_include_summary"].isChecked()
            cfg.report_include_telegram_report = self._check_boxes["report_include_telegram_report"].isChecked()
            cfg.report_include_chart = self._check_boxes["report_include_chart"].isChecked()
            cfg.report_include_dca = self._check_boxes["report_include_dca"].isChecked()
            cfg.report_include_broker_prices = self._check_boxes["report_include_broker_prices"].isChecked()

            cfg.notification_per_coin = self._check_boxes["notification_per_coin"].isChecked()
            cfg.notification_include_chart = self._check_boxes["notification_include_chart"].isChecked()
            cfg.notification_chart_timeframes = notification_timeframes
            cfg.notification_include_brokers = self._check_boxes["notification_include_brokers"].isChecked()
            cfg.notification_send_glossary = self._check_boxes["notification_send_glossary"].isChecked()
            if enabled_brokers:
                cfg.enabled_brokers = enabled_brokers
            elif not cfg.enabled_brokers:
                cfg.enabled_brokers = ["binance", "revolut"]
            cfg.broker_settings = broker_overrides
            cfg.notification_thresholds = notification_thresholds

            coin_settings: Dict[str, Dict[str, Any]] = {}
            notification_content_map: Dict[str, Dict[str, Any]] = {}
            existing_notification_content = self._config.notification_content_by_coin or {}
            target_symbols = {symbol.upper() for symbol in self._config.crypto_symbols}
            for key, value in existing_notification_content.items():
                if not isinstance(value, dict):
                    continue
                if key == "default" or key not in target_symbols:
                    notification_content_map[key] = dict(value)

            for symbol in self._config.crypto_symbols:
                key = symbol.upper()
                coin_cfg = dict(self._config.coin_settings.get(key, {}))

                # Rapport
                report_include = self._coin_report_checkboxes[symbol]["include_report"].isChecked()
                coin_cfg["include_report"] = report_include
                report_hours = self._parse_hours_list(
                    self._coin_report_hours_edit[symbol].text(),
                    f"Heures rapport ({symbol})"
                )
                coin_cfg["report_hours"] = report_hours

                report_options = {
                    "show_price": self._coin_report_checkboxes[symbol]["show_price"].isChecked(),
                    "show_volume": self._coin_report_checkboxes[symbol]["show_volume"].isChecked(),
                    "show_curves": self._coin_report_checkboxes[symbol]["show_curves"].isChecked(),
                    "show_technicals": self._coin_report_checkboxes[symbol]["show_technicals"].isChecked(),
                    "show_prediction": self._coin_report_checkboxes[symbol]["show_prediction"].isChecked(),
                    "show_opportunity": self._coin_report_checkboxes[symbol]["show_opportunity"].isChecked(),
                    "show_brokers": self._coin_report_checkboxes[symbol]["show_brokers"].isChecked(),
                    "show_fear_greed": self._coin_report_checkboxes[symbol]["show_fear_greed"].isChecked(),
                    "show_gain": self._coin_report_checkboxes[symbol]["show_gain"].isChecked(),
                }
                report_timeframes = self._parse_timeframes_list(
                    self._coin_report_timeframes_edit[symbol].text(),
                    f"Courbes rapport ({symbol})"
                )
                if report_timeframes:
                    report_options["chart_timeframes"] = report_timeframes
                coin_cfg["report_options"] = report_options

                # Notifications
                include_notification = self._coin_notification_checkboxes[symbol]["include"].isChecked()
                coin_cfg["include_notification"] = include_notification
                notification_hours = self._parse_hours_list(
                    self._coin_notification_hours_edit[symbol].text(),
                    f"Heures notification ({symbol})"
                )
                coin_cfg["notification_hours"] = notification_hours

                notification_options = {
                    "show_price": self._coin_notification_checkboxes[symbol]["show_price"].isChecked(),
                    "show_curves": self._coin_notification_checkboxes[symbol]["show_curves"].isChecked(),
                    "show_prediction": self._coin_notification_checkboxes[symbol]["show_prediction"].isChecked(),
                    "show_opportunity": self._coin_notification_checkboxes[symbol]["show_opportunity"].isChecked(),
                    "show_brokers": self._coin_notification_checkboxes[symbol]["show_brokers"].isChecked(),
                    "show_fear_greed": self._coin_notification_checkboxes[symbol]["show_fear_greed"].isChecked(),
                    "show_gain": self._coin_notification_checkboxes[symbol]["show_gain"].isChecked(),
                }
                notif_timeframes = self._parse_timeframes_list(
                    self._coin_notification_timeframes_edit[symbol].text(),
                    f"Courbes notification ({symbol})"
                )
                if notif_timeframes:
                    notification_options["chart_timeframes"] = notif_timeframes
                coin_cfg["notification_options"] = notification_options

                content_entry: Dict[str, Any] = {}
                title_text = self._coin_notification_title_edit[symbol].text().strip()
                if title_text:
                    content_entry["title"] = title_text

                intro_text = self._coin_notification_intro_edit[symbol].toPlainText().strip()
                if intro_text:
                    content_entry["intro"] = intro_text

                custom_lines_text = self._coin_notification_custom_lines_edit[symbol].toPlainText()
                custom_lines = [
                    line.strip()
                    for line in custom_lines_text.splitlines()
                    if line.strip()
                ]
                if custom_lines:
                    content_entry["custom_lines"] = custom_lines

                outro_text = self._coin_notification_outro_edit[symbol].toPlainText().strip()
                if outro_text:
                    content_entry["outro"] = outro_text

                glossary_enabled = self._coin_glossary_enable_check[symbol].isChecked()
                glossary_title = self._coin_glossary_title_edit[symbol].text().strip()
                glossary_intro = self._coin_glossary_intro_edit[symbol].toPlainText().strip()
                glossary_entries_text = self._coin_glossary_entries_edit[symbol].toPlainText().strip()

                glossary_data: Dict[str, Any] = {"enabled": glossary_enabled}
                if glossary_title:
                    glossary_data["title"] = glossary_title
                if glossary_intro:
                    glossary_data["intro"] = glossary_intro

                entries_list: List[Dict[str, str]] = []
                if glossary_entries_text:
                    try:
                        raw_entries = json.loads(glossary_entries_text)
                    except json.JSONDecodeError as exc:
                        raise ValueError(
                            f"Glossaire {symbol}: JSON invalide ({exc.msg})."
                        ) from exc
                    if not isinstance(raw_entries, list):
                        raise ValueError(
                            f"Glossaire {symbol}: la valeur doit être une liste d'objets {{\"term\", \"definition\"}}."
                        )
                    for idx, entry in enumerate(raw_entries, start=1):
                        if not isinstance(entry, dict):
                            raise ValueError(
                                f"Glossaire {symbol}: entrée #{idx} invalide, un objet {{\"term\", \"definition\"}} est attendu."
                            )
                        term = str(entry.get("term", "")).strip()
                        definition = str(entry.get("definition", "")).strip()
                        if not term or not definition:
                            raise ValueError(
                                f"Glossaire {symbol}: chaque entrée doit contenir 'term' et 'definition' non vides."
                            )
                        entries_list.append({"term": term, "definition": definition})
                if entries_list:
                    glossary_data["entries"] = entries_list

                content_entry["glossary"] = glossary_data

                coin_settings[key] = coin_cfg
                notification_content_map[key] = content_entry

            cfg.coin_settings = coin_settings
            cfg.notification_content_by_coin = notification_content_map

            cfg.detail_level = self._combo_boxes["detail_level"].currentText()
            cfg.investment_amount = investment
            cfg.crypto_symbols = crypto_symbols

            cfg.database_path = database_path
            cfg.keep_history_days = keep_history
            cfg.log_file = log_file
            cfg.log_level = log_level

            if self._on_save:
                self._on_save(cfg)

            self.accept()
        except ValueError as err:
            QMessageBox.critical(self, "Erreur", str(err))

    @staticmethod
    def _parse_hours_list(text: str, label: str) -> List[int]:
        if not text or not text.strip():
            return []
        result: List[int] = []
        normalized = text.replace(";", ",")
        for part in normalized.split(","):
            part = part.strip()
            if not part:
                continue
            if not part.lstrip("+-").isdigit():
                raise ValueError(f"{label} doit contenir uniquement des heures entières (0-23).")
            value = int(part)
            if value < 0 or value > 23:
                raise ValueError(f"{label} doit être compris entre 0 et 23.")
            result.append(value)
        return sorted(set(result))

    @staticmethod
    def _parse_timeframes_list(text: str, label: str) -> List[int]:
        if not text or not text.strip():
            return []
        result: List[int] = []
        normalized = text.replace(";", ",")
        for part in normalized.split(","):
            part = part.strip()
            if not part:
                continue
            if not part.lstrip("+-").isdigit():
                raise ValueError(f"{label} doit contenir uniquement des heures positives.")
            value = int(part)
            if value <= 0:
                raise ValueError(f"{label} doit être supérieur à 0.")
            result.append(value)
        return sorted(set(result))

    def _reset_config(self):
        answer = QMessageBox.question(
            self,
            "Réinitialisation",
            "Réinitialiser toute la configuration ?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if answer == QMessageBox.StandardButton.Yes:
            self._config = BotConfiguration()
            self._load_config(self._config)
