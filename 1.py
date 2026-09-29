"""
MatchDesk Studio v4.2 — Standalone eSports Tournament Desk
Fast-Start Cinematic Splash Screen, Heavy Sub-Drop Audio Engine,
Universal MP3/WAV Reader & Complete Bracket Synchronization.
"""

import copy
import datetime as dt
import json
import math
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import tkinter as tk
import wave
from pathlib import Path
from tkinter import colorchooser, filedialog, messagebox, simpledialog, ttk

APP_NAME = "MatchDesk Studio"
APP_VERSION = "4.2.0"
APP_ID = f"esports.matchdesk.studio.{APP_VERSION}"

if sys.platform == "win32":
    try:
        import ctypes
        ctypes.windll.shcore.SetProcessDpiAwareness(1)
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID(APP_ID)
    except Exception:
        pass


def get_app_storage_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("APPDATA", Path.home()))
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path.home() / ".config"
    target = base / "MatchDeskStudio"
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_build_storage_dir() -> Path:
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData" / "Local"))
    else:
        base = Path.home() / ".cache"
    target = base / "MatchDeskBuild"
    target.mkdir(parents=True, exist_ok=True)
    return target


def get_script_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).parent
    try:
        return Path(__file__).resolve().parent
    except Exception:
        return Path.cwd()


