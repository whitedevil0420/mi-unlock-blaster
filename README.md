# 🔓 MI Unlock Blaster

**Simultaneous Xiaomi bootloader unlock request blaster — firing with <10 ms spread**

[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?style=flat-square&logo=python)](https://python.org)
[![License: MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Platform](https://img.shields.io/badge/Platform-Linux%20%7C%20Termux%20%7C%20Windows-lightgrey?style=flat-square)]()

Fires multiple requests simultaneously before midnight Beijing time (GMT+8), releasing threads at the *same microsecond* via a `threading.Event` barrier — giving you the best possible shot at getting your Xiaomi bootloader unlock approved.

---

## ✨ Features

- 🔁 **Configurable Parallel Requests**: Specify from 1 up to 60 requests (strict cap).
- ⚡ **<10 ms Spread**: All threads released at the same microsecond.
- 🕛 **Auto Midnight Targeting**: Syncs to China Standard Time (GMT+8) automatically.
- 🌐 **NTP Precision**: Uses Alibaba's `ntp1.aliyun.com` for low-latency time synchronization.
- 🚀 **Pre-warming connection pool**: Establishes TCP/TLS keep-alive connections 10 seconds before firing to eliminate handshake latency.
- 🎯 **Busy-wait precision**: Utilizes busy-waiting in the last 50 ms stretch for microsecond accuracy.
- 📊 **Summary report**: Prints per-thread success message and overall thread release spread.
- 📦 **100% Self-Contained**: No external dependency on pre-installed login packages. Features terminal password hidden input, browser/QR login, and 2FA SMS/Email verifications.

---

## 📋 Requirements

- Python **3.8+**
- Termux (Android) **or** Linux/Windows with Python

---

## 🚀 Installation

### Option 1 — One-liner (Recommended)

```bash
git clone https://github.com/whitedevil0420/mi-unlock-blaster.git
cd mi-unlock-blaster
bash install.sh
```

### Option 2 — Manual

```bash
git clone https://github.com/whitedevil0420/mi-unlock-blaster.git
cd mi-unlock-blaster
pip install -r requirements.txt
pip install -e .
```

### Termux (Android)

```bash
pkg update && pkg install python git -y
git clone https://github.com/whitedevil0420/mi-unlock-blaster.git
cd mi-unlock-blaster
bash install.sh
```

---

## ▶️ Usage

```bash
# After installation:
mi-unlock-blaster

# OR run directly:
python3 -m mi_unlock_blaster.main
```

### What happens when you run it?

1. **Login**: You'll be prompted to log in using either the browser (default), terminal inputs, or scanning a QR code.
2. **Parameters**: Input the number of requests (1 to 60) and target delay in ms before midnight.
3. **NTP Sync**: Syncs with high-precision time servers.
4. **Spawn & Wait**: Spawns workers and blocks them at a synchronized barrier.
5. **Connection Pre-warming**: Pre-opens connections 10 seconds prior.
6. **Fire**: Releaes all request threads at the exact same microsecond!

---

## 🔧 How It Works

```
                        ┌─────────────────────┐
                        │   Login & Get Token  │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  NTP Sync (Alibaba) │
                        │  Get exact GMT+8    │
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Spawn N Threads    │
                        │  (all block at      │
                        │   fire_event.wait)  │
                        └──────────┬──────────┘
                                   │
                ┌─── 10s before ───▼───────────────┐
                │   Pre-warm N TCP connections      │
                └───────────────────────────────────┘
                                   │
                ┌─── 50ms before ──▼────────────────┐
                │   Busy-wait (max precision)       │
                └───────────────────────────────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  fire_event.set()   │  ← All threads
                        │  🚀 FIRE!           │    released at the
                        │  <10ms spread       │    same microsecond
                        └──────────┬──────────┘
                                   │
                        ┌──────────▼──────────┐
                        │  Collect Results    │
                        │  Print Summary      │
                        └─────────────────────┘
```

---

## ⚠️ Disclaimer

- This tool is for **educational purposes only**.
- You must have a valid Mi Community account and have requested bootloader unlock through official channels.
- Do **not** abuse Xiaomi's API. Use responsibly.
- The author is not responsible for account bans or any other consequences.

---

## 📄 License

MIT © [whitedevil0420](https://github.com/whitedevil0420)
