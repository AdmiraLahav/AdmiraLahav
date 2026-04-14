#!/usr/bin/env python3
"""
Launch Control Dashboard \u2014 Termux-compatible, pure curses rendering
Dependencies: pip install psutil --break-system-packages
"""

import os, sys, time, threading, subprocess, datetime, socket, platform, curses, signal

# \u2500\u2500 auto-install psutil \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil",
                           "--break-system-packages", "-q"])
    import psutil

# \u2500\u2500 Termux: ASCII-safe box chars (no Unicode box-drawing) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
# Termux fonts handle these fine; the double-line box chars often corrupt.
TL, TR, BL, BR = "+", "+", "+", "+"
H, V           = "-", "|"
HFILL          = "-"
BAR_FULL       = "#"
BAR_EMPTY      = "."

LOGO_LINES = [
    " _        _   _   _  _  __  _  _",
    "| |      / \\ | | | || ||  \\| || |",
    "| |__   / _ \\| |_| || ||     || |",
    "|____| /_/ \\_|\\___/ |_||_|\\__||_|",
    " LAUNCH CONTROL DASHBOARD  v1.0  ",
]
LOGO_MINI = "[ LAUNCH CONTROL DASHBOARD v1.0 ]"

# \u2500\u2500 scripts (Termux-safe commands) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
SCRIPTS = [
    ("sysinfo",   "uname -a && uptime",
                  "System info"),
    ("disk",      "df -h /data 2>/dev/null || df -h / 2>/dev/null || df -h",
                  "Disk usage"),
    ("processes", "ps aux 2>/dev/null | head -20 || ps -A 2>/dev/null | head -20",
                  "Top processes"),
    ("network",   "ip route 2>/dev/null || netstat -rn 2>/dev/null || echo 'N/A'",
                  "Routing table"),
    ("tmp count", "find /tmp -maxdepth 1 -type f 2>/dev/null | wc -l || echo 0",
                  "Temp files"),
    ("ping",      "ping -c 4 8.8.8.8 2>/dev/null || echo 'ping unavailable'",
                  "Ping 8.8.8.8"),
    ("env vars",  "printenv | sort | head -30",
                  "Environment"),
    ("ports",     "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo 'N/A'",
                  "Open ports"),
]

# \u2500\u2500 state \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
class State:
    def __init__(self):
        self.selected      = 0
        self.mode          = "menu"
        self.log           = []
        self.output        = []
        self.run_count     = [0] * len(SCRIPTS)
        self.script_name   = None
        self.exit_code     = None
        self.start_time    = datetime.datetime.now()
        self.lock          = threading.Lock()

S = State()

# \u2500\u2500 color pair indices (1-based; 0 = terminal default) \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
C_CYAN    = 1
C_GREEN   = 2
C_YELLOW  = 3
C_RED     = 4
C_MAGENTA = 5
C_BLUE    = 6
C_DIM     = 7
C_WHITE   = 8
C_HILIGHT = 9   # selected-row: black on cyan

def init_colors():
    curses.start_color()
    curses.use_default_colors()
    bg = -1
    curses.init_pair(C_CYAN,    curses.COLOR_CYAN,    bg)
    curses.init_pair(C_GREEN,   curses.COLOR_GREEN,   bg)
    curses.init_pair(C_YELLOW,  curses.COLOR_YELLOW,  bg)
    curses.init_pair(C_RED,     curses.COLOR_RED,     bg)
    curses.init_pair(C_MAGENTA, curses.COLOR_MAGENTA, bg)
    curses.init_pair(C_BLUE,    curses.COLOR_BLUE,    bg)
    curses.init_pair(C_DIM,     curses.COLOR_WHITE,   bg)
    curses.init_pair(C_WHITE,   curses.COLOR_WHITE,   bg)
    curses.init_pair(C_HILIGHT, curses.COLOR_BLACK,   curses.COLOR_CYAN)

