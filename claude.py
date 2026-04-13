#!/usr/bin/env python3
"""
Launch Control Dashboard — pure curses rendering, no Rich Layout
Dependencies: pip install psutil
(rich is NOT needed anymore)
"""

import os, sys, time, threading, subprocess, datetime, socket, platform, curses, shutil, signal, textwrap

# ── auto-install psutil ───────────────────────────────────────────────────────
try:
    import psutil
except ImportError:
    subprocess.check_call([sys.executable, "-m", "pip", "install", "psutil",
                           "--break-system-packages", "-q"])
    import psutil

# ── scripts ───────────────────────────────────────────────────────────────────
SCRIPTS = [
    ("sysinfo",    "uname -a && uptime",                                             "System info"),
    ("disk",       "df -h /",                                                        "Disk usage"),
    ("processes",  "ps aux --sort=-%cpu | head -20",                                 "Top CPU procs"),
    ("network",    "ip route 2>/dev/null || netstat -rn 2>/dev/null || echo N/A",    "Routing table"),
    ("tmp count",  "find /tmp -maxdepth 1 -type f | wc -l",                          "Temp files"),
    ("ping",       "ping -c 4 8.8.8.8 2>/dev/null || echo 'ping unavailable'",       "Ping 8.8.8.8"),
    ("env vars",   "printenv | sort | head -30",                                     "Environment"),
    ("ports",      "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo N/A",  "Open ports"),
]

LOGO_LINES = [
    "██╗      █████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗  ██╗",
    "██║     ██╔══██╗██║   ██║████╗  ██║██╔════╝██║  ██║",
    "██║     ███████║██║   ██║██╔██╗ ██║██║     ███████║",
    "██║     ██╔══██║██║   ██║██║╚██╗██║██║     ██╔══██║",
    "███████╗██║  ██║╚██████╔╝██║ ╚████║╚██████╗██║  ██║",
    "╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝",
    " C O N T R O L  ·  D A S H B O A R D  ·  v 1 . 0  ",
]
LOGO_MINI = "[ LAUNCH CONTROL DASHBOARD v1.0 ]"

# ── state ─────────────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        self.selected     = 0
        self.mode         = "menu"          # menu | running | output
        self.log          = []              # (ts, msg, color_pair)
        self.output       = []              # stdout lines from last script
        self.run_count    = [0]*len(SCRIPTS)
        self.script_name  = None
        self.exit_code    = None
        self.start_time   = datetime.datetime.now()
        self.lock         = threading.Lock()
        self.output_scroll= 0               # lines from bottom
        self.needs_redraw = True

S = State()

# ── color pair constants (defined after curses.start_color) ───────────────────
C_NORMAL  = 0   # default
C_CYAN    = 1
C_GREEN   = 2
C_YELLOW  = 3
C_RED     = 4
C_MAGENTA = 5
C_BLUE    = 6
C_DIM     = 7
C_WHITE   = 8
C_HILIGHT = 9   # selected row bg

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

# ── safe draw helpers ─────────────────────────────────────────────────────────
def safe_addstr(win, y, x, text, attr=0):
    """Draw text clipped to window bounds — never raises."""
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y or x >= max_x:
        return
    if x < 0:
        text = text[-x:]
        x = 0
    available = max_x - x - 1           # leave rightmost cell alone (curses quirk)
    if available <= 0:
        return
    text = text[:available]
    try:
        win.addstr(y, x, text, attr)
    except curses.error:
        pass

def hline(win, y, x, ch, n, attr=0):
    max_y, max_x = win.getmaxyx()
    if y < 0 or y >= max_y:
        return
    n = min(n, max_x - x - 1)
    if n <= 0:
        return
    try:
        win.hline(y, x, ch, n, attr)
    except curses.error:
        pass

