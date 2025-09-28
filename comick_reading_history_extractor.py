import os, sys, json, sqlite3, tempfile, shutil, re, configparser, csv
from pathlib import Path
from datetime import datetime
import tkinter as tk
from tkinter import ttk, messagebox

APP_TITLE = "Comick List Extractor From History"
PLACEHOLDER_NO_CHAPTER = "NOT READ"
COMIC_PATH_ALLOW = re.compile(r"https?://(?:www\.)?comick\.io/comic/", re.IGNORECASE)
COMIC_PATH_DISALLOW = re.compile(r"https?://(?:www\.)?comick\.io/user/", re.IGNORECASE)
PAT_STRICT = re.compile(r"comick\.io/comic/(?P<slug>[^/]+)/[^/]*-chapter-(?P<chap>\d+(?:\.\d+)?)(?:-[a-z]{2})?(?:/|$)", re.IGNORECASE)
PAT_FALLBACK = re.compile(r"comick\.io/comic/(?P<slug>[^/]+)/(?:[^/]*-)?chapter[-_]?(\d+(?:\.\d+)?)(?:/|$)", re.IGNORECASE)
PAT_LASTDITCH = re.compile(r"comick\.io/comic/(?P<slug>[^/]+)/.*?(\d+(?:\.\d+)?)(?:[^\d.]|$)", re.IGNORECASE)
TITLE_CHAPTER_PATTERN = re.compile(r"\bchapter\s*[:#-]?\s*(\d+(?:\.\d+)?)\b", re.IGNORECASE)

def normalize_title_key(raw: str):
    if not raw: return None
    s = raw.lower().replace("_"," ").replace("-"," ")
    s = re.sub(r"[^\w\s]"," ", s)
    s = re.sub(r"\s+"," ", s).strip()
    return s or None

def extract_slug_and_chapter(url: str, title: str):
    if COMIC_PATH_DISALLOW.search(url): return None, None
    if not COMIC_PATH_ALLOW.search(url): return None, None
    m = PAT_STRICT.search(url)
    if m:
        slug = m.group("slug"); chap = m.group("chap")
        try: chap_num = float(chap) if "." in chap else int(chap)
        except: chap_num = None
        return normalize_title_key(slug), chap_num
    m = PAT_FALLBACK.search(url)
    if m:
        slug, chap = m.group(1), m.group(2)
        try: chap_num = float(chap) if "." in chap else int(chap)
        except: chap_num = None
        return normalize_title_key(slug), chap_num
    m = re.search(r"comick\.io/comic/([^/]+)(?:/|$)", url, re.IGNORECASE)
    if m:
        slug = m.group(1)
        m2 = PAT_LASTDITCH.search(url)
        if m2 and len(m2.groups())>=2:
            chap = m2.group(2)
            try: chap_num = float(chap) if "." in chap else int(chap)
            except: chap_num = None
        else:
            chap_num = None
        return normalize_title_key(slug), chap_num
    if "comick.io" in url.lower() and "/comic/" in url.lower():
        m = re.search(r"/comic/([^/]+)/", url, re.IGNORECASE)
        tkey = normalize_title_key(m.group(1)) if m else None
        if tkey:
            m3 = TITLE_CHAPTER_PATTERN.search(title or "")
            if m3:
                ch = m3.group(1)
                try: chap_num = float(ch) if "." in ch else int(ch)
                except: chap_num = None
            else:
                chap_num = None
            return tkey, chap_num
    return None, None

def safe_copy_file(src: Path):
    if not src.exists(): return None
    tmpdir = Path(tempfile.mkdtemp(prefix="hist_copy_"))
    dst = tmpdir / (src.name + ".copy")
    try:
        shutil.copy2(src, dst); return dst
    except Exception as e:
        print(f"[copy fail] {src}: {e}"); return None

def get_env_paths():
    LOCAL = os.environ.get("LOCALAPPDATA") or str(Path.home()/"AppData"/"Local")
    ROAM  = os.environ.get("APPDATA") or str(Path.home()/"AppData"/"Roaming")
    return Path(LOCAL), Path(ROAM)

def read_chrome_local_state(base_dir: Path):
    ls = base_dir / "Local State"; out = {}
    if not ls.exists(): return out
    try:
        data = json.loads(ls.read_text(encoding="utf-8"))
        info = data.get("profile", {}).get("info_cache", {})
        for prof_dir, meta in info.items():
            out[prof_dir] = {"name": meta.get("name") or prof_dir, "avatar": meta.get("avatar_icon") or meta.get("gaia_picture_file") or ""}
    except: pass
    return out

def read_prefs_name(profile_dir: Path):
    prefs = profile_dir / "Preferences"
    if prefs.exists():
        try:
            data = json.loads(prefs.read_text(encoding="utf-8"))
            nm = data.get("profile", {}).get("name")
            if nm: return nm
        except: pass
    return profile_dir.name

