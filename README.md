# Comick List Extractor From History

Harvest your local browser history for **comick.io** series you visited, deduplicate by title, detect the **last chapter** reached, and export your library to organized files.

![License](https://img.shields.io/badge/license-MIT-green)
[![Stars](https://img.shields.io/github/stars/Deb-Deep-Dutta/Comick-List-Extractor-From-History?style=social)](https://github.com/Deb-Deep-Dutta/Comick-List-Extractor-From-History)
[![Issues](https://img.shields.io/github/issues/Deb-Deep-Dutta/Comick-List-Extractor-From-History)](https://github.com/Deb-Deep-Dutta/Comick-List-Extractor-From-History/issues)

---

## Why sync matters

This tool reads **local** history databases on the machine where you run it. If your browser doesn't sync history from your other devices, URLs opened elsewhere will **not** appear here. To maximize coverage, enable **history sync** on the browsers you use and make sure you've signed in. Then give the browser time to download remote history onto this machine before running the extractor.

### Quick idea of "forced" sync
1. Sign in and turn **History** sync on (per browser steps below).  
2. Leave the browser open for a few minutes to let it fetch.  
3. Optionally visit **History** (Ctrl/Cmd+H) and scroll—many browsers fetch more as you scroll.  
4. If needed, briefly toggle sync **off → on** again for the history data type to nudge a refresh.

---

## Enable history sync (per browser)

> Turn on sync and ensure **History** is included. Some browsers differ in what exactly gets synchronized.

- **Google Chrome (Desktop)**
  - Profile icon → **Turn on sync** → **Yes, I'm in**.  
  - `Settings → You and Google → Sync and Google services → Manage what you sync` → choose **Customize sync** → enable **History**.

- **Microsoft Edge (Desktop)**
  - `Settings (… or Alt+F) → Profiles → Sync` → toggle on and enable **Browsing history**.

- **Mozilla Firefox**
  - Create/sign in to a **Mozilla account**, then `Settings → Sync` → choose what to sync and include **History**.

- **Vivaldi**
  - `Settings → Sync` → sign in to your Vivaldi account → enable **History** (or sync everything).

- **Brave**
  - Brave Sync synchronizes "browsing history" per Brave's help docs, but behavior can vary by version/platform. If full history doesn't appear, run the extractor on each device or temporarily use Chrome/Vivaldi/Edge for more complete history sync.  
  - `brave://settings/braveSync/setup` to join a Sync chain; ensure **History** is enabled. 

- **Chromium (open-source builds)**
  - Many packaged builds lack Google account sync. If your Chromium build can't sign in, syncing history across devices may not be available—use Chrome, Edge, Vivaldi, or Firefox on at least one machine to consolidate history. Advanced users can compile with API keys to enable Google sync in some cases. 

> After enabling, keep the browser open for a bit so history can download locally before running the extractor.

---

## Requirements

- **Python** 3.9+ (3.10–3.12 recommended)
- `tkinter` (GUI) — bundled with python.org installers for Windows/macOS; on Linux install via your package manager.
- `openpyxl` for Excel export (`pip install -r requirements.txt`)

---

## Install

```bash
git clone https://github.com/Deb-Deep-Dutta/Comick-List-Extractor-From-History.git
cd REPO
python -m pip install -r requirements.txt
````

Linux example for GUI deps (Debian/Ubuntu):

```bash
sudo apt-get update
sudo apt-get install -y python3 python3-pip python3-tk
```

---

## Run

```bash
python comick_reading_history_extractor.py
```

* On launch, the app creates `./comic_list/`, scans detected profiles, and auto-exports **seven files** per run (see below).
* Use the GUI to **Scan Selected**, **Scan All**, or **Export Files** again.

---

## Outputs (7 files per run)

Two versions are generated for easier access and help:

**A) With URLs (for your own reference/auditing)**

1. `comick_results_<timestamp>.json` — full JSON dump: `title`, `highest`, `url`, `profile`
2. `comick_results_<timestamp>.csv` — columns: `title,highest_chapter,url_for_highest,profile_source`
3. `comick_results_<timestamp>.xlsx` — Excel version ("Comick Results" sheet)

**B) Portable lists (NO URLs)** — safe to share or use with external helpers/converters
4. `portable_titles_v1_<timestamp>.json`
Schema:

```json
{
  "schema": "comics-list.v1",
  "source": "comick-history-extractor",
  "generated_at": "…Z",
  "items": [
    { "title": "one piece", "chapters_read": 1101, "profile": "Chrome — Default", "source_hint": "comick" }
  ]
}
```

5. `portable_titles_v1_<timestamp>.csv` — columns: `title,chapters_read,profile,source_hint`
6. `portable_titles_v1_<timestamp>.xlsx` — Excel version ("Portable List" sheet)
7. `portable_titles_v1_<timestamp>.txt` — human-readable lines:
   `title | chapters_read | profile | source_hint`

> `chapters_read` is numeric where known; if unknown (only series page seen), it's blank in tabular files.

---

## Privacy

All processing is local. The app reads local browser history databases and writes files to `./comic_list/`.

---

## Contributing

Issues and PRs welcome! If this helps you, please ⭐ **star the repo**.
Before submitting changes, run the app and verify exports.

---

## License

MIT. See `LICENSE`.

---