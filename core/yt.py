"""
محرك التحميل (yt-dlp) — كل الدوال هنا حاجبة، تُستدعى دائماً عبر asyncio.to_thread
كي ما تجمّد السورس. يدعم يوتيوب + أي موقع يدعمه yt-dlp (انستا، تيك توك، تويتر ...).
"""
import os
import re
import shutil
import time

import yt_dlp

URL_RE = re.compile(r"https?://\S+", re.I)
STD_HEIGHTS = (144, 240, 360, 480, 720, 1080, 1440, 2160)
MP3_QUALITIES = ("128", "192", "320")


def has_ffmpeg():
    return shutil.which("ffmpeg") is not None


def is_url(text):
    return bool(URL_RE.match((text or "").strip()))


def extract_url(text):
    m = URL_RE.search(text or "")
    return m.group(0) if m else None


def _base_opts():
    opts = {
        "quiet": True, "no_warnings": True, "noprogress": True,
        "nocheckcertificate": True, "socket_timeout": 20, "retries": 3,
        "noplaylist": True, "geo_bypass": True,
    }
    cookies = os.getenv("RECO_COOKIES", "cookies.txt")
    if cookies and os.path.exists(cookies):
        opts["cookiefile"] = cookies
    return opts


def search(query, n=5):
    """بحث يوتيوب سريع (بدون جلب الصيغ). يرجع قائمة نتائج مختصرة."""
    opts = _base_opts() | {"extract_flat": True, "skip_download": True}
    with yt_dlp.YoutubeDL(opts) as ydl:
        data = ydl.extract_info(f"ytsearch{n}:{query}", download=False)
    out = []
    for e in (data or {}).get("entries") or []:
        if not e or not e.get("id"):
            continue
        out.append({
            "id": e["id"],
            "url": e.get("url") or f"https://www.youtube.com/watch?v={e['id']}",
            "title": e.get("title") or "بدون عنوان",
            "channel": e.get("channel") or e.get("uploader") or "",
            "duration": e.get("duration") or 0,
            "views": e.get("view_count") or 0,
            "thumb": f"https://i.ytimg.com/vi/{e['id']}/hqdefault.jpg",
        })
    return out


def get_info(url):
    """معلومات كاملة + الصيغ المتاحة."""
    with yt_dlp.YoutubeDL(_base_opts() | {"skip_download": True}) as ydl:
        info = ydl.extract_info(url, download=False)
    if info and "entries" in info:
        info = next((e for e in info["entries"] if e), None)
    if not info:
        raise ValueError("ما لقيت شي بهذا الرابط")
    if info.get("is_live"):
        raise ValueError("هذا بث مباشر — ما أكدر أحمله")
    return info


def brief(info):
    """نتيجة مختصرة بنفس شكل search() من info كامل."""
    return {
        "id": info.get("id"), "url": info.get("webpage_url") or info.get("original_url"),
        "title": info.get("title") or "بدون عنوان",
        "channel": info.get("channel") or info.get("uploader") or "",
        "duration": info.get("duration") or 0, "views": info.get("view_count") or 0,
        "thumb": info.get("thumbnail") or "",
    }


def _fsize(f, duration):
    s = f.get("filesize") or f.get("filesize_approx")
    if not s and f.get("tbr") and duration:
        s = f["tbr"] * 1000 / 8 * duration
    return int(s or 0)