def draw_box(win, y, x, h, w, title="", color=C_BLUE):
    """Draw a rounded-ish border, clipped to win."""
    max_y, max_x = win.getmaxyx()
    attr = curses.color_pair(color) | curses.A_BOLD
    # top
    safe_addstr(win, y,     x,     "╭", attr)
    hline(      win, y,     x+1,   ord("─"), w-2, attr)
    safe_addstr(win, y,     x+w-1, "╮", attr)
    # bottom
    safe_addstr(win, y+h-1, x,     "╰", attr)
    hline(      win, y+h-1, x+1,   ord("─"), w-2, attr)
    safe_addstr(win, y+h-1, x+w-1, "╯", attr)
    # sides
    for row in range(y+1, min(y+h-1, max_y)):
        safe_addstr(win, row, x,     "│", attr)
        safe_addstr(win, row, x+w-1, "│", attr)
    # title
    if title and w > 6:
        label = f" {title} "[:w-4]
        safe_addstr(win, y, x+2, label, curses.color_pair(color) | curses.A_BOLD)

# ── system info ───────────────────────────────────────────────────────────────
psutil.cpu_percent(interval=None)

def get_info():
    cpu  = psutil.cpu_percent(interval=None)
    mem  = psutil.virtual_memory()
    disk = psutil.disk_usage("/")
    net  = psutil.net_io_counters()
    boot = datetime.datetime.fromtimestamp(psutil.boot_time())
    up   = str(datetime.datetime.now() - boot).split(".")[0]
    try:
        temps = psutil.sensors_temperatures() or {}
        temp  = next((e.current for entries in temps.values()
                      for e in entries if e.current > 0), None)
    except Exception:
        temp = None
    return dict(
        cpu_pct   = cpu,
        cpu_count = psutil.cpu_count(logical=True),
        mem_pct   = mem.percent,
        mem_used  = mem.used,
        mem_total = mem.total,
        disk_pct  = disk.percent,
        disk_used = disk.used,
        disk_total= disk.total,
        net_sent  = net.bytes_sent,
        net_recv  = net.bytes_recv,
        uptime    = up,
        temp_c    = temp,
        hostname  = socket.gethostname(),
        user      = os.environ.get("USER", os.environ.get("USERNAME","?")),
        os_str    = platform.system()+" "+platform.release(),
        arch      = platform.machine(),
        python    = platform.python_version(),
        shell     = os.environ.get("SHELL","?"),
    )

