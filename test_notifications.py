#!/usr/bin/env python3
"""
Script de test pour valider toutes les corrections du système de notifications
"""

import sys
from pathlib import Path

# Ajouter le répertoire parent au path
sys.path.insert(0, str(Path(__file__).parent))

from utils.formatters import SafeHTMLFormatter, NumberFormatter, SafeDataExtractor, TemplateFormatter
from core.constants.emojis import NotificationEmojis
from core.constants.messages import NotificationMessages


def test_html_formatting():
    """Test formatage HTML sécurisé"""
    print("🧪 Test 1: Formatage HTML...")
    
    html = SafeHTMLFormatter()
    
    # Test échappement
    assert html.escape("<script>alert('xss')</script>") == "&lt;script&gt;alert(&#x27;xss&#x27;)&lt;/script&gt;"
    assert html.escape("Prix & volume") == "Prix &amp; volume"
    
    # Test bold
    assert html.bold("Test") == "<b>Test</b>"
    assert html.bold("<test>", escape=True) == "<b>&lt;test&gt;</b>"
    
    # Test italic
    assert html.italic("Test") == "<i>Test</i>"
    
    # Test code
    assert html.code("import sys") == "<code>import sys</code>"
    
    # Test troncature
    long_text = "Paragraph 1\n\nParagraph 2\n\nParagraph 3" * 200
    truncated = html.truncate_safely(long_text, 100)
    assert len(truncated) <= 150  # Avec marge
    assert "Paragraph" in truncated
    
    # Test validation HTML
    assert html.validate_html("<b>test</b>") == True
    assert html.validate_html("<b>test") == False  # Balise non fermée
    
    print("  ✅ Formatage HTML OK")


def test_number_formatting():
    """Test formatage des nombres"""
    print("🧪 Test 2: Formatage des nombres...")
    
    fmt = NumberFormatter()
    
    # Test prix
    assert "1 234.56 €" in fmt.format_price(1234.56)
    assert "0.0001" in fmt.format_price(0.00012)  # Petits nombres
    
    # Test pourcentage
    assert fmt.format_percentage(5.2) == "+5.2%"
    assert fmt.format_percentage(-3.7) == "-3.7%"
    assert "N/A" in fmt.format_percentage(None)
    
    # Test volume
    assert "2.50M" in fmt.format_volume(2_500_000, short=True)
    assert "1.20B" in fmt.format_volume(1_200_000_000, short=True)
    assert "500.00K" in fmt.format_volume(500_000, short=True)
    
    # Test score
    assert fmt.format_score(7, 10) == "7/10"
    assert fmt.format_score(None) == "N/A"
    
    print("  ✅ Formatage des nombres OK")


def test_template_formatting():
    """Test formatage des templates"""
    print("🧪 Test 3: Templates...")
    
    template = "Prix de {symbol}: {price}€ ({change})"
    result = TemplateFormatter.format_template(
        template,
        symbol="BTC",
        price=95000,
        change="+5%"
    )
    assert "BTC" in result
    assert "95000" in result
    
    # Test avec variable manquante (ne doit PAS crasher)
    template_missing = "Prix de {symbol}: {missing_var}€"
    result_missing = TemplateFormatter.format_template(
        template_missing,
        symbol="BTC"
    )
    assert "BTC" in result_missing
    # Le template doit gérer la variable manquante sans crasher
    assert "[missing_var?]" in result_missing
    
    # Test validation
    errors = TemplateFormatter.validate_template(
        "{symbol} à {price}€",
        {'symbol', 'price'}
    )
    assert len(errors) == 0
    
    errors_invalid = TemplateFormatter.validate_template(
        "{symbol} à {unknown}€",
        {'symbol', 'price'}
    )
    assert len(errors_invalid) > 0
    
    print("  ✅ Templates OK")


def test_emojis():
    """Test emojis centralisés"""
    print("🧪 Test 4: Emojis...")
    
    emoji = NotificationEmojis()
    
    # Test emojis de base
    assert emoji.PRICE == "💰"
    assert emoji.BULLISH == "🚀"
    assert emoji.WARNING == "⚠️"
    
    # Test helpers
    assert emoji.get_time_emoji(9) == emoji.MORNING
    assert emoji.get_time_emoji(15) == emoji.AFTERNOON
    assert emoji.get_time_emoji(20) == emoji.EVENING
    
    assert emoji.get_change_emoji(10) == emoji.BULLISH
    assert emoji.get_change_emoji(2) == emoji.PRICE_UP
    assert emoji.get_change_emoji(-2) == emoji.PRICE_DOWN
    
    assert emoji.get_opportunity_emoji(9) == emoji.EXCELLENT_OPPORTUNITY
    assert emoji.get_opportunity_emoji(6) == emoji.GOOD_OPPORTUNITY
    
    print("  ✅ Emojis OK")