# \u2500\u2500 safe draw helpers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
def safe_addstr(win, y, x, text, attr=0):
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    available = max_x - x - 1
    if available <= 0:
        return
    text = str(text)[:available]
    # Strip non-ASCII characters that may corrupt Termux display
    text = text.encode("ascii", errors="replace").decode("ascii")
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass

def hline_str(win, y, x, ch, n, attr=0):
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x - 1:
        return
    n = min(n, max_x - x - 1)
    if n <= 0:
        return
    safe_addstr(win, y, x, ch * n, attr)

def draw_box(win, y, x, h, w, title="", color=C_BLUE):
    """Draw an ASCII border box."""
    max_y, max_x = win.getmaxyx()
    attr = curses.color_pair(color) | curses.A_BOLD
    # top row
    safe_addstr(win, y,     x,     TL,       attr)
    hline_str(  win, y,     x+1,   H,  w-2,  attr)
    safe_addstr(win, y,     x+w-1, TR,       attr)
    # bottom row
    if y+h-1 < max_y:
        safe_addstr(win, y+h-1, x,     BL,       attr)
        hline_str(  win, y+h-1, x+1,   H,  w-2,  attr)
        safe_addstr(win, y+h-1, x+w-1, BR,       attr)
    # sides
    for row in range(y+1, min(y+h-1, max_y)):
        safe_addstr(win, row, x,     V, attr)
        if x+w-1 < max_x:
            safe_addstr(win, row, x+w-1, V, attr)
    # title
    if title and w > 6:
        label = f" {title} "[:w-4]
        safe_addstr(win, y, x+2, label, curses.color_pair(color) | curses.A_BOLD)

# \u2500\u2500 system info \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500
psutil.cpu_percent(interval=None)   # prime the pump

def _safe_hostname():
    try:
        return socket.gethostname()
    except Exception:
        return os.environ.get("HOSTNAME", "localhost")

def _safe_disk():
    """Try several paths common on Termux/Android."""
    for path in ("/data", "/data/data", "/", "/sdcard"):
        try:
            return psutil.disk_usage(path), path
        except Exception:
            continue
    return None, "?"

def get_info():
    cpu  = psutil.cpu_percent(interval=None)
    mem  = psutil.virtual_memory()
    disk, dpath = _safe_disk()
    net  = psutil.net_io_counters()
    try:
        boot = datetime.datetime.fromtimestamp(psutil.boot_time())
        up   = str(datetime.datetime.now() - boot).split(".")[0]
    except Exception:
        up = "?"

    # Temperature \u2014 Android exposes via sensors_temperatures on some devices
    temp = None
    try:
        temps = psutil.sensors_temperatures() or {}
        temp  = next((e.current for entries in temps.values()
                      for e in entries if e.current and e.current > 0), None)
    except (AttributeError, Exception):
        pass   # Not available on Android \u2014 silently skip

    return dict(
        cpu_pct    = cpu,
        cpu_count  = psutil.cpu_count(logical=True) or 1,
        mem_pct    = mem.percent,
        mem_used   = mem.used,
        mem_total  = mem.total,
        disk_pct   = disk.percent   if disk else 0,
        disk_used  = disk.used      if disk else 0,
        disk_total = disk.total     if disk else 0,
        disk_path  = dpath,
        net_sent   = net.bytes_sent if net else 0,
        net_recv   = net.bytes_recv if net else 0,
        uptime     = up,
        temp_c     = temp,
        hostname   = _safe_hostname(),
        user       = os.environ.get("USER", os.environ.get("USERNAME", "?")),
        os_str     = platform.system() + " " + platform.release(),
        arch       = platform.machine(),
        python     = platform.python_version(),
        shell      = os.environ.get("SHELL", "?"),
    )

def fmt_bytes(n):
    for u in ("B", "KB", "MB", "GB", "TB"):
        if n < 1024:
            return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def pct_bar(pct, width):
    """ASCII progress bar that fits exactly `width` chars."""
    if width < 6:
        return f"{pct:.0f}%"[:width]
    bar_w  = width - 6
    filled = int(bar_w * pct / 100)
    empty  = bar_w - filled
    bar    = BAR_FULL * filled + BAR_EMPTY * empty
    return f"{bar} {pct:4.1f}%"

