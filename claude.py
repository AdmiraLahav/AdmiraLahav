#!/usr/bin/env python3
"""
Launch Control Dashboard
Dependencies: pip install rich psutil
"""

import os, sys, time, threading, subprocess, datetime, socket, platform, curses, shutil

for pkg in ("rich", "psutil"):
    try:
        __import__(pkg)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", pkg, "-q"])

import psutil
from rich.console import Console
from rich.layout import Layout
from rich.panel import Panel
from rich.table import Table
from rich.text import Text
from rich.live import Live
from rich.align import Align
from rich import box

# ── MIN TERMINAL SIZE ─────────────────────────────────────────────────────────
MIN_COLS = 90
MIN_ROWS = 28

# ── scripts ───────────────────────────────────────────────────────────────────
SCRIPTS = [
    ("sysinfo",    "uname -a && uptime",                                            "System info + uptime"),
    ("disk usage", "df -h /",                                                       "Disk usage report"),
    ("processes",  "ps aux --sort=-%cpu | head -15",                                "Top CPU processes"),
    ("network",    "ip route 2>/dev/null || netstat -rn 2>/dev/null || echo N/A",   "Routing table"),
    ("temp files", "find /tmp -maxdepth 1 -type f | wc -l && echo 'temp files'",    "Count /tmp files"),
    ("ping test",  "ping -c 4 8.8.8.8 2>/dev/null || echo 'ping unavailable'",      "Ping Google DNS"),
    ("env vars",   "printenv | sort | head -25",                                    "Environment variables"),
    ("open ports", "ss -tlnp 2>/dev/null || netstat -tlnp 2>/dev/null || echo N/A", "Listening ports"),
]

ASCII_LOGO_FULL = """\
██╗      █████╗ ██╗   ██╗███╗   ██╗ ██████╗██╗  ██╗
██║     ██╔══██╗██║   ██║████╗  ██║██╔════╝██║  ██║
██║     ███████║██║   ██║██╔██╗ ██║██║     ███████║
██║     ██╔══██║██║   ██║██║╚██╗██║██║     ██╔══██║
███████╗██║  ██║╚██████╔╝██║ ╚████║╚██████╗██║  ██║
╚══════╝╚═╝  ╚═╝ ╚═════╝ ╚═╝  ╚═══╝ ╚═════╝╚═╝  ╚═╝
  C O N T R O L   ·   D A S H B O A R D   v 1 . 0"""

ASCII_LOGO_SMALL = """\
╔═══════════════════════════════╗
║  LAUNCH CONTROL DASHBOARD     ║
║  ·  v1.0  ·  Script Runner ·  ║
╚═══════════════════════════════╝"""

# ── state ─────────────────────────────────────────────────────────────────────
class State:
    def __init__(self):
        self.selected     = 0
        self.mode         = "menu"
        self.log_lines    = []
        self.output_lines = []
        self.run_count    = [0] * len(SCRIPTS)
        self.running_name = None
        self.exit_code    = None
        self.start_time   = datetime.datetime.now()
        self.lock         = threading.Lock()

S = State()

def log(msg, style="white"):
    ts = datetime.datetime.now().strftime("%H:%M:%S")
    with S.lock:
        S.log_lines.append((ts, msg, style))
        if len(S.log_lines) > 200:
            S.log_lines.pop(0)

def fmt_bytes(n):
    for u in ("B","KB","MB","GB","TB"):
        if n < 1024: return f"{n:.1f}{u}"
        n /= 1024
    return f"{n:.1f}PB"

def bar_color(p):
    return "bright_green" if p < 50 else "yellow" if p < 75 else "bright_red"