def discover_profiles():
    profiles = []
    LOCAL, ROAM = get_env_paths()
    chromes = [
        ("Chrome",   LOCAL/"Google"/"Chrome"/"User Data"),
        ("Edge",     LOCAL/"Microsoft"/"Edge"/"User Data"),
        ("Brave",    LOCAL/"BraveSoftware"/"Brave-Browser"/"User Data"),
        ("Vivaldi",  LOCAL/"Vivaldi"/"User Data"),
        ("Chromium", LOCAL/"Chromium"/"User Data"),
    ]
    for bname, base in chromes:
        if not base.exists(): continue
        cache = read_chrome_local_state(base)
        for prof in list(base.glob("Default")) + list(base.glob("Profile *")):
            hist = prof/"History"
            if hist.exists():
                key = prof.name
                prof_name = cache.get(key, {}).get("name") or read_prefs_name(prof)
                icon = None
                for cand in ["Google Profile Picture.png","Profile Picture.png","avatar.png","avatar.jpg"]:
                    p = prof/cand
                    if p.exists(): icon = str(p); break
                profiles.append({
                    "browser":"Chromium","browser_name":bname,"path_type":"chromium","profile_dir": str(prof),
                    "profile_key": key,"display_name": f"{bname} — {prof_name}","history_path": str(hist),"icon_path": icon
                })
    ff = ROAM/"Mozilla"/"Firefox"
    ini = ff/"profiles.ini"
    if ini.exists():
        cfg = configparser.ConfigParser(); cfg.read(ini, encoding="utf-8")
        for sec in cfg.sections():
            if not sec.startswith("Profile"): continue
            name = cfg.get(sec, "Name", fallback=None)
            path_rel = cfg.get(sec, "Path", fallback=None)
            is_rel = cfg.get(sec, "IsRelative", fallback="1") == "1"
            base = ff if is_rel else Path("/")
            prof_dir = base/path_rel if path_rel else None
            if prof_dir and (prof_dir/"places.sqlite").exists():
                profiles.append({
                    "browser":"Firefox","browser_name":"Firefox","path_type":"firefox","profile_dir": str(prof_dir),
                    "profile_key": prof_dir.name,"display_name": f"Firefox — {name or prof_dir.name}",
                    "history_path": str(prof_dir/"places.sqlite"),"icon_path": None
                })
    return profiles

def read_chromium_history(history_path: Path):
    rows = []; tmp = safe_copy_file(history_path)
    if not tmp: return rows
    try:
        conn = sqlite3.connect(str(tmp)); conn.row_factory = sqlite3.Row
        cur = conn.cursor(); cur.execute("SELECT url, title FROM urls")
        rows = [{"url": r["url"] or "", "title": r["title"] or ""} for r in cur]
        conn.close()
    except Exception as e:
        print(f"[chromium read] {history_path}: {e}")
    finally:
        try: shutil.rmtree(tmp.parent, ignore_errors=True)
        except: pass
    return rows

def read_firefox_history(places_sqlite: Path):
    rows = []; tmp = safe_copy_file(places_sqlite)
    if not tmp: return rows
    try:
        conn = sqlite3.connect(str(tmp)); conn.row_factory = sqlite3.Row
        cur = conn.cursor(); cur.execute("SELECT url, title FROM moz_places")
        rows = [{"url": r["url"] or "", "title": r["title"] or ""} for r in cur]
        conn.close()
    except Exception as e:
        print(f"[firefox read] {places_sqlite}: {e}")
    finally:
        try: shutil.rmtree(tmp.parent, ignore_errors=True)
        except: pass
    return rows

def aggregate(entries, profile_label):
    agg = {}
    for r in entries:
        url, title = r.get("url",""), r.get("title","")
        if not COMIC_PATH_ALLOW.search(url) or COMIC_PATH_DISALLOW.search(url): continue
        tkey, chap = extract_slug_and_chapter(url, title)
        if not tkey: continue
        rec = agg.get(tkey)
        if rec is None: agg[tkey] = {"title": tkey, "highest": None, "url": url, "profile": profile_label}
        if chap is not None:
            cur = agg[tkey]["highest"]
            if cur is None or float(chap) > float(cur):
                agg[tkey]["highest"] = chap; agg[tkey]["url"] = url; agg[tkey]["profile"] = profile_label
    out = []
    for k, v in agg.items():
        out.append({"title": v["title"], "highest": v["highest"] if v["highest"] is not None else PLACEHOLDER_NO_CHAPTER, "url": v["url"], "profile": v["profile"]})
    def sort_key(x):
        ch = x["highest"]
        try: return (0, -float(ch), x["title"])
        except: return (1, 0, x["title"])
    out.sort(key=sort_key)
    return out

