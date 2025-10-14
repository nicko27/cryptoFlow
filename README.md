# 🚀 Crypto Bot v3.0 PyQt6

Bot crypto intelligent avec GUI PyQt6 (compatible macOS 10.13+).

## ✅ Corrections appliquées

- ✅ requirements.txt: urllib3<2.0 (fix LibreSSL)
- ✅ GUI: PyQt6 au lieu de customtkinter
- ✅ Timezone: datetime.now(timezone.utc) partout
- ✅ Import Dict dans alert_service.py

## 📦 Installation

```bash
pip3 install -r requirements.txt
python3 main.py --setup
python3 main.py  # GUI PyQt6
```

## 🎮 Usage

```bash
python3 main.py              # GUI
python3 main.py --daemon     # Démon
python3 main.py --once       # Test
```

## 🔧 Telegram Setup

1. @BotFather → /newbot → Token
2. @userinfobot → Chat ID
3. python3 main.py --setup

Compatible macOS 10.13+, Python 3.9+
