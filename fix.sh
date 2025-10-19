#!/bin/bash
echo "🔧 Correction automatique du projet..."

# 1. Timezone
echo "📅 Fix timezone..."
find . -name "*.py" -type f -exec sed -i '' 's/datetime\.now()/datetime.now(timezone.utc)/g' {} +
find . -name "*.py" -type f -exec sed -i '' '/from datetime import/s/$/, timezone/' {} +

# 2. Nom de classe
echo "🏷️  Fix class name..."
sed -i '' 's/class CryptoBot GUI/class CryptoBotGUI/g' ui/main_window.py

# 3. __init__.py
echo "📦 Création __init__.py..."
for dir in database ml strategies analysis optimizations; do
    mkdir -p $dir
    echo '"""'$dir' Package"""' > $dir/__init__.py
done

# 4. Nettoyage backups
echo "🧹 Nettoyage..."
# rm -rf backups/  # Décommenter si Git activé

echo "✅ Corrections terminées!"
echo "▶️  Lancer: python main.py --once"
