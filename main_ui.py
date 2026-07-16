import os
import sys
import urllib.request
import ssl

# TỰ ĐỘNG TẢI main.py
MAIN_PY_URL = "https://raw.githubusercontent.com/URF6160/Netflix-Checker/main/main.py"
MAIN_PY_FILE = "main.py"

def download_main_py():
    if os.path.exists(MAIN_PY_FILE):
        return True, ""
    
    print("\n" + "═" * 50)
    print("✨ Netflix Cookie Checker")
    print("═" * 50)
    print("📥 Đang tải main.py từ GitHub...")
    
    try:
        ctx = ssl.create_default_context()
        ctx.check_hostname = False
        ctx.verify_mode = ssl.CERT_NONE
        
        req = urllib.request.Request(MAIN_PY_URL,
            headers={'User-Agent': 'Mozilla/5.0'})
        
        with urllib.request.urlopen(req, timeout=30, context=ctx) as resp:
            content = resp.read()
            
        if len(content) < 1000:
            return False, "File quá nhỏ"
            
        with open(MAIN_PY_FILE, 'wb') as f:
            f.write(content)
            
        print("✅ Tải thành công!\n")
        return True, ""
        
    except Exception as e:
        return False, str(e)

ok, err = download_main_py()
if not ok:
    print(f"❌ Lỗi: {err}")
    print(f"Tải thủ công: {MAIN_PY_URL}")
    input("\nEnter để thoát...")
    sys.exit(1)

# IMPORTS
import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import queue
import copy
import random
import string
import time

try:
    from main import (
        DEFAULT_CONFIG, APP_VERSION,
        cookies_folder, output_folder, failed_folder, broken_folder,
        create_base_folders, load_config, load_proxies, cleanup_stale_temp_files,
        get_run_folder, processed_emails,
        extract_netflix_cookie_bundles, has_required_netflix_cookies,
        cookies_dict_from_netscape, build_bundle_filename, build_bundle_display_name,
        get_account_page, extract_info, is_subscribed_account, is_on_hold_account,
        has_complete_account_info, derive_output_plan_bucket,
        get_canonical_output_label, format_cookie_file, decode_netflix_value,
        generate_unknown_guid, describe_http_error, format_plan_label,
        create_nftoken, get_nftoken_mode,
        move_cookie_with_reason, write_cookie_with_reason, write_text_file_safely,
        create_output_folder_when_needed, send_notifications,
        guid_lock, requests,
    )
except ImportError as e:
    print(f"❌ Import error: {e}")
    print("Thử xóa main.py và chạy lại")
    input("\nEnter để thoát...")
    sys.exit(1)


# THEME
class Theme:
    # Background
    BG_DARK = "#0f0f1a"
    BG_MID = "#1a1a2e"
    
    # Glass
    GLASS = "#252545"
    GLASS_LIGHT = "#2d2d55"
    GLASS_BORDER = "#3d3d6d"
    
    # Accent
    PRIMARY = "#818cf8"      # Indigo
    SECONDARY = "#a78bfa"    # Purple
    PINK = "#f472b6"
    CYAN = "#22d3ee"
    GREEN = "#4ade80"
    YELLOW = "#fbbf24"
    ORANGE = "#fb923c"
    RED = "#f87171"
    
    # Text
    TEXT = "#f1f5f9"
    TEXT_DIM = "#94a3b8"
    TEXT_MUTED = "#64748b"
    
    # Status
    SUCCESS = "#4ade80"
    WARNING = "#fbbf24"
    ERROR = "#f87171"
    FREE = "#22d3ee"
    PREMIUM = "#fbbf24"
    DUPLICATE = "#e879f9"
    EXTRA = "#a78bfa"


