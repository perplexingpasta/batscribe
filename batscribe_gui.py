"""Batscribe GUI: drop a folder, press Start, get an .srt next to every video.

Launch with .venv\\Scripts\\pythonw.exe batscribe_gui.py [folder-or-video ...]
"""
import ctypes
import datetime as dt
import faulthandler
import os
import queue
import subprocess
import sys
import threading
import tkinter as tk
import traceback
import winsound
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from tkinterdnd2 import DND_FILES, TkinterDnD

import batscribe as bs

NOTHING_SELECTED = "Nothing selected yet."
APP_ID = "Batscribe.Captions"  # must match create_shortcut.ps1
# pythonw has no console, so errors would otherwise vanish. faulthandler also writes here if the
# process itself crashes (e.g. inside the GPU engine).
try:
    CRASH_FILE = open(bs.CRASH_LOG, "a", encoding="utf-8")
except OSError:
    CRASH_FILE = None  # the app must still open if the log folder isn't writable
AUTO_LANGUAGE = "Auto-detect"
LANGUAGE_CODES = {name: code for code, name in sorted(bs.LANGUAGES.items(), key=lambda kv: kv[1])}


def log_crash(text):
    if CRASH_FILE:
        CRASH_FILE.write(f"--- {dt.datetime.now():%Y-%m-%d %H:%M:%S}\n{text}\n")
        CRASH_FILE.flush()