def term_size():
    s = shutil.get_terminal_size(fallback=(80, 24))
    return s.columns, s.lines

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
        temp  = next(
            (e.current for entries in temps.values() for e in entries if e.current > 0), None)
    except Exception:
        temp = None
    return dict(
        cpu_pct=cpu, cpu_count=psutil.cpu_count(logical=True),
        mem_used=mem.used, mem_total=mem.total, mem_pct=mem.percent,
        disk_used=disk.used, disk_total=disk.total, disk_pct=disk.percent,
        net_sent=net.bytes_sent, net_recv=net.bytes_recv,
        uptime=up, temp_c=temp,
        hostname=socket.gethostname(),
        user=os.environ.get("USER", os.environ.get("USERNAME","?")),
        os_str=platform.system()+" "+platform.release(),
        arch=platform.machine(),
        python=platform.python_version(),
        shell=os.environ.get("SHELL","?"),
    )

# ── too-small warning screen ──────────────────────────────────────────────────
def build_too_small(cols, rows):
    t = Text(justify="center")
    t.append("\n\n")
    t.append("  ⚠  TERMINAL TOO SMALL  ⚠\n\n", style="bold bright_red")
    t.append(f"  Current:  {cols} × {rows}\n",  style="yellow")
    t.append(f"  Required: {MIN_COLS} × {MIN_ROWS}\n\n", style="bright_white")
    t.append("  Resize your terminal window\n",  style="dim")
    t.append("  and the dashboard will appear.\n\n", style="dim")
    t.append("  Q  →  quit", style="dim italic")
    return Panel(Align.center(t, vertical="middle"),
                 border_style="bright_red", box=box.DOUBLE_EDGE,
                 title="[bold bright_red]LAUNCH CONTROL[/]")

# ── panels ────────────────────────────────────────────────────────────────────
def panel_logo(cols):
    logo = ASCII_LOGO_FULL if cols >= 120 else ASCII_LOGO_SMALL
    t = Text(justify="center")
    colors = ["bright_cyan","cyan","bright_blue","blue","bright_magenta","magenta","bright_cyan"]
    for i, line in enumerate(logo.split("\n")):
        t.append(line + "\n", style=f"bold {colors[i % len(colors)]}")
    return Panel(Align.center(t), border_style="bright_blue", box=box.DOUBLE_EDGE, padding=(0,1))

def pct_bar(pct, w=14):
    filled = int(w * pct / 100)
    t = Text()
    t.append("█" * filled,       style=bar_color(pct))
    t.append("░" * (w - filled), style="grey30")
    t.append(f" {pct:5.1f}%",    style=bar_color(pct))
    return t

def panel_sysinfo(info, compact=False):
    now = datetime.datetime.now().strftime("%H:%M:%S")
    g = Table.grid(padding=(0,1))
    g.add_column(style="bright_cyan bold", min_width=7)
    g.add_column(min_width=22)

    rows = [
        ("HOST",   Text(info["hostname"], style="bold white")),
        ("USER",   Text(info["user"],     style="bright_green")),
        ("OS",     Text(info["os_str"],   style="dim white")),
        ("UPTIME", Text(info["uptime"],   style="bright_white")),
        ("TIME",   Text(now,              style="bright_cyan bold")),
        ("",       Text("")),
        (f"CPU×{info['cpu_count']}", pct_bar(info["cpu_pct"])),
        ("RAM",    pct_bar(info["mem_pct"])),
        ("DISK",   pct_bar(info["disk_pct"])),
    ]
    if not compact:
        rows += [
            ("",       Text(f"{fmt_bytes(info['mem_used'])} / {fmt_bytes(info['mem_total'])}", style="dim")),
            ("",       Text(f"{fmt_bytes(info['disk_used'])} / {fmt_bytes(info['disk_total'])}", style="dim")),
            ("",       Text("")),
            ("↑ NET",  Text(fmt_bytes(info["net_sent"]), style="bright_green")),
            ("↓ NET",  Text(fmt_bytes(info["net_recv"]), style="bright_blue")),
        ]
        if info["temp_c"]:
            c = "red" if info["temp_c"] > 80 else "yellow" if info["temp_c"] > 60 else "green"
            rows.append(("TEMP", Text(f"{info['temp_c']:.1f}°C", style=f"bold {c}")))

    for k, v in rows:
        g.add_row(k, v)
    return Panel(g, title="[bold bright_cyan]◈ SYSTEM[/]", border_style="bright_blue", box=box.ROUNDED)

