import curses
import subprocess
import time

RESET = "\x1b[0m";
green_color = "\x1b[38;5;40m";
blue_color = "\x1b[38;5;12m";
red_color = "\x1b[38;5;196m";
yellow_color = "\x1b[38;5;226m";
program_name = f"[{blue_color}Custom Human Debug{RESET}]";
info = f"[{green_color}INF{RESET}]";
error = f"[{red_color}ERR{RESET}]";
warning = f"[{yellow_color}WRN{RESET}]";

leave_menu = "+----------------+\n|    Quitting    |\n+----------------+"

"                                                           [|||||||||||||>-----]"
discord_bot_path = r"C:\Users\lavhr\OneDrive\Desktop\main.py"

options = ["Run Discord Bot", "Loading Bar", "option 3"]

def draw_menu(stdscr, selected_idx):
    stdscr.clear()
    
    for i, option in enumerate(options):
        if i == selected_idx:
            stdscr.addstr("[")
            stdscr.addstr("*", curses.color_pair(1))  # blue
            stdscr.addstr(f"] {option}\n")
        else:
            stdscr.addstr(f"[ ] {option}\n")
    
    stdscr.refresh()

def DiscordBot():
    subprocess.run(f"python {discord_bot_path}",shell=True)

def LoadingBar(stdscr):
    curses.curs_set(0)  # Hide cursor

    total = 100
    bar_width = 10  # visual width of the bar

    for i in range(total + 1):
        stdscr.clear()

        # Calculate progress
        progress = i / total
        filled = int(bar_width * progress)

        bar = "=" * filled + "-" * (bar_width - filled)

        stdscr.addstr(0, 0, f"{i}% [{bar}] {int(progress*100)}/{total}",curses.color_pair(3))

        stdscr.refresh()
        time.sleep(0.05)

def Print():
    print(1)
def main(stdscr):
    curses.curs_set(0)  # Hide cursor

    curses.start_color()
    curses.use_default_colors()

    curses.init_pair(1, curses.COLOR_BLUE, -1)   # blue text, default background
    curses.init_pair(2, curses.COLOR_GREEN, -1)
    curses.init_pair(3, curses.COLOR_RED, -1)
    curses.init_pair(4, curses.COLOR_YELLOW, -1)

    selected_idx = 0

    while True:
        draw_menu(stdscr, selected_idx)

        key = stdscr.getch()

        if key == curses.KEY_UP:
            selected_idx = (selected_idx - 1) % len(options)

        elif key == curses.KEY_DOWN:
            selected_idx = (selected_idx + 1) % len(options)

        elif key == ord('\n'):  # Enter key
            stdscr.clear()
            stdscr.refresh()
            if selected_idx == 0:
                DiscordBot()
            elif selected_idx == 1:
                LoadingBar(stdscr)
            elif selected_idx == 2:
                Print()
            break

        elif key == 27: #ESC KEY
            stdscr.clear()
            stdscr.addstr(leave_menu)
            stdscr.getch()
            break

curses.wrapper(main)