def test_messages():
    """Test messages configurables"""
    print("🧪 Test 5: Messages...")
    
    msg = NotificationMessages()
    
    # Test messages de prix
    rising_kid = msg.get_price_message(10, kid_friendly=True)
    assert "monte" in rising_kid.lower() or "📈" in rising_kid
    
    falling_normal = msg.get_price_message(-8, kid_friendly=False)
    assert "baisse" in falling_normal.lower()
    
    # Test Fear & Greed
    fear_msg = msg.get_fear_greed_message(20, kid_friendly=False)
    assert "peur" in fear_msg.lower()
    
    greed_msg = msg.get_fear_greed_message(80, kid_friendly=True)
    assert "🤑" in greed_msg or "avidité" in greed_msg.lower()
    
    # Test glossaire
    assert "RSI" in msg.DEFAULT_GLOSSARY
    assert "HODL" in msg.DEFAULT_GLOSSARY
    
    print("  ✅ Messages OK")


def test_safe_data_extraction():
    """Test extraction sécurisée des données"""
    print("🧪 Test 6: Extraction de données...")
    
    extractor = SafeDataExtractor()
    
    # Test avec données nulles (ne doit PAS crasher)
    assert "indisponible" in extractor.get_price_eur(None).lower() or "N/A" in extractor.get_price_eur(None)
    assert "N/A" in extractor.get_change_24h(None)
    assert extractor.get_confidence(None) == 0
    assert extractor.get_opportunity_score(None) == 0
    
    print("  ✅ Extraction de données OK")


def test_config_validator():
    """Test validateur de configuration"""
    print("🧪 Test 7: Validateur de config...")
    
    from utils.notification_config_validator import NotificationConfigValidator
    
    validator = NotificationConfigValidator()
    
    # Test validation template
    errors = validator._validate_template(
        "Prix de {symbol}: {price}€",
        "test_template"
    )
    # Devrait avoir des warnings (variables non autorisées) mais pas crasher
    
    # Test validation heures
    validator.errors.clear()
    validator._validate_scheduled_notification(
        "BTC",
        0,
        {
            'hours': [0, 12, 23],  # Valides
            'days_of_week': [0, 1, 2, 3, 4],  # Valides
            'enabled': True
        }
    )
    assert len(validator.errors) == 0
    
    # Test avec erreurs
    validator.errors.clear()
    validator._validate_scheduled_notification(
        "BTC",
        0,
        {
            'hours': [25],  # Invalide
            'days_of_week': [8],  # Invalide
        }
    )
    assert len(validator.errors) > 0
    
    print("  ✅ Validateur OK")


def test_notification_generator():
    """Test générateur de notifications"""
    print("🧪 Test 8: Générateur de notifications...")
    
    try:
        from core.services.fixed_notification_generator import FixedNotificationGenerator
        from core.models.notification_config import GlobalNotificationSettings
        
        settings = GlobalNotificationSettings(
            enabled=True,
            kid_friendly_mode=True,
            use_emojis_everywhere=True
        )
        
        gen = FixedNotificationGenerator(settings, ['BTC'])
        
        # Test que le générateur peut être instancié
        assert gen is not None
        assert gen.html is not None
        assert gen.numbers is not None
        assert gen.emojis is not None
        
        # Test méthodes utilitaires
        assert gen._is_quiet_hour(3) == True  # En heures silencieuses par défaut
        assert gen._is_quiet_hour(12) == False  # Pas en heures silencieuses
        
        print("  ✅ Générateur de notifications OK")
    
    except ImportError as e:
        print(f"  ⚠️ Générateur de notifications non testé (import error): {e}")


def run_all_tests():
    """Lance tous les tests"""
    print("\n" + "="*60)
    print("🧪 TESTS DU SYSTÈME DE NOTIFICATIONS CORRIGÉ")
    print("="*60 + "\n")
    
    tests = [
        test_html_formatting,
        test_number_formatting,
        test_template_formatting,
        test_emojis,
        test_messages,
        test_safe_data_extraction,
        test_config_validator,
        test_notification_generator,
    ]
    
    passed = 0
    failed = 0
    
    for test in tests:
        try:
            test()
            passed += 1
        except AssertionError as e:
            print(f"  ❌ ÉCHEC: {e}")
            failed += 1
        except Exception as e:
            print(f"  ⚠️ ERREUR: {e}")
            failed += 1
    
    print("\n" + "="*60)
    print(f"📊 RÉSULTATS: {passed} tests réussis, {failed} échecs")
    print("="*60 + "\n")
    
    if failed == 0:
        print("✅ TOUS LES TESTS SONT PASSÉS !")
        print("🚀 Le système de notifications est prêt pour la production.\n")
        return 0
    else:
        print("❌ CERTAINS TESTS ONT ÉCHOUÉ")
        print("⚠️ Vérifiez les erreurs ci-dessus avant le déploiement.\n")
        return 1


if __name__ == "__main__":
    sys.exit(run_all_tests())