# MAIN GUI
class NetflixCheckerGUI:
    def __init__(self, root):
        self.root = root
        self.root.title(f"Netflix Cookie Checker v{APP_VERSION}")
        self.root.geometry("1100x820")
        self.root.minsize(950, 700)
        self.root.configure(bg=Theme.BG_DARK)
        
        # State
        self.is_running = False
        self.stop_requested = threading.Event()
        self.config = None
        self.log_queue = queue.Queue()
        self.stats_queue = queue.Queue()
        self.stats_snapshot_lock = threading.Lock()
        self.latest_stats_snapshot = None
        self.max_log_batch = 150
        self.max_log_lines = 4000
        self.started_at = None
        self.last_progress_at = None
        self.last_done_count = 0
        self.smoothed_rate = 0.0
        self.active_workers = 0
        self.run_finished = False
        
        # Stats
        self.counts = {"hits": 0, "free": 0, "bad": 0, "duplicate": 0, "on_hold": 0, "errors": 0}
        self.plan_counts = {}
        self.plan_labels = {}
        self.cookies_total = 0
        self.cookies_left = 0
        
        self.create_ui()
        self.load_config()
        self.process_queues()
        
    def create_ui(self):
        # Main
        main = tk.Frame(self.root, bg=Theme.BG_DARK)
        main.pack(fill=tk.BOTH, expand=True, padx=20, pady=20)
        
        self.create_header(main)
        
        content = tk.Frame(main, bg=Theme.BG_DARK)
        content.pack(fill=tk.BOTH, expand=True, pady=(15, 0))
        
        # Left
        left = tk.Frame(content, bg=Theme.BG_DARK, width=300)
        left.pack(side=tk.LEFT, fill=tk.Y, padx=(0, 15))
        left.pack_propagate(False)
        
        self.create_stats_panel(left)
        self.create_info_panel(left)
        
        # Right
        right = tk.Frame(content, bg=Theme.BG_DARK)
        right.pack(side=tk.LEFT, fill=tk.BOTH, expand=True)
        
        self.create_control_panel(right)
        self.create_progress_panel(right)
        self.create_log_panel(right)
        
    def create_header(self, parent):
        header = tk.Frame(parent, bg=Theme.BG_DARK)
        header.pack(fill=tk.X, pady=(0, 5))
        
        # Left - Title
        left = tk.Frame(header, bg=Theme.BG_DARK)
        left.pack(side=tk.LEFT)
        
        tk.Label(left, text="🎬", font=("Segoe UI Emoji", 32),
                bg=Theme.BG_DARK, fg=Theme.PRIMARY).pack(side=tk.LEFT, padx=(0, 12))
        
        title_frame = tk.Frame(left, bg=Theme.BG_DARK)
        title_frame.pack(side=tk.LEFT)
        
        tk.Label(title_frame, text="Netflix Cookie Checker",
                font=("Segoe UI", 24, "bold"),
                bg=Theme.BG_DARK, fg=Theme.TEXT).pack(anchor='w')
        
        tk.Label(title_frame, text=f"v{APP_VERSION}✨",
                font=("Segoe UI", 10),
                bg=Theme.BG_DARK, fg=Theme.SECONDARY).pack(anchor='w')
        
        # Right - Author
        author_frame = tk.Frame(header, bg=Theme.GLASS,
                               highlightbackground=Theme.GLASS_BORDER,
                               highlightthickness=1)
        author_frame.pack(side=tk.RIGHT, pady=10)
        
        tk.Label(author_frame, text="  ✨ by Mania_kov  ",
                font=("Segoe UI", 10, "bold"),
                bg=Theme.GLASS, fg=Theme.PINK).pack(padx=12, pady=6)
        
    def create_glass_panel(self, parent, title=None, icon=None):
        outer = tk.Frame(parent, bg=Theme.BG_DARK)
        outer.pack(fill=tk.X, pady=(0, 12))
        
        glass = tk.Frame(outer, bg=Theme.GLASS,
                        highlightbackground=Theme.GLASS_BORDER,
                        highlightthickness=1)
        glass.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(glass, bg=Theme.GLASS)
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        if title:
            title_row = tk.Frame(inner, bg=Theme.GLASS)
            title_row.pack(fill=tk.X, pady=(0, 10))
            
            if icon:
                tk.Label(title_row, text=icon, font=("Segoe UI Emoji", 12),
                        bg=Theme.GLASS, fg=Theme.PRIMARY).pack(side=tk.LEFT, padx=(0, 8))
            
            tk.Label(title_row, text=title, font=("Segoe UI", 12, "bold"),
                    bg=Theme.GLASS, fg=Theme.TEXT).pack(side=tk.LEFT)
                    
        return inner
        
    def create_stats_panel(self, parent):
        """Số lượng theo gói"""
        panel = self.create_glass_panel(parent, "Số lượng theo gói", "📊")
        
        self.plan_widgets = {}
        plans = [
            ("premium", "💎", "Premium", Theme.PREMIUM),
            ("standard", "✦", "Standard", Theme.PRIMARY),
            ("standard_with_ads", "📺", "Standard (Ads)", Theme.SECONDARY),
            ("basic", "●", "Basic", Theme.ORANGE),
            ("mobile", "📱", "Mobile", Theme.CYAN),
            ("free", "○", "Free", Theme.FREE),
        ]
        
        for key, icon, label, color in plans:
            # Main row
            row = tk.Frame(panel, bg=Theme.GLASS)
            row.pack(fill=tk.X, pady=3)
            
            left = tk.Frame(row, bg=Theme.GLASS)
            left.pack(side=tk.LEFT)
            # Icon với màu tương ứng
            tk.Label(left, text=icon, font=("Segoe UI", 11),
                    bg=Theme.GLASS, fg=color).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(left, text=label, font=("Segoe UI", 10),
                    bg=Theme.GLASS, fg=Theme.TEXT_DIM).pack(side=tk.LEFT)
            
            count_lbl = tk.Label(row, text="0", font=("Segoe UI", 12, "bold"),
                                bg=Theme.GLASS, fg=color)
            count_lbl.pack(side=tk.RIGHT)
            
            # Extra member row
            extra_row = tk.Frame(panel, bg=Theme.GLASS)
            
            extra_left = tk.Frame(extra_row, bg=Theme.GLASS)
            extra_left.pack(side=tk.LEFT)
            tk.Label(extra_left, text="     └─ Extra Member", font=("Segoe UI", 9),
                    bg=Theme.GLASS, fg=Theme.TEXT_MUTED).pack(side=tk.LEFT)
            
            extra_count = tk.Label(extra_row, text="0", font=("Segoe UI", 10, "bold"),
                                  bg=Theme.GLASS, fg=Theme.EXTRA)
            extra_count.pack(side=tk.RIGHT)
            
            self.plan_widgets[key] = {
                'row': row,
                'count': count_lbl,
                'extra_row': extra_row,
                'extra_count': extra_count,
                'color': color
            }
            
    def create_info_panel(self, parent):
        """Thông tin"""
        panel = self.create_glass_panel(parent, "Thông tin", "📋")
        
        self.info_labels = {}
        # Icon đẹp hơn
        items = [
            ("valid", "✓", "Hợp lệ", Theme.SUCCESS),
            ("hits", "★", "Ngon", Theme.SUCCESS),
            ("bad", "✗", "Hỏng", Theme.ERROR),
            ("duplicate", "◎", "Trùng", Theme.DUPLICATE),
            ("on_hold", "⏸", "Bị giữ", Theme.CYAN),
            ("errors", "⚠", "Lỗi", Theme.WARNING),
        ]
        
        for key, icon, label, color in items:
            row = tk.Frame(panel, bg=Theme.GLASS)
            row.pack(fill=tk.X, pady=2)
            
            left = tk.Frame(row, bg=Theme.GLASS)
            left.pack(side=tk.LEFT)
            # Icon với màu tương ứng
            tk.Label(left, text=icon, font=("Segoe UI", 11, "bold"),
                    bg=Theme.GLASS, fg=color).pack(side=tk.LEFT, padx=(0, 8))
            tk.Label(left, text=label, font=("Segoe UI", 10),
                    bg=Theme.GLASS, fg=Theme.TEXT_DIM).pack(side=tk.LEFT)
            
            val = tk.Label(row, text="0", font=("Segoe UI", 11, "bold"),
                          bg=Theme.GLASS, fg=color)
            val.pack(side=tk.RIGHT)
            self.info_labels[key] = val
            
    def create_control_panel(self, parent):
        panel = self.create_glass_panel(parent)
        
        ctrl = tk.Frame(panel, bg=Theme.GLASS)
        ctrl.pack(fill=tk.X)
        
        # Threads
        tk.Label(ctrl, text="⚡ Số luồng:", font=("Segoe UI", 10),
                bg=Theme.GLASS, fg=Theme.TEXT_DIM).pack(side=tk.LEFT, padx=(0, 8))
        
        self.thread_var = tk.StringVar(value="45")
        self.thread_entry = tk.Entry(ctrl, textvariable=self.thread_var,
                                    width=5, font=("Segoe UI", 11),
                                    bg=Theme.GLASS_LIGHT, fg=Theme.TEXT,
                                    insertbackground=Theme.TEXT,
                                    relief=tk.FLAT, justify='center')
        self.thread_entry.pack(side=tk.LEFT, ipady=5)
        
        # Folder info
        self.folder_label = tk.Label(ctrl, text="📁 0 cookies • 🌐 0 proxies",
                                    font=("Segoe UI", 9),
                                    bg=Theme.GLASS, fg=Theme.TEXT_MUTED)
        self.folder_label.pack(side=tk.LEFT, padx=(20, 0))
        
        # Buttons
        btn_frame = tk.Frame(ctrl, bg=Theme.GLASS)
        btn_frame.pack(side=tk.RIGHT)
        
        self.refresh_btn = tk.Button(btn_frame, text="↻", font=("Segoe UI", 12, "bold"),
                                    bg=Theme.GLASS_LIGHT, fg=Theme.PRIMARY,
                                    relief=tk.FLAT, padx=12, pady=6,
                                    cursor='hand2', command=self.refresh_counts)
        self.refresh_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.start_btn = tk.Button(btn_frame, text="▶ BẮT ĐẦU",
                                  font=("Segoe UI", 10, "bold"),
                                  bg=Theme.PRIMARY, fg="white",
                                  relief=tk.FLAT, padx=20, pady=8,
                                  cursor='hand2', command=self.start_checking)
        self.start_btn.pack(side=tk.LEFT, padx=(0, 8))
        
        self.stop_btn = tk.Button(btn_frame, text="■ DỪNG",
                                 font=("Segoe UI", 10, "bold"),
                                 bg=Theme.TEXT_MUTED, fg="white",
                                 relief=tk.FLAT, padx=15, pady=8,
                                 cursor='hand2', command=self.stop_checking,
                                 state=tk.DISABLED)
        self.stop_btn.pack(side=tk.LEFT)
        
    def create_progress_panel(self, parent):
        panel = self.create_glass_panel(parent)
        
        self.progress_label = tk.Label(panel, text="● Sẵn sàng",
                                       font=("Segoe UI", 10),
                                       bg=Theme.GLASS, fg=Theme.TEXT)
        self.progress_label.pack(anchor='w', pady=(0, 8))

        self.progress_meta_label = tk.Label(panel, text="⚡ ETA: -- • Tốc độ: 0.00 cookies/s",
                                           font=("Segoe UI", 9),
                                           bg=Theme.GLASS, fg=Theme.TEXT_MUTED)
        self.progress_meta_label.pack(anchor='w', pady=(0, 10))
        
        prog_bg = tk.Frame(panel, bg=Theme.GLASS_LIGHT, height=8)
        prog_bg.pack(fill=tk.X)
        prog_bg.pack_propagate(False)
        
        self.progress_fill = tk.Frame(prog_bg, bg=Theme.PRIMARY, height=8)
        self.progress_fill.place(x=0, y=0, relheight=1, relwidth=0)
        
    def create_log_panel(self, parent):
        outer = tk.Frame(parent, bg=Theme.BG_DARK)
        outer.pack(fill=tk.BOTH, expand=True, pady=(12, 0))
        
        glass = tk.Frame(outer, bg=Theme.GLASS,
                        highlightbackground=Theme.GLASS_BORDER,
                        highlightthickness=1)
        glass.pack(fill=tk.BOTH, expand=True)
        
        inner = tk.Frame(glass, bg=Theme.GLASS)
        inner.pack(fill=tk.BOTH, expand=True, padx=15, pady=12)
        
        # Header
        header = tk.Frame(inner, bg=Theme.GLASS)
        header.pack(fill=tk.X, pady=(0, 8))
        
        tk.Label(header, text="📋 Nhật ký", font=("Segoe UI", 12, "bold"),
                bg=Theme.GLASS, fg=Theme.TEXT).pack(side=tk.LEFT)
        
        tk.Button(header, text="🗑 Xóa", font=("Segoe UI", 9),
                 bg=Theme.GLASS_LIGHT, fg=Theme.TEXT_DIM,
                 relief=tk.FLAT, padx=10, pady=3,
                 cursor='hand2', command=self.clear_log).pack(side=tk.RIGHT)
        
        # Log
        self.log_text = scrolledtext.ScrolledText(
            inner, bg="#12122a", fg=Theme.TEXT,
            font=("Consolas", 9), relief=tk.FLAT, wrap=tk.WORD,
            insertbackground=Theme.TEXT, padx=8, pady=8
        )
        self.log_text.pack(fill=tk.BOTH, expand=True)
        
        # Tags
        self.log_text.tag_configure("success", foreground=Theme.SUCCESS)
        self.log_text.tag_configure("free", foreground=Theme.FREE)
        self.log_text.tag_configure("error", foreground=Theme.ERROR)
        self.log_text.tag_configure("warning", foreground=Theme.WARNING)
        self.log_text.tag_configure("info", foreground=Theme.TEXT)
        self.log_text.tag_configure("duplicate", foreground=Theme.DUPLICATE)
        self.log_text.tag_configure("dim", foreground=Theme.TEXT_MUTED)
        self.log_text.tag_configure("extra", foreground=Theme.EXTRA)
        self.log_text.tag_configure("accent", foreground=Theme.PRIMARY)
        
    # LOGIC
    
    def load_config(self):
        create_base_folders()
        cleanup_stale_temp_files()
        self.config, src = load_config()
        self.refresh_counts()
        self.log("═" * 45, "dim")
        self.log("✨ Netflix Cookie Checker", "accent")
        self.log(f"📁 Config: {src}", "info")
        self.log("═" * 45, "dim")
        
    def refresh_counts(self):
        cookies = []
        if os.path.exists(cookies_folder):
            for root, dirs, files in os.walk(cookies_folder):
                for f in files:
                    if f.lower().endswith((".txt", ".json")) and not f.startswith("."):
                        cookies.append(f)
        proxies = load_proxies()
        self.folder_label.config(text=f"📁 {len(cookies)} cookies • 🌐 {len(proxies)} proxies")
        self.log(f"🔍 {len(cookies)} cookies, {len(proxies)} proxies", "info")
        
    def log(self, msg, tag="info"):
        self.log_queue.put((msg, tag))

    def _set_latest_stats_snapshot(self, data):
        with self.stats_snapshot_lock:
            self.latest_stats_snapshot = data

    def _apply_latest_stats_snapshot(self):
        with self.stats_snapshot_lock:
            data = self.latest_stats_snapshot
            self.latest_stats_snapshot = None

        if not data:
            return False

        self.counts = data["counts"]
        self.plan_counts = data["plan_counts"]
        self.plan_labels = data["plan_labels"]
        self.cookies_total = data["cookies_total"]
        self.cookies_left = data["cookies_left"]
        self.update_display()
        return True

    def _trim_log_if_needed(self):
        line_count = int(self.log_text.index("end-1c").split(".")[0])
        if line_count > self.max_log_lines:
            trim_lines = line_count - self.max_log_lines
            self.log_text.delete("1.0", f"{trim_lines + 1}.0")

    def _format_duration(self, seconds):
        if seconds is None:
            return "--"

        seconds = max(0, int(round(seconds)))
        hours, remainder = divmod(seconds, 3600)
        minutes, secs = divmod(remainder, 60)

        if hours > 0:
            return f"{hours:02d}:{minutes:02d}:{secs:02d}"
        return f"{minutes:02d}:{secs:02d}"
        
    def process_queues(self):
        log_batch = []
        for _ in range(self.max_log_batch):
            try:
                log_batch.append(self.log_queue.get_nowait())
            except queue.Empty:
                break

        if log_batch:
            for msg, tag in log_batch:
                self.log_text.insert(tk.END, msg + "\n", tag)
            self._trim_log_if_needed()
            self.log_text.see(tk.END)

        self._apply_latest_stats_snapshot()

        if self.run_finished:
            self.run_finished = False
            self._done()

        next_delay = 35 if len(log_batch) >= self.max_log_batch else 100
        self.root.after(next_delay, self.process_queues)
        
    def clear_log(self):
        self.log_text.delete(1.0, tk.END)
        
    def update_display(self):
        """Cập nhật hiển thị"""
        # Tính extra
        extra_counts = {}
        for k, v in self.plan_counts.items():
            if str(k).startswith("extra_member_") and v > 0:
                base = str(k)[len("extra_member_"):] or "unknown"
                extra_counts[base] = extra_counts.get(base, 0) + v
        
        # Cập nhật từng plan
        plan_order = ["premium", "standard", "standard_with_ads", "basic", "mobile", "free"]
        
        for key in plan_order:
            if key not in self.plan_widgets:
                continue
                
            w = self.plan_widgets[key]
            base_val = self.plan_counts.get(key, 0)
            extra_val = extra_counts.get(key, 0)
            
            w['count'].config(text=str(base_val + extra_val))
            
            w['extra_row'].pack_forget()
            if extra_val > 0:
                w['extra_row'].pack(fill=tk.X, pady=1, after=w['row'])
                w['extra_count'].config(text=str(extra_val))
        
        # Info
        total_free = self.plan_counts.get("free", 0)
        total_hits = self.counts["hits"]
        valid = total_hits + total_free
        
        self.info_labels["valid"].config(text=str(valid))
        self.info_labels["hits"].config(text=str(total_hits))
        self.info_labels["bad"].config(text=str(self.counts["bad"]))
        self.info_labels["duplicate"].config(text=str(self.counts["duplicate"]))
        self.info_labels["on_hold"].config(text=str(self.counts["on_hold"]))
        self.info_labels["errors"].config(text=str(self.counts["errors"]))
        
        # Progress
        done = self.cookies_total - self.cookies_left
        if self.cookies_total > 0:
            pct = done / self.cookies_total
            self.progress_fill.place(relwidth=pct)
            self.progress_label.config(
                text=f"● {done}/{self.cookies_total} ({pct*100:.1f}%) • Còn: {self.cookies_left}"
            )

            now = time.monotonic()
            if self.started_at is not None:
                if self.last_progress_at is None:
                    self.last_progress_at = now

                delta_done = done - self.last_done_count
                delta_time = now - self.last_progress_at
                if delta_done > 0 and delta_time > 0:
                    current_rate = delta_done / delta_time
                    if self.smoothed_rate <= 0:
                        self.smoothed_rate = current_rate
                    else:
                        self.smoothed_rate = (self.smoothed_rate * 0.65) + (current_rate * 0.35)
                    self.last_done_count = done
                    self.last_progress_at = now

                elapsed = max(now - self.started_at, 0.001)
                avg_rate = done / elapsed if done > 0 else 0.0
                rate = self.smoothed_rate if self.smoothed_rate > 0 else avg_rate
                eta_seconds = (self.cookies_left / rate) if rate > 0 and self.cookies_left > 0 else 0
                eta_text = self._format_duration(eta_seconds if done > 0 else None)
                worker_text = self.active_workers or "-"
                self.progress_meta_label.config(
                    text=f"⚡ ETA: {eta_text} • Tốc độ: {rate:.2f} cookies/s • Luồng chạy: {worker_text}"
                )
        else:
            self.progress_label.config(text="● Sẵn sàng")
            self.progress_meta_label.config(text="⚡ ETA: -- • Tốc độ: 0.00 cookies/s")
        
    def start_checking(self):
        if self.is_running:
            return
            
        try:
            threads = int(self.thread_var.get())
            if not 1 <= threads <= 9999999999:
                raise ValueError
        except:
            messagebox.showerror("Lỗi", "Số luồng: 1-9999999999")
            return
            
        cookies = []
        if os.path.exists(cookies_folder):
            for root, dirs, files in os.walk(cookies_folder):
                for f in files:
                    if f.lower().endswith((".txt", ".json")) and not f.startswith("."):
                        cookies.append(f)
        
        if not cookies:
            messagebox.showwarning("!", "Không có cookies!")
            return
            
        # Reset
        self.is_running = True
        self.stop_requested.clear()
        self.counts = {"hits": 0, "free": 0, "bad": 0, "duplicate": 0, "on_hold": 0, "errors": 0}
        self.plan_counts = {}
        self.plan_labels = {}
        self.latest_stats_snapshot = None
        self.started_at = time.monotonic()
        self.last_progress_at = self.started_at
        self.last_done_count = 0
        self.smoothed_rate = 0.0
        self.active_workers = 0
        self.run_finished = False
        processed_emails.clear()
        
        for w in self.plan_widgets.values():
            w['count'].config(text="0")
            w['extra_row'].pack_forget()
        for l in self.info_labels.values():
            l.config(text="0")
        
        self.start_btn.config(state=tk.DISABLED)
        self.stop_btn.config(state=tk.NORMAL, bg=Theme.ERROR)
        self.thread_entry.config(state=tk.DISABLED)
        self.progress_fill.place(relwidth=0)
        self.progress_label.config(text="● Đang chuẩn bị...")
        self.progress_meta_label.config(text="⚡ ETA: -- • Tốc độ: 0.00 cookies/s • Luồng chạy: 0")
        
        self.log("═" * 45, "dim")
        self.log(f"🚀 Bắt đầu với {threads} luồng...", "accent")
        self.log("═" * 45, "dim")
        
        threading.Thread(target=self._run, args=(threads,), daemon=True).start()
        
    def stop_checking(self):
        if self.is_running:
            self.stop_requested.set()
            self.log("■ Đang dừng...", "warning")
        
    def _run(self, num_threads):
        try:
            self._check(num_threads)
        except Exception as e:
            self.log(f"✗ {e}", "error")
        finally:
            self.is_running = False
            self.run_finished = True
            
    def _done(self):
        self.start_btn.config(state=tk.NORMAL)
        self.stop_btn.config(state=tk.DISABLED, bg=Theme.TEXT_MUTED)
        self.thread_entry.config(state=tk.NORMAL)
        
        # Xóa folder trống trong cookies
        if os.path.exists(cookies_folder):
            for root, dirs, files in os.walk(cookies_folder, topdown=False):
                for dir_name in dirs:
                    full_path = os.path.join(root, dir_name)
                    try:
                        if not os.listdir(full_path):
                            os.rmdir(full_path)
                    except:
                        pass
        self._apply_latest_stats_snapshot()
        
        self.update_display()

        elapsed = None
        if self.started_at is not None:
            elapsed = max(0, time.monotonic() - self.started_at)
        
        # Kết quả - LẤY TỪ plan_counts ĐÃ FLUSH
        total_free = self.plan_counts.get("free", 0)
        total_hits = self.counts["hits"]
        valid = total_hits + total_free
        
        self.log("═" * 45, "dim")
        if self.stop_requested.is_set() and self.cookies_left > 0:
            self.log("■ ĐÃ DỪNG", "warning")
        else:
            self.log("✨ HOÀN TẤT!", "accent")
        self.log(f"   Tổng: {self.cookies_total}", "info")
        if elapsed is not None:
            avg_rate = (self.cookies_total - self.cookies_left) / elapsed if elapsed > 0 else 0.0
            self.log(f"   Thời gian: {self._format_duration(elapsed)}", "info")
            self.log(f"   Tốc độ TB: {avg_rate:.2f} cookies/s", "info")
        
        # Plans
        extra_counts = {}
        for k, v in self.plan_counts.items():
            if str(k).startswith("extra_member_"):
                base = str(k)[len("extra_member_"):]
                extra_counts[base] = extra_counts.get(base, 0) + v
        
        for key in ["premium", "standard", "standard_with_ads", "basic", "mobile", "free"]:
            base = self.plan_counts.get(key, 0)
            extra = extra_counts.get(key, 0)
            total = base + extra
            if total > 0:
                lbl = decode_netflix_value(self.plan_labels.get(key)) or format_plan_label(key)
                self.log(f"   {lbl}: {total}", "success" if key != "free" else "free")
                if extra > 0:
                    self.log(f"      └─ Extra: {extra}", "extra")
        
        self.log(f"   Hợp lệ: {valid}", "success")
        self.log(f"   Hỏng: {self.counts['bad']}", "error")
        self.log(f"   Trùng: {self.counts['duplicate']}", "duplicate")
        self.log(f"   Lỗi: {self.counts['errors']}", "error")
        self.log("═" * 45, "dim")

        if self.stop_requested.is_set() and self.cookies_left > 0:
            self.progress_meta_label.config(
                text=f"⚡ Đã dừng • Hoàn thành: {self.cookies_total - self.cookies_left}/{self.cookies_total} • Luồng chạy: {self.active_workers or '-'}"
            )
        elif elapsed is not None:
            avg_rate = (self.cookies_total - self.cookies_left) / elapsed if elapsed > 0 else 0.0
            self.progress_meta_label.config(
                text=f"⚡ Xong trong {self._format_duration(elapsed)} • Tốc độ TB: {avg_rate:.2f} cookies/s • Luồng chạy: {self.active_workers or '-'}"
            )
        
    def _check(self, num_threads):
        """Logic check"""
        config = self.config or copy.deepcopy(DEFAULT_CONFIG)
        create_base_folders()
        
        counts = {"hits": 0, "free": 0, "bad": 0, "duplicate": 0, "on_hold": 0, "errors": 0}
        plan_counts = {}
        plan_labels = {}
        run_folder = get_run_folder()
        
        proxies = load_proxies()
        cfg_retry = config.get("retries", {})
        cfg_perf = config.get("performance", {})
        max_retry = max(1, int(cfg_retry.get("error_proxy_attempts", 5)))
        nft_retry = max(1, int(cfg_retry.get("nftoken_attempts", 5)))
        timeout = max(5, int(cfg_perf.get("request_timeout_seconds", 15)))
        fallback = bool(cfg_perf.get("fallback_account_page", False))
        retry_inc = bool(cfg_perf.get("retry_incomplete_info", False))
        nft_free = bool(cfg_perf.get("nftoken_for_free", False))
        
        retry_codes = {403, 429, 500, 502, 503, 504}
        
        tasks = []
        states = {}
        
        # Quét tất cả file trong folder cookies và subfolders
        all_cookie_data = []
        for root, dirs, files in os.walk(cookies_folder):
            for f in files:
                if f.lower().endswith((".txt", ".json")) and not f.startswith("."):
                    all_cookie_data.append((f, os.path.join(root, f)))

        for f, path in all_cookie_data:

            try:
                with open(path, "r", encoding="utf-8", errors="ignore") as fp:
                    content = fp.read()
            except:
                tasks.append({"kind": "read_error", "file": f, "path": path})
                continue
                
            bundles = extract_netflix_cookie_bundles(content)
            if not bundles:
                tasks.append({"kind": "missing", "file": f, "path": path})
                continue
                
            total = len(bundles)
            rewrite = f.lower().endswith(".txt") and total > 1
            if total > 1:
                states[path] = {
                    "lock": threading.Lock(),
                    "remaining": {b.get("index", 1) for b in bundles},
                    "bundles": {b.get("index", 1): b for b in bundles},
                    "rewrite": rewrite,
                }
                
            for b in bundles:
                idx = b.get("index", 1)
                tasks.append({
                    "kind": "bundle", "file": f, "path": path,
                    "bundle": b, "index": idx, "total": total,
                    "bundle_file": build_bundle_filename(f, idx, total),
                    "label": build_bundle_display_name(f, idx, total),
                    "remove": total <= 1,
                })
                
        total_tasks = len(tasks)
        left = [total_tasks]
        proxy_cursor = [0]
        proxy_cursor_lock = threading.Lock()
        last_stats_push = [0.0]

        def publish_stats(force=False):
            now = time.monotonic()
            if not force and left[0] > 0 and (now - last_stats_push[0]) < 0.2:
                return
            last_stats_push[0] = now
            self._set_latest_stats_snapshot({
                "counts": dict(counts), "plan_counts": dict(plan_counts),
                "plan_labels": dict(plan_labels),
                "cookies_total": total_tasks, "cookies_left": left[0]
            })

        effective_threads = max(1, min(num_threads, total_tasks or 1, 9999999999))
        self.active_workers = effective_threads

        if effective_threads != num_threads:
            self.log(f"ℹ Dùng {effective_threads} luồng thực tế để UI ổn định hơn", "info")

        publish_stats(force=True)

        if total_tasks == 0:
            return

        self._set_latest_stats_snapshot({
            "counts": dict(counts), "plan_counts": dict(plan_counts),
            "plan_labels": dict(plan_labels),
            "cookies_total": total_tasks, "cookies_left": left[0]
        })
        
        q = queue.Queue()
        for t in tasks:
            q.put(t)
            
        lock = threading.Lock()
        
        def get_proxy(used):
            if not proxies:
                return None, None
            avail = [i for i in range(len(proxies)) if i not in used]
            if not avail:
                avail = list(range(len(proxies)))
            with proxy_cursor_lock:
                for _ in range(len(proxies)):
                    rotated = proxy_cursor[0] % len(proxies)
                    proxy_cursor[0] = (proxy_cursor[0] + 1) % len(proxies)
                    if rotated not in used:
                        return proxies[rotated], rotated
            idx = avail[0]
            return proxies[idx], idx
            
        def handle(info, netscape, path, file, subscribed, cookies, remove=True):
            create_base_folders()
            guid = info.get("userGuid")
            if not guid or guid == "null":
                guid = generate_unknown_guid()
            plan_key, folder_lbl, plan_name = derive_output_plan_bucket(info, subscribed)
            on_hold = subscribed and is_on_hold_account(info)
            info["userGuid"] = guid
            country = info.get("countryOfSignup") or "?"
            suffix = "".join(random.choices(string.ascii_uppercase + string.digits, k=5))
            fname = f"{country}_Hachimi_{suffix}.txt"
            
            email = (decode_netflix_value(info.get("email")) or "").strip().lower()
            dup_key = email or guid
            
            with guid_lock:
                if dup_key in processed_emails:
                    nft = None
                    if subscribed and get_nftoken_mode(config) != "false":
                        nft, _ = create_nftoken(cookies, nft_retry)
                    fmt = format_cookie_file(info, netscape, config, subscribed, nft)
                    dup_dir = create_output_folder_when_needed(output_folder, get_canonical_output_label("duplicate"), run_folder)
                    write_text_file_safely(os.path.join(dup_dir, f"DUP_{fname}"), fmt)
                    if remove and os.path.exists(path):
                        os.remove(path)
                    return "duplicate", None, None, False
                processed_emails.add(dup_key)
                
            if subscribed:
                cat = "On Hold" if on_hold else None
                out_dir = create_output_folder_when_needed(output_folder, folder_lbl, run_folder, category=cat)
                result = "success"
            else:
                out_dir = create_output_folder_when_needed(output_folder, get_canonical_output_label("free"), run_folder)
                result = "free"
                
            nft = None
            if get_nftoken_mode(config) != "false" and (subscribed or nft_free):
                nft, _ = create_nftoken(cookies, nft_retry)
            fmt = format_cookie_file(info, netscape, config, subscribed, nft)
            write_text_file_safely(os.path.join(out_dir, fname), fmt)
            
            if remove and os.path.exists(path):
                os.remove(path)
                
            send_notifications(config, info, subscribed, fname, fmt, netscape, nft)
            return result, plan_key, plan_name, on_hold
            
        def record(result, label, plan_key=None, plan_name=None, reason=None, country=None, on_hold=False):
            with lock:
                if result == "success":
                    counts["hits"] += 1
                    if on_hold:
                        counts["on_hold"] += 1
                    if plan_key:
                        plan_counts[plan_key] = plan_counts.get(plan_key, 0) + 1
                        if plan_name:
                            plan_labels[plan_key] = plan_name
                elif result == "free":
                    counts["free"] += 1
                    plan_counts["free"] = plan_counts.get("free", 0) + 1
                    plan_labels["free"] = "Free"
                elif result == "failed":
                    counts["bad"] += 1
                elif result == "duplicate":
                    counts["duplicate"] += 1
                else:
                    counts["errors"] += 1
                    
                left[0] -= 1
                publish_stats()
                
                is_extra = plan_key and str(plan_key).startswith("extra_member_")
                
                if result == "success":
                    disp = decode_netflix_value(plan_name) or format_plan_label(plan_key) if plan_key else "?"
                    extra_tag = " [Extra]" if is_extra else ""
                    hold_tag = " [HOLD]" if on_hold else ""
                    tag = "extra" if is_extra else "success"
                    self.log(f"✓ {label} - {country or '?'} - {disp}{extra_tag}{hold_tag}", tag)
                elif result == "free":
                    self.log(f"○ {label} - {country or '?'} - Free", "free")
                elif result == "failed":
                    self.log(f"✗ {label} - {reason or '?'}", "error")
                elif result == "duplicate":
                    self.log(f"◎ {label} - Trùng", "duplicate")
                else:
                    self.log(f"⚠ {label} - {reason or 'Lỗi'}", "warning")
                    
        def finalize(task):
            path = task.get("path")
            state = states.get(path)
            if not state:
                return
            with state["lock"]:
                state["remaining"].discard(task.get("index", 1))
                if state["remaining"]:
                    if not state.get("rewrite"):
                        return
                    texts = []
                    for i in sorted(state["remaining"]):
                        b = state["bundles"].get(i) or {}
                        t = b.get("netscape_text", "").strip()
                        if t:
                            texts.append(t)
                    if not texts:
                        try:
                            if os.path.exists(path):
                                os.remove(path)
                        except:
                            pass
                        return
                    try:
                        write_text_file_safely(path, "\n\n".join(texts) + "\n")
                    except:
                        pass
                    return
                try:
                    if os.path.exists(path):
                        os.remove(path)
                except:
                    pass
                states.pop(path, None)
                
        def process(task):
            if self.stop_requested.is_set():
                return
                
            kind = task.get("kind")
            file = task.get("file")
            path = task.get("path")
            
            if kind == "read_error":
                try:
                    move_cookie_with_reason(path, broken_folder, file, "read error")
                except:
                    pass
                record("error", file, reason="read error")
                return
                
            if kind == "missing":
                try:
                    move_cookie_with_reason(path, failed_folder, file, "missing")
                except:
                    pass
                record("failed", file, reason="missing")
                return
                
            bundle = task.get("bundle") or {}
            netscape = bundle.get("netscape_text", "")
            bundle_file = task.get("bundle_file") or file
            label = task.get("label") or file
            remove = task.get("remove", True)
            
            plan_key = plan_name = result = reason = country = None
            on_hold = False
            
            try:
                cookies = bundle.get("cookies") or cookies_dict_from_netscape(netscape)
                if not cookies or not has_required_netflix_cookies(cookies):
                    result = "failed"
                    reason = "missing"
                    if remove:
                        move_cookie_with_reason(path, failed_folder, file, reason)
                    else:
                        write_cookie_with_reason(failed_folder, bundle_file, reason, netscape)
                    return
                    
                session = requests.Session()
                session.cookies.update(cookies)
                
                used = set()
                resp = status = info = err = None
                
                for att in range(max_retry):
                    if self.stop_requested.is_set():
                        return
                    proxy, idx = get_proxy(used)
                    if idx is not None:
                        used.add(idx)
                    try:
                        resp, status, info = get_account_page(
                            session, proxy, request_timeout=timeout, fallback_account_page=fallback
                        )
                        if status == 200 and resp:
                            if retry_inc and att < max_retry - 1:
                                if not (info and has_complete_account_info(info)):
                                    continue
                            break
                        if status in retry_codes and att < max_retry - 1:
                            continue
                        break
                    except Exception as e:
                        err = e
                        if att < max_retry - 1:
                            continue
                            
                if status == 200 and resp:
                    info = info or extract_info(resp)
                    if info.get("countryOfSignup") and info.get("countryOfSignup") != "null":
                        subscribed = is_subscribed_account(info)
                        country = info.get("countryOfSignup")
                        result, plan_key, plan_name, on_hold = handle(
                            info, netscape, path, bundle_file, subscribed, cookies, remove=remove
                        )
                    else:
                        result = "failed"
                        reason = "incomplete"
                        if remove:
                            move_cookie_with_reason(path, failed_folder, file, reason)
                        else:
                            write_cookie_with_reason(failed_folder, bundle_file, reason, netscape)
                elif err or status in retry_codes:
                    result = "error"
                    if status in retry_codes:
                        reason = describe_http_error(status)
                    elif isinstance(err, requests.exceptions.Timeout):
                        reason = "timeout"
                    else:
                        reason = "proxy"
                    if remove:
                        move_cookie_with_reason(path, broken_folder, file, reason)
                    else:
                        write_cookie_with_reason(broken_folder, bundle_file, reason, netscape)
                else:
                    result = "failed"
                    reason = "incomplete"
                    if remove:
                        move_cookie_with_reason(path, failed_folder, file, reason)
                    else:
                        write_cookie_with_reason(failed_folder, bundle_file, reason, netscape)
            except:
                result = "error"
                reason = reason or "error"
                try:
                    if remove:
                        move_cookie_with_reason(path, broken_folder, file, reason)
                    else:
                        write_cookie_with_reason(broken_folder, bundle_file, reason, netscape)
                except:
                    pass
            finally:
                record(result or "error", label, plan_key=plan_key, plan_name=plan_name,
                      reason=reason, country=country, on_hold=on_hold)
                if not remove:
                    finalize(task)
                    
        def worker():
            while not self.stop_requested.is_set():
                try:
                    task = q.get_nowait()
                except queue.Empty:
                    break
                process(task)
                
        threads = [threading.Thread(target=worker, daemon=True) for _ in range(effective_threads)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        publish_stats(force=True)


def main():
    root = tk.Tk()
    root.update_idletasks()
    w, h = 1100, 820
    x = (root.winfo_screenwidth() - w) // 2
    y = (root.winfo_screenheight() - h) // 2
    root.geometry(f"{w}x{h}+{x}+{y}")
    
    NetflixCheckerGUI(root)
    root.mainloop()


if __name__ == "__main__":
    main()