def panel_scripts(compact=False):
    tbl = Table(box=box.SIMPLE_HEAD, show_header=True, header_style="bold bright_cyan",
                expand=True, padding=(0,1))
    tbl.add_column("#",      style="dim",          width=3,  justify="right")
    tbl.add_column("SCRIPT", style="bold white",   min_width=12)
    if not compact:
        tbl.add_column("DESC",   style="dim white",  min_width=18)
    tbl.add_column("RUNS",   style="bright_yellow",width=5,  justify="right")

    for i, (name, _, desc) in enumerate(SCRIPTS):
        sel = (i == S.selected)
        prefix = "▶ " if sel else "  "
        row = [str(i+1), prefix+name]
        if not compact:
            row.append(desc)
        row.append(str(S.run_count[i]) if S.run_count[i] else "—")
        tbl.add_row(*row, style="on grey19" if sel else "")

    hint = Text("\n  ↑↓ navigate  ENTER launch  Q quit", style="dim italic")
    wrap = Table.grid(); wrap.add_row(tbl); wrap.add_row(hint)
    return Panel(wrap, title="[bold bright_magenta]◈ SCRIPTS[/]",
                 border_style="bright_blue", box=box.ROUNDED)

def panel_output():
    t = Text()
    for line in S.output_lines[-30:]:
        t.append(line + "\n", style="bright_green")
    if S.mode == "output" and S.exit_code is not None:
        c = "bright_green" if S.exit_code == 0 else "bright_red"
        t.append(f"\n  ── exit code: {S.exit_code} ──\n", style=c)
    t.append("\n  ESC / Q → back to menu", style="dim italic")
    ec_tag = ""
    if S.exit_code is not None:
        c = "bright_green" if S.exit_code == 0 else "bright_red"
        ec_tag = f"  [{c}]exit:{S.exit_code}[/{c}]"
    status = "[blink bright_yellow]● RUNNING[/]" if S.mode == "running" else "[bright_green]● DONE[/]"
    label  = S.running_name or "output"
    return Panel(t, title=f"[bold]{status}  {label.upper()}{ec_tag}[/]",
                 border_style="bright_green", box=box.ROUNDED)

def panel_log(compact=False):
    t = Text()
    limit = 6 if compact else 12
    for ts, msg, style in S.log_lines[-limit:]:
        t.append(f"[{ts}] ", style="dim")
        t.append(msg + "\n", style=style)
    return Panel(t, title="[bold bright_yellow]◈ LOG[/]",
                 border_style="blue", box=box.ROUNDED)

def panel_status():
    now   = datetime.datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    sess  = str(datetime.datetime.now() - S.start_time).split(".")[0]
    total = sum(S.run_count)
    mc    = {"menu":"bright_cyan","running":"bright_green","output":"bright_magenta"}.get(S.mode,"white")
    cols, rows = term_size()
    bar   = Table.grid(expand=True)
    bar.add_column(ratio=3); bar.add_column(ratio=2, justify="center"); bar.add_column(ratio=3, justify="right")
    bar.add_row(
        Text(f"  ◈ [{mc}]{S.mode.upper()}[/{mc}]  runs:{total}  term:{cols}×{rows}", style="bold"),
        Text(f"UP {sess}", style="dim"),
        Text(f"{now}  ", style="dim cyan"),
    )
    return Panel(bar, border_style="blue", box=box.HORIZONTALS, padding=(0,0))