class App:
    def __init__(self, root, initial_inputs):
        self.root = root
        self.events = queue.Queue()      # worker thread -> UI thread
        self.stop_flag = threading.Event()
        self.inputs, self.todo, self.durations, self.rows = [], [], {}, {}
        self.finished = set()            # videos captioned in the current/last run
        self.busy = False                # scanning or transcribing
        self.running = False             # transcribing
        self.current = ""

        root.title("Batscribe")
        root.geometry("680x620")
        root.minsize(480, 400)
        root.protocol("WM_DELETE_WINDOW", self.on_close)
        root.drop_target_register(DND_FILES)
        root.dnd_bind("<<Drop>>", self.on_drop)

        pad = {"padx": 12, "pady": (10, 0)}
        drop = tk.Frame(root, bg="#eef3fb", highlightbackground="#9db4d8", highlightthickness=2)
        drop.pack(fill="x", **pad)
        tk.Label(drop, text="Drop a folder or videos here", bg="#eef3fb", fg="#2b4a75",
                 font=("Segoe UI", 13)).pack(pady=(14, 4))
        pick = tk.Frame(drop, bg="#eef3fb")
        pick.pack(pady=(0, 14))
        self.browse_btn = ttk.Button(pick, text="Choose folder…", command=self.browse)
        self.browse_btn.pack(side="left", padx=4)
        self.files_btn = ttk.Button(pick, text="Choose videos…", command=self.browse_files)
        self.files_btn.pack(side="left", padx=4)

        self.summary = ttk.Label(root, text=NOTHING_SELECTED)
        self.summary.pack(fill="x", **pad)
        self.summary.bind("<Configure>", lambda e: self.summary.config(wraplength=e.width))

        list_frame = ttk.Frame(root)
        list_frame.pack(fill="both", expand=True, **pad)
        self.tree = ttk.Treeview(list_frame, columns=("status",), selectmode="browse")
        self.tree.heading("#0", text="Video  (double-click to play)", anchor="w")
        self.tree.heading("status", text="Status", anchor="w")
        self.tree.column("status", width=160, stretch=False)
        self.tree.tag_configure("done", foreground="#1e7b34")
        self.tree.tag_configure("failed", foreground="#b3261e")
        self.tree.tag_configure("active", foreground="#1a56b0")
        self.tree.tag_configure("warn", foreground="#a15c00")
        scroll = ttk.Scrollbar(list_frame, orient="vertical", command=self.tree.yview)
        self.tree.configure(yscrollcommand=scroll.set)
        self.tree.pack(side="left", fill="both", expand=True)
        scroll.pack(side="right", fill="y")
        self.tree.bind("<Double-1>", self.open_selected)

        self.progress = ttk.Progressbar(root, maximum=100)
        self.progress.pack(fill="x", **pad)
        self.stats = ttk.Label(root, text="")
        self.stats.pack(fill="x", padx=12, pady=(4, 0))

        options = ttk.Frame(root)
        options.pack(fill="x", padx=12, pady=(10, 0))
        lang_row = ttk.Frame(options)
        lang_row.pack(anchor="w", pady=(0, 4))
        ttk.Label(lang_row, text="Spoken language:").pack(side="left")
        self.language = tk.StringVar(value=AUTO_LANGUAGE)
        self.language_box = ttk.Combobox(lang_row, textvariable=self.language, state="readonly", width=22,
                                         values=[AUTO_LANGUAGE, *LANGUAGE_CODES])
        self.language_box.pack(side="left", padx=(6, 0))

        buttons = ttk.Frame(root)
        buttons.pack(fill="x", padx=12, pady=12)
        self.start_btn = ttk.Button(buttons, text="Start", command=self.start, state="disabled")
        self.start_btn.pack(side="left")
        self.stop_btn = ttk.Button(buttons, text="Stop", command=self.stop, state="disabled")
        self.stop_btn.pack(side="left", padx=(8, 0))
        ttk.Button(buttons, text="Show in folder", command=self.show_in_folder).pack(side="right")
        ttk.Button(buttons, text="Logs", command=self.show_logs).pack(side="right", padx=(0, 8))

        root.report_callback_exception = self.report_error
        threading.excepthook = lambda a: self.events.put(
            ("error", {"text": "".join(traceback.format_exception(a.exc_type, a.exc_value, a.exc_traceback))}))
        root.after(100, self.pump)
        threading.Thread(target=lambda: self.events.put(("checked", {"problems": bs.check_prerequisites(),
                                                                     "lost": bs.unfinished_batches(),
                                                                     "gpu": bs.cuda_available()})),
                         daemon=True).start()
        if initial_inputs:
            self.load(initial_inputs)

    # ---- choosing input -------------------------------------------------
    def on_drop(self, event):
        if not self.busy:
            self.load(list(self.root.tk.splitlist(event.data)))

    def browse(self):
        folder = filedialog.askdirectory(title="Choose a folder of videos")
        if folder:
            self.load([folder])

    def browse_files(self):
        exts = " ".join("*" + e for e in sorted(bs.VIDEO_EXTS))
        files = filedialog.askopenfilenames(title="Choose videos", filetypes=[("Videos", exts), ("All files", "*.*")])
        if files:
            self.load(list(files))

    def start_over(self):
        """Clear the window so another folder or set of videos can be chosen."""
        self.start_btn.config(text="Start", command=self.start)
        self.inputs, self.todo, self.durations = [], [], {}
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()
        self.summary.config(text=NOTHING_SELECTED)
        self.progress["value"] = 0
        self.stats.config(text="")
        self.set_busy(False)

    def load(self, inputs):
        """Scan in the background (ffprobe on many files takes a few seconds)."""
        self.inputs = [str(Path(p)) for p in inputs]
        self.start_btn.config(text="Start", command=self.start)
        self.set_busy(True)
        self.summary.config(text="Scanning…")
        self.tree.delete(*self.tree.get_children())
        self.rows.clear()

        def scan():
            try:
                videos = bs.collect(self.inputs)
                clashes = bs.name_clashes(videos)
                todo = [v for v in videos if v not in clashes and not v.with_suffix(".srt").exists()]
                others = {v: names for v in todo if (names := bs.other_captions(v))}
                durations = {v: bs.video_duration(v) for v in todo}
            except Exception as e:  # e.g. the drive was unplugged or a folder can't be read
                log_crash(traceback.format_exc())
                self.events.put(("scan_failed", {"error": str(e)}))
                return
            self.events.put(("scanned", {"videos": videos, "todo": todo, "durations": durations,
                                         "clashes": clashes, "others": others}))

        threading.Thread(target=scan, daemon=True).start()

    def on_scan_failed(self, error):
        self.summary.config(text=NOTHING_SELECTED)
        self.set_busy(False)
        self.notify("Batscribe – couldn't read", f"Couldn't read what you chose:\n\n{error}", error=True)

    def on_scanned(self, videos, todo, durations, clashes, others):
        self.todo, self.durations = todo, durations
        base = Path(self.inputs[0]) if Path(self.inputs[0]).is_dir() else None
        for v in videos:
            label = str(v.relative_to(base)) if base and v.is_relative_to(base) else v.name
            if v in clashes:
                status, tag = "⚠ name clash", ("warn",)
            elif v not in durations:
                status, tag = "✔ already done", ("done",)
            else:
                status, tag = ("waiting (has captions)" if v in others else "waiting"), ()
            self.rows[v] = self.tree.insert("", "end", text=label, tags=tag, values=(status,))
        where = self.inputs[0] if len(self.inputs) == 1 else f"{len(self.inputs)} items"
        text = (f"{where}\n{len(videos)} videos · {len(videos) - len(todo) - len(clashes)} already captioned · "
                f"{len(todo)} to do ({bs.fmt_dur(sum(durations.values()))} of audio)")
        if clashes:
            v, first = next(iter(clashes.items()))
            text += (f"\n⚠ {len(clashes)} skipped: same name as another video (e.g. {v.name} and {first.name}"
                     " would share one .srt). Rename one to caption both.")
        if others:
            v, names = next(iter(others.items()))
            text += (f"\n⚠ {len(others)} already have other caption files (e.g. {names[0]}); "
                     f"they'll still get a new {v.stem}.srt.")
        self.summary.config(text=text)
        self.progress["value"] = 0
        self.stats.config(text="" if todo else "Nothing to do — every video already has captions.")
        self.set_busy(False)

    # ---- running --------------------------------------------------------
    def start(self):
        self.finished = set()
        self.stop_flag.clear()
        self.running = True
        self.set_busy(True)
        self.stop_btn.config(state="normal")
        self.progress["value"] = 0

        def work():
            try:
                bs.run_batch(self.todo, self.durations, bs.ERROR_LOG,
                             on_event=lambda kind, **info: self.events.put((kind, info)),
                             should_stop=self.stop_flag.is_set,
                             fast=True, language=LANGUAGE_CODES.get(self.language.get()))
            except Exception as e:  # e.g. model/GPU failed to load
                self.events.put(("crashed", {"error": str(e)}))

        threading.Thread(target=work, daemon=True).start()

    def stop(self):
        self.stop_flag.set()
        self.stop_btn.config(state="disabled")
        self.stats.config(text="Stopping… (the current video will be redone next time)")

    def pump(self):
        """Apply worker events on the UI thread."""
        try:
            while not self.events.empty():
                kind, info = self.events.get()
                getattr(self, "on_" + kind)(**info)
        finally:  # keep the window alive even if one event handler fails
            self.root.after(100, self.pump)

    def set_status(self, video, text, tag=()):
        self.tree.item(self.rows[video], values=(text,), tags=tag)

    def report_error(self, exc_type, exc, tb):
        self.on_error("".join(traceback.format_exception(exc_type, exc, tb)))

    def on_error(self, text):
        log_crash(text)
        self.notify("Batscribe – unexpected error", f"Something went wrong:\n\n{text.strip().splitlines()[-1]}\n\n"
                    f"Details were saved to:\n{bs.CRASH_LOG}", error=True)

    def on_checked(self, problems, lost, gpu):
        if problems:
            self.notify("Batscribe – setup problem", "Captioning won't work until this is fixed:\n\n"
                        + "\n\n".join(f"• {p}" for p in problems), error=True)
        elif not gpu:
            self.notify("Batscribe – no NVIDIA GPU", "No NVIDIA GPU (CUDA) was found, so captioning will run on the "
                        "CPU. That works, but is roughly 10x slower: a 1-hour video may take 30–60 minutes "
                        "depending on your processor.\n\nIf you do have an NVIDIA GPU, update its driver.")
        if lost:
            msg = ("The last captioning run ended without finishing — the app crashed, the PC lost power "
                   f"or restarted, or the window was force-closed:\n\n{lost[-1]}\n\n"
                   "Captions finished before that are saved. Choose the same folder and press Start to continue.")
            started = dt.datetime.strptime(lost[-1][:19], "%Y-%m-%d %H:%M:%S").timestamp()
            if bs.CRASH_LOG.exists() and bs.CRASH_LOG.stat().st_mtime > started:
                msg += f"\n\nTechnical details may be in:\n{bs.CRASH_LOG}"
            self.notify("Batscribe – last run didn't finish", msg, error=True)

    def on_loading(self, model, device):
        self.stats.config(text=f"Loading model {model} on the {'GPU' if device == 'cuda' else 'CPU'}…")

    def on_start(self, n, total, video, duration):
        self.set_status(video, "▶ starting…", ("active",))
        self.tree.see(self.rows[video])
        self.current = f"Video {n} of {total}"
        if not self.stop_flag.is_set():
            self.stats.config(text=f"{self.current} · decoding audio…")

    def on_progress(self, n, video, file_pct, overall_pct, speed, eta):
        self.set_status(video, f"▶ {file_pct:.0f}%", ("active",))
        self.progress["value"] = overall_pct
        self.root.title(f"{overall_pct:.0f}% · Batscribe")
        if not self.stop_flag.is_set():
            self.stats.config(text=f"{self.current} · {overall_pct:.1f}% overall · "
                                   f"{speed:.1f}x realtime · about {bs.fmt_dur(eta)} left")

    def on_done(self, n, video, srt):
        self.finished.add(video)
        self.set_status(video, "✔ done", ("done",))

    def on_skipped(self, n, video):
        self.set_status(video, "✔ already done", ("done",))

    def on_failed(self, n, video, error):
        self.set_status(video, "✖ failed", ("failed",))

    def on_finished(self, ok, failed, stopped, gpu_error, elapsed, log_path):
        for v in self.todo:  # the video that was interrupted, if any
            if self.tree.set(self.rows[v], "status").startswith("▶"):
                self.set_status(v, "stopped")
        self.todo = [v for v in self.todo if v not in self.finished and not v.with_suffix(".srt").exists()]
        self.running = False
        self.set_busy(False)
        if not stopped and not gpu_error:  # stopped or GPU-failed batches keep "Start" to continue
            self.start_btn.config(text="Start over", command=self.start_over, state="normal")
        self.root.title("Batscribe")
        msg = f"{'Stopped' if stopped else 'Finished'} after {bs.fmt_dur(elapsed)}: {ok} captioned, {failed} failed."
        self.stats.config(text=msg)
        if failed:
            msg += f"\n\nDetails of failures:\n{log_path}"
        if gpu_error:
            msg += ("\n\nThe GPU failed, so the remaining videos were not attempted:\n"
                    f"{gpu_error}\n\nClose other GPU-heavy apps (or restart the PC), then press Start to continue.")
        elif self.todo and not stopped:
            msg += "\n\nTo retry the failed videos, choose the same folder again and press Start."
        self.notify("Batscribe", msg, error=bool(failed))

    def on_crashed(self, error):
        self.running = False
        self.set_busy(False)
        self.root.title("Batscribe")
        self.stats.config(text="Could not run.")
        self.notify("Batscribe – error", f"Transcription could not start or stopped unexpectedly:\n\n{error}", error=True)

    # ---- helpers --------------------------------------------------------
    def notify(self, title, msg, error=False):
        winsound.MessageBeep(winsound.MB_ICONHAND if error else winsound.MB_ICONASTERISK)
        self.root.deiconify()
        self.root.lift()
        (messagebox.showwarning if error else messagebox.showinfo)(title, msg, parent=self.root)

    def set_busy(self, busy):
        self.busy = busy
        for btn in (self.browse_btn, self.files_btn):
            btn.config(state="disabled" if busy else "normal")
        self.language_box.config(state="disabled" if busy else "readonly")
        self.start_btn.config(state="disabled" if busy or not self.todo else "normal")
        if not busy:
            self.stop_btn.config(state="disabled")

    def selected_video(self):
        sel = self.tree.selection()
        return next((v for v, item in self.rows.items() if sel and item == sel[0]), None)

    def open_selected(self, _event=None):
        video = self.selected_video()
        if video:
            os.startfile(video)  # players like VLC/MPC pick up the matching .srt automatically

    def show_in_folder(self):
        video = self.selected_video()
        target = video if video else (Path(self.inputs[0]) if self.inputs else None)
        if target:
            subprocess.Popen(f'explorer /select,"{target}"')

    def show_logs(self):
        if bs.HISTORY_LOG.exists():
            os.startfile(bs.HISTORY_LOG)  # opens in Notepad (or the default .log viewer)
        else:
            messagebox.showinfo("Batscribe", "Nothing has been converted yet.", parent=self.root)

    def on_close(self):
        if self.running:
            if not messagebox.askyesno("Batscribe", "Captioning is still running. Quit anyway?\n\n"
                                       "Finished videos are kept; the current one will be redone next time.",
                                       parent=self.root):
                return
            bs.log_batch("STOPPED  window closed while running")
            os._exit(0)  # don't wait for the GPU thread
        self.root.destroy()


def main():
    if CRASH_FILE:
        faulthandler.enable(CRASH_FILE)
    ctypes.windll.shcore.SetProcessDpiAwareness(1)  # crisp text on high-DPI screens
    # Identify as Batscribe, not "Python", so a taskbar pin relaunches this app (see create_shortcut.ps1).
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    root = TkinterDnD.Tk()
    root.iconphoto(True, tk.PhotoImage(file=Path(__file__).with_name("batscribe.png")))
    App(root, sys.argv[1:])
    root.mainloop()


if __name__ == "__main__":
    main()