def pct_color(p):
    if p < 50:  return curses.color_pair(C_GREEN)  | curses.A_BOLD
    if p < 75:  return curses.color_pair(C_YELLOW) | curses.A_BOLD
    return              curses.color_pair(C_RED)    | curses.A_BOLD

def log(msg, pair=C_DIM):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    # Strip non-ASCII so log lines never corrupt display
    msg = msg.encode("ascii", errors="replace").decode("ascii")
    with S.lock:
        S.log.append((ts, msg, pair))
        if len(S.log) > 500:
            S.log.pop(0)

# \u2500\u2500 section renderers \u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500\u2500

def draw_logo(win, y, x, w):
    logo_w = max(len(l) for l in LOGO_LINES)
    colors = [C_CYAN, C_CYAN, C_BLUE, C_MAGENTA, C_CYAN]
    if w >= logo_w + 2:
        cx = x + (w - logo_w) // 2
        for i, line in enumerate(LOGO_LINES):
            safe_addstr(win, y+i, cx, line,
                        curses.color_pair(colors[i % len(colors)]) | curses.A_BOLD)
    else:
        label = LOGO_MINI[:w-2]
        safe_addstr(win, y, x + max(0, (w - len(label)) // 2), label,
                    curses.color_pair(C_CYAN) | curses.A_BOLD)

def draw_sysinfo(win, y, x, h, w, info):
    draw_box(win, y, x, h, w, "SYSTEM", C_CYAN)
    inner_w = w - 4
    row = y + 1

    def kv(label, val, vc=C_WHITE):
        nonlocal row
        if row >= y + h - 1:
            return
        lbl = f"{label:<8}"[:8]
        safe_addstr(win, row, x+2,  lbl, curses.color_pair(C_CYAN) | curses.A_BOLD)
        safe_addstr(win, row, x+10, str(val)[:max(0, inner_w - 8)],
                    curses.color_pair(vc))
        row += 1

    def bar_row(label, pct):
        nonlocal row
        if row >= y + h - 1:
            return
        bar_w = inner_w - 9
        safe_addstr(win, row, x+2, f"{label:<8}"[:8],
                    curses.color_pair(C_CYAN) | curses.A_BOLD)
        if bar_w > 4:
            safe_addstr(win, row, x+10, pct_bar(pct, bar_w), pct_color(pct))
        row += 1

    now = datetime.datetime.now().strftime("%H:%M:%S")
    kv("HOST",   info["hostname"][:inner_w-9],  C_WHITE)
    kv("USER",   info["user"],                  C_GREEN)
    kv("OS",     info["os_str"][:inner_w-9],    C_DIM)
    kv("ARCH",   info["arch"],                  C_DIM)
    kv("PYTHON", info["python"],                C_YELLOW)
    kv("UPTIME", info["uptime"],                C_WHITE)
    kv("TIME",   now,                           C_CYAN)
    row += 1
    bar_row(f"CPU*{info['cpu_count']}", info["cpu_pct"])
    bar_row("RAM",  info["mem_pct"])
    bar_row(f"DISK", info["disk_pct"])

    if row < y + h - 1:
        mem_str = f"{fmt_bytes(info['mem_used'])}/{fmt_bytes(info['mem_total'])}"
        safe_addstr(win, row, x+10, mem_str[:max(0, inner_w-9)],
                    curses.color_pair(C_DIM))
        row += 1
    if row < y + h - 1:
        disk_str = f"{fmt_bytes(info['disk_used'])}/{fmt_bytes(info['disk_total'])} ({info['disk_path']})"
        safe_addstr(win, row, x+10, disk_str[:max(0, inner_w-9)],
                    curses.color_pair(C_DIM))
        row += 1

    row += 1
    kv("Up NET", fmt_bytes(info["net_sent"]), C_GREEN)
    kv("Dn NET", fmt_bytes(info["net_recv"]), C_BLUE)

    if info["temp_c"] and row < y + h - 1:
        tc = info["temp_c"]
        vc = C_RED if tc > 80 else C_YELLOW if tc > 60 else C_GREEN
        kv("TEMP", f"{tc:.1f}C", vc)

def draw_scripts(win, y, x, h, w):
    draw_box(win, y, x, h, w, "SCRIPTS", C_MAGENTA)
    show_desc = w >= 60
    col_num   = 3
    col_name  = 12
    col_desc  = 20 if show_desc else 0
    col_runs  = 5
    hdr_attr  = curses.color_pair(C_CYAN) | curses.A_BOLD

    hx = x + 2
    safe_addstr(win, y+1, hx,                       " # ",    hdr_attr)
    safe_addstr(win, y+1, hx+col_num,               "SCRIPT", hdr_attr)
    if show_desc:
        safe_addstr(win, y+1, hx+col_num+col_name,  "DESC",   hdr_attr)
    safe_addstr(win, y+1, x+w-col_runs-2,           "RUNS",   hdr_attr)
    hline_str(win, y+2, x+1, HFILL, w-2, curses.color_pair(C_BLUE))

    max_rows = h - 4
    for i, (name, _, desc) in enumerate(SCRIPTS):
        row = y + 3 + i
        if i >= max_rows or row >= y + h - 1:
            break
        sel  = (i == S.selected)
        attr = curses.color_pair(C_HILIGHT) | curses.A_BOLD if sel else curses.color_pair(C_WHITE)
        dim  = curses.color_pair(C_HILIGHT) if sel else curses.color_pair(C_DIM)
        prefix = "> " if sel else "  "
        runs   = str(S.run_count[i]) if S.run_count[i] else "-"

        safe_addstr(win, row, x+1, " " * (w-2), attr if sel else 0)
        safe_addstr(win, row, x+2,               f"{i+1:>2} ",             dim)
        safe_addstr(win, row, x+2+col_num,       f"{prefix}{name}"[:col_name], attr)
        if show_desc:
            safe_addstr(win, row, x+2+col_num+col_name, desc[:col_desc],   dim)
        safe_addstr(win, row, x+w-col_runs-2,   f"{runs:>3}",              dim)

    hint_row = y + h - 2
    if hint_row > y + 2:
        safe_addstr(win, hint_row, x+2,
                    " ^/v navigate  ENTER launch  Q quit "[:w-4],
                    curses.color_pair(C_DIM))

def draw_output(win, y, x, h, w):
    name = S.script_name or "output"
    ec   = S.exit_code
    if S.mode == "running":
        title = f"* RUNNING: {name}"
        tcol  = C_YELLOW
    else:
        ok    = (ec == 0) if ec is not None else True
        mark  = "OK" if ok else "ERR"
        title = f"[{mark}] {name}  exit:{ec}"
        tcol  = C_GREEN if ok else C_RED
    draw_box(win, y, x, h, w, title[:w-6], tcol)

    inner_h = h - 2
    lines   = S.output[-inner_h:]
    for i, line in enumerate(lines):
        safe_addstr(win, y+1+i, x+2, line[:w-4], curses.color_pair(C_GREEN))

    hint_row = y + h - 2
    if hint_row > y + 1:
        safe_addstr(win, hint_row, x+2, " ESC/Q -> menu "[:w-4],
                    curses.color_pair(C_DIM))

def draw_log(win, y, x, h, w):
    draw_box(win, y, x, h, w, "LOG", C_YELLOW)
    inner_h = h - 2
    with S.lock:
        lines = list(S.log[-inner_h:])
    for i, (ts, msg, pair) in enumerate(lines):
        row = y + 1 + i
        if row >= y + h - 1:
            break
        safe_addstr(win, row, x+2,  f"[{ts}] ", curses.color_pair(C_DIM))
        safe_addstr(win, row, x+12, msg[:max(0, w-14)], curses.color_pair(pair))

def draw_statusbar(win, y, x, w, cols, rows):
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sess  = str(datetime.datetime.now() - S.start_time).split(".")[0]
    total = sum(S.run_count)
    mc    = {
        "menu":    cur