# -----------------------------------------------------------------------------
# Cinematic Trailer Audio Engine
# -----------------------------------------------------------------------------
def get_or_create_cinematic_wav() -> Path:
    target_wav = get_app_storage_dir() / "cinematic_impact_fast.wav"
    if target_wav.is_file() and target_wav.stat().st_size > 10000:
        return target_wav

    sample_rate = 44100
    duration = 2.0
    num_samples = int(sample_rate * duration)
    impact_time = 0.20  # Точное совпадение со столкновением на 13-м кадре (13 * 15 мс)

    samples = []
    for i in range(num_samples):
        t = i / sample_rate
        val = 0.0

        if t < impact_time:
            prog = t / impact_time
            rumble_freq = 40.0 + (prog ** 2.0) * 60.0
            rumble = math.sin(2.0 * math.pi * rumble_freq * t) * (prog ** 1.6) * 0.6
            noise = random.uniform(-1.0, 1.0) * (prog ** 2.0) * 0.3
            val = rumble + noise
        else:
            dt_imp = t - impact_time
            kick_env = math.exp(-dt_imp * 30.0)
            kick_pitch = 145.0 * math.exp(-dt_imp * 36.0) + 48.0
            kick = math.sin(2.0 * math.pi * kick_pitch * dt_imp) * kick_env * 0.8

            anvil_env = math.exp(-dt_imp * 18.0)
            anvil = (
                math.sin(2.0 * math.pi * 210.0 * dt_imp) * 0.35
                + math.sin(2.0 * math.pi * 380.0 * dt_imp) * 0.25
                + math.sin(2.0 * math.pi * 620.0 * dt_imp) * 0.15
            ) * anvil_env

            sub_pitch = 26.0 + 62.0 * math.exp(-dt_imp * 3.0)
            sub_env = math.exp(-dt_imp * 1.3)
            sub = math.sin(2.0 * math.pi * sub_pitch * dt_imp) * sub_env * 0.95

            tail_noise = random.uniform(-1.0, 1.0) * math.exp(-dt_imp * 7.0) * 0.16
            raw = kick + anvil + sub + tail_noise
            val = math.tanh(raw * 1.5) * 0.95

        val = max(-1.0, min(1.0, val))
        samples.append(struct.pack("<h", int(val * 32767)))

    try:
        with wave.open(str(target_wav), "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(2)
            wf.setframerate(sample_rate)
            wf.writeframes(b"".join(samples))
    except Exception:
        pass

    return target_wav


def find_user_sound_file() -> Path | None:
    search_dirs = [
        get_script_dir(),
        get_script_dir() / "players",
        Path.cwd(),
        Path.cwd() / "players",
        Path(sys.argv[0]).resolve().parent,
        Path(sys.argv[0]).resolve().parent / "players",
    ]
    audio_extensions = {".wav", ".mp3", ".ogg"}
    keywords = ("sound", "intro", "music", "audio", "theme", "track", "splash", "hit")

    for d in search_dirs:
        if not d.is_dir():
            continue
        for f in d.iterdir():
            if f.is_file() and f.suffix.lower() in audio_extensions:
                if any(k in f.stem.lower() for k in keywords):
                    return f

    for d in (get_script_dir() / "players", Path.cwd() / "players"):
        if d.is_dir():
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in audio_extensions:
                    return f

    for d in (get_script_dir(), Path.cwd()):
        if d.is_dir():
            for f in d.iterdir():
                if f.is_file() and f.suffix.lower() in audio_extensions:
                    return f

    return None


def play_sound_universal(file_path: Path):
    if sys.platform != "win32":
        return

    ext = file_path.suffix.lower()
    safe_temp = Path(tempfile.gettempdir()) / f"matchdesk_audio_stream{ext}"
    try:
        shutil.copy2(file_path, safe_temp)
        audio_target = safe_temp
    except Exception:
        audio_target = file_path

    if ext == ".wav":
        try:
            import winsound
            winsound.PlaySound(
                str(audio_target.resolve()),
                winsound.SND_FILENAME | winsound.SND_ASYNC | winsound.SND_NODEFAULT,
            )
            return
        except Exception:
            pass

    try:
        import ctypes
        winmm = ctypes.windll.winmm
        alias = "md_splash_media"
        winmm.mciSendStringW(f"close {alias}", None, 0, 0)

        buf = ctypes.create_unicode_buffer(512)
        ctypes.windll.kernel32.GetShortPathNameW(str(audio_target.resolve()), buf, 512)
        short_path = buf.value or str(audio_target.resolve())

        open_cmd = f'open "{short_path}" type mpegvideo alias {alias}'
        res = winmm.mciSendStringW(open_cmd, None, 0, 0)
        if res != 0:
            open_cmd = f'open "{short_path}" alias {alias}'
            winmm.mciSendStringW(open_cmd, None, 0, 0)

        winmm.mciSendStringW(f"play {alias}", None, 0, 0)
    except Exception:
        pass


# -----------------------------------------------------------------------------
# Color Palette & Constants
# -----------------------------------------------------------------------------
MIN_TEAMS, MAX_TEAMS = 2, 64

BG = "#0B0C10"
BG2 = "#0F1117"
PANEL = "#13161F"
PANEL_ALT = "#181C26"
CARD = "#1C212E"
CARD_ALT = "#141822"
SURFACE = "#0D0F15"
BORDER = "#252B3A"
BORDER_SOFT = "#1A1F2B"
TEXT = "#F3F5F9"
MUTED = "#788194"
ACCENT = "#FF462D"
ACCENT_HOVER = "#E03620"
ACCENT_2 = "#FF6B4A"
ORANGE_TINT = "#2B1714"
CYAN = "#38BDF8"
GREEN = "#10B981"
GOLD = "#F59E0B"
RED = "#EF4444"
LINE = "#323847"

MODES = {
    "Single Elimination": "single",
    "Double Elimination": "double",
    "Round Robin": "round_robin",
}

PRESETS = {
    "CS2 Major (16)": [
        "Natus Vincere", "FaZe Clan", "Team Vitality", "G2 Esports",
        "Team Spirit", "MOUZ", "Virtus.pro", "Cloud9",
        "Heroic", "Eternal Fire", "Complexity", "FURIA Esports",
        "The MongolZ", "Imperial Esports", "paiN Gaming", "ECSTATIC",
    ],
    "Valorant Masters (8)": [
        "Sentinels", "Paper Rex", "Fnatic", "Gen.G Esports",
        "Team Heretics", "Leviatán", "EDward Gaming", "DRX",
    ],
    "FGC Local (8)": [
        "Striker", "Vortex", "Shadow", "Phoenix",
        "Titan", "Ghost", "Blaze", "Echo",
    ],
}


# -----------------------------------------------------------------------------
# Fast-Start Splash Screen with Corner Photos
# -----------------------------------------------------------------------------
class SplashScreen(tk.Toplevel):
    def __init__(self, parent, on_complete):
        super().__init__(parent)
        self.on_complete = on_complete

        self.overrideredirect(True)
        self.configure(bg=BG)

        self.width = self.winfo_screenwidth()
        self.height = self.winfo_screenheight()
        self.geometry(f"{self.width}x{self.height}+0+0")

        self.scale = min(self.width, self.height) / 900.0

        self.canvas = tk.Canvas(
            self,
            width=self.width,
            height=self.height,
            bg=BG,
            highlightthickness=0,
        )
        self.canvas.pack(fill="both", expand=True)

        self.bind("<Button-1>", lambda e: self.finish())
        self.bind("<Key>", lambda e: self.finish())

        self.bg_photos = []
        self._load_background_photos()
        self._trigger_sound()

        self.frame = 0
        self.frame_delay = 15     # Шаг анимации 15 мс (~66 FPS)
        self.impact_frame = 13    # Быстрое схождение: удар наступает в 2 раза быстрее
        self.total_frames = 85    # Общий хронометраж заставки
        self.running = True

        self.sparks = []
        self.shockwaves = []
        self.shake_energy = 0.0

        self.animate()

    def _trigger_sound(self):
        def _run():
            track = find_user_sound_file()
            if not track:
                track = get_or_create_cinematic_wav()
            if track and track.is_file():
                play_sound_universal(track)

        threading.Thread(target=_run, daemon=True).start()

    def _load_background_photos(self):
        try:
            from PIL import Image, ImageTk
        except ImportError:
            return

        candidate_dirs = [
            get_script_dir() / "players",
            Path.cwd() / "players",
            Path(sys.argv[0]).resolve().parent / "players",
        ]
        players_dir = None
        for d in candidate_dirs:
            if d.is_dir():
                players_dir = d
                break

        if not players_dir:
            return

        files = [
            f for f in players_dir.iterdir()
            if f.is_file() and f.suffix.lower() in (".png", ".jpg", ".jpeg", ".webp")
        ]
        if not files:
            return

        random.shuffle(files)
        chosen_files = files[:4]

        quadrants = [
            (-self.width * 0.33, -self.height * 0.22, -4.5, 0.22),
            (self.width * 0.33, -self.height * 0.22, 4.0, 0.22),
            (-self.width * 0.32, self.height * 0.24, 3.5, 0.20),
            (self.width * 0.32, self.height * 0.24, -4.0, 0.20),
        ]

        resample_filter = (
            getattr(Image, "Resampling", Image).LANCZOS
            if hasattr(Image, "Resampling")
            else getattr(Image, "LANCZOS", 1)
        )

        for idx, fpath in enumerate(chosen_files):
            try:
                with Image.open(fpath) as img:
                    img = img.convert("RGBA")
                    target_w = int(random.uniform(360, 440) * self.scale)
                    img.thumbnail((target_w, target_w), resample_filter)

                    ox, oy, base_angle, alpha_pct = quadrants[idx]
                    angle = base_angle + random.uniform(-1.5, 1.5)

                    try:
                        bicubic = (
                            getattr(Image, "Resampling", Image).BICUBIC
                            if hasattr(Image, "Resampling")
                            else getattr(Image, "BICUBIC", 3)
                        )
                        img = img.rotate(angle, expand=True, resample=bicubic)
                    except Exception:
                        img = img.rotate(angle, expand=True)

                    r, g, b, a = img.split()
                    a = a.point(lambda p: int(p * alpha_pct))
                    img.putalpha(a)

                    photo = ImageTk.PhotoImage(img)
                    self.bg_photos.append({"photo": photo, "ox": ox, "oy": oy})
            except Exception:
                continue

    def animate(self):
        if not self.running or not self.winfo_exists():
            return

        self.canvas.delete("all")

        shake_x, shake_y = 0.0, 0.0
        if self.shake_energy > 0.1:
            shake_x = random.uniform(-self.shake_energy, self.shake_energy)
            shake_y = random.uniform(-self.shake_energy, self.shake_energy)
            self.shake_energy *= 0.72

        cx = self.width / 2 + shake_x
        cy = (self.height / 2 - 40 * self.scale) + shake_y

        for item in self.bg_photos:
            px = cx + item["ox"]
            py = cy + item["oy"]
            self.canvas.create_image(px, py, image=item["photo"], anchor="center")

        if self.frame < self.impact_frame:
            prog = self.frame / float(self.impact_frame)
            offset_x = math.pow(1.0 - prog, 1.8) * (480.0 * self.scale)

            trail_len = (1.0 - prog) * (90.0 * self.scale)
            for i in range(1, 4):
                t_off = offset_x + i * trail_len * 0.35
                self._draw_cup_half(cx - t_off, cy, side=-1, mode="trail")
                self._draw_cup_half(cx + t_off, cy, side=1, mode="trail")

            self._draw_cup_half(cx - offset_x, cy, side=-1, mode="steel")
            self._draw_cup_half(cx + offset_x, cy, side=1, mode="steel")

            if random.random() < 0.85:
                self.sparks.append({
                    "x": cx - offset_x + random.uniform(-15, 15),
                    "y": cy + random.uniform(-50, 50),
                    "vx": random.uniform(-12, -4),
                    "vy": random.uniform(-4, 4),
                    "life": 12, "max_life": 12,
                    "color": ACCENT, "size": 3.0 * self.scale, "drag": 0.9, "gravity": 0.1,
                })
                self.sparks.append({
                    "x": cx + offset_x + random.uniform(-15, 15),
                    "y": cy + random.uniform(-50, 50),
                    "vx": random.uniform(4, 12),
                    "vy": random.uniform(-4, 4),
                    "life": 12, "max_life": 12,
                    "color": ACCENT, "size": 3.0 * self.scale, "drag": 0.9, "gravity": 0.1,
                })

        elif self.frame == self.impact_frame:
            offset_x = 0.0
            self.shake_energy = 24.0 * self.scale

            for _ in range(110):
                angle = random.uniform(0, math.pi * 2)
                speed = random.uniform(8.0, 36.0) * self.scale
                color = random.choice(["#FFFFFF", "#FEF08A", "#FF462D", "#F59E0B", "#FF6B4A", "#FFFFFF"])
                self.sparks.append({
                    "x": cx,
                    "y": cy + random.uniform(-80, 70),
                    "vx": math.cos(angle) * speed,
                    "vy": math.sin(angle) * speed - random.uniform(2, 6) * self.scale,
                    "life": random.randint(22, 45),
                    "max_life": 45,
                    "color": color,
                    "size": random.uniform(2.5, 5.0) * self.scale,
                    "drag": random.uniform(0.92, 0.96),
                    "gravity": 0.4 * self.scale,
                })

            self.shockwaves.append({"radius": 10.0, "max": 380.0 * self.scale, "color": "#FFFFFF", "width": 5})
            self.shockwaves.append({"radius": 4.0, "max": 280.0 * self.scale, "color": ACCENT, "width": 8})

            seam_h = 220 * self.scale
            self.canvas.create_line(cx, cy - seam_h, cx, cy + seam_h, fill="#FFFFFF", width=int(12 * self.scale))
            self.canvas.create_oval(cx - 50 * self.scale, cy - 50 * self.scale, cx + 50 * self.scale, cy + 50 * self.scale, fill="#FFFFFF", outline=ACCENT, width=4)

            self._draw_cup_half(cx, cy, side=-1, mode="gold")
            self._draw_cup_half(cx, cy, side=1, mode="gold")

        else:
            post_prog = min(1.0, (self.frame - self.impact_frame) / 16.0)
            self._draw_cup_half(cx, cy, side=-1, mode="gold", shine=post_prog)
            self._draw_cup_half(cx, cy, side=1, mode="gold", shine=post_prog)

            if self.frame - self.impact_frame < 10:
                fade = 1.0 - (self.frame - self.impact_frame) / 10.0
                h = 180 * self.scale * fade
                self.canvas.create_line(cx, cy - h, cx, cy + h, fill="#FFFFFF", width=int(5 * self.scale * fade) or 1)

        for sw in list(self.shockwaves):
            sw["radius"] += (sw["max"] - sw["radius"]) * 0.22
            alpha = max(0, 1.0 - sw["radius"] / sw["max"])
            if alpha <= 0.04:
                self.shockwaves.remove(sw)
                continue
            r = sw["radius"]
            w = max(1, int(sw["width"] * alpha))
            self.canvas.create_oval(cx - r, cy - r * 0.65, cx + r, cy + r * 0.65, outline=sw["color"], width=w)

        for p in list(self.sparks):
            p["x"] += p["vx"]
            p["y"] += p["vy"]
            p["vx"] *= p["drag"]
            p["vy"] += p["gravity"]
            p["life"] -= 1

            if p["life"] <= 0:
                self.sparks.remove(p)
                continue

            streak_len = 1.8
            tail_x = p["x"] - p["vx"] * streak_len
            tail_y = p["y"] - p["vy"] * streak_len
            thickness = max(1, int(p["size"] * (p["life"] / float(p["max_life"]))))
            self.canvas.create_line(p["x"], p["y"], tail_x, tail_y, fill=p["color"], width=thickness)

        if self.frame >= self.impact_frame:
            txt_alpha = min(1.0, (self.frame - self.impact_frame) / 14.0)
            txt_color = TEXT if txt_alpha > 0.8 else MUTED

            text_y = cy + 130 * self.scale
            sub_y = cy + 165 * self.scale

            self.canvas.create_text(
                cx, text_y,
                text="CYBERSPORT.KING",
                fill=txt_color,
                font=("Segoe UI", int(22 * self.scale), "bold"),
            )
            self.canvas.create_text(
                cx, sub_y,
                text=f"ТУРНИРНЫЙ ГЕНЕРАТОР СЕТОК • v{APP_VERSION}",
                fill=ACCENT,
                font=("Consolas", int(11 * self.scale)),
            )

            bar_w = int(380 * self.scale)
            bar_h = int(4 * self.scale)
            bx = cx - bar_w / 2
            by = cy + 205 * self.scale

            self.canvas.create_rectangle(bx, by, bx + bar_w, by + bar_h, fill=CARD_ALT, outline="")
            load_prog = min(1.0, (self.frame - self.impact_frame) / float(self.total_frames - self.impact_frame))
            self.canvas.create_rectangle(bx, by, bx + bar_w * load_prog, by + bar_h, fill=ACCENT, outline="")

            status_msg = (
                "ИНИЦИАЛИЗАЦИЯ ТУРНИРНОЙ СИСТЕМЫ..."
                if self.frame < (self.impact_frame + 20)
                else "ЗАГРУЗКА ПРЕСЕТОВ И ФОРМАТОВ..."
                if self.frame < (self.total_frames - 15)
                else "ГОТОВО К СТАРТУ"
            )
            self.canvas.create_text(
                cx, cy + 230 * self.scale,
                text=status_msg,
                fill=MUTED,
                font=("Consolas", int(9 * self.scale)),
            )

        self.frame += 1
        if self.frame >= self.total_frames:
            self.after(150, self.finish)
        else:
            self.after(self.frame_delay, self.animate)

    def _draw_cup_half(self, cx, cy, side=1, mode="gold", shine=1.0):
        s = side
        sc = self.scale

        if mode == "trail":
            c_base, c_body, c_light, c_rim, c_handle, outline_c = (
                "#0F131C", "#141926", "#1B2335", "#242E45", "#141926", "#1B2233",
            )
        elif mode == "steel":
            c_base, c_body, c_light, c_rim, c_handle, outline_c = (
                "#1C202C", "#313849", "#5A657D", "#8E9BB5", "#414B60", ACCENT,
            )
        else:
            c_base, c_body, c_light, c_rim, c_handle, outline_c = (
                "#181B24", "#B45309", "#F59E0B", "#FEF08A", "#D97706", "#FDE68A",
            )

        handle_poly = [
            cx + s * (42 * sc), cy - (44 * sc),
            cx + s * (72 * sc), cy - (54 * sc),
            cx + s * (88 * sc), cy - (36 * sc),
            cx + s * (90 * sc), cy - (8 * sc),
            cx + s * (82 * sc), cy + (20 * sc),
            cx + s * (64 * sc), cy + (38 * sc),
            cx + s * (34 * sc), cy + (30 * sc),
            cx + s * (32 * sc), cy + (24 * sc),
            cx + s * (58 * sc), cy + (30 * sc),
            cx + s * (74 * sc), cy + (14 * sc),
            cx + s * (78 * sc), cy - (8 * sc),
            cx + s * (76 * sc), cy - (28 * sc),
            cx + s * (62 * sc), cy - (44 * sc),
            cx + s * (42 * sc), cy - (36 * sc),
        ]
        self.canvas.create_polygon(handle_poly, fill=c_handle, outline=outline_c, width=max(1, int(1.5 * sc)))

        plinth_pts = [
            cx, cy + (68 * sc),
            cx + s * (46 * sc), cy + (68 * sc),
            cx + s * (50 * sc), cy + (86 * sc),
            cx, cy + (86 * sc),
        ]
        self.canvas.create_polygon(plinth_pts, fill=c_base, outline="#333A4A", width=max(1, int(2 * sc)))

        if mode == "gold":
            plate_pts = [
                cx, cy + (72 * sc),
                cx + s * (44 * sc), cy + (72 * sc),
                cx + s * (46 * sc), cy + (82 * sc),
                cx, cy + (82 * sc),
            ]
            self.canvas.create_polygon(plate_pts, fill="#D97706", outline=outline_c, width=max(1, int(sc)))

        foot_pts = [
            cx, cy + (56 * sc),
            cx + s * (24 * sc), cy + (56 * sc),
            cx + s * (36 * sc), cy + (68 * sc),
            cx, cy + (68 * sc),
        ]
        self.canvas.create_polygon(foot_pts, fill=c_body, outline=outline_c, width=max(1, int(sc)))

        chalice_pts = [
            cx, cy - (52 * sc),
            cx + s * (52 * sc), cy - (52 * sc),
            cx + s * (53 * sc), cy - (40 * sc),
            cx + s * (50 * sc), cy - (18 * sc),
            cx + s * (44 * sc), cy + (4 * sc),
            cx + s * (34 * sc), cy + (24 * sc),
            cx + s * (22 * sc), cy + (38 * sc),
            cx + s * (13 * sc), cy + (46 * sc),
            cx + s * (11 * sc), cy + (50 * sc),
            cx + s * (13 * sc), cy + (56 * sc),
            cx, cy + (56 * sc),
        ]
        self.canvas.create_polygon(chalice_pts, fill=c_body, outline=outline_c, width=max(1, int(2 * sc)))

        lustre_pts = [
            cx, cy - (50 * sc),
            cx + s * (32 * sc), cy - (50 * sc),
            cx + s * (31 * sc), cy - (22 * sc),
            cx + s * (24 * sc), cy + (6 * sc),
            cx + s * (14 * sc), cy + (26 * sc),
            cx + s * (8 * sc), cy + (44 * sc),
            cx, cy + (48 * sc),
        ]
        self.canvas.create_polygon(lustre_pts, fill=c_light, outline="")

        if mode == "gold":
            glint_pts = [
                cx, cy - (48 * sc),
                cx + s * (14 * sc), cy - (48 * sc),
                cx + s * (13 * sc), cy - (18 * sc),
                cx + s * (9 * sc), cy + (10 * sc),
                cx, cy + (32 * sc),
            ]
            self.canvas.create_polygon(glint_pts, fill="#FEF08A", outline="")

        rim_band = [
            cx, cy - (56 * sc),
            cx + s * (52 * sc), cy - (56 * sc),
            cx + s * (52 * sc), cy - (50 * sc),
            cx, cy - (50 * sc),
        ]
        self.canvas.create_polygon(rim_band, fill=c_rim, outline=outline_c, width=max(1, int(sc)))

        cavity_pts = [
            cx, cy - (54 * sc),
            cx + s * (46 * sc), cy - (54 * sc),
            cx + s * (38 * sc), cy - (50 * sc),
            cx, cy - (50 * sc),
        ]
        self.canvas.create_polygon(cavity_pts, fill="#78350F" if mode == "gold" else "#0F172A", outline="")

    def finish(self):
        if not self.running:
            return
        self.running = False
        try:
            import ctypes
            ctypes.windll.winmm.mciSendStringW("stop md_splash_media", None, 0, 0)
            ctypes.windll.winmm.mciSendStringW("close md_splash_media", None, 0, 0)
        except Exception:
            pass
        self.destroy()
        self.on_complete()


# -----------------------------------------------------------------------------
# Tournament Generation Algorithms
# -----------------------------------------------------------------------------
def next_power_of_two(n):
    p = 1
    while p < n:
        p *= 2
    return p


def round_name(size):
    return {
        64: "1/32 финала",
        32: "1/16 финала",
        16: "1/8 финала",
        8: "1/4 финала",
        4: "Полуфинал",
        2: "Финал",
    }.get(size, f"Раунд ({size})")


def make_match(a=None, b=None, *, a_ready=False, b_ready=False, a_source=None, b_source=None, best_of=3):
    match = {
        "a": a,
        "b": b,
        "winner": None,
        "a_ready": a_ready,
        "b_ready": b_ready,
        "resolved": False,
        "best_of": best_of,
        "score_a": None,
        "score_b": None,
    }
    if a_source is not None:
        match["a_source"] = a_source
    if b_source is not None:
        match["b_source"] = b_source
    refresh_match(match, a, b, a_ready, b_ready, force=True)
    return match


def refresh_match(match, a, b, a_ready, b_ready, *, force=False):
    changed = force or any((
        match.get("a") != a,
        match.get("b") != b,
        bool(match.get("a_ready")) != a_ready,
        bool(match.get("b_ready")) != b_ready,
    ))
    match["a"], match["b"] = a, b
    match["a_ready"], match["b_ready"] = a_ready, b_ready
    if changed:
        match["winner"] = None
        match["resolved"] = False
        match["score_a"] = None
        match["score_b"] = None

    if not (a_ready and b_ready):
        match["winner"] = None
        match["resolved"] = False
        match["score_a"] = None
        match["score_b"] = None
    elif a is None or b is None:
        match["winner"] = b if a is None else a
        match["resolved"] = True
    elif match.get("winner") not in (a, b):
        match["winner"] = None
        match["resolved"] = False
        match["score_a"] = None
        match["score_b"] = None
    else:
        match["resolved"] = True


def feeder(bracket, round_index, match_index, outcome="winner"):
    return {
        "bracket": bracket,
        "round": round_index,
        "match": match_index,
        "outcome": outcome,
    }


def seeded_slots(teams, shuffle=random.shuffle):
    names = list(teams)
    shuffle(names)
    size = next_power_of_two(len(names))
    bye_count = size - len(names)
    pairs = []
    for _ in range(bye_count):
        team = names.pop()
        pair = [team, None]
        shuffle(pair)
        pairs.append(pair)
    while names:
        pairs.append([names.pop(), names.pop()])
    shuffle(pairs)
    return [slot for pair in pairs for slot in pair]


def build_upper_rounds(teams, *, prefix="", shuffle=random.shuffle, best_of=3):
    slots = seeded_slots(teams, shuffle=shuffle)
    rounds = []
    matches = [
        make_match(slots[i], slots[i + 1], a_ready=True, b_ready=True, best_of=best_of)
        for i in range(0, len(slots), 2)
    ]
    rounds.append({"name": prefix + round_name(len(slots)), "matches": matches})
    previous_count = len(matches)
    round_index = 1
    while previous_count > 1:
        matches = []
        for match_index in range(previous_count // 2):
            matches.append(
                make_match(
                    a_source=feeder("upper", round_index - 1, match_index * 2),
                    b_source=feeder("upper", round_index - 1, match_index * 2 + 1),
                    best_of=best_of,
                )
            )
        rounds.append({"name": prefix + round_name(previous_count), "matches": matches})
        previous_count = len(matches)
        round_index += 1
    return rounds


def build_lower_rounds(upper_rounds, *, best_of=3):
    lower = []
    upper_match_count = len(upper_rounds[0]["matches"])
    if upper_match_count == 1:
        sources = [(feeder("upper", 0, 0), feeder("upper", 0, 0, "loser"))]
        lower.append(_source_round("Гранд-финал", sources, best_of))
        return lower

    sources = [
        (feeder("upper", 0, i * 2, "loser"), feeder("upper", 0, i * 2 + 1, "loser"))
        for i in range(upper_match_count // 2)
    ]
    lower.append(_source_round("Нижняя: раунд 1", sources, best_of))

    for upper_index in range(1, len(upper_rounds)):
        previous = len(lower) - 1
        count = len(upper_rounds[upper_index]["matches"])
        sources = [
            (feeder("lower", previous, i), feeder("upper", upper_index, i, "loser"))
            for i in range(count)
        ]
        lower.append(_source_round(f"Нижняя: раунд {len(lower) + 1}", sources, best_of))
        if upper_index < len(upper_rounds) - 1:
            previous = len(lower) - 1
            sources = [
                (feeder("lower", previous, i * 2), feeder("lower", previous, i * 2 + 1))
                for i in range(count // 2)
            ]
            lower.append(_source_round(f"Нижняя: раунд {len(lower) + 1}", sources, best_of))

    lower.append(
        _source_round(
            "Гранд-финал",
            [(feeder("upper", len(upper_rounds) - 1, 0), feeder("lower", len(lower) - 1, 0))],
            best_of,
        )
    )
    return lower


def _source_round(name, sources, best_of=3):
    return {
        "name": name,
        "matches": [
            make_match(a_source=a_source, b_source=b_source, best_of=best_of)
            for a_source, b_source in sources
        ],
    }


def parse_score(raw, best_of):
    if best_of not in (1, 3, 5):
        raise ValueError("Доступны только BO1, BO3 и BO5.")
    parts = raw.strip().replace("-", ":").split(":")
    if len(parts) != 2:
        raise ValueError("Счёт нужно ввести в формате 2:1.")
    try:
        score_a, score_b = (int(part.strip()) for part in parts)
    except ValueError as exc:
        raise ValueError("Счёт должен состоять из целых чисел.") from exc
    wins_needed = best_of // 2 + 1
    if min(score_a, score_b) < 0 or max(score_a, score_b) != wins_needed or min(score_a, score_b) >= wins_needed:
        raise ValueError(f"Недопустимый итоговый счёт для BO{best_of}.")
    return score_a, score_b


def parse_score_entry(raw, default_best_of):
    value = raw.strip()
    best_of = default_best_of
    if value.upper().startswith("BO"):
        try:
            prefix, value = value.split(maxsplit=1)
            best_of = int(prefix[2:])
        except (ValueError, IndexError) as exc:
            raise ValueError("Используйте формат BO5 3:1 или просто 3:1.") from exc
    score_a, score_b = parse_score(value, best_of)
    return best_of, score_a, score_b


def _source_value(source, brackets):
    source_match = brackets[source["bracket"]][source["round"]]["matches"][source["match"]]
    if not source_match.get("resolved"):
        return None, False
    if source.get("outcome", "winner") == "winner":
        return source_match.get("winner"), True
    a, b, winner = source_match.get("a"), source_match.get("b"), source_match.get("winner")
    loser = b if winner == a else a if winner == b else None
    return loser, True


def sync_brackets(upper_rounds, lower_rounds=None):
    brackets = {"upper": upper_rounds, "lower": lower_rounds or []}
    for bracket_name in ("upper", "lower"):
        for round_data in brackets[bracket_name]:
            for match in round_data["matches"]:
                values = []
                for slot in ("a", "b"):
                    source = match.get(f"{slot}_source")
                    if source is None:
                        values.append((match.get(slot), bool(match.get(f"{slot}_ready"))))
                    else:
                        values.append(_source_value(source, brackets))
                refresh_match(match, values[0][0], values[1][0], values[0][1], values[1][1])


def connector_segments(source_centers, target_centers, x1, x2):
    if len(source_centers) == len(target_centers):
        return [(x1, y1, x2, y2) for y1, y2 in zip(source_centers, target_centers)]
    if len(source_centers) != len(target_centers) * 2:
        return []
    mid = (x1 + x2) / 2
    segments = []
    for index, target in enumerate(target_centers):
        y1, y2 = source_centers[index * 2 : index * 2 + 2]
        segments.extend([
            (x1, y1, mid, y1),
            (x1, y2, mid, y2),
            (mid, y1, mid, y2),
            (mid, target, x2, target),
        ])
    return segments


# -----------------------------------------------------------------------------
# Main Application Class (MatchDesk Studio)
# -----------------------------------------------------------------------------
class MatchDeskStudioApp:
    def __init__(self, root, *, demo_mode=False):
        self.root = root
        self.demo_mode = demo_mode
        self.root.title(f"{APP_NAME} v{APP_VERSION}" + (" — [Демо]" if demo_mode else ""))
        self.root.geometry("1440x880")
        self.root.minsize(1120, 720)
        self.root.configure(bg=BG)

        self.teams = []
        self.rounds = []
        self.rr_matches = []
        self.generated_size = 0
        self.bye_count = 0
        self.mode = "single"
        self.tournament_title = "Пятничный микс #4"
        self.lower_rounds = []
        self.team_meta = {}
        self.default_bo = 3

        self._panning = False
        self._fullscreen = False
        self._restoring_history = False
        self.mode_buttons = {}
        self.last_bracket_bounds = (0, 0)
        self.zoom = 1.0
        self.history = []
        self.redo_stack = []
        self._logo_images = {}

        self.app_dir = get_app_storage_dir()
        self.autosave_path = self.app_dir / "autosave.json"

        self.setup_style()
        self.build_ui()
        self.change_mode()
        self.show_welcome()

        self.root.bind_all("<Control-z>", self.undo)
        self.root.bind_all("<Control-y>", self.redo)
        self.root.bind("<Control-Return>", self.request_generate)
        self.root.bind("<F11>", self.toggle_fullscreen)
        self.root.bind("<Escape>", self.exit_fullscreen)

        if demo_mode:
            self.root.after(100, self.load_demo_tournament)
        else:
            self.root.after(250, self.offer_autosave_restore)

    # --------------------------- Top-level Lifecycle ---------------------------
    def new_tournament(self):
        if self.rounds or self.rr_matches:
            if not messagebox.askyesno("Новый турнир", "Начать новый турнир и очистить текущие результаты?"):
                return
        self.clear_teams()
        self.title_var.set("Пятничный микс #4")
        self.mode_var.set("Single Elimination")
        self.change_mode()
        self.autosave()

    def status(self, text):
        self.status_label.config(text=text)
        self.footer.config(text=text)

    def clear_teams(self):
        if self.teams:
            self._remember()
        self.teams = []
        self.team_meta = {}
        self._invalidate_generated()
        self.refresh_list()
        self.bracket_title.config(text="ТУРНИРНАЯ СЕТКА")
        self.autosave()

    def refresh_list(self):
        self.listbox.delete(0, "end")
        for i, team in enumerate(self.teams, 1):
            self.listbox.insert("end", f"{i:02d}   {team}")
        self.count_label.config(text=f"{len(self.teams)} / {MAX_TEAMS} команд")
        self.stats.config(
            text=f"● ГОТОВ К СТАРТУ  |  {len(self.teams)}"
            if len(self.teams) >= 2
            else f"● ДОБАВЬТЕ КОМАНДЫ  |  {len(self.teams)}"
        )
        if not self.rounds and not self.rr_matches:
            self.show_welcome()

    def save_tournament(self):
        data = self.serialize_state()
        path = filedialog.asksaveasfilename(
            title="Сохранить турнир",
            defaultextension=".json",
            filetypes=[("Tournament JSON", "*.json")],
        )
        if not path:
            return
        try:
            self.tournament_title = data["title"]
            Path(path).write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
            self.status(f"Турнир сохранён: {Path(path).name}")
        except OSError as exc:
            messagebox.showerror("Ошибка сохранения", str(exc))

    def load_tournament(self):
        path = filedialog.askopenfilename(title="Загрузить турнир", filetypes=[("Tournament JSON", "*.json")])
        if not path:
            return
        previous_snapshot = self._snapshot()
        try:
            data = json.loads(Path(path).read_text(encoding="utf-8"))
            self._restore_snapshot(data)
            self.history.append(previous_snapshot)
            del self.history[:-50]
            self.redo_stack.clear()
            self.autosave()
            self.status(f"Загружен турнир: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Ошибка загрузки", f"Не удалось прочитать файл:\n{exc}")

    def export_menu(self):
        if not (self.rounds or self.rr_matches):
            messagebox.showinfo("Нет турнира", "Сначала создайте сетку турнира.")
            return
        if messagebox.askyesno(
            "Экспорт сетки",
            "Экспортировать в PNG?\n\n[Да] — Высокое разрешение PNG\n[Нет] — Векторный PDF документ",
        ):
            self.export_png()
        else:
            self.export_pdf()

    def open_demo_mode(self):
        window = tk.Toplevel(self.root)
        MatchDeskStudioApp(window, demo_mode=True)

    # --------------------------- UI Construction ---------------------------
    def setup_style(self):
        style = ttk.Style()
        try:
            style.theme_use("clam")
        except tk.TclError:
            pass

        style.configure("TFrame", background=BG)
        style.configure("Panel.TFrame", background=PANEL)
        style.configure("PanelAlt.TFrame", background=PANEL_ALT)
        style.configure("TLabel", background=BG, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Panel.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI", 10))
        style.configure("Muted.Panel.TLabel", background=PANEL, foreground=MUTED, font=("Segoe UI", 9))
        style.configure("Section.TLabel", background=PANEL, foreground=TEXT, font=("Segoe UI Semibold", 10))

        style.configure(
            "TG.TCombobox",
            fieldbackground=SURFACE,
            background=SURFACE,
            foreground=TEXT,
            arrowcolor=TEXT,
            bordercolor=BORDER,
            darkcolor=SURFACE,
            lightcolor=SURFACE,
            insertcolor=TEXT,
            padding=5,
        )
        style.map("TG.TCombobox", fieldbackground=[("readonly", SURFACE)], foreground=[("readonly", TEXT)])

        style.configure(
            "TG.TEntry",
            fieldbackground=SURFACE,
            foreground=TEXT,
            insertcolor=TEXT,
            bordercolor=BORDER,
            lightcolor=SURFACE,
            darkcolor=SURFACE,
            padding=7,
        )

    def build_ui(self):
        self.build_header()
        self.build_main()
        self.build_footer()

    def build_header(self):
        header = tk.Frame(self.root, bg=BG, padx=20, pady=14)
        header.pack(fill="x")
        header.grid_columnconfigure(1, weight=1)

        brand_box = tk.Frame(header, bg=BG)
        brand_box.grid(row=0, column=0, rowspan=2, sticky="w", padx=(0, 16))

        tk.Label(brand_box, text="🔥 CYBERSPORT", bg=BG, fg=TEXT, font=("Segoe UI", 14, "bold"), bd=0).pack(side="left")
        tk.Label(brand_box, text=".KING", bg=BG, fg=ACCENT, font=("Segoe UI", 14, "bold"), bd=0).pack(side="left")

        title_wrap = tk.Frame(header, bg=BG)
        title_wrap.grid(row=0, column=1, sticky="w")
        tk.Label(title_wrap, text="ТУРНИРНЫЙ МЕНЕДЖЕР", bg=BG, fg=MUTED, font=("Segoe UI Semibold", 9)).pack(side="left")

        self.lbl_hud_status = tk.Label(
            header,
            text="● БЕСПЛАТНЫЙ ИНСТРУМЕНТ // КИБЕРСПОРТИВНЫЕ СЕТКИ",
            bg=BG,
            fg=ACCENT_2,
            font=("Segoe UI", 8, "bold"),
        )
        self.lbl_hud_status.grid(row=1, column=1, sticky="w", pady=(2, 0))

        right = tk.Frame(header, bg=BG)
        right.grid(row=0, column=2, rowspan=2, sticky="e")
        btns = tk.Frame(right, bg=BG)
        btns.pack(anchor="e")

        for txt, cmd in [
            ("Новый", lambda: self.new_tournament()),
            ("Сохранить", lambda: self.save_tournament()),
            ("Загрузить", lambda: self.load_tournament()),
            ("Экспорт", lambda: self.export_menu()),
            ("Демо", lambda: self.open_demo_mode()),
        ]:
            self.make_button(btns, txt, cmd, small=True).pack(side="left", padx=3)

    def build_main(self):
        main = tk.Frame(self.root, bg=BG, padx=16, pady=0)
        main.pack(fill="both", expand=True)
        main.grid_columnconfigure(1, weight=1)
        main.grid_rowconfigure(0, weight=1)

        self.sidebar = tk.Frame(main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER, width=336)
        self.sidebar.grid(row=0, column=0, sticky="nsew", padx=(0, 14))
        self.sidebar.grid_propagate(False)

        self.build_sidebar_actions()
        scroll_area = tk.Frame(self.sidebar, bg=PANEL)
        scroll_area.pack(fill="both", expand=True)
        side_canvas = tk.Canvas(scroll_area, bg=PANEL, highlightthickness=0)
        self.sidebar_canvas = side_canvas
        side_scroll = ttk.Scrollbar(scroll_area, orient="vertical", command=side_canvas.yview)
        side_canvas.configure(yscrollcommand=side_scroll.set)
        side_scroll.pack(side="right", fill="y")
        side_canvas.pack(side="left", fill="both", expand=True)
        self.sidebar_inner = tk.Frame(side_canvas, bg=PANEL)
        self.sidebar_window = side_canvas.create_window((0, 0), window=self.sidebar_inner, anchor="nw")
        self.sidebar_inner.bind("<Configure>", lambda e: self._sync_sidebar_scroll(side_canvas))
        side_canvas.bind("<Configure>", lambda e: side_canvas.itemconfig(self.sidebar_window, width=e.width))

        self.build_sidebar_content()

        self.main_panel = tk.Frame(main, bg=PANEL, highlightthickness=1, highlightbackground=BORDER)
        self.main_panel.grid(row=0, column=1, sticky="nsew")
        self.main_panel.grid_rowconfigure(1, weight=1)
        self.main_panel.grid_columnconfigure(0, weight=1)

        self.build_bracket_panel()

    def build_sidebar_actions(self):
        self.sidebar_actions = tk.Frame(self.sidebar, bg=PANEL_ALT)
        self.sidebar_actions.pack(side="bottom", fill="x")
        tk.Frame(self.sidebar_actions, bg=BORDER, height=1).pack(fill="x")
        self.generate_button = self.make_button(
            self.sidebar_actions,
            "⚡ СОЗДАТЬ СЕТКУ",
            self.request_generate,
            accent=True,
            big=True,
        )
        self.generate_button.configure(
            takefocus=True,
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=ACCENT,
        )
        self.generate_button.pack(fill="x", padx=10, pady=(8, 3))
        tk.Label(
            self.sidebar_actions,
            text="Ctrl+Enter  •  от 2 до 64 команд",
            bg=PANEL_ALT,
            fg=MUTED,
            font=("Segoe UI", 8),
        ).pack(pady=(0, 6))

    def build_footer(self):
        footer_wrap = tk.Frame(self.root, bg=BG, padx=20, pady=6)
        footer_wrap.pack(fill="x")

        self.footer = tk.Label(
            footer_wrap,
            text="Готово к проведению матчей",
            bg=BG,
            fg=MUTED,
            anchor="w",
            font=("Segoe UI", 9),
        )
        self.footer.pack(side="left")

        self.lbl_clock = tk.Label(footer_wrap, text="", bg=BG, fg=MUTED, anchor="e", font=("Consolas", 9))
        self.lbl_clock.pack(side="right")
        self._update_clock()

    def _update_clock(self):
        now = dt.datetime.now().strftime("%H:%M:%S")
        self.lbl_clock.config(text=f"SYS TIME: {now}")
        self.root.after(1000, self._update_clock)

    def _sync_sidebar_scroll(self, canvas):
        canvas.configure(scrollregion=canvas.bbox("all"))

    def build_sidebar_content(self):
        self.sidebar_inner.columnconfigure(0, weight=1)

        top_card = self.make_card(self.sidebar_inner)
        top_card.pack(fill="x", padx=10, pady=(10, 6))
        tk.Label(top_card, text="ТУРНИРНЫЙ ПУЛЬТ", bg=PANEL_ALT, fg=TEXT, font=("Segoe UI Semibold", 11)).pack(anchor="w")
        tk.Label(top_card, text="Управление ростером, правилами и пресетами.", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(2, 0))

        self.build_presets_section()
        self.build_mode_section()
        self.build_teams_section()
        self.build_settings_section()
        self.build_tools_section()
        self.build_help_section()

    def build_presets_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=6)
        self.section_title(sec, "КИБЕРСПОРТИВНЫЕ ПРЕСЕТЫ")

        btn_box = tk.Frame(sec, bg=PANEL_ALT)
        btn_box.pack(fill="x", pady=(6, 0))
        btn_box.columnconfigure((0, 1), weight=1)

        b1 = self.make_button(btn_box, "CS2 Major (16)", lambda: self.load_preset("CS2 Major (16)"), small=True)
        b1.grid(row=0, column=0, sticky="ew", padx=(0, 3), pady=2)
        b2 = self.make_button(btn_box, "Valorant (8)", lambda: self.load_preset("Valorant Masters (8)"), small=True)
        b2.grid(row=0, column=1, sticky="ew", padx=(3, 0), pady=2)
        b3 = self.make_button(btn_box, "FGC Local (8)", lambda: self.load_preset("FGC Local (8)"), small=True)
        b3.grid(row=1, column=0, columnspan=2, sticky="ew", pady=(2, 0))

    def load_preset(self, preset_name):
        teams = PRESETS.get(preset_name, [])
        if not teams:
            return
        if self.teams and not messagebox.askyesno("Смена ростера", f"Заменить текущий ростер на пресет «{preset_name}»?"):
            return
        self._remember()
        self.teams = list(teams)
        self.tournament_title = preset_name
        self.title_var.set(self.tournament_title)
        self.team_meta.clear()
        self._invalidate_generated()
        self.refresh_list()
        self.status(f"Загружен пресет «{preset_name}» ({len(self.teams)} участников)")

    def build_mode_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=6)
        self.section_title(sec, "1. ФОРМАТ СЕТКИ")

        modes_row = tk.Frame(sec, bg=PANEL_ALT)
        modes_row.pack(fill="x", pady=(8, 0))
        modes_row.grid_columnconfigure((0, 1, 2), weight=1)

        labels = {
            "Single Elimination": "Single\nElim",
            "Double Elimination": "Double\nElim",
            "Round Robin": "Round\nRobin",
        }
        for col, name in enumerate(MODES):
            btn = tk.Button(
                modes_row,
                text=labels[name],
                command=lambda n=name: self.set_mode(n),
                bg=CARD,
                fg=TEXT,
                activebackground=CARD_ALT,
                activeforeground=TEXT,
                relief="flat",
                bd=0,
                font=("Segoe UI", 9),
                justify="center",
                padx=4,
                pady=8,
                cursor="hand2",
            )
            btn.grid(row=0, column=col, sticky="ew", padx=(0 if col == 0 else 3, 0 if col == 2 else 3))
            self.mode_buttons[name] = btn

        self.mode_var = tk.StringVar(value="Single Elimination")
        self.mode_hint = tk.Label(
            sec,
            text="Классический олимпийский плей-офф: проиграл — вылетел.",
            bg=PANEL_ALT,
            fg=MUTED,
            wraplength=260,
            justify="left",
            font=("Segoe UI", 8),
        )
        self.mode_hint.pack(anchor="w", pady=(8, 0))

    def build_teams_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=6)
        self.section_title(sec, "2. УЧАСТНИКИ")

        tk.Label(sec, text="Название сетки", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        self.title_var = tk.StringVar(value=self.tournament_title)
        self.title_entry = ttk.Entry(sec, textvariable=self.title_var, style="TG.TEntry")
        self.title_entry.pack(fill="x")
        self.title_var.trace_add("write", self._on_title_change)

        tk.Label(sec, text="Добавить команду", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        row = tk.Frame(sec, bg=PANEL_ALT)
        row.pack(fill="x")
        self.entry = ttk.Entry(row, style="TG.TEntry")
        self.entry.pack(side="left", fill="x", expand=True)
        self.entry.bind("<Return>", lambda e: self.add_team())
        self.entry.bind("<Control-Return>", self.request_generate)
        self.entry.bind("<<Paste>>", self.handle_paste)
        self.make_button(row, "+", self.add_team, width=3, accent=True).pack(side="left", padx=(5, 0))

        bulk_row = tk.Frame(sec, bg=PANEL_ALT)
        bulk_row.pack(fill="x", pady=(6, 0))
        self.make_button(bulk_row, "Импорт TXT", self.import_roster_txt, small=True).pack(side="left", fill="x", expand=True, padx=(0, 2))
        self.make_button(bulk_row, "Экспорт TXT", self.export_roster_txt, small=True).pack(side="left", fill="x", expand=True, padx=(2, 0))

        list_wrap = tk.Frame(sec, bg=PANEL_ALT, highlightthickness=1, highlightbackground=BORDER_SOFT)
        list_wrap.pack(fill="both", expand=True, pady=(6, 0))
        self.listbox = tk.Listbox(
            list_wrap,
            height=8,
            bg=SURFACE,
            fg=TEXT,
            relief="flat",
            highlightthickness=0,
            selectbackground=BORDER,
            selectforeground=TEXT,
            activestyle="none",
            font=("Consolas", 9),
        )
        self.listbox.pack(side="left", fill="both", expand=True)
        lb_scroll = ttk.Scrollbar(list_wrap, orient="vertical", command=self.listbox.yview)
        lb_scroll.pack(side="right", fill="y")
        self.listbox.configure(yscrollcommand=lb_scroll.set)
        self.listbox.bind("<Delete>", lambda e: self.remove_team())
        self.listbox.bind("<Double-Button-1>", lambda e: self.show_team_card())

        btn_row = tk.Frame(sec, bg=PANEL_ALT)
        btn_row.pack(fill="x", pady=(6, 0))
        self.make_button(btn_row, "Удалить", self.remove_team).pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.make_button(btn_row, "Очистить", self.clear_teams).pack(side="left", fill="x", expand=True, padx=(3, 0))

        team_tools = tk.Frame(sec, bg=PANEL_ALT)
        team_tools.pack(fill="x", pady=(6, 0))
        self.make_button(team_tools, "Оформление", self.customize_selected_team).pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.make_button(team_tools, "Карточка", self.show_team_card).pack(side="left", fill="x", expand=True, padx=(3, 0))

        stats_row = tk.Frame(sec, bg=PANEL_ALT)
        stats_row.pack(fill="x", pady=(6, 0))
        self.count_label = self.make_info_pill(stats_row, "0 / 64 команд")
        self.count_label.pack(side="left", fill="x", expand=True, padx=(0, 3))
        self.bye_label = self.make_info_pill(stats_row, "BYE: —")
        self.bye_label.pack(side="left", fill="x", expand=True, padx=(3, 0))

        self.stats = tk.Label(
            sec,
            text="● ДОБАВЬТЕ КОМАНДЫ",
            bg=CARD,
            fg=ACCENT,
            anchor="w",
            padx=8,
            pady=6,
            font=("Segoe UI Semibold", 8),
            highlightthickness=1,
            highlightbackground=BORDER_SOFT,
        )
        self.stats.pack(fill="x", pady=(6, 0))

    def _on_title_change(self, *args):
        self.tournament_title = self.title_var.get()
        if not self.rounds and not self.rr_matches:
            val = self.title_var.get().strip() or "Например: Пятничный микс #4"
            if self.canvas.find_withtag("welcome_title_display"):
                self.canvas.itemconfigure("welcome_title_display", text=val)

    def import_roster_txt(self):
        path = filedialog.askopenfilename(title="Импорт участников", filetypes=[("Текстовые файлы", "*.txt;*.csv")])
        if not path:
            return
        try:
            content = Path(path).read_text(encoding="utf-8")
            a, d, s = self._add_names(self.normalize(content))
            messagebox.showinfo("Импорт ростера", f"Успешно добавлено: {a}\nДубликатов: {d}\nПропущено: {s}")
        except Exception as exc:
            messagebox.showerror("Ошибка импорта", str(exc))

    def export_roster_txt(self):
        if not self.teams:
            messagebox.showinfo("Ростер пуст", "Добавьте участников для экспорта.")
            return
        path = filedialog.asksaveasfilename(title="Экспорт участников", defaultextension=".txt", filetypes=[("Текстовый файл", "*.txt")])
        if not path:
            return
        try:
            Path(path).write_text("\n".join(self.teams), encoding="utf-8")
            self.status(f"Ростер сохранён: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Ошибка сохранения", str(exc))

    def build_settings_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=6)
        self.section_title(sec, "3. ПРАВИЛА МАТЧЕЙ")

        tk.Label(sec, text="Формат турнира", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        self.mode_combo = ttk.Combobox(sec, textvariable=self.mode_var, values=list(MODES), state="readonly", style="TG.TCombobox")
        self.mode_combo.pack(fill="x")
        self.mode_combo.bind("<<ComboboxSelected>>", self.change_mode)

        tk.Label(sec, text="Формат серий", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        self.default_bo_var = tk.StringVar(value="BO3")
        bo_combo = ttk.Combobox(
            sec,
            textvariable=self.default_bo_var,
            values=("BO1", "BO3", "BO5"),
            state="readonly",
            style="TG.TCombobox",
        )
        bo_combo.pack(fill="x")
        bo_combo.bind("<<ComboboxSelected>>", self.change_default_bo)

        tk.Label(sec, text="Хранилище данных", bg=PANEL_ALT, fg=MUTED, font=("Segoe UI", 8)).pack(anchor="w", pady=(8, 2))
        self.theme_preview = self.make_info_pill(sec, "%APPDATA% / Synced")
        self.theme_preview.pack(fill="x")

    def build_tools_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=6)
        self.section_title(sec, "ИНСТРУМЕНТЫ И СБОРКА")
        self.make_button(sec, "Открыть демо-турнир", lambda: self.open_demo_mode()).pack(fill="x", pady=(6, 3))
        self.make_button(sec, "Экспорт диплома (PDF)", lambda: self.export_certificate()).pack(fill="x", pady=2)
        self.make_button(sec, "⚡ Собрать в автономный EXE", lambda: self.compile_to_exe(), accent=True).pack(fill="x", pady=(6, 2))

    def compile_to_exe(self):
        if not messagebox.askyesno(
            "Сборка EXE",
            "Запустить автоматическую сборку MatchDesk Studio в автономный EXE файл?\n\n"
            "Сборка будет выполнена в изолированном безопасном каталоге AppData.",
            parent=self.root,
        ):
            return

        build_win = tk.Toplevel(self.root)
        build_win.title("Сборщик MatchDesk Studio EXE")
        build_win.geometry("680x440")
        build_win.configure(bg=PANEL)
        build_win.transient(self.root)
        build_win.grab_set()

        lbl_head = tk.Label(
            build_win,
            text="КОМПИЛЯЦИЯ АВТОНОМНОГО ПРИЛОЖЕНИЯ",
            bg=PANEL,
            fg=TEXT,
            font=("Segoe UI Semibold", 12),
        )
        lbl_head.pack(anchor="w", padx=16, pady=(16, 4))

        status_lbl = tk.Label(
            build_win,
            text="Инициализация безопасного каталога...",
            bg=PANEL,
            fg=ACCENT,
            font=("Segoe UI", 9),
        )
        status_lbl.pack(anchor="w", padx=16, pady=(0, 8))

        log_box = tk.Text(
            build_win,
            bg=SURFACE,
            fg=TEXT,
            font=("Consolas", 8),
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER_SOFT,
        )
        log_box.pack(fill="both", expand=True, padx=16, pady=(0, 12))

        btn_row = tk.Frame(build_win, bg=PANEL)
        btn_row.pack(fill="x", padx=16, pady=(0, 16))

        open_btn = self.make_button(btn_row, "Открыть папку с EXE", lambda: None, accent=True)
        open_btn.config(state="disabled")
        open_btn.pack(side="left", padx=(0, 6))

        close_btn = self.make_button(btn_row, "Закрыть", build_win.destroy)
        close_btn.pack(side="right")

        def append_log_safe(text):
            if build_win.winfo_exists():
                build_win.after(0, lambda: (log_box.insert("end", text), log_box.see("end")))

        def set_status_safe(text, color=ACCENT):
            if build_win.winfo_exists():
                build_win.after(0, lambda: status_lbl.config(text=text, fg=color))

        def build_worker():
            try:
                build_root = get_build_storage_dir()
                spec_dir = build_root / "spec"
                work_dir = build_root / "work"
                dist_dir = build_root / "dist"

                for d in (spec_dir, work_dir, dist_dir):
                    d.mkdir(parents=True, exist_ok=True)

                current_file = Path(sys.argv[0]).resolve()
                isolated_script = build_root / "matchdesk_app.py"
                shutil.copy2(current_file, isolated_script)

                os.chdir(build_root)

                append_log_safe(f"-> Безопасный каталог сборщика: {build_root}\n")
                append_log_safe("-> Проверка библиотек PyInstaller, Pillow, ReportLab...\n")
                set_status_safe("Установка библиотек компилятора...")

                pip_cmd = [
                    sys.executable, "-m", "pip", "install",
                    "--upgrade", "pyinstaller", "pillow", "reportlab",
                ]
                proc_pip = subprocess.Popen(
                    pip_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(build_root),
                )
                for line in proc_pip.stdout:
                    append_log_safe(line)
                proc_pip.wait()

                if proc_pip.returncode != 0:
                    raise RuntimeError("Ошибка при установке сборочных пакетов pip.")

                append_log_safe("\n-> Старт сборки PyInstaller в изолированном пространстве...\n")
                set_status_safe("Компиляция бинарных файлов (PyInstaller)...")

                pyi_cmd = [
                    sys.executable, "-m", "PyInstaller",
                    "--noconfirm",
                    "--onedir",
                    "--windowed",
                    "--name", "MatchDeskStudio",
                    "--clean",
                    "--specpath", str(spec_dir),
                    "--workpath", str(work_dir),
                    "--distpath", str(dist_dir),
                    str(isolated_script),
                ]

                proc_pyi = subprocess.Popen(
                    pyi_cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    cwd=str(build_root),
                )
                for line in proc_pyi.stdout:
                    append_log_safe(line)
                proc_pyi.wait()

                if proc_pyi.returncode != 0:
                    raise RuntimeError(f"PyInstaller завершился с кодом ошибки {proc_pyi.returncode}.")

                final_exe_dir = dist_dir / "MatchDeskStudio"
                final_exe = final_exe_dir / "MatchDeskStudio.exe"

                if not final_exe.is_file():
                    raise FileNotFoundError(f"EXE файл не был создан по пути {final_exe}")

                append_log_safe(f"\n[УСПЕХ] Приложение успешно скомпилировано!\nИсполняемый файл: {final_exe}\n")
                set_status_safe("Сборка успешно завершена!", GREEN)

                def open_folder():
                    if sys.platform == "win32":
                        os.startfile(final_exe_dir)
                    else:
                        subprocess.run(["xdg-open", str(final_exe_dir)])

                if build_win.winfo_exists():
                    build_win.after(0, lambda: open_btn.config(state="normal", command=open_folder))
                self.root.after(0, lambda: self.status("Сборка EXE завершена успешно!"))

            except Exception as ex:
                append_log_safe(f"\n[ОШИБКА] {ex}\n")
                set_status_safe("Ошибка во время сборки.", RED)
                self.root.after(0, lambda: self.status("Ошибка сборки EXE"))

        threading.Thread(target=build_worker, daemon=True).start()

    def build_help_section(self):
        sec = self.make_card(self.sidebar_inner)
        sec.pack(fill="x", padx=10, pady=(6, 10))
        self.section_title(sec, "УПРАВЛЕНИЕ ХОЛСТОМ")
        text = (
            "• Ctrl+Enter — создать сетку.\n"
            "• ЛКМ по слоту — ввести счёт матча.\n"
            "• ПКМ по слоту — карточка статистики.\n"
            "• Зажатие ЛКМ — свободная панорама.\n"
            "• Ctrl + колесо — зум, F11 — полный экран."
        )
        tk.Label(sec, text=text, bg=PANEL_ALT, fg=MUTED, justify="left", font=("Segoe UI", 8), wraplength=265).pack(anchor="w", pady=(8, 0))

    def build_bracket_panel(self):
        top = tk.Frame(self.main_panel, bg=PANEL, padx=14, pady=10)
        top.grid(row=0, column=0, sticky="ew")
        top.grid_columnconfigure(0, weight=1)

        title_wrap = tk.Frame(top, bg=PANEL)
        title_wrap.grid(row=0, column=0, sticky="w")
        self.bracket_title = tk.Label(title_wrap, text="ТУРНИРНАЯ СЕТКА", bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 13))
        self.bracket_title.pack(side="left")

        self.progress_pill = self.make_info_pill(top, "ПРОГРЕСС: 0%")
        self.progress_pill.grid(row=0, column=1, padx=6)

        self.status_label = tk.Label(
            top,
            text="Требуется минимум 2 команды",
            bg=CARD,
            fg=TEXT,
            font=("Segoe UI", 8),
            padx=8,
            pady=4,
            highlightthickness=1,
            highlightbackground=BORDER_SOFT,
        )
        self.status_label.grid(row=0, column=2, sticky="e")

        controls = tk.Frame(top, bg=PANEL)
        controls.grid(row=1, column=0, columnspan=3, sticky="e", pady=(6, 0))
        for text, command in [
            ("−", lambda: self.set_zoom(self.zoom / 1.15)),
            ("+", lambda: self.set_zoom(self.zoom * 1.15)),
            ("По центру", lambda: self.fit_bracket()),
            ("Полный экран", lambda: self.toggle_fullscreen()),
            ("Отмена", lambda: self.undo()),
            ("Повтор", lambda: self.redo()),
        ]:
            self.make_button(controls, text, command, small=True).pack(side="left", padx=2)

        wrap = tk.Frame(self.main_panel, bg=PANEL)
        wrap.grid(row=1, column=0, sticky="nsew", padx=10, pady=(0, 10))
        wrap.grid_rowconfigure(0, weight=1)
        wrap.grid_columnconfigure(0, weight=1)

        self.canvas = tk.Canvas(wrap, bg=BG2, highlightthickness=0)
        self.canvas.grid(row=0, column=0, sticky="nsew")

        vs = ttk.Scrollbar(wrap, orient="vertical", command=self.canvas.yview)
        hs = ttk.Scrollbar(wrap, orient="horizontal", command=self.canvas.xview)
        vs.grid(row=0, column=1, sticky="ns")
        hs.grid(row=1, column=0, sticky="ew")
        self.canvas.configure(yscrollcommand=vs.set, xscrollcommand=hs.set)

        self.canvas.bind("<ButtonPress-1>", self.pan_start, add="+")
        self.canvas.bind("<B1-Motion>", self.pan_move, add="+")
        self.canvas.bind("<ButtonRelease-1>", self.pan_end, add="+")
        self.canvas.bind("<MouseWheel>", self.pan_wheel)
        self.canvas.bind("<Shift-MouseWheel>", self.pan_wheel_horizontal)
        self.canvas.bind("<Control-MouseWheel>", self.zoom_wheel)
        self.canvas.bind("<Configure>", self._on_canvas_resize)

    def _on_canvas_resize(self, event=None):
        if not self.rounds and not self.rr_matches:
            self.show_welcome()

    def make_card(self, parent):
        return tk.Frame(parent, bg=PANEL_ALT, padx=10, pady=10, highlightthickness=1, highlightbackground=BORDER_SOFT)

    def section_title(self, parent, text):
        tk.Label(parent, text=text, bg=PANEL_ALT, fg=TEXT, font=("Segoe UI Semibold", 10)).pack(anchor="w")

    def make_button(self, parent, text, command, small=False, accent=False, big=False, width=None):
        bg = ACCENT if accent else CARD
        active = ACCENT_HOVER if accent else "#222735"
        font = ("Segoe UI Semibold" if accent or big else "Segoe UI", 8 if small else 10 if big else 9)
        pady = 4 if small else 8 if big else 6
        btn = tk.Button(
            parent,
            text=text,
            command=command,
            bg=bg,
            fg="#FFFFFF" if accent else TEXT,
            activebackground=active,
            activeforeground="#FFFFFF",
            relief="flat",
            bd=0,
            padx=8 if small else 12,
            pady=pady,
            cursor="hand2",
            font=font,
            width=width,
            highlightthickness=0 if accent else 1,
            highlightbackground=BORDER_SOFT,
        )
        return btn

    def make_info_pill(self, parent, text):
        return tk.Label(
            parent,
            text=text,
            bg=SURFACE,
            fg=TEXT,
            padx=8,
            pady=5,
            font=("Segoe UI", 8),
            anchor="center",
            highlightthickness=1,
            highlightbackground=BORDER_SOFT,
        )

    def set_mode(self, mode_name):
        if mode_name not in MODES:
            return
        self.mode_var.set(mode_name)
        self.change_mode()

    def update_mode_buttons(self):
        for name, btn in self.mode_buttons.items():
            selected = name == self.mode_var.get()
            btn.configure(
                bg=ORANGE_TINT if selected else CARD,
                fg=ACCENT if selected else TEXT,
                highlightthickness=1,
                highlightbackground=ACCENT if selected else BORDER_SOFT,
            )

    # --------------------------- Canvas Geometry & UI ---------------------------
    def draw_backdrop(self, width, height):
        self.canvas.create_rectangle(0, 0, width, height, fill=BG2, outline="")
        for x in range(0, width, 48):
            self.canvas.create_line(x, 0, x, height, fill="#121620", width=1)
        for y in range(0, height, 48):
            self.canvas.create_line(0, y, width, y, fill="#121620", width=1)

    def create_round_rect(self, x1, y1, x2, y2, radius=4, **kwargs):
        points = [
            x1 + radius, y1,
            x2 - radius, y1,
            x2, y1,
            x2, y1 + radius,
            x2, y2 - radius,
            x2, y2,
            x2 - radius, y2,
            x1 + radius, y2,
            x1, y2,
            x1, y2 - radius,
            x1, y1 + radius,
            x1, y1,
        ]
        return self.canvas.create_polygon(points, smooth=True, splinesteps=18, **kwargs)

    def neon_line(self, x1, y1, x2, y2, color=LINE, width=1):
        self.canvas.create_line(x1, y1, x2, y2, fill=color, width=width)

    def glow_box(self, x1, y1, x2, y2, fill=CARD, outline=BORDER, radius=4, glow=None):
        self.create_round_rect(x1, y1, x2, y2, radius=radius, fill=fill, outline=outline, width=1)

    def fit_name(self, name, limit=21):
        if not name:
            return ""
        return name if len(name) <= limit else name[: limit - 1] + "…"

    def current_champion(self):
        if self.mode == "round_robin":
            if self.rr_matches and all(m["winner"] for m in self.rr_matches):
                ranked, _ = self.rr_table()
                return ranked[0]
            return None
        if self.mode == "double" and self.lower_rounds:
            grand_final = self.lower_rounds[-1]["matches"][0]
            if grand_final.get("name") == "reset":
                return grand_final.get("winner")
            if grand_final.get("resolved") and grand_final.get("winner") == grand_final.get("a"):
                return grand_final.get("winner")
            return None
        if self.rounds and self.rounds[-1]["matches"]:
            return self.rounds[-1]["matches"][0].get("winner")
        return None

    def draw_header_pills(self, width):
        teams_txt = f"{len(self.teams)} УЧАСТНИКОВ"
        mode_txt = self.mode_var.get().upper()
        self.canvas.create_rectangle(26, 18, 26 + 230, 44, fill=PANEL, outline=BORDER_SOFT)
        self.canvas.create_text(38, 31, anchor="w", text=teams_txt, fill=ACCENT, font=("Segoe UI Semibold", 8))
        self.canvas.create_text(138, 31, anchor="w", text=mode_txt, fill=TEXT, font=("Segoe UI Semibold", 8))

        self.canvas.create_rectangle(width - 240, 18, width - 26, 44, fill=PANEL, outline=BORDER_SOFT)
        self.canvas.create_text(width - 228, 31, anchor="w", text="ЛКМ: ПАНОРАМА • КЛИК: СЧЁТ", fill=MUTED, font=("Segoe UI", 8))

    # --------------------------- Pan / Zoom ---------------------------
    def pan_start(self, event):
        current = self.canvas.find_withtag("current")
        if current and "clickable" in self.canvas.gettags(current[0]):
            return
        self._panning = True
        self.canvas.scan_mark(event.x, event.y)
        self.canvas.config(cursor="fleur")

    def pan_move(self, event):
        if self._panning:
            self.canvas.scan_dragto(event.x, event.y, gain=1)

    def pan_end(self, event):
        if self._panning:
            self._panning = False
            self.canvas.config(cursor="")

    def pan_wheel(self, event):
        step = int(-1 * (event.delta / 120))
        self.canvas.yview_scroll(step, "units")

    def pan_wheel_horizontal(self, event):
        step = int(-1 * (event.delta / 120))
        self.canvas.xview_scroll(step, "units")

    def zoom_wheel(self, event):
        self.set_zoom(self.zoom * (1.12 if event.delta > 0 else 1 / 1.12))
        return "break"

    def set_zoom(self, value):
        self.zoom = max(0.3, min(2.0, float(value)))
        self.draw()
        self.status(f"Масштаб: {self.zoom:.0%}")

    def fit_bracket(self):
        width, height = self.last_bracket_bounds
        if not width or not height:
            return
        available_width = max(1, self.canvas.winfo_width() - 20)
        available_height = max(1, self.canvas.winfo_height() - 20)
        self.set_zoom(min(1.5, available_width / width, available_height / height))
        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)

    def toggle_fullscreen(self, event=None):
        self._fullscreen = not self._fullscreen
        self.root.attributes("-fullscreen", self._fullscreen)
        return "break"

    def exit_fullscreen(self, event=None):
        if self._fullscreen:
            self._fullscreen = False
            self.root.attributes("-fullscreen", False)
        return "break"

    def _finish_canvas(self, width, height):
        self.last_bracket_bounds = (width, height)
        if self.zoom != 1.0:
            self.canvas.scale("all", 0, 0, self.zoom, self.zoom)
        self.canvas.configure(scrollregion=(0, 0, width * self.zoom, height * self.zoom))

    # --------------------------- Welcome View ---------------------------
    def show_welcome(self):
        self.canvas.delete("all")
        self.zoom = 1.0

        self.root.update_idletasks()
        w = max(self.canvas.winfo_width(), 1060)
        h = max(self.canvas.winfo_height(), 660)
        self.draw_backdrop(w, h)

        cx = w / 2
        cy = h / 2

        self.canvas.create_text(
            cx - 430, cy - 250,
            text="● БЕСПЛАТНЫЙ ИНСТРУМЕНТ",
            anchor="w",
            fill=ACCENT,
            font=("Segoe UI", 9, "bold"),
        )
        self.canvas.create_text(
            cx - 430, cy - 220,
            text="Генератор турнирных сеток",
            anchor="w",
            fill=TEXT,
            font=("Segoe UI", 22, "bold"),
        )
        self.canvas.create_text(
            cx - 430, cy - 188,
            text="Single и Double Elimination, Round Robin — до 64 участников. Управление результатами, сетка и экспорт.",
            anchor="w",
            fill=MUTED,
            font=("Segoe UI", 10),
        )

        box_w = 900
        box_h = 420
        box_x1 = cx - box_w / 2
        box_x2 = cx + box_w / 2
        box_y1 = cy - 160
        box_y2 = box_y1 + box_h

        self.glow_box(box_x1, box_y1, box_x2, box_y2, fill=PANEL, outline=BORDER, radius=8)

        divider_x = box_x1 + 440
        self.canvas.create_line(divider_x, box_y1 + 20, divider_x, box_y2 - 70, fill=BORDER_SOFT, width=1)

        lx = box_x1 + 24
        self.canvas.create_text(lx, box_y1 + 25, anchor="w", text="Название сетки", fill=MUTED, font=("Segoe UI Semibold", 9))
        self.glow_box(lx, box_y1 + 42, lx + 390, box_y1 + 78, fill=CARD, outline=BORDER, radius=6)

        title_display = self.title_var.get().strip() or "Например: Пятничный микс #4"
        self.canvas.create_text(
            lx + 14, box_y1 + 60,
            anchor="w",
            text=title_display,
            fill=TEXT,
            font=("Segoe UI", 10),
            tags=("welcome_title_display", "clickable"),
        )
        self.canvas.tag_bind("welcome_title_display", "<Button-1>", lambda e: self.title_entry.focus_set())

        self.canvas.create_text(lx, box_y1 + 102, anchor="w", text="Формат турнира", fill=MUTED, font=("Segoe UI Semibold", 9))

        format_cards = [
            ("Single Elimination", "Классический олимпийский плей-офф\nпроиграл — вылетел", "single"),
            ("Double Elimination", "Верхняя и нижняя сетка: право на одну\nошибку", "double"),
            ("Round Robin", "Круговая система: каждый с каждым", "round_robin"),
        ]

        curr_mode = self.mode
        for idx, (title, desc, key) in enumerate(format_cards):
            fy1 = box_y1 + 122 + idx * 64
            fy2 = fy1 + 54
            is_active = curr_mode == key
            f_fill = ORANGE_TINT if is_active else CARD
            f_border = ACCENT if is_active else BORDER_SOFT

            card_tag = f"fmt_card_{key}"
            self.create_round_rect(lx, fy1, lx + 390, fy2, radius=6, fill=f_fill, outline=f_border, width=1.5 if is_active else 1, tags=("clickable", card_tag))
            self.canvas.create_text(lx + 14, fy1 + 16, anchor="w", text=("🔥 " if is_active else "") + title, fill=ACCENT if is_active else TEXT, font=("Segoe UI Semibold", 10), tags=("clickable", card_tag))
            self.canvas.create_text(lx + 14, fy1 + 36, anchor="w", text=desc, fill=MUTED, font=("Segoe UI", 8), tags=("clickable", card_tag))

            mode_name = next(k for k, v in MODES.items() if v == key)
            self.canvas.tag_bind(card_tag, "<Button-1>", lambda e, m=mode_name: self.set_mode(m))
            self.canvas.tag_bind(card_tag, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
            self.canvas.tag_bind(card_tag, "<Leave>", lambda e: self.canvas.config(cursor=""))

        rx = divider_x + 24
        self.canvas.create_text(rx, box_y1 + 25, anchor="w", text="Участники — по одному на строку", fill=MUTED, font=("Segoe UI Semibold", 9))
        self.canvas.create_text(box_x2 - 24, box_y1 + 25, anchor="e", text=f"{len(self.teams)} / {MAX_TEAMS}", fill=MUTED, font=("Consolas", 9), tags=("welcome_team_count",))

        self.glow_box(rx, box_y1 + 42, box_x2 - 24, box_y2 - 70, fill=SURFACE, outline=BORDER, radius=6)

        if not self.teams:
            self.canvas.create_text(
                (rx + box_x2 - 24) / 2,
                (box_y1 + 42 + box_y2 - 70) / 2 - 10,
                text="Ростер участников пуст",
                fill=BORDER,
                font=("Segoe UI Semibold", 11),
                tags=("welcome_roster_box", "clickable"),
            )
            self.canvas.create_text(
                (rx + box_x2 - 24) / 2,
                (box_y1 + 42 + box_y2 - 70) / 2 + 15,
                text="Добавьте команды через панель слева\nили выберите готовый пресет",
                fill=MUTED,
                font=("Segoe UI", 9),
                tags=("welcome_roster_box", "clickable"),
            )
        else:
            show_teams = self.teams[:9]
            for t_idx, t_name in enumerate(show_teams):
                ty = box_y1 + 60 + t_idx * 26
                self.canvas.create_text(rx + 16, ty, anchor="w", text=f"{t_idx+1:02d}.  {t_name}", fill=TEXT, font=("Consolas", 9), tags=("welcome_roster_box", "clickable"))
            if len(self.teams) > 9:
                self.canvas.create_text(rx + 16, box_y1 + 60 + 9 * 26, anchor="w", text=f"... ещё {len(self.teams) - 9} участников", fill=MUTED, font=("Segoe UI", 8), tags=("welcome_roster_box", "clickable"))

        self.canvas.tag_bind("welcome_roster_box", "<Button-1>", lambda e: self.entry.focus_set())

        btn_y1 = box_y2 - 54
        btn_y2 = box_y2 - 14
        btn_tag = "btn_generate_main"

        self.create_round_rect(box_x1 + 24, btn_y1, box_x2 - 24, btn_y2, radius=6, fill=ACCENT, outline="", tags=("clickable", btn_tag))
        self.canvas.create_text(
            cx, (btn_y1 + btn_y2) / 2,
            text="⚡ СОЗДАТЬ ТУРНИРНУЮ СЕТКУ (Ctrl+Enter)",
            fill="#FFFFFF",
            font=("Segoe UI Semibold", 11),
            tags=("clickable", btn_tag),
        )
        self.canvas.tag_bind(btn_tag, "<Button-1>", lambda e: self.request_generate())
        self.canvas.tag_bind(btn_tag, "<Enter>", lambda e: self.canvas.config(cursor="hand2"))
        self.canvas.tag_bind(btn_tag, "<Leave>", lambda e: self.canvas.config(cursor=""))

        self.canvas.xview_moveto(0)
        self.canvas.yview_moveto(0)
        self._finish_canvas(w, h)

    def change_mode(self, event=None):
        selected_mode_name = self.mode_var.get()
        if selected_mode_name not in MODES:
            return

        mode = MODES[selected_mode_name]
        changed = mode != self.mode

        if changed and (self.rounds or self.rr_matches):
            if not messagebox.askyesno("Смена формата", "Смена формата очистит текущие результаты турнира. Продолжить?"):
                previous = next(name for name, value in MODES.items() if value == self.mode)
                self.mode_var.set(previous)
                self.update_mode_buttons()
                return
            self._remember()

        self.mode = mode
        hints = {
            "single": "Классический олимпийский плей-офф: проиграл — вылетел.",
            "double": "Верхняя и нижняя сетка: право на одну ошибку.",
            "round_robin": "Круговая система: каждый играет с каждым, таблица очков.",
        }
        self.mode_hint.config(text=hints[mode])
        self.update_mode_buttons()

        if changed and (self.rounds or self.rr_matches):
            self.rounds = []
            self.rr_matches = []
            self.lower_rounds = []
            self.generated_size = 0
            self.bye_count = 0
            self.bye_label.config(text="BYE: —")
            self.show_welcome()
        elif not self.rounds and not self.rr_matches:
            self.show_welcome()

        self.status(f"Выбран формат: {self.mode_var.get()}")
        if changed:
            self.autosave()

    # --------------------------- Team Management ---------------------------
    def normalize(self, raw):
        raw = raw.replace("\r\n", "\n").replace("\r", "\n")
        out = []
        for line in raw.split("\n"):
            out += [x.strip() for x in line.split(";") if x.strip()]
        return out

    def _add_names(self, names):
        previous = self._snapshot()
        added = dups = skipped = 0
        existing = {x.casefold() for x in self.teams}
        for name in names:
            if len(self.teams) >= MAX_TEAMS:
                skipped += 1
                continue
            if len(name) > 40:
                skipped += 1
                continue
            if name.casefold() in existing:
                dups += 1
                continue
            self.teams.append(name)
            existing.add(name.casefold())
            added += 1
        if added and (self.rounds or self.rr_matches):
            self._invalidate_generated()
        if added:
            self.history.append(previous)
            del self.history[:-50]
            self.redo_stack.clear()
            self.autosave()
        self.refresh_list()
        return added, dups, skipped

    def add_team(self):
        raw = self.entry.get().strip()
        self.entry.delete(0, "end")
        if raw:
            self._add_names(self.normalize(raw))
            self.status(f"Участников в ростере: {len(self.teams)}")

    def handle_paste(self, event=None):
        try:
            raw = self.root.clipboard_get()
        except tk.TclError:
            return
        if "\n" in raw or ";" in raw:
            a, d, s = self._add_names(self.normalize(raw))
            messagebox.showinfo("Импорт команд", f"Добавлено: {a}\nДубликатов: {d}\nПропущено: {s}")
            return "break"

    def remove_team(self):
        sel = self.listbox.curselection()
        if sel and 0 <= sel[0] < len(self.teams):
            self._remember()
            removed = self.teams.pop(sel[0])
            self.team_meta.pop(removed, None)
            self._invalidate_generated()
            self.refresh_list()
            self.status("Команда удалена из ростера.")
            self.autosave()

    def _invalidate_generated(self):
        self.rounds = []
        self.rr_matches = []
        self.lower_rounds = []
        self.generated_size = 0
        self.bye_count = 0
        self.bye_label.config(text="BYE: —")
        self.progress_pill.config(text="ПРОГРЕСС: 0%")
        self.lbl_hud_status.config(text="● ТУРНИР ОЖИДАЕТ ГЕНЕРАЦИИ СЕТКИ")
        self.show_welcome()

    def _selected_team(self):
        selected = self.listbox.curselection()
        if not selected or selected[0] >= len(self.teams):
            messagebox.showinfo("Команда", "Выберите команду в списке.")
            return None
        return self.teams[selected[0]]

    def customize_selected_team(self):
        team = self._selected_team()
        if team is None:
            return
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Оформление — {team}")
        dialog.geometry("430x250")
        dialog.resizable(False, False)
        dialog.configure(bg=PANEL)
        dialog.transient(self.root)
        dialog.grab_set()
        tk.Label(dialog, text=team, bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 16)).pack(pady=(20, 6))
        meta_label = tk.Label(dialog, bg=PANEL, fg=MUTED, font=("Segoe UI", 9), wraplength=370)
        meta_label.pack(pady=(0, 14))

        def refresh_meta():
            meta = self.team_meta.get(team, {})
            logo_name = Path(meta["logo"]).name if meta.get("logo") else "не выбран"
            meta_label.config(text=f"Цвет: {meta.get('color', ACCENT)}   •   Логотип: {logo_name}")

        def choose_color():
            initial = self.team_meta.get(team, {}).get("color", ACCENT)
            _, color = colorchooser.askcolor(initialcolor=initial, parent=dialog, title="Цвет команды")
            if color:
                self._remember()
                self.team_meta.setdefault(team, {})["color"] = color
                refresh_meta()
                self.draw()
                self.autosave()

        def choose_logo():
            path = filedialog.askopenfilename(
                parent=dialog,
                title="Логотип команды",
                filetypes=[("Изображения", "*.png *.jpg *.jpeg")],
            )
            if not path:
                return
            if Path(path).stat().st_size > 2 * 1024 * 1024:
                messagebox.showerror("Логотип", "Файл должен быть не больше 2 МБ.", parent=dialog)
                return
            try:
                from PIL import Image
                with Image.open(path) as image:
                    image.verify()
            except Exception as exc:
                messagebox.showerror("Логотип", f"Не удалось прочитать изображение:\n{exc}", parent=dialog)
                return
            self._remember()
            self.team_meta.setdefault(team, {})["logo"] = str(Path(path).resolve())
            self._logo_images.pop(team, None)
            refresh_meta()
            self.draw()
            self.autosave()

        buttons = tk.Frame(dialog, bg=PANEL)
        buttons.pack(fill="x", padx=24)
        self.make_button(buttons, "Цвет", choose_color).pack(side="left", fill="x", expand=True, padx=(0, 5))
        self.make_button(buttons, "Логотип", choose_logo).pack(side="left", fill="x", expand=True, padx=5)

        def clear_logo():
            if self.team_meta.get(team, {}).get("logo"):
                self._remember()
                self.team_meta[team].pop("logo", None)
                self._logo_images.pop(team, None)
                refresh_meta()
                self.draw()
                self.autosave()

        self.make_button(buttons, "Убрать", clear_logo).pack(side="left", fill="x", expand=True, padx=(5, 0))
        refresh_meta()

    def _get_team_logo(self, team):
        if not team:
            return None
        path = self.team_meta.get(team, {}).get("logo")
        if not path or not Path(path).is_file():
            return None
        cached = self._logo_images.get(team)
        if cached and cached[0] == path:
            return cached[1]
        try:
            from PIL import Image, ImageTk
            with Image.open(path) as source:
                image = source.convert("RGBA")
            image.thumbnail((20, 20))
            photo = ImageTk.PhotoImage(image)
            self._logo_images[team] = (path, photo)
            return photo
        except Exception:
            return None

    def team_statistics(self, team):
        stats = {"played": 0, "wins": 0, "losses": 0, "matches": []}
        sources = []
        if self.mode == "round_robin":
            sources.append(("Round Robin", [{"name": "Лига", "matches": self.rr_matches}]))
        else:
            sources.append(("Верхняя сетка", self.rounds))
            if self.mode == "double":
                sources.append(("Нижняя сетка", self.lower_rounds))
        for bracket_name, rounds in sources:
            for round_data in rounds:
                for match in round_data.get("matches", []):
                    if not match.get("resolved") or team not in (match.get("a"), match.get("b")):
                        continue
                    opponent = match.get("b") if team == match.get("a") else match.get("a")
                    if opponent is None:
                        continue
                    won = match.get("winner") == team
                    stats["played"] += 1
                    stats["wins" if won else "losses"] += 1
                    score = f"{match.get('score_a')}:{match.get('score_b')}" if match.get("score_a") is not None else "-"
                    stats["matches"].append((bracket_name, round_data.get("name", ""), opponent, score, "Победа" if won else "Поражение"))
        return stats

    def show_team_card(self, team=None):
        team = team or self._selected_team()
        if team is None:
            return
        stats = self.team_statistics(team)
        dialog = tk.Toplevel(self.root)
        dialog.title(f"Карточка команды — {team}")
        dialog.geometry("760x440")
        dialog.configure(bg=PANEL)
        tk.Label(dialog, text=team, bg=PANEL, fg=TEXT, font=("Segoe UI Semibold", 20)).pack(anchor="w", padx=20, pady=(16, 4))
        tk.Label(dialog, text=f"Матчи: {stats['played']}    Победы: {stats['wins']}    Поражения: {stats['losses']}", bg=PANEL, fg=ACCENT, font=("Segoe UI Semibold", 10)).pack(anchor="w", padx=20, pady=(0, 12))
        tree = ttk.Treeview(dialog, columns=("bracket", "round", "opponent", "score", "result"), show="headings")
        for column, title, width in (("bracket", "Сетка", 140), ("round", "Раунд", 170), ("opponent", "Соперник", 150), ("score", "Счёт", 70), ("result", "Итог", 110)):
            tree.heading(column, text=title)
            tree.column(column, width=width, anchor="w")
        for row in stats["matches"]:
            tree.insert("", "end", values=row)
        tree.pack(fill="both", expand=True, padx=20, pady=(0, 20))

    def load_demo_tournament(self):
        self.teams = ["Альфа", "Бета", "Гамма", "Дельта", "Импульс", "Квант", "Орбита", "Спектр"]
        colors = [ACCENT, "#EC4899", GOLD, GREEN, CYAN, RED, "#5DE2A5", "#FF8F5C"]
        self.team_meta = {team: {"color": colors[index]} for index, team in enumerate(self.teams)}
        self.tournament_title = "Учебный Double Elimination"
        self.title_var.set(self.tournament_title)
        self.mode_var.set("Double Elimination")
        self.mode = "double"
        self.default_bo = 3
        self.default_bo_var.set("BO3")
        self.refresh_list()
        self.generate()
        self.history.clear()
        self.redo_stack.clear()
        self.status("Демо-режим: сетка сформирована, доступен пошаговый ввод счёта")

    def export_certificate(self):
        champion = self.current_champion()
        if not champion:
            messagebox.showinfo("Диплом", "Сначала определите победителя турнира.")
            return
        safe_name = "".join(char if char.isalnum() else "_" for char in champion).strip("_") or "winner"
        path = filedialog.asksaveasfilename(
            title="PDF-диплом победителя",
            defaultextension=".pdf",
            initialfile=f"diplom_{safe_name}.pdf",
            filetypes=[("PDF", "*.pdf")],
        )
        if not path:
            return
        try:
            self.create_certificate(path, champion)
            self.status(f"Диплом сохранён: {Path(path).name}")
        except Exception as exc:
            messagebox.showerror("Ошибка диплома", str(exc))

    def create_certificate(self, path, champion, certificate_date=None):
        from reportlab.lib.colors import HexColor
        from reportlab.lib.pagesizes import A4, landscape
        from reportlab.lib.utils import ImageReader
        from reportlab.pdfbase import pdfmetrics
        from reportlab.pdfbase.ttfonts import TTFont
        from reportlab.pdfgen import canvas

        font_paths = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ]
        bold_paths = [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial Bold.ttf"),
        ]
        regular = next((font for font in font_paths if font.is_file()), None)
        bold = next((font for font in bold_paths if font.is_file()), None)

        if regular is not None and bold is not None:
            try:
                pdfmetrics.registerFont(TTFont("TGRegular", str(regular)))
                pdfmetrics.registerFont(TTFont("TGBold", str(bold)))
                reg_name, bold_name = "TGRegular", "TGBold"
            except Exception:
                reg_name, bold_name = "Helvetica", "Helvetica-Bold"
        else:
            reg_name, bold_name = "Helvetica", "Helvetica-Bold"

        width, height = landscape(A4)
        pdf = canvas.Canvas(str(path), pagesize=(width, height))
        pdf.setTitle(f"Диплом победителя — {champion}")
        pdf.setFillColor(HexColor(BG))
        pdf.rect(0, 0, width, height, fill=1, stroke=0)
        pdf.setStrokeColor(HexColor(BORDER))
        pdf.setLineWidth(2)
        pdf.roundRect(28, 28, width - 56, height - 56, 10, fill=0, stroke=1)

        pdf.setFillColor(HexColor(ACCENT))
        pdf.setFont(bold_name, 14)
        pdf.drawCentredString(width / 2, height - 95, "CYBERSPORT.KING // TOURNAMENT")
        pdf.setFillColor(HexColor(TEXT))
        pdf.setFont(bold_name, 30)
        pdf.drawCentredString(width / 2, height - 150, "ДИПЛОМ ПОБЕДИТЕЛЯ")
        pdf.setFillColor(HexColor(MUTED))
        pdf.setFont(reg_name, 13)
        pdf.drawCentredString(width / 2, height - 190, "Вручается команде")

        team_color = self.team_meta.get(champion, {}).get("color", ACCENT)
        pdf.setFillColor(HexColor(team_color))
        pdf.roundRect(140, height - 310, width - 280, 70, 8, fill=1, stroke=0)
        pdf.setFillColor(HexColor(TEXT))
        pdf.setFont(bold_name, 26)
        pdf.drawCentredString(width / 2, height - 285, champion[:35])

        logo_path = self.team_meta.get(champion, {}).get("logo")
        if logo_path and Path(logo_path).is_file():
            try:
                pdf.drawImage(ImageReader(logo_path), 64, height - 330, width=80, height=80, preserveAspectRatio=True, mask="auto", anchor="c")
            except Exception:
                pass

        pdf.setFillColor(HexColor(TEXT))
        tournament = self.tournament_title[:70]
        pdf.setFont(reg_name, 16)
        pdf.drawCentredString(width / 2, height - 365, f"за победу в турнире «{tournament}»")
        day = certificate_date or dt.date.today()
        pdf.setFillColor(HexColor(MUTED))
        pdf.setFont(reg_name, 11)
        pdf.drawString(62, 58, day.strftime("%d.%m.%Y"))
        pdf.drawRightString(width - 62, 58, f"Формат: {self.mode_var.get()}  •  BO{self.default_bo}")
        pdf.save()

    def update_progress_hud(self):
        total_matches = 0
        resolved_matches = 0

        if self.mode == "round_robin":
            total_matches = len(self.rr_matches)
            resolved_matches = sum(1 for m in self.rr_matches if m.get("resolved"))
        else:
            all_rounds = self.rounds + (self.lower_rounds if self.mode == "double" else [])
            for rnd in all_rounds:
                for m in rnd.get("matches", []):
                    if m.get("a") is not None and m.get("b") is not None:
                        total_matches += 1
                        if m.get("resolved"):
                            resolved_matches += 1

        percent = int((resolved_matches / total_matches) * 100) if total_matches > 0 else 0
        self.progress_pill.config(text=f"СЫГРАНО: {resolved_matches}/{total_matches} ({percent}%)")

        champion = self.current_champion()
        if champion:
            self.lbl_hud_status.config(text=f"🏆 ТУРНИР ЗАВЕРШЕН // ЧЕМПИОН: {champion}")
        elif total_matches > 0:
            self.lbl_hud_status.config(text=f"Матчи в процессе ({resolved_matches}/{total_matches}) • Кликните на слот для ввода счёта")

    def serialize_state(self):
        return {
            "version": 6,
            "title": (self.title_var.get().strip() or "Пятничный микс #4")[:80],
            "mode": self.mode,
            "teams": self.teams,
            "team_meta": self.team_meta,
            "default_bo": self.default_bo,
            "generated_size": self.generated_size,
            "bye_count": self.bye_count,
            "rounds": self.rounds,
            "rr_matches": self.rr_matches,
            "lower_rounds": self.lower_rounds,
        }

    def _snapshot(self):
        return copy.deepcopy(self.serialize_state())

    def _remember(self):
        if self._restoring_history:
            return
        self.history.append(self._snapshot())
        del self.history[:-50]
        self.redo_stack.clear()

    def _restore_snapshot(self, state):
        mode = state.get("mode", "single")
        default_bo = int(state.get("default_bo", 3))
        teams = state.get("teams", [])
        if mode not in MODES.values() or default_bo not in (1, 3, 5) or not isinstance(teams, list):
            raise ValueError("Некорректное состояние турнира.")
        self._restoring_history = True
        try:
            self.teams = copy.deepcopy(teams)
            self.team_meta = copy.deepcopy(state.get("team_meta", {}))
            self.tournament_title = str(state.get("title", "Пятничный микс #4"))[:80]
            self.mode = mode
            self.default_bo = default_bo
            self.generated_size = int(state.get("generated_size", 0))
            self.bye_count = int(state.get("bye_count", 0))
            self.rounds = copy.deepcopy(state.get("rounds", []))
            self.rr_matches = copy.deepcopy(state.get("rr_matches", []))
            self.lower_rounds = copy.deepcopy(state.get("lower_rounds", []))
            self._ensure_match_fields()
            self.title_var.set(self.tournament_title)
            self.mode_var.set(next(name for name, value in MODES.items() if value == self.mode))
            self.default_bo_var.set(f"BO{self.default_bo}")
            self.refresh_list()
            self.update_mode_buttons()
            self.bye_label.config(text=f"BYE: {self.bye_count}" if self.mode != "round_robin" else "BYE: —")
            self.bracket_title.config(text=self.tournament_title.upper() if self.rounds or self.rr_matches else "ТУРНИРНАЯ СЕТКА")
            self.draw()
        finally:
            self._restoring_history = False

    def _ensure_match_fields(self):
        for rounds in (self.rounds, self.lower_rounds):
            for round_data in rounds:
                for match in round_data.get("matches", []):
                    match.setdefault("best_of", self.default_bo)
                    match.setdefault("score_a", None)
                    match.setdefault("score_b", None)
        for match in self.rr_matches:
            match.setdefault("best_of", self.default_bo)
            match.setdefault("score_a", None)
            match.setdefault("score_b", None)
            match.setdefault("a_ready", True)
            match.setdefault("b_ready", True)
            match.setdefault("resolved", match.get("winner") is not None)

    def undo(self, event=None):
        if not self.history:
            self.status("Нечего отменять")
            return "break"
        self.redo_stack.append(self._snapshot())
        self._restore_snapshot(self.history.pop())
        self.autosave()
        self.status("Последнее действие отменено")
        return "break"

    def redo(self, event=None):
        if not self.redo_stack:
            self.status("Нечего повторять")
            return "break"
        self.history.append(self._snapshot())
        self._restore_snapshot(self.redo_stack.pop())
        self.autosave()
        self.status("Действие повторено")
        return "break"

    def autosave(self):
        if self.demo_mode:
            return
        try:
            temp_path = self.autosave_path.with_suffix(".tmp")
            temp_path.write_text(json.dumps(self.serialize_state(), ensure_ascii=False, indent=2), encoding="utf-8")
            temp_path.replace(self.autosave_path)
        except OSError as exc:
            self.status(f"Автосохранение недоступно: {exc}")

    def offer_autosave_restore(self):
        if not self.autosave_path.exists():
            return
        try:
            state = json.loads(self.autosave_path.read_text(encoding="utf-8"))
            if not isinstance(state, dict) or len(state.get("teams", [])) < 2:
                return
            if messagebox.askyesno("Восстановление сессии", "Найдено автосохранение последнего турнира. Восстановить?"):
                self._restore_snapshot(state)
                self.status("Сессия восстановлена из системного хранилища")
        except Exception:
            return

    def change_default_bo(self, event=None):
        self._remember()
        self.default_bo = int(self.default_bo_var.get().removeprefix("BO"))
        for rounds in (self.rounds, self.lower_rounds):
            for round_data in rounds:
                for match in round_data.get("matches", []):
                    if not match.get("resolved"):
                        match["best_of"] = self.default_bo
        for match in self.rr_matches:
            if not match.get("resolved"):
                match["best_of"] = self.default_bo
        self.draw()
        self.autosave()
        self.status(f"Новые матчи переведены в формат: BO{self.default_bo}")

    # --------------------------- Generation ---------------------------
    def request_generate(self, event=None):
        if len(self.teams) >= MIN_TEAMS and (self.rounds or self.rr_matches):
            confirmed = messagebox.askyesno(
                "Создать сетку заново?",
                "Будет проведена новая жеребьёвка, а текущие результаты "
                "матчей сбросятся.\n\nПродолжить?",
                parent=self.root,
            )
            if not confirmed:
                return "break"
        self.generate()
        return "break"

    def generate(self):
        if len(self.teams) < 2:
            messagebox.showwarning("Недостаточно команд", "Добавьте минимум 2 команды.")
            return
        self._remember()
        self.tournament_title = (self.title_var.get().strip() or "Пятничный микс #4")[:80]
        self.title_var.set(self.tournament_title)
        self.mode = MODES[self.mode_var.get()]
        self.rounds = []
        self.rr_matches = []
        self.lower_rounds = []
        if self.mode == "round_robin":
            self.generate_rr()
        elif self.mode == "double":
            self.generate_double()
        else:
            self.generate_single()
        self.bracket_title.config(text=self.tournament_title.upper())
        self.draw()
        self.autosave()

    def generate_single(self):
        size = next_power_of_two(len(self.teams))
        self.generated_size = size
        self.bye_count = size - len(self.teams)
        self.rounds = build_upper_rounds(self.teams, best_of=self.default_bo)
        self.sync_progression()
        self.bye_label.config(text=f"BYE: {self.bye_count}")
        self.status(f"Single Elimination • {size} слотов • BYE: {self.bye_count}")

    def generate_double(self):
        size = next_power_of_two(len(self.teams))
        self.generated_size = size
        self.bye_count = size - len(self.teams)
        self.rounds = build_upper_rounds(self.teams, prefix="Верхняя: ", best_of=self.default_bo)
        self.lower_rounds = build_lower_rounds(self.rounds, best_of=self.default_bo)
        self.sync_progression()
        self.bye_label.config(text=f"BYE: {self.bye_count}")
        self.status(f"Double Elimination • сетка на {size} слотов • 2 поражения до вылета")

    def generate_rr(self):
        self.generated_size = len(self.teams)
        self.bye_count = 0
        self.rr_matches = []
        for i in range(len(self.teams)):
            for j in range(i + 1, len(self.teams)):
                self.rr_matches.append(
                    make_match(self.teams[i], self.teams[j], a_ready=True, b_ready=True, best_of=self.default_bo)
                )
        self.bye_label.config(text="BYE: —")
        self.status(f"Round Robin • {len(self.teams)} участников • {len(self.rr_matches)} матчей")

    def sync_progression(self):
        sync_brackets(self.rounds, self.lower_rounds)
        self._sync_double_reset()

    def _sync_double_reset(self):
        if self.mode != "double" or not self.lower_rounds:
            return
        if self.lower_rounds[-1]["matches"][0].get("name") == "reset":
            reset_round = self.lower_rounds[-1]
            grand_final = self.lower_rounds[-2]["matches"][0]
        else:
            reset_round = None
            grand_final = self.lower_rounds[-1]["matches"][0]

        reset_needed = (
            grand_final.get("resolved")
            and grand_final.get("a") is not None
            and grand_final.get("b") is not None
            and grand_final.get("winner") == grand_final.get("b")
        )
        if reset_needed and reset_round is None:
            reset = make_match(
                grand_final["a"],
                grand_final["b"],
                a_ready=True,
                b_ready=True,
                best_of=grand_final.get("best_of", self.default_bo),
            )
            reset["name"] = "reset"
            self.lower_rounds.append({"name": "Решающий финал", "matches": [reset]})
        elif not reset_needed and reset_round is not None:
            self.lower_rounds.pop()

    # --------------------------- Matches & Scores ---------------------------
    def open_score_dialog(self, section, round_index, match_index):
        rounds = self.lower_rounds if section else self.rounds
        match = rounds[round_index]["matches"][match_index]
        if not self._can_choose(match, match.get("a")):
            messagebox.showinfo("Матч не готов", "Сначала дождитесь распределения обоих участников.")
            return
        current = ""
        if match.get("score_a") is not None and match.get("score_b") is not None:
            current = f"{match['score_a']}:{match['score_b']}"
        best_of = match.get("best_of", self.default_bo)
        raw = simpledialog.askstring(
            f"Счёт матча — BO{best_of}",
            f"{match['a']}  —  {match['b']}\n\nВведите счёт (например 2:1).\nДля смены формата напишите: BO5 3:1.",
            initialvalue=current,
            parent=self.root,
        )
        if raw is not None:
            self.set_match_score("lower" if section else "upper", round_index, match_index, raw)

    def open_rr_score_dialog(self, index):
        match = self.rr_matches[index]
        current = ""
        if match.get("score_a") is not None and match.get("score_b") is not None:
            current = f"{match['score_a']}:{match['score_b']}"
        best_of = match.get("best_of", self.default_bo)
        raw = simpledialog.askstring(
            f"Счёт матча — BO{best_of}",
            f"{match['a']}  —  {match['b']}\n\nВведите счёт или BO5 3:1.",
            initialvalue=current,
            parent=self.root,
        )
        if raw is not None:
            self.set_match_score("round_robin", 0, index, raw)

    def set_match_score(self, bracket, round_index, match_index, raw):
        if bracket == "round_robin":
            match = self.rr_matches[match_index]
        else:
            rounds = self.lower_rounds if bracket == "lower" else self.rounds
            match = rounds[round_index]["matches"][match_index]
        if not self._can_choose(match, match.get("a")):
            return False
        try:
            best_of, score_a, score_b = parse_score_entry(raw, match.get("best_of", self.default_bo))
        except ValueError as exc:
            messagebox.showerror("Неверный счёт", str(exc))
            return False
        self._remember()
        match["best_of"] = best_of
        match["score_a"], match["score_b"] = score_a, score_b
        match["winner"] = match["a"] if score_a > score_b else match["b"]
        match["resolved"] = True
        if bracket != "round_robin":
            self.sync_progression()
        winner = match["winner"]
        self.status(f"Результат BO{best_of}: {score_a}:{score_b} • Победитель: {winner}")
        self.draw()
        self.autosave()
        return True

    @staticmethod
    def _can_choose(match, team):
        return (
            match.get("a_ready")
            and match.get("b_ready")
            and match.get("a") is not None
            and match.get("b") is not None
            and team in (match["a"], match["b"])
        )

    def rr_table(self):
        table = {t: {"w": 0, "l": 0, "p": 0} for t in self.teams}
        for m in self.rr_matches:
            if not m["winner"]:
                continue
            winner = m["winner"]
            loser = m["b"] if winner == m["a"] else m["a"]
            table[winner]["w"] += 1
            table[winner]["p"] += 3
            table[loser]["l"] += 1
        return sorted(self.teams, key=lambda t: (-table[t]["p"], -table[t]["w"], t.casefold())), table

    # --------------------------- Canvas Rendering ---------------------------
    def draw(self):
        self.canvas.delete("all")
        if self.mode == "round_robin":
            self.draw_rr()
            self.update_progress_hud()
            return
        if not self.rounds:
            self.show_welcome()
            self.update_progress_hud()
            return

        upper_width, upper_height = self.estimate_bracket_size(self.rounds)
        lower_width = 0
        lower_height = 0
        if self.mode == "double" and self.lower_rounds:
            lower_width, lower_height = self.estimate_bracket_size(self.lower_rounds)
        total_width = max(self.canvas.winfo_width(), upper_width + 340, lower_width + 340)
        total_height = max(self.canvas.winfo_height(), upper_height + lower_height + 220)
        self.draw_backdrop(total_width, total_height)
        self.draw_header_pills(total_width)

        self.draw_bracket(self.rounds, 0, offset_y=80, total_width=total_width)
        if self.mode == "double" and self.lower_rounds:
            self.draw_bracket(self.lower_rounds, 1, offset_y=max(upper_height + 110, 500), total_width=total_width)

        champion = self.current_champion()
        champ_x1 = total_width - 270
        champ_x2 = total_width - 40
        champ_y1 = 100
        champ_y2 = 280
        self.glow_box(champ_x1, champ_y1, champ_x2, champ_y2, fill=PANEL, outline=BORDER, radius=6)
        self.canvas.create_text((champ_x1 + champ_x2) / 2, champ_y1 + 24, text="ЧЕМПИОН ТУРНИРА", fill=GOLD, font=("Segoe UI Semibold", 10))
        self.canvas.create_text((champ_x1 + champ_x2) / 2, champ_y1 + 80, text="WINNER", fill=MUTED, font=("Consolas", 18, "bold"))
        self.canvas.create_text((champ_x1 + champ_x2) / 2, champ_y1 + 125, text=self.fit_name(champion) if champion else "—", fill=TEXT, font=("Segoe UI Semibold", 14))
        sub = "Матчи завершены" if champion else "Ожидание гранд-финала"
        self.canvas.create_text((champ_x1 + champ_x2) / 2, champ_y1 + 152, text=sub, fill=MUTED, font=("Segoe UI", 9))

        self.canvas.create_rectangle(340, total_height - 54, total_width - 340, total_height - 26, fill=PANEL, outline=BORDER_SOFT)
        self.canvas.create_text(total_width / 2, total_height - 40, text="Зажмите левую кнопку мыши для свободного перемещения по сетке", fill=MUTED, font=("Segoe UI", 9))

        self._finish_canvas(total_width, total_height)
        self.update_progress_hud()

    def estimate_bracket_size(self, rounds):
        if not rounds:
            return 1200, 700
        card_w = 240
        card_h = 76
        gap = 70
        base = card_h + 24
        first = len(rounds[0]["matches"])
        width = 36 + len(rounds) * (card_w + gap) + 100
        height = 120 + max(480, first * base + 80)
        return width, height

    def draw_bracket(self, rounds, section=0, offset_y=0, total_width=1600):
        card_w = 240
        card_h = 76
        gap = 70
        left = 38
        top = offset_y + 85
        first = len(rounds[0]["matches"])
        base = card_h + 24

        centers = []
        for rnd in rounds:
            step = (first * base) / len(rnd["matches"])
            centers.append([top + (i + 0.5) * step for i in range(len(rnd["matches"]))])

        title = (
            "ВЕРХНЯЯ СЕТКА" if section == 0 and self.mode == "double" else
            "НИЖНЯЯ СЕТКА" if section else
            self.mode_var.get().upper()
        )
        self.canvas.create_text(left, offset_y + 30, anchor="w", text=title, fill=TEXT, font=("Segoe UI Semibold", 13))

        for r in range(len(centers) - 1):
            x1 = left + r * (card_w + gap) + card_w
            x2 = left + (r + 1) * (card_w + gap)
            for segment in connector_segments(centers[r], centers[r + 1], x1, x2):
                self.neon_line(*segment)

        for r, rnd in enumerate(rounds):
            x = left + r * (card_w + gap)
            self.canvas.create_text(x, top - 40, anchor="w", text=rnd["name"].upper(), fill=ACCENT, font=("Segoe UI Semibold", 10))
            self.canvas.create_text(x, top - 22, anchor="w", text="Клик — ввести счёт", fill=MUTED, font=("Segoe UI", 8))
            step = (first * base) / len(rnd["matches"])
            for m, match in enumerate(rnd["matches"]):
                y = top + (m + 0.5) * step - card_h / 2
                self.draw_match(x, y, card_w, card_h, r, m, match, section=section)

    def draw_match(self, x, y, w, h, r, m, match, section=0):
        self.glow_box(x, y, x + w, y + h, fill=CARD, outline=BORDER, radius=4)
        best_of = match.get("best_of", self.default_bo)
        self.canvas.create_text(x + 8, y - 10, anchor="w", text=f"MATCH {m + 1:02d}  •  BO{best_of}", fill=MUTED, font=("Consolas", 8))
        self.draw_team_row(x, y + 2, w, h / 2 - 2, match.get("a"), match.get("winner"), r, m, seed=m * 2 + 1, ready=bool(match.get("a_ready")), section=section, score=match.get("score_a"))
        self.draw_team_row(x, y + h / 2, w, h / 2 - 2, match.get("b"), match.get("winner"), r, m, seed=m * 2 + 2, ready=bool(match.get("b_ready")), section=section, score=match.get("score_b"))

    def draw_team_row(self, x, y, w, h, team, winner, r, m, seed=None, ready=True, section=0, score=None):
        label = team if team is not None else "BYE" if ready else "Ожидание"
        is_win = team is not None and team == winner
        row_fill = "#1A2522" if is_win else CARD_ALT
        row_outline = GREEN if is_win else BORDER_SOFT
        tag_bg = self.create_round_rect(x + 4, y + 1, x + w - 4, y + h - 1, radius=3, fill=row_fill, outline=row_outline, width=1, tags=("clickable",))

        seed_fill = BORDER if not is_win else "#1A3E39"
        self.create_round_rect(x + 8, y + 5, x + 32, y + h - 5, radius=2, fill=seed_fill, outline="", tags=("clickable",))
        self.canvas.create_text(x + 20, y + h / 2, text=f"{seed:02d}" if seed else "", fill=TEXT, font=("Consolas", 8), tags=("clickable",))

        meta = self.team_meta.get(team, {}) if team else {}
        team_color = meta.get("color", ACCENT)
        self.canvas.create_rectangle(x + 36, y + 6, x + 39, y + h - 6, fill=team_color, outline="", tags=("clickable",))

        logo = self._get_team_logo(team)
        if logo is not None:
            self.canvas.create_image(x + 51, y + h / 2, image=logo, tags=("clickable",))
        name_x = x + 66 if logo is not None else x + 46
        self.canvas.create_text(
            name_x,
            y + h / 2,
            anchor="w",
            text=("✓ " if is_win else "") + self.fit_name(label, 17),
            fill=GREEN if is_win else (MUTED if team is None else TEXT),
            font=("Segoe UI Semibold" if is_win else "Segoe UI", 9),
            tags=("clickable",),
        )

        badge_text = str(score) if score is not None else "BYE" if team is None and ready else "—"
        badge_fill = GREEN if is_win else (BORDER if score is not None else SURFACE)
        self.create_round_rect(x + w - 38, y + 5, x + w - 8, y + h - 5, radius=2, fill=badge_fill, outline="", tags=("clickable",))
        self.canvas.create_text(x + w - 23, y + h / 2, text=badge_text, fill=BG if is_win else TEXT, font=("Consolas", 8, "bold"), tags=("clickable",))

        if team:
            self.canvas.tag_bind(tag_bg, "<Button-1>", lambda e: self.open_score_dialog(section, r, m))
            self.canvas.tag_bind(tag_bg, "<Button-3>", lambda e, t=team: self.show_team_card(t))
            self.canvas.tag_bind(tag_bg, "<Enter>", lambda e, i=tag_bg: self.canvas.itemconfig(i, outline=ACCENT, width=1))
            self.canvas.tag_bind(tag_bg, "<Leave>", lambda e, i=tag_bg, o=row_outline: self.canvas.itemconfig(i, outline=o, width=1))

        overlapping = self.canvas.find_enclosed(x + 4, y + 1, x + w - 4, y + h - 1)
        for item in overlapping:
            if team:
                self.canvas.tag_bind(item, "<Button-1>", lambda e: self.open_score_dialog(section, r, m))
                self.canvas.tag_bind(item, "<Button-3>", lambda e, t=team: self.show_team_card(t))
            self.canvas.addtag_withtag("clickable", item)

    def draw_rr(self):
        width = max(self.canvas.winfo_width(), 1320)
        height = max(self.canvas.winfo_height(), 760)
        self.draw_backdrop(width, height)
        self.draw_header_pills(width)

        ranked, table = self.rr_table()

        self.canvas.create_text(34, 76, anchor="w", text="ROUND ROBIN // ТАБЛИЦА ЛИГИ", fill=TEXT, font=("Segoe UI Semibold", 14))
        self.canvas.create_text(width - 34, 76, anchor="e", text=f"Всего матчей: {len(self.rr_matches)}", fill=MUTED, font=("Segoe UI", 9))

        self.glow_box(34, 100, 480, 100 + 40 + 34 * max(6, len(ranked)), fill=PANEL, outline=BORDER, radius=6)
        self.canvas.create_text(52, 122, anchor="w", text="ПОЛОЖЕНИЕ В ТАБЛИЦЕ", fill=ACCENT, font=("Segoe UI Semibold", 10))
        heads = ["#", "Команда", "W", "L", "PTS"]
        cols = [52, 90, 310, 360, 420]
        for col, head in zip(cols, heads):
            self.canvas.create_text(col, 150, anchor="w", text=head, fill=MUTED, font=("Consolas", 9, "bold"))
        row_y = 175
        for i, team in enumerate(ranked, 1):
            fill = CARD if i % 2 else PANEL_ALT
            self.create_round_rect(44, row_y - 12, 470, row_y + 14, radius=3, fill=fill, outline="")
            values = [f"{i:02d}", self.fit_name(team, 20), str(table[team]["w"]), str(table[team]["l"]), str(table[team]["p"])]
            for idx, val in enumerate(values):
                color = GOLD if idx == 0 and i == 1 else (TEXT if idx != 4 else ACCENT)
                font = ("Consolas", 9, "bold") if idx in (0, 4) else ("Segoe UI", 9)
                self.canvas.create_text(cols[idx], row_y, anchor="w", text=val, fill=color, font=font)
            row_y += 30

        card_x = 510
        card_y = 100
        cols = 2
        card_w = 370
        card_h = 76
        total_rows = math.ceil(len(self.rr_matches) / cols)
        panel_h = max(520, 60 + total_rows * (card_h + 10))
        self.glow_box(card_x, card_y, width - 34, card_y + panel_h, fill=PANEL, outline=BORDER, radius=6)
        self.canvas.create_text(card_x + 18, card_y + 20, anchor="w", text="МАТЧИ ТУРА", fill=ACCENT, font=("Segoe UI Semibold", 10))
        self.canvas.create_text(width - 50, card_y + 20, anchor="e", text="Кликните на победителя", fill=MUTED, font=("Segoe UI", 8))

        start_y = card_y + 46
        for i, match in enumerate(self.rr_matches):
            col = i % cols
            row = i // cols
            x = card_x + 16 + col * (card_w + 14)
            y = start_y + row * (card_h + 10)
            self.draw_rr_match(x, y, card_w, card_h, i, match)

        total_height = max(height, card_y + panel_h + 40)
        self._finish_canvas(width, total_height)
        if self.rr_matches and all(m["winner"] for m in self.rr_matches):
            self.status(f"Лидер по очкам: {ranked[0]}")

    def draw_rr_match(self, x, y, w, h, index, match):
        self.glow_box(x, y, x + w, y + h, fill=CARD, outline=BORDER_SOFT, radius=4)
        self.canvas.create_text(x + 10, y + 12, anchor="w", text=f"MATCH {index + 1:02d}  •  BO{match.get('best_of', self.default_bo)}", fill=MUTED, font=("Consolas", 8))
        teams = (match["a"], match["b"])
        for k, team in enumerate(teams):
            win = team == match["winner"]
            yy = y + 24 + k * 22
            row_fill = "#1A2522" if win else CARD_ALT
            row_outline = GREEN if win else BORDER_SOFT
            row = self.create_round_rect(x + 8, yy, x + w - 8, yy + 18, radius=2, fill=row_fill, outline=row_outline, width=1, tags=("clickable",))
            self.canvas.create_text(x + 14, yy + 9, anchor="w", text=("✓ " if win else "") + self.fit_name(team, 24), fill=GREEN if win else TEXT, font=("Segoe UI", 8), tags=("clickable",))
            score = match.get("score_a" if k == 0 else "score_b")
            self.canvas.create_text(x + w - 16, yy + 9, anchor="e", text=str(score) if score is not None else "—", fill=GREEN if win else MUTED, font=("Consolas", 8), tags=("clickable",))
            self.canvas.tag_bind(row, "<Button-1>", lambda e, idx=index: self.open_rr_score_dialog(idx))
            self.canvas.tag_bind(row, "<Button-3>", lambda e, t=team: self.show_team_card(t))
            for item in self.canvas.find_enclosed(x + 8, yy, x + w - 8, yy + 18):
                self.canvas.addtag_withtag("clickable", item)
                self.canvas.tag_bind(item, "<Button-1>", lambda e, idx=index: self.open_rr_score_dialog(idx))
                self.canvas.tag_bind(item, "<Button-3>", lambda e, t=team: self.show_team_card(t))

    # --------------------------- Export Services ---------------------------
    def render_export(self):
        from PIL import Image, ImageDraw, ImageFont

        cardw, cardh, gap, base_step = 240, 72, 50, 92
        if self.mode == "round_robin":
            W = 1800
            H = max(1100, 240 + len(self.teams) * 32)
        else:
            sections = [self.rounds] + ([self.lower_rounds] if self.mode == "double" and self.lower_rounds else [])
            max_rounds = max(len(section) for section in sections)
            W = max(1800, 60 + max_rounds * (cardw + gap) + 340)
            H = max(1100, 140 + sum(90 + len(section[0]["matches"]) * base_step for section in sections) + 70)
        img = Image.new("RGB", (W, H), BG)
        draw = ImageDraw.Draw(img)
        regular_candidates = [
            Path("C:/Windows/Fonts/arial.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial.ttf"),
            Path("/Library/Fonts/Arial.ttf"),
        ]
        bold_candidates = [
            Path("C:/Windows/Fonts/arialbd.ttf"),
            Path("/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"),
            Path("/System/Library/Fonts/Supplemental/Arial Bold.ttf"),
            Path("/Library/Fonts/Arial Bold.ttf"),
        ]
        regular_path = next((path for path in regular_candidates if path.is_file()), None)
        bold_path = next((path for path in bold_candidates if path.is_file()), None)
        if regular_path and bold_path:
            title_font = ImageFont.truetype(str(bold_path), 32)
            head_font = ImageFont.truetype(str(bold_path), 16)
            normal_font = ImageFont.truetype(str(regular_path), 13)
        else:
            title_font = head_font = normal_font = ImageFont.load_default()

        def paste_logo(team, x, y):
            logo_path = self.team_meta.get(team, {}).get("logo") if team else None
            if not logo_path or not Path(logo_path).is_file():
                return 0
            try:
                with Image.open(logo_path) as source:
                    logo = source.convert("RGBA")
                logo.thumbnail((16, 16))
                img.paste(logo, (int(x), int(y)), logo)
                return 20
            except Exception:
                return 0

        draw.text((45, 28), self.title_var.get().strip() or "Турнирная сетка", fill=TEXT, font=title_font)
        draw.text((45, 70), self.mode_var.get() + f" • {len(self.teams)} команд", fill=MUTED, font=normal_font)
        draw.rounded_rectangle((35, 100, W - 35, H - 35), radius=8, fill=PANEL, outline=BORDER, width=1)

        if self.mode == "round_robin":
            ranked, table = self.rr_table()
            draw.text((60, 130), "ROUND ROBIN // СТАТИСТИКА", fill=ACCENT, font=head_font)
            y = 175
            for i, team in enumerate(ranked, 1):
                draw.rounded_rectangle((55, y - 8, 680, y + 18), radius=4, fill=CARD, outline=None)
                draw.text((70, y), f"{i:02d}", fill=GOLD if i == 1 else TEXT, font=normal_font)
                draw.text((120, y), team, fill=TEXT, font=normal_font)
                draw.text((470, y), f"W {table[team]['w']}", fill=TEXT, font=normal_font)
                draw.text((540, y), f"L {table[team]['l']}", fill=TEXT, font=normal_font)
                draw.text((610, y), f"PTS {table[team]['p']}", fill=ACCENT, font=normal_font)
                y += 30
        else:
            base_x = 60

            def draw_section(rounds, section_y, title):
                draw.text((base_x, section_y), title, fill=TEXT, font=head_font)
                top = section_y + 60
                first = len(rounds[0]["matches"])
                centers = []
                for round_data in rounds:
                    step = (first * base_step) / len(round_data["matches"])
                    centers.append([top + (index + 0.5) * step for index in range(len(round_data["matches"]))])

                for round_index in range(len(centers) - 1):
                    x1 = base_x + round_index * (cardw + gap) + cardw
                    x2 = base_x + (round_index + 1) * (cardw + gap)
                    for segment in connector_segments(centers[round_index], centers[round_index + 1], x1, x2):
                        draw.line(segment, fill=LINE, width=2)

                for round_index, round_data in enumerate(rounds):
                    x = base_x + round_index * (cardw + gap)
                    draw.text((x, top - 28), round_data["name"].upper(), fill=ACCENT, font=normal_font)
                    for match_index, match in enumerate(round_data["matches"]):
                        y = centers[round_index][match_index] - cardh / 2
                        draw.rounded_rectangle((x, y, x + cardw, y + cardh), radius=4, fill=CARD, outline=BORDER)
                        a_win = match.get("a") is not None and match.get("winner") == match.get("a")
                        b_win = match.get("b") is not None and match.get("winner") == match.get("b")
                        draw.rounded_rectangle((x + 6, y + 6, x + cardw - 6, y + 30), radius=3, fill="#1A2522" if a_win else CARD_ALT)
                        draw.rounded_rectangle((x + 6, y + 36, x + cardw - 6, y + 60), radius=3, fill="#1A2522" if b_win else CARD_ALT)
                        a_label = match.get("a") or ("BYE" if match.get("a_ready") else "Ожидание")
                        b_label = match.get("b") or ("BYE" if match.get("b_ready") else "Ожидание")
                        a_color = self.team_meta.get(match.get("a"), {}).get("color", ACCENT)
                        b_color = self.team_meta.get(match.get("b"), {}).get("color", ACCENT)
                        draw.rectangle((x + 10, y + 10, x + 13, y + 26), fill=a_color)
                        draw.rectangle((x + 10, y + 40, x + 13, y + 56), fill=b_color)
                        a_logo_width = paste_logo(match.get("a"), x + 18, y + 10)
                        b_logo_width = paste_logo(match.get("b"), x + 18, y + 40)
                        draw.text((x + 20 + a_logo_width, y + 11), self.fit_name(a_label, 17), fill=GREEN if a_win else TEXT, font=normal_font)
                        draw.text((x + 20 + b_logo_width, y + 41), self.fit_name(b_label, 17), fill=GREEN if b_win else TEXT, font=normal_font)
                        if match.get("score_a") is not None:
                            draw.text((x + cardw - 26, y + 11), str(match["score_a"]), fill=GREEN if a_win else TEXT, font=normal_font)
                        if match.get("score_b") is not None:
                            draw.text((x + cardw - 26, y + 41), str(match["score_b"]), fill=GREEN if b_win else TEXT, font=normal_font)
                return top + first * base_step + 24

            next_y = draw_section(self.rounds, 125, "ВЕРХНЯЯ СЕТКА" if self.mode == "double" else self.mode_var.get().upper())
            if self.mode == "double" and self.lower_rounds:
                draw_section(self.lower_rounds, next_y + 24, "НИЖНЯЯ СЕТКА")
            champion = self.current_champion() or "—"
            draw.rounded_rectangle((W - 310, 140, W - 60, 320), radius=6, fill=PANEL, outline=BORDER, width=1)
            draw.text((W - 240, 165), "ПОБЕДИТЕЛЬ", fill=GOLD, font=head_font)
            draw.text((W - 220, 225), champion, fill=TEXT, font=head_font)

        return img

    def export_png(self):
        path = filedialog.asksaveasfilename(title="Экспорт PNG", defaultextension=".png", filetypes=[("PNG", "*.png")])
        if not path:
            return
        try:
            self.render_export().save(path, "PNG")
            self.status(f"PNG экспортирован: {Path(path).name}")
        except ImportError:
            messagebox.showerror("Pillow не установлен", "Для экспорта в PNG требуется библиотека Pillow:\npip install pillow")
        except Exception as exc:
            messagebox.showerror("Ошибка экспорта", str(exc))

    def export_pdf(self):
        path = filedialog.asksaveasfilename(title="Экспорт PDF", defaultextension=".pdf", filetypes=[("PDF", "*.pdf")])
        if not path:
            return
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.pdfgen import canvas
            from reportlab.lib.utils import ImageReader

            img = self.render_export()
            pdf = canvas.Canvas(path, pagesize=landscape(A4))
            W, H = landscape(A4)
            pdf.drawImage(ImageReader(img), 0, 0, width=W, height=H, preserveAspectRatio=True, anchor="c")
            pdf.save()
            self.status(f"PDF экспортирован: {Path(path).name}")
        except ImportError:
            messagebox.showerror("reportlab не установлен", "Для экспорта в PDF требуется библиотека reportlab:\npip install reportlab")
        except Exception as exc:
            messagebox.showerror("Ошибка экспорта", str(exc))


# -----------------------------------------------------------------------------
# Protected Application Entry Point
# -----------------------------------------------------------------------------
if __name__ == "__main__":
    try:
        root = tk.Tk()
        root.withdraw()

        app = MatchDeskStudioApp(root)

        def reveal_main_app():
            root.deiconify()
            root.attributes("-fullscreen", True)
            root.lift()
            root.focus_force()

        splash = SplashScreen(root, on_complete=reveal_main_app)
        root.mainloop()
    except Exception:
        import traceback
        err = traceback.format_exc()
        try:
            import tkinter.messagebox as mb
            mb.showerror("MatchDesk Studio — Ошибка запуска", f"Сбой при запуске приложения:\n\n{err}")
        except Exception:
            pass
        print(err)
        input("\nНажмите Enter для выхода...")