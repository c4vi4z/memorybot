import os, sys, subprocess, venv

here = os.path.dirname(os.path.abspath(__file__))
venv_dir = os.path.join(os.path.dirname(here), ".venv-memory")
if os.name == "nt":
    py_console = os.path.join(venv_dir, "Scripts", "python.exe")
    py_window = os.path.join(venv_dir, "Scripts", "pythonw.exe")
    if "pythonw" in os.path.basename(sys.executable).lower():
        py_run = py_window
    else:
        py_run = py_console
    noflag = subprocess.CREATE_NO_WINDOW
else:
    py_console = py_run = os.path.join(venv_dir, "bin", "python")
    noflag = 0

if not getattr(sys, "frozen", False) and os.path.abspath(sys.prefix) != os.path.abspath(venv_dir):
    try:
        import selenium
    except ImportError:
        if not os.path.exists(py_console):
            venv.create(venv_dir, with_pip=True)
        if subprocess.call([py_console, "-c", "import selenium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=noflag) != 0:
            subprocess.check_call([py_console, "-m", "pip", "install", "--quiet", "selenium"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, creationflags=noflag)
        sys.exit(subprocess.call([py_run, os.path.abspath(__file__)] + sys.argv[1:]))

import json, queue, threading
import tkinter as tk
from tkinter import messagebox, ttk

if "--setup" in sys.argv:
    try:
        import bot as b
        b.ensure_browser()
    except Exception as e:
        print("setup mislukt:", e)
        sys.exit(1)
    sys.exit(0)

try:
    import bot as bot_mod
except Exception as e:
    r = tk.Tk()
    r.withdraw()
    messagebox.showerror("Memory Bot", str(e))
    sys.exit(1)

try:
    import updater
except Exception:
    updater = None

SETTINGS = os.path.join(bot_mod.BASE, "settings.json")
ICON = os.path.join(bot_mod.RES, "icon.png")
DEFAULT_URL = "https://SCHOOL.memorylab.app"


def load_settings():
    try:
        with open(SETTINGS, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def open_path(path):
    if sys.platform.startswith("win"):
        os.startfile(path)
    elif sys.platform == "darwin":
        subprocess.Popen(["open", path])
    else:
        subprocess.Popen(["xdg-open", path])


class Ask(tk.Toplevel):
    def __init__(self, parent, text, options=None, entry=False):
        super().__init__(parent)
        self.title("Memory Bot")
        self.result = None
        self.transient(parent)
        ttk.Label(self, text=text, wraplength=380, justify="left").pack(padx=14, pady=(14, 8))
        self.var = tk.StringVar()
        if entry:
            e = ttk.Entry(self, textvariable=self.var, width=40)
            e.pack(padx=14, pady=4)
            e.focus_set()
            e.bind("<Return>", lambda ev: self.done(("answer", self.var.get().strip())))
        if options:
            for i in range(len(options)):
                ttk.Button(self, text=str(i + 1) + ") " + options[i], command=lambda i=i: self.done(("pick", i))).pack(fill="x", padx=14, pady=2)
        row = ttk.Frame(self)
        row.pack(pady=12)
        if entry:
            ttk.Button(row, text="OK", command=lambda: self.done(("answer", self.var.get().strip()))).pack(side="left", padx=4)
        ttk.Button(row, text="Zelf doen", command=lambda: self.done(("skip", None))).pack(side="left", padx=4)
        ttk.Button(row, text="Stop bot", command=lambda: self.done(("stop", None))).pack(side="left", padx=4)
        self.protocol("WM_DELETE_WINDOW", lambda: self.done(("stop", None)))
        try:
            self.wait_visibility()
            self.grab_set()
        except tk.TclError:
            pass
        self.lift()

    def done(self, result):
        if self.result is None:
            self.result = result
        self.destroy()


class App:
    def __init__(self, root):
        self.root = root
        root.title("Memory Bot v" + bot_mod.APP_VERSION)
        root.geometry("540x740")
        root.minsize(480, 640)
        if sys.platform.startswith("linux"):
            try:
                ttk.Style().theme_use("clam")
            except tk.TclError:
                pass

        self.icon = None
        if os.path.exists(ICON):
            try:
                self.icon = tk.PhotoImage(file=ICON)
                root.iconphoto(True, self.icon)
            except tk.TclError:
                self.icon = None

        self.q = queue.Queue()
        self.stop = threading.Event()
        self.pending = None
        self.dialog = None
        self.worker = None
        self.update_rel = None
        self.settings = load_settings()

        bot_mod.log = self.log
        bot_mod.ask_open = self.ask_open
        bot_mod.ask_mc = self.ask_mc
        bot_mod.stop = self.stop

        self.build_ui()
        self.refresh_lists()
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        self.poll()

        if updater is not None:
            threading.Thread(target=self.check_updates, args=(True,), daemon=True).start()

    def build_ui(self):
        r = self.root
        pad = {"padx": 10, "pady": 5}

        top = ttk.Frame(r)
        top.pack(fill="x", **pad)
        ttk.Label(top, text="Site:").pack(side="left")
        self.url = tk.StringVar(value=self.settings.get("url", DEFAULT_URL))
        ttk.Entry(top, textvariable=self.url).pack(side="left", fill="x", expand=True, padx=6)
        self.btn_open = ttk.Button(top, text="1. Open Chrome", command=self.open_chrome)
        self.btn_open.pack(side="left")

        box = ttk.LabelFrame(r, text="2. Kies lijsten. volgorde = kaarten van boven naar beneden")
        box.pack(fill="both", expand=True, **pad)
        box.columnconfigure(0, weight=1, uniform="c")
        box.columnconfigure(1, weight=1, uniform="c")
        box.rowconfigure(1, weight=1)
        ttk.Label(box, text="Beschikbaar").grid(row=0, column=0, sticky="w", padx=6)
        ttk.Label(box, text="Volgorde (bovenste = eerste kaart)").grid(row=0, column=1, sticky="w", padx=6)

        f1 = ttk.Frame(box)
        f1.grid(row=1, column=0, sticky="nsew", padx=6)
        self.avail = tk.Listbox(f1, selectmode="extended", height=8, exportselection=False)
        sb1 = ttk.Scrollbar(f1, command=self.avail.yview)
        self.avail.configure(yscrollcommand=sb1.set)
        sb1.pack(side="right", fill="y")
        self.avail.pack(side="left", fill="both", expand=True)

        f2 = ttk.Frame(box)
        f2.grid(row=1, column=1, sticky="nsew", padx=6)
        self.order = tk.Listbox(f2, selectmode="browse", height=8, exportselection=False)
        sb2 = ttk.Scrollbar(f2, command=self.order.yview)
        self.order.configure(yscrollcommand=sb2.set)
        sb2.pack(side="right", fill="y")
        self.order.pack(side="left", fill="both", expand=True)

        self.avail.bind("<Double-Button-1>", lambda ev: self.add())
        self.order.bind("<Double-Button-1>", lambda ev: self.remove())

        left = ttk.Frame(box)
        left.grid(row=2, column=0, sticky="w", padx=6, pady=4)
        ttk.Button(left, text="Voeg toe >>", command=self.add).pack(side="left", padx=(0, 4))
        ttk.Button(left, text="Alles >>", command=self.add_all).pack(side="left", padx=(0, 4))
        ttk.Button(left, text="Vernieuw", command=self.refresh_lists).pack(side="left")

        right = ttk.Frame(box)
        right.grid(row=2, column=1, sticky="w", padx=6, pady=4)
        ttk.Button(right, text="Omhoog", width=8, command=lambda: self.move(-1)).pack(side="left", padx=(0, 4))
        ttk.Button(right, text="Omlaag", width=8, command=lambda: self.move(1)).pack(side="left", padx=(0, 4))
        ttk.Button(right, text="Weg", width=5, command=self.remove).pack(side="left")

        ttk.Button(box, text="Lijstenmap openen", command=lambda: open_path(bot_mod.LISTS_DIR)).grid(row=3, column=0, sticky="w", padx=6, pady=(0, 6))
        ttk.Button(box, text="Kaart overslaan", command=self.add_skip).grid(row=3, column=1, sticky="w", padx=6, pady=(0, 6))

        opt = ttk.Frame(r)
        opt.pack(fill="x", **pad)
        ttk.Label(opt, text="Begin bij kaart nr (1 = bovenste):").pack(side="left")
        self.first_card = tk.IntVar(value=int(self.settings.get("first_card", 1)))
        ttk.Spinbox(opt, from_=1, to=500, width=5, textvariable=self.first_card).pack(side="left", padx=6)

        ctl = ttk.Frame(r)
        ctl.pack(fill="x", **pad)
        self.btn_start = ttk.Button(ctl, text="3. Start", command=self.start)
        self.btn_start.pack(side="left")
        self.btn_stop = ttk.Button(ctl, text="Stop", command=self.stop_run, state="disabled")
        self.btn_stop.pack(side="left", padx=6)
        self.status = tk.StringVar(value="klaar voor gebruik")
        ttk.Label(ctl, textvariable=self.status).pack(side="left", padx=10)

        logf = ttk.Frame(r)
        logf.pack(fill="both", expand=True, **pad)
        self.logbox = tk.Text(logf, height=8, wrap="word", state="disabled")
        sb3 = ttk.Scrollbar(logf, command=self.logbox.yview)
        self.logbox.configure(yscrollcommand=sb3.set)
        sb3.pack(side="right", fill="y")
        self.logbox.pack(side="left", fill="both", expand=True)

        if updater is not None:
            upd = ttk.Frame(r)
            upd.pack(fill="x", **pad)
            self.upd_text = tk.StringVar(value="versie " + bot_mod.APP_VERSION)
            ttk.Label(upd, textvariable=self.upd_text).pack(side="left")
            self.btn_update = ttk.Button(upd, text="Zoek updates", command=self.update_click)
            self.btn_update.pack(side="right")

    def refresh_lists(self):
        self.avail.delete(0, "end")
        files = []
        if os.path.isdir(bot_mod.LISTS_DIR):
            files = bot_mod.find_lists()
        for f in files:
            self.avail.insert("end", f)
        if self.order.size() == 0:
            for f in self.settings.get("order", []):
                if f in files or f == bot_mod.SKIP:
                    self.order.insert("end", f)
        if not files:
            self.status.set("geen lijsten: zet .txt bestanden in de lijstenmap")

    def add(self):
        have = list(self.order.get(0, "end"))
        for i in self.avail.curselection():
            name = self.avail.get(i)
            if name not in have:
                self.order.insert("end", name)
                have.append(name)

    def add_all(self):
        have = list(self.order.get(0, "end"))
        for name in self.avail.get(0, "end"):
            if name not in have:
                self.order.insert("end", name)

    def add_skip(self):
        sel = self.order.curselection()
        if sel:
            pos = sel[0] + 1
        else:
            pos = self.order.size()
        self.order.insert(pos, bot_mod.SKIP)
        self.order.selection_clear(0, "end")
        self.order.selection_set(pos)

    def remove(self):
        for i in reversed(self.order.curselection()):
            self.order.delete(i)

    def move(self, d):
        sel = self.order.curselection()
        if not sel:
            return
        i = sel[0]
        j = i + d
        if j < 0 or j >= self.order.size():
            return
        t = self.order.get(i)
        self.order.delete(i)
        self.order.insert(j, t)
        self.order.selection_set(j)

    def get_first(self):
        try:
            return max(1, int(self.first_card.get()))
        except (ValueError, tk.TclError):
            return 1

    def save_settings(self):
        data = {
            "url": self.url.get().strip(),
            "order": list(self.order.get(0, "end")),
            "first_card": self.get_first(),
        }
        try:
            with open(SETTINGS, "w", encoding="utf-8") as f:
                json.dump(data, f)
        except OSError:
            pass

    def log(self, text):
        self.q.put(("log", str(text)))

    def ask(self, kind, *payload):
        reply = queue.Queue()
        self.pending = reply
        self.q.put(("ask", kind, payload, reply))
        res = reply.get()
        self.pending = None
        return res

    def ask_open(self, cue):
        return self.ask("open", cue)

    def ask_mc(self, cue, texts):
        return self.ask("mc", cue, texts)

    def poll(self):
        self.root.after(100, self.poll)
        try:
            while True:
                msg = self.q.get_nowait()
                if msg[0] == "log":
                    self.logbox.configure(state="normal")
                    self.logbox.insert("end", msg[1] + "\n")
                    self.logbox.see("end")
                    self.logbox.configure(state="disabled")
                elif msg[0] == "status":
                    self.status.set(msg[1])
                elif msg[0] == "idle":
                    self.set_running(False)
                elif msg[0] == "ask":
                    self.handle_ask(msg[1], msg[2], msg[3])
                elif msg[0] == "upd":
                    self.update_rel = msg[1]
                    self.upd_text.set(msg[2])
                    if msg[1] is None:
                        self.btn_update.configure(text="Zoek updates", state="normal")
                    else:
                        self.btn_update.configure(text="Nu updaten", state="normal")
                elif msg[0] == "updated":
                    self.handle_updated(msg[1])
        except queue.Empty:
            pass

    def handle_ask(self, kind, payload, reply):
        if kind == "open":
            dlg = Ask(self.root, "'" + payload[0] + "' staat niet in de lijst.\nTyp het antwoord:", entry=True)
        else:
            dlg = Ask(self.root, "'" + payload[0] + "' niet gevonden. kies het juiste antwoord:", options=payload[1])
        self.dialog = dlg
        self.root.wait_window(dlg)
        self.dialog = None
        what, val = dlg.result or ("stop", None)
        if what == "stop":
            out = None
        elif what == "skip":
            if kind == "open":
                out = ""
            else:
                out = -1
        else:
            out = val
        reply.put(out)

    def set_running(self, running):
        if running:
            self.btn_start.configure(state="disabled")
            self.btn_stop.configure(state="normal")
            self.btn_open.configure(state="disabled")
        else:
            self.btn_start.configure(state="normal")
            self.btn_stop.configure(state="disabled")
            self.btn_open.configure(state="normal")

    def check_updates(self, silent):
        try:
            rel = updater.latest_release()
        except Exception:
            if not silent:
                self.q.put(("upd", None, "geen verbinding met github"))
            return
        if rel:
            self.q.put(("upd", rel, "update beschikbaar: " + str(rel.get("tag_name", "?"))))
        elif not silent:
            self.q.put(("upd", None, "je hebt de nieuwste versie (" + bot_mod.APP_VERSION + ")"))

    def update_click(self):
        if self.worker and self.worker.is_alive():
            messagebox.showinfo("Memory Bot", "stop eerst de bot.")
            return
        if self.update_rel is None:
            self.btn_update.configure(state="disabled")
            self.upd_text.set("zoeken...")
            threading.Thread(target=self.check_updates, args=(False,), daemon=True).start()
            return
        if not messagebox.askyesno("Memory Bot", "Update naar " + str(self.update_rel.get("tag_name", "")) + " installeren?"):
            return
        self.btn_update.configure(state="disabled")
        self.upd_text.set("updaten...")
        threading.Thread(target=self.do_update, daemon=True).start()

    def do_update(self):
        rel = self.update_rel
        try:
            res = updater.apply_update(rel, self.log)
        except Exception as e:
            lines = str(e).splitlines()
            self.log("update mislukt: " + (lines[0] if lines else type(e).__name__))
            self.q.put(("upd", rel, "update mislukt, probeer opnieuw"))
            return
        self.q.put(("updated", res))

    def handle_updated(self, res):
        self.update_rel = None
        self.btn_update.configure(text="Zoek updates", state="normal")
        if res == "restart":
            self.upd_text.set("update klaar, herstart nodig")
            if messagebox.askyesno("Memory Bot", "Update klaar. Nu opnieuw starten?"):
                self.restart()
        elif res == "installer":
            self.upd_text.set("installer gestart")
            txt = "De installer is gestart. Memory Bot sluit nu af."
            if sys.platform == "darwin":
                txt += "\n\nSleep Memory Bot in het venster naar Apps en kies Vervang."
            messagebox.showinfo("Memory Bot", txt)
            self.on_close()
        else:
            self.upd_text.set("download staat in je browser")
            messagebox.showinfo("Memory Bot", "De downloadpagina is geopend in je browser.")

    def restart(self):
        self.stop.set()
        self.save_settings()
        bot_mod.close()
        if getattr(sys, "frozen", False):
            cmd = [sys.executable] + sys.argv[1:]
        else:
            cmd = [sys.executable, os.path.abspath(__file__)] + sys.argv[1:]
        subprocess.Popen(cmd)
        self.root.destroy()

    def open_chrome(self):
        url = self.url.get().strip()
        if not url:
            return
        if "://" not in url:
            url = "https://" + url
            self.url.set(url)
        self.save_settings()
        self.btn_open.configure(state="disabled")
        self.status.set("chrome openen...")

        def work():
            try:
                bot_mod.open_browser(url)
                self.log("chrome open. log in, ga naar de pagina met de lessen, kies lijsten en klik Start.")
                self.q.put(("status", "wacht op jou: log in en kies lijsten"))
            except Exception as e:
                lines = str(e).splitlines()
                self.log("fout: " + (lines[0] if lines else type(e).__name__))
                self.q.put(("status", "chrome starten mislukt"))
            self.q.put(("idle",))

        threading.Thread(target=work, daemon=True).start()

    def start(self):
        if self.worker and self.worker.is_alive():
            return
        names = list(self.order.get(0, "end"))
        if not names:
            messagebox.showinfo("Memory Bot", "kies eerst lijsten (dubbelklik links om toe te voegen).")
            return
        if not bot_mod.alive():
            messagebox.showinfo("Memory Bot", "klik eerst 'Open Chrome', log in en ga naar de lessen.")
            return
        self.save_settings()
        self.log("volgorde:")
        try:
            steps = bot_mod.build_steps(names, self.get_first())
        except Exception as e:
            messagebox.showerror("Memory Bot", "lijst lezen mislukt: " + str(e))
            return
        if not steps:
            messagebox.showinfo("Memory Bot", "er staan alleen overgeslagen kaarten in de volgorde.")
            return
        self.stop.clear()
        self.set_running(True)
        self.status.set("bezig...")
        self.worker = threading.Thread(target=self.run_bot, args=(steps,), daemon=True)
        self.worker.start()

    def run_bot(self, steps):
        try:
            res = bot_mod.run(steps)
            if res == "done":
                self.q.put(("status", "alles klaar"))
            elif res == "stopped":
                self.q.put(("status", "gestopt"))
            else:
                self.q.put(("status", "gestopt: " + str(res)))
        except Exception as e:
            lines = str(e).splitlines()
            self.log("fout: " + (lines[0] if lines else type(e).__name__))
            self.q.put(("status", "fout, zie log"))
        self.q.put(("idle",))

    def stop_run(self):
        self.stop.set()
        if self.pending is not None:
            self.pending.put(None)
        if self.dialog is not None:
            try:
                self.dialog.destroy()
            except tk.TclError:
                pass
        self.status.set("stoppen...")

    def on_close(self):
        self.stop.set()
        if self.pending is not None:
            self.pending.put(None)
        self.save_settings()
        bot_mod.close()
        self.root.destroy()


def main():
    root = tk.Tk()
    App(root)
    root.mainloop()


if __name__ == "__main__":
    main()
