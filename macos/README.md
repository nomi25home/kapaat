# kapaat-macos

[![Kapaat](https://img.shields.io/badge/Kapaat-main%20repo-blue?logo=github)](https://github.com/nomi25home/kapaat)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)
[![macOS 13+](https://img.shields.io/badge/macOS-13%2B-lightgrey?logo=apple)](https://github.com/nomi25home/kapaat-macos)
[![Swift 5.9+](https://img.shields.io/badge/Swift-5.9%2B-orange?logo=swift)](https://swift.org)

Native macOS menu-bar app for [Kapaat](https://github.com/nomi25home/kapaat) — a self-hosted storage inventory app.

Launches the Kapaat FastAPI server as a subprocess on `localhost:8096` and renders the full web UI inside a `WKWebView` panel attached to a menu-bar icon.

**Requires macOS 13 (Ventura) or later.**

---

## Quick start

### 1. Clone both repos side by side

```bash
git clone https://github.com/nomi25home/kapaat.git
git clone https://github.com/nomi25home/kapaat-macos.git
```

### 2. Install Python dependencies

```bash
cd kapaat-macos
./setup.sh ../kapaat          # creates ../kapaat/.venv and installs requirements
```

### 3. Build the app

```bash
./build.sh                    # produces build/Kapaat.app
```

Requires Xcode Command Line Tools (`xcode-select --install`).

### 4. Run

```bash
open build/Kapaat.app
```

Or drag `Kapaat.app` to `/Applications`.

---

## How it works

| Component | File | Role |
|---|---|---|
| `KapaatApp.swift` | `@main` SwiftUI `App` | wires the `MenuBarExtra` scene |
| `ServerManager.swift` | `@MainActor ObservableObject` | spawns `uvicorn`, polls until ready, auto-generates and persists `AUTH_SECRET_KEY` |
| `WebView.swift` | `NSViewRepresentable` | `WKWebView` wrapper; external links open in Safari |
| `MenuBarContentView.swift` | SwiftUI view | 900 × 620 panel, status dot, Open in Browser, Quit |

### Python resolution order

1. `.venv/bin/python3` inside the kapaat directory
2. `/opt/homebrew/bin/python3`
3. `/usr/local/bin/python3`
4. `/usr/bin/python3`

Run `setup.sh` once to ensure option 1 is always used.

### Data storage

SQLite database and photos are stored in `~/Library/Application Support/Kapaat/`, separate from any Docker deployment.

---

## License

[MIT](LICENSE) © 2025 nomi25home