def fmt_bytes(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def pct_bar(pct, width):
    """ASCII progress bar that fits exactly `width` chars."""
    if width < 6:
        return f"{pct:.0f}%"[:width]
    bar_w  = width - 6          # leave room for " XX.X%"
    filled = int(bar_w * pct / 100)
    empty  = bar_w - filled
    bar    = "█" * filled + "░" * empty
    return f"{bar} {pct:4.1f}%"

def pct_color(p):
    if p < 50:  return curses.color_pair(C_GREEN)  | curses.A_BOLD
    if p < 75:  return curses.color_pair(C_YELLOW) | curses.A_BOLD
    return              curses.color_pair(C_RED)    | curses.A_BOLD

def log(msg, pair=C_DIM):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    with S.lock:
        S.log.append((ts, msg, pair))
        if len(S.log) > 500:
            S.log.pop(0)

# ── section renderers (all clipped) ──────────────────────────────────────────

def draw_logo(win, y, x, w):
    logo_w = len(LOGO_LINES[0])
    colors = [C_CYAN, C_CYAN, C_BLUE, C_BLUE, C_MAGENTA, C_MAGENTA, C_CYAN]
    if w >= logo_w + 4:
        cx = x + (w - logo_w) // 2
        for i, line in enumerate(LOGO_LINES):
            safe_addstr(win, y+i, cx, line,
                        curses.color_pair(colors[i]) | curses.A_BOLD)
    else:
        label = LOGO_MINI[:w-2]
        safe_addstr(win, y, x + (w - len(label))//2, label,
                    curses.color_pair(C_CYAN) | curses.A_BOLD)

def draw_sysinfo(win, y, x, h, w, info):
    draw_box(win, y, x, h, w, "SYSTEM", C_CYAN)
    inner_w = w - 4
    row = y + 1

    def kv(label, val, vc=C_WHITE):
        nonlocal row
        if row >= y + h - 1: return
        safe_addstr(win, row, x+2, f"{label:<8}", curses.color_pair(C_CYAN) | curses.A_BOLD)
        safe_addstr(win, row, x+10, str(val)[:inner_w-8], curses.color_pair(vc))
        row += 1

    def bar_row(label, pct):
        nonlocal row
        if row >= y + h - 1: return
        bar_w = inner_w - 9
        safe_addstr(win, row, x+2, f"{label:<8}", curses.color_pair(C_CYAN) | curses.A_BOLD)
        if bar_w > 4:
            safe_addstr(win, row, x+10, pct_bar(pct, bar_w), pct_color(pct))
        row += 1

    now = datetime.datetime.now().strftime("%H:%M:%S")
    kv("HOST",   info["hostname"],   C_WHITE)
    kv("USER",   info["user"],       C_GREEN)
    kv("OS",     info["os_str"][:inner_w-9], C_DIM)
    kv("ARCH",   info["arch"],       C_DIM)
    kv("PYTHON", info["python"],     C_YELLOW)
    kv("UPTIME", info["uptime"],     C_WHITE)
    kv("TIME",   now,                C_CYAN)
    row += 1
    bar_row(f"CPU×{info['cpu_count']}", info["cpu_pct"])
    bar_row("RAM",  info["mem_pct"])
    bar_row("DISK", info["disk_pct"])
    if row < y + h - 1:
        mem_str  = f"{fmt_bytes(info['mem_used'])}/{fmt_bytes(info['mem_total'])}"
        disk_str = f"{fmt_bytes(info['disk_used'])}/{fmt_bytes(info['disk_total'])}"
        safe_addstr(win, row, x+10, mem_str[:inner_w-9],  curses.color_pair(C_DIM)); row += 1
    if row < y + h - 1:
        disk_str = f"{fmt_bytes(info['disk_used'])}/{fmt_bytes(info['disk_total'])}"
        safe_addstr(win, row, x+10, disk_str[:inner_w-9], curses.color_pair(C_DIM)); row += 1
    row += 1
    kv("↑ NET", fmt_bytes(info["net_sent"]), C_GREEN)
    kv("↓ NET", fmt_bytes(info["net_recv"]), C_BLUE)
    if info["temp_c"] and row < y + h - 1:
        tc = info["temp_c"]
        vc = C_RED if tc > 80 else C_YELLOW if tc > 60 else C_GREEN
        kv("TEMP", f"{tc:.1f}°C", vc)

def draw_scripts(win, y, x, h, w):
    draw_box(win, y, x, h, w, "SCRIPTS", C_MAGENTA)
    show_desc = w >= 70
    col_num   = 3
    col_name  = 14
    col_desc  = 22 if show_desc else 0
    col_runs  = 6
    hdr_attr  = curses.color_pair(C_CYAN) | curses.A_BOLD

    # header
    hx = x + 2
    safe_addstr(win, y+1, hx,                          " # ",     hdr_attr)
    safe_addstr(win, y+1, hx+col_num,                  "SCRIPT",  hdr_attr)
    if show_desc:
        safe_addstr(win, y+1, hx+col_num+col_name,     "DESC",    hdr_attr)
    safe_addstr(win, y+1, x+w-col_runs-2,              "RUNS",    hdr_attr)
    hline(win, y+2, x+1, ord("─"), w-2, curses.color_pair(C_BLUE))

    max_rows = h - 4   # box top+hdr+divider+bottom
    for i, (name, _, desc) in enumerate(SCRIPTS):
        row = y + 3 + i
        if i >= max_rows or row >= y + h - 1:
            break
        sel  = (i == S.selected)
        attr = curses.color_pair(C_HILIGHT) | curses.A_BOLD if sel else curses.color_pair(C_WHITE)
        dim  = curses.color_pair(C_HILIGHT) if sel else curses.color_pair(C_DIM)
        prefix = "▶ " if sel else "  "
        runs   = str(S.run_count[i]) if S.run_count[i] else "—"

        # clear the row inside box
        safe_addstr(win, row, x+1, " "*(w-2), attr if sel else 0)
        safe_addstr(win, row, x+2,                  f"{i+1:>2} ",        dim)
        safe_addstr(win, row, x+2+col_num,           f"{prefix}{name}"[:col_name], attr)
        if show_desc:
            safe_addstr(win, row, x+2+col_num+col_name, desc[:col_desc],  dim)
        safe_addstr(win, row, x+w-col_runs-2,        f"{runs:>4}",        dim)

    # hint
    hint_row = y + h - 2
    if hint_row > y + 2:
        safe_addstr(win, hint_row, x+2,
                    " ↑↓ navigate   ENTER launch   Q quit "[:w-4],
                    curses.color_pair(C_DIM))

def draw_output(win, y, x, h, w):
    name = S.script_name or "output"
    ec   = S.exit_code
    if S.mode == "running":
        title = f"● RUNNING: {name}"
        tcol  = C_YELLOW
    else:
        ok    = ec == 0 if ec is not None else True
        title = f"{'✔' if ok else '✘'} DONE: {name}  exit:{ec}"
        tcol  = C_GREEN if ok else C_RED
    draw_box(win, y, x, h, w, title[:w-6], tcol)

    inner_h = h - 2
    lines   = S.output[-inner_h:]
    for i, line in enumerate(lines):
        safe_addstr(win, y+1+i, x+2, line[:w-4], curses.color_pair(C_GREEN))

    hint_row = y + h - 2
    if hint_row > y + 1:
        safe_addstr(win, hint_row, x+2, " ESC/Q → menu "[:w-4],
                    curses.color_pair(C_DIM))

def draw_log(win, y, x, h, w):
    draw_box(win, y, x, h, w, "LOG", C_YELLOW)
    inner_h = h - 2
    with S.lock:
        lines = S.log[-inner_h:]
    for i, (ts, msg, pair) in enumerate(lines):
        row = y + 1 + i
        if row >= y + h - 1: break
        safe_addstr(win, row, x+2,  f"[{ts}] ", curses.color_pair(C_DIM))
        safe_addstr(win, row, x+12, msg[:w-14], curses.color_pair(pair))

def draw_statusbar(win, y, x, w, cols, rows):
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sess  = str(datetime.datetime.now() - S.start_time).split(".")[0]
    total = sum(S.run_count)
    mc    = {  "menu":    curses.color_pair(C_CYAN)    | curses.A_BOLD,
               "running": curses.color_pair(C_GREEN)   | curses.A_BOLD,
               "output":  curses.color_pair(C_MAGENTA) | curses.A_BOLD,
            }.get(S.mode, 0)
    hline(win, y, x, ord("─"), w, curses.color_pair(C_BLUE))
    left  = f"  ◈ MODE:"
    right = f"UP:{sess}  {now}  {cols}×{rows}  "
    safe_addstr(win, y+1, x,          left,           curses.color_pair(C_WHITE) | curses.A_BOLD)
    safe_addstr(win, y+1, x+9,        S.mode.upper(), mc)
    safe_addstr(win, y+1, x+17,       f"  runs:{total}", curses.color_pair(C_DIM))
    safe_addstr(win, y+1, x+w-len(right), right,      curses.color_pair(C_DIM))

def draw_too_small(win, rows, cols):
    win.clear()
    msg1 = "⚠  TERMINAL TOO SMALL  ⚠"
    msg2 = f"Current:  {cols} × {rows}"
    msg3 = "Required: 80 × 24 minimum"
    msg4 = "Resize window to continue."
    msg5 = "Q to quit"
    mid  = rows // 2
    cx   = cols // 2
    safe_addstr(win, mid-2, cx-len(msg1)//2, msg1, curses.color_pair(C_RED)    | curses.A_BOLD)
    safe_addstr(win, mid,   cx-len(msg2)//2, msg2, curses.color_pair(C_YELLOW) | curses.A_BOLD)
    safe_addstr(win, mid+1, cx-len(msg3)//2, msg3, curses.color_pair(C_WHITE))
    safe_addstr(win, mid+2, cx-len(msg4)//2, msg4, curses.color_pair(C_DIM))
    safe_addstr(win, mid+4, cx-len(msg5)//2, msg5, curses.color_pair(C_DIM))

# ── layout engine ─────────────────────────────────────────────────────────────
def render(win, info):
    rows, cols = win.getmaxyx()

    if cols < 60 or rows < 16:
        draw_too_small(win, rows, cols)
        return

    win.erase()

    # ── decide geometry ───────────────────────────────────────────────────────
    show_logo  = rows >= 30
    logo_h     = len(LOGO_LINES) + 1 if show_logo else 0

    status_h   = 3
    body_y     = logo_h
    body_h     = rows - logo_h - status_h
    status_y   = rows - status_h

    left_w     = min(38, cols // 3)
    right_w    = cols - left_w

    # ── logo ──────────────────────────────────────────────────────────────────
    if show_logo:
        draw_logo(win, 0, 0, cols)

    # ── left: sysinfo ─────────────────────────────────────────────────────────
    draw_sysinfo(win, body_y, 0, body_h, left_w, info)

    # ── right: scripts/output (top) + log (bottom) ───────────────────────────
    right_x = left_w
    log_h   = max(5, min(10, body_h // 4))
    main_h  = body_h - log_h

    if S.mode in ("running", "output"):
        draw_output(win, body_y, right_x, main_h, right_w)
    else:
        draw_scripts(win, body_y, right_x, main_h, right_w)

    draw_log(win, body_y + main_h, right_x, log_h, right_w)

    # ── status bar ────────────────────────────────────────────────────────────
    draw_statusbar(win, status_y, 0, cols, cols, rows)

    win.noutrefresh()
    curses.doupdate()

# ── script runner ─────────────────────────────────────────────────────────────
def run_script(idx):
    name, cmd, _ = SCRIPTS[idx]
    S.script_name = name
    S.output      = []
    S.exit_code   = None
    S.mode        = "running"
    S.run_count[idx] += 1
    log(f"▶ '{name}'", C_GREEN)
    try:
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            with S.lock:
                S.output.append(line.rstrip())
        proc.wait()
        S.exit_code = proc.returncode
        ok = proc.returncode == 0
        log(f"{'✔' if ok else '✘'} '{name}' exit:{proc.returncode}",
            C_GREEN if ok else C_RED)
    except Exception as e:
        S.output.append(f"ERROR: {e}")
        S.exit_code = -1
        log(f"✘ error: {e}", C_RED)
    S.mode = "output"

# ── main curses loop ──────────────────────────────────────────────────────────
def main(stdscr):
    curses.curs_set(0)
    stdscr.nodelay(True)
    stdscr.keypad(True)
    stdscr.timeout(120)           # ms — controls refresh rate
    init_colors()

    log("◈ Dashboard started", C_CYAN)
    log("  ↑↓ navigate · ENTER launch · Q quit", C_DIM)

    info = get_info()
    last_info = time.time()

    while True:
        # refresh system info every 1 s
        now = time.time()
        if now - last_info >= 1.0:
            info = get_info()
            last_info = now

        # ── render ────────────────────────────────────────────────────────────
        render(stdscr, info)

        # ── input ─────────────────────────────────────────────────────────────
        try:
            key = stdscr.getch()
        except curses.error:
            key = -1

        if key == curses.KEY_RESIZE:
            stdscr.clear()
            continue

        if S.mode == "menu":
            if key in (curses.KEY_UP, ord('k'), ord('K')):
                S.selected = (S.selected - 1) % len(SCRIPTS)
            elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
                S.selected = (S.selected + 1) % len(SCRIPTS)
            elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER, ord(' ')):
                if not any(t.name == "runner" for t in threading.enumerate()):
                    threading.Thread(target=run_script, args=(S.selected,),
                                     daemon=True, name="runner").start()
            elif key in (ord('q'), ord('Q'), 3):
                break

        elif S.mode == "output":
            if key in (27, ord('q'), ord('Q'), 3):
                S.mode = "menu"
                S.output = []
                S.script_name = None

        # running: no keys (just wait)

if __name__ == "__main__":
    if sys.platform == "win32":
        print("⚠  Run inside WSL on Windows.")
        sys.exit(1)
    try:
        curses.wrapper(main)
    except KeyboardInterrupt:
        pass
    print("\n\033[1;36m  ◈ Goodbye!\033[0m\n")