def video_options(info):
    """قائمة (ارتفاع، حجم_تقريبي) للدقات المتاحة، بترتيب تصاعدي."""
    dur = info.get("duration") or 0
    formats = info.get("formats") or []
    audio = [f for f in formats if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")]
    best_audio = max((_fsize(f, dur) for f in audio), default=0)
    by_h = {}
    for f in formats:
        h = f.get("height")
        if not h or f.get("vcodec") in (None, "none"):
            continue
        size = _fsize(f, dur)
        if f.get("acodec") in (None, "none"):
            size += best_audio
        by_h[h] = max(by_h.get(h, 0), size)
    # نوحّد على الدقات القياسية (أقرب دقة قياسية ≤ الارتفاع)
    std = {}
    for h, size in by_h.items():
        cands = [s for s in STD_HEIGHTS if s <= h + 8]
        if not cands:
            continue
        s = cands[-1]
        std[s] = max(std.get(s, 0), size)
    return sorted(std.items())


def audio_size(info):
    dur = info.get("duration") or 0
    return max((_fsize(f, dur) for f in info.get("formats") or []
                if f.get("acodec") not in (None, "none") and f.get("vcodec") in (None, "none")), default=0)


def download(url, kind, quality, outdir, hook=None):
    """
    تحميل. kind: "v" فيديو، "a" صوت.
    quality: للفيديو الارتفاع (مثل 720)، للصوت "m4a" أو "mp3_192".
    يرجع (مسار_الملف, info).
    """
    os.makedirs(outdir, exist_ok=True)
    ff = has_ffmpeg()
    opts = _base_opts() | {"outtmpl": os.path.join(outdir, "%(title).70s [%(id)s].%(ext)s"),
                           "restrictfilenames": False, "windowsfilenames": True,
                           "concurrent_fragment_downloads": 4}
    if hook:
        opts["progress_hooks"] = [hook]

    if kind == "v":
        h = int(quality or 720)
        if ff:
            opts["format"] = (f"bv*[height<={h}][ext=mp4]+ba[ext=m4a]/bv*[height<={h}]+ba/"
                              f"b[height<={h}][ext=mp4]/b[height<={h}]/b")
            opts["merge_output_format"] = "mp4"
        else:
            opts["format"] = f"b[height<={h}][ext=mp4]/b[height<={h}]/b"
    else:
        q = str(quality or "m4a")
        if q.startswith("mp3") and ff:
            kbps = q.split("_")[1] if "_" in q else "192"
            opts["format"] = "bestaudio/best"
            opts["postprocessors"] = [{"key": "FFmpegExtractAudio", "preferredcodec": "mp3",
                                       "preferredquality": kbps}]
        else:
            opts["format"] = "bestaudio[ext=m4a]/bestaudio/best"

    with yt_dlp.YoutubeDL(opts) as ydl:
        info = ydl.extract_info(url, download=True)
        if info and "entries" in info:
            info = next((e for e in info["entries"] if e), info)
        path = None
        reqs = info.get("requested_downloads") or []
        if reqs and reqs[0].get("filepath"):
            path = reqs[0]["filepath"]
        if not path or not os.path.exists(path):
            path = ydl.prepare_filename(info)
            if kind == "a" and str(quality).startswith("mp3") and ff:
                path = os.path.splitext(path)[0] + ".mp3"
            elif kind == "v" and ff and not os.path.exists(path):
                path = os.path.splitext(path)[0] + ".mp4"
    if not os.path.exists(path):
        # آخر محاولة: أحدث ملف بالمجلد
        files = sorted((os.path.join(outdir, f) for f in os.listdir(outdir)), key=os.path.getmtime)
        if not files:
            raise FileNotFoundError("انتهى التحميل لكن الملف غير موجود")
        path = files[-1]
    return path, info


class ProgressHook:
    """يحوّل hook الخاص بـ yt-dlp (يعمل بخيط) إلى قيم نسبة مئوية تقرأها حلقة التحديث."""

    def __init__(self):
        self.pct = 0.0
        self.speed = 0
        self.eta = None
        self.status = "downloading"
        self.total = 0
        self.done = 0
        self.cancel_check = None   # دالة ترجع True لو المستخدم ألغى

    def __call__(self, d):
        if self.cancel_check and self.cancel_check():
            raise RuntimeError("cancelled by user")
        self.status = d.get("status", "")
        if self.status == "downloading":
            tot = d.get("total_bytes") or d.get("total_bytes_estimate") or 0
            got = d.get("downloaded_bytes") or 0
            self.total, self.done = tot, got
            self.pct = (got / tot * 100) if tot else self.pct
            self.speed = d.get("speed") or 0
            self.eta = d.get("eta")
        elif self.status == "finished":
            self.pct = 100.0


def update_ytdlp():
    """pip install -U yt-dlp (بخيط)."""
    import subprocess
    import sys
    r = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "--break-system-packages", "-q"],
                       capture_output=True, text=True, timeout=300)
    if r.returncode != 0:
        r = subprocess.run([sys.executable, "-m", "pip", "install", "-U", "yt-dlp", "-q"],
                           capture_output=True, text=True, timeout=300)
    return r.returncode == 0, (r.stderr or r.stdout)[-300:]


def clean_tmp(path):
    shutil.rmtree(path, ignore_errors=True)


def ts():
    return int(time.time())