def ensure_export_dir():
    base = Path(__file__).resolve().parent
    export_dir = base / "comic_list"
    export_dir.mkdir(parents=True, exist_ok=True)
    return export_dir

def _numeric_or_none(v):
    if isinstance(v, (int, float)): return v
    if isinstance(v, str) and v.replace('.','',1).isdigit():
        f = float(v); return int(f) if f.is_integer() else f
    return None

def export_all(results, export_dir: Path):
    if not results: return None
    ts = datetime.utcnow().strftime("%Y%m%dT%H%M%SZ")
    with_urls_json = export_dir / f"comick_results_{ts}.json"
    with_urls_csv  = export_dir / f"comick_results_{ts}.csv"
    with_urls_xlsx = export_dir / f"comick_results_{ts}.xlsx"
    portable_json  = export_dir / f"portable_titles_v1_{ts}.json"
    portable_csv   = export_dir / f"portable_titles_v1_{ts}.csv"
    portable_xlsx  = export_dir / f"portable_titles_v1_{ts}.xlsx"
    portable_txt   = export_dir / f"portable_titles_v1_{ts}.txt"
    with open(with_urls_json,"w",encoding="utf-8") as jf:
        json.dump({"generated_at": datetime.utcnow().isoformat()+"Z","results":results}, jf, indent=2, ensure_ascii=False)
    with open(with_urls_csv,"w",newline="",encoding="utf-8") as cf:
        w=csv.writer(cf); w.writerow(["title","highest_chapter","url_for_highest","profile_source"])
        for r in results: w.writerow([r["title"], r["highest"], r["url"], r["profile"]])
    try:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Comick Results"
        ws.append(["title","highest_chapter","url_for_highest","profile_source"])
        for r in results: ws.append([r["title"], r["highest"], r["url"], r["profile"]])
        wb.save(str(with_urls_xlsx))
    except Exception as e:
        print(f"[xlsx export (with urls)] {e}")
    portable_items = [
        {"title": r["title"], "chapters_read": _numeric_or_none(r["highest"]), "source_hint":"comick", "profile": r["profile"]}
        for r in results
    ]
    with open(portable_json,"w",encoding="utf-8") as pf:
        json.dump({"schema":"comics-list.v1","source":"comick-history-extractor","generated_at": datetime.utcnow().isoformat()+"Z","items": portable_items}, pf, indent=2, ensure_ascii=False)
    with open(portable_csv,"w",newline="",encoding="utf-8") as cf:
        w=csv.writer(cf); w.writerow(["title","chapters_read","profile","source_hint"])
        for it in portable_items: w.writerow([it["title"], it["chapters_read"] if it["chapters_read"] is not None else "", it["profile"], it["source_hint"]])
    try:
        from openpyxl import Workbook
        wb = Workbook(); ws = wb.active; ws.title = "Portable List"
        ws.append(["title","chapters_read","profile","source_hint"])
        for it in portable_items: ws.append([it["title"], it["chapters_read"], it["profile"], it["source_hint"]])
        wb.save(str(portable_xlsx))
    except Exception as e:
        print(f"[xlsx export (portable)] {e}")
    with open(portable_txt,"w",encoding="utf-8") as tf:
        tf.write("# Portable comics list (no URLs)\n")
        tf.write("# Columns: title | chapters_read | profile | source_hint\n")
        for it in portable_items:
            ch = "" if it["chapters_read"] is None else str(it["chapters_read"])
            tf.write(f"{it['title']} | {ch} | {it['profile']} | {it['source_hint']}\n")
    return {
        "with_urls_json": with_urls_json, "with_urls_csv": with_urls_csv, "with_urls_xlsx": with_urls_xlsx,
        "portable_json": portable_json, "portable_csv": portable_csv, "portable_xlsx": portable_xlsx, "portable_txt": portable_txt
    }