# ── adaptive layout builder ───────────────────────────────────────────────────
def build_layout(info):
    cols, rows = term_size()

    # ── too small: show warning only ──────────────────────────────────────────
    if cols < MIN_COLS or rows < MIN_ROWS:
        return build_too_small(cols, rows)

    compact_sys     = cols < 130          # hide mem/disk detail + net in sysinfo
    compact_scripts = cols < 110          # hide description column
    compact_log     = rows < 40           # fewer log lines
    show_logo       = rows >= 36          # drop logo on short terminals

    L = Layout()

    sections = []
    if show_logo:
        sections.append(Layout(name="logo", size=6))
    sections.append(Layout(name="body",   ratio=1))
    sections.append(Layout(name="status", size=3))
    L.split_column(*sections)

    L["body"].split_row(Layout(name="left", ratio=2), Layout(name="right", ratio=3))
    L["right"].split_column(Layout(name="scripts", ratio=2), Layout(name="log", ratio=1))

    if show_logo:
        L["logo"].update(panel_logo(cols))

    L["left"].update(panel_sysinfo(info, compact=compact_sys))
    L["status"].update(panel_status())
    L["log"].update(panel_log(compact=compact_log))

    if S.mode in ("running", "output"):
        L["scripts"].update(panel_output())
    else:
        L["scripts"].update(panel_scripts(compact=compact_scripts))

    return L

# ── script runner ─────────────────────────────────────────────────────────────
def run_script(idx):
    name, cmd, _ = SCRIPTS[idx]
    S.running_name = name
    S.output_lines = []
    S.exit_code    = None
    S.mode         = "running"
    S.run_count[idx] += 1
    log(f"▶ '{name}' started", "bright_green")
    try:
        proc = subprocess.Popen(cmd, shell=True,
                                stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        for line in proc.stdout:
            with S.lock:
                S.output_lines.append(line.rstrip())
        proc.wait()
        S.exit_code = proc.returncode
        ok = proc.returncode == 0
        log(f"{'✔' if ok else '✘'} '{name}' exit:{proc.returncode}",
            "bright_green" if ok else "bright_red")
    except Exception as e:
        S.output_lines.append(f"ERROR: {e}")
        S.exit_code = -1
        log(f"✘ '{name}' error: {e}", "red")
    S.mode = "output"

# ── curses key reader ─────────────────────────────────────────────────────────
def _key_loop(stdscr):
    stdscr.nodelay(True)
    stdscr.keypad(True)
    while True:
        try:
            key = stdscr.getch()
        except Exception:
            time.sleep(0.05)
            continue
        if key == -1:
            time.sleep(0.04)
            continue

        if S.mode == "menu":
            if   key in (curses.KEY_UP,   ord('k'), ord('K')):
                S.selected = (S.selected - 1) % len(SCRIPTS)
            elif key in (curses.KEY_DOWN, ord('j'), ord('J')):
                S.selected = (S.selected + 1) % len(SCRIPTS)
            elif key in (ord('\n'), ord('\r'), curses.KEY_ENTER, ord(' ')):
                if not any(t.name == "runner" for t in threading.enumerate()):
                    threading.Thread(target=run_script, args=(S.selected,),
                                     daemon=True, name="runner").start()
            elif key in (ord('q'), ord('Q'), 3):
                os._exit(0)

        elif S.mode == "output":
            if key in (27, ord('q'), ord('Q'), 3):
                S.mode = "menu"
                S.output_lines = []
                S.running_name = None

def start_key_reader():
    curses.wrapper(_key_loop)

# ── main ──────────────────────────────────────────────────────────────────────
def main():
    log("◈ Dashboard started", "bright_cyan")
    log("  ↑↓ navigate · ENTER launch · Q quit", "dim")

    threading.Thread(target=start_key_reader, daemon=True).start()
    time.sleep(0.15)

    console = Console()
    info = get_info()
    with Live(build_layout(info), refresh_per_second=8, screen=True, console=console) as live:
        while True:
            info = get_info()
            live.update(build_layout(info))
            time.sleep(0.12)

if __name__ == "__main__":
    if sys.platform == "win32":
        print("⚠  Windows detected – run inside WSL for best results.")
        sys.exit(1)
    try:
        main()
    except KeyboardInterrupt:
        pass
    finally:
        print("\n\033[1;36m  ◈ Dashboard closed. Goodbye!\033[0m\n")