class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title(APP_TITLE)
        self.geometry("1000x620"); self.minsize(900,560)
        self.export_dir = ensure_export_dir()
        self.profiles = discover_profiles()
        self.results = []
        self._build_ui()
        self.after(200, self.auto_scan_on_start)

    def _build_ui(self):
        top = ttk.Frame(self, padding=8); top.pack(fill="x")
        ttk.Label(top, text="Profiles (pick one or Scan All):", font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.tree_profiles = ttk.Treeview(top, columns=("name","path"), show="headings", height=6)
        self.tree_profiles.heading("name", text="Profile")
        self.tree_profiles.heading("path", text="History Path")
        self.tree_profiles.column("name", width=360, anchor="w")
        self.tree_profiles.column("path", width=580, anchor="w")
        self.tree_profiles.pack(fill="x", pady=(4,6))
        for i,p in enumerate(self.profiles):
            self.tree_profiles.insert("", "end", iid=str(i), values=(p["display_name"], p["history_path"]))
        btns = ttk.Frame(top); btns.pack(fill="x")
        ttk.Button(btns, text="Scan Selected", command=self.scan_selected).pack(side="left")
        ttk.Button(btns, text="Scan All", command=self.scan_all).pack(side="left", padx=6)
        ttk.Button(btns, text="Export Files", command=self.export_results).pack(side="left", padx=18)
        mid = ttk.Frame(self, padding=(8,4)); mid.pack(fill="both", expand=True)
        ttk.Label(mid, text='Results (Title — Highest Chapter — URL — Profile):', font=("Segoe UI",10,"bold")).pack(anchor="w")
        self.tree_results = ttk.Treeview(mid, columns=("title","highest","url","profile"), show="headings")
        for c,w in zip(("title","highest","url","profile"), [320,120,420,120]):
            self.tree_results.heading(c, text=c.title(), command=lambda col=c: self._sort_tree(col, False))
            self.tree_results.column(c, width=w, anchor="w")
        self.tree_results.pack(fill="both", expand=True)
        vsb = ttk.Scrollbar(self.tree_results, orient="vertical", command=self.tree_results.yview)
        self.tree_results.configure(yscrollcommand=vsb.set); vsb.pack(side="right", fill="y")
        self.status = tk.StringVar(value="Ready.")
        ttk.Label(self, textvariable=self.status, relief="sunken", anchor="w").pack(fill="x")

    def _sort_tree(self, col, reverse):
        items = [(self.tree_results.set(k, col), k) for k in self.tree_results.get_children("")]
        if col == "highest":
            def keyfn(it):
                v = it[0]
                try:  return (0, -float(v))
                except: return (1, v)
        else:
            keyfn = lambda it: (0, it[0].lower())
        items.sort(key=keyfn, reverse=reverse)
        for i,(_,k) in enumerate(items): self.tree_results.move(k, "", i)
        self.tree_results.heading(col, command=lambda: self._sort_tree(col, not reverse))

    def scan_selected(self):
        sel = self.tree_profiles.selection()
        if not sel:
            messagebox.showinfo("Pick one", "Select a profile first.")
            return
        prof = self.profiles[int(sel[0])]
        self._scan([prof])

    def scan_all(self):
        if not self.profiles:
            messagebox.showinfo("No Profiles", "No browser profiles found.")
            return
        self._scan(self.profiles)

    def _scan(self, profiles):
        self.status.set("Scanning…"); self.update_idletasks()
        rows = []
        for p in profiles:
            hp = Path(p["history_path"])
            part = read_chromium_history(hp) if p["path_type"]=="chromium" else read_firefox_history(hp)
            for r in part: r["__profile"] = p["display_name"]
            rows += part
        grouped = {}
        labels = sorted(set(r["__profile"] for r in rows))
        for lab in labels:
            sub = [r for r in rows if r["__profile"]==lab]
            for item in aggregate(sub, lab):
                key = (item["title"], item["profile"])
                grouped[key] = item
        self.results = sorted(grouped.values(),
                              key=lambda x: (0 if str(x["highest"]).replace('.','',1).isdigit() else 1,
                                             -float(x["highest"]) if str(x["highest"]).replace('.','',1).isdigit() else 0,
                                             x["title"]))
        for k in self.tree_results.get_children(""): self.tree_results.delete(k)
        for r in self.results:
            self.tree_results.insert("", "end", values=(r["title"], str(r["highest"]), r["url"], r["profile"]))
        self.status.set(f"Scan complete. Found {len(self.results)} titles.")

    def export_results(self):
        if not self.results:
            messagebox.showinfo("Nothing to export", "Scan first.")
            return
        files = export_all(self.results, self.export_dir)
        if files:
            messagebox.showinfo(
                "Exported",
                "Saved:\n- {}\n- {}\n- {}\n- {}\n- {}\n- {}\n- {}".format(
                    files["with_urls_json"], files["with_urls_csv"], files["with_urls_xlsx"],
                    files["portable_json"], files["portable_csv"], files["portable_xlsx"], files["portable_txt"]
                )
            )

    def auto_scan_on_start(self):
        try:
            if self.profiles:
                self._scan(self.profiles)
                self.status.set("Auto-scan complete. Use 'Export Files' to save the 7 outputs.")
            else:
                self.status.set("No profiles found.")
        except Exception as e:
            self.status.set(f"Auto-scan error: {e}")

def main():
    app = App()
    if not app.profiles:
        messagebox.showwarning("No Profiles", "No browser profiles found. Make sure history exists locally.")
    app.mainloop()

if __name__ == "__main__":
    main()