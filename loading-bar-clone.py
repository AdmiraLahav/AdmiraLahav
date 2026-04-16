import curses
import time
from pathlib import Path

LOGO = """ --.          :-:     :+###+.       @@@@@@@@        *@@@          
=@@@.        %@@@   +@@@@@@@@@:         :@@@        *@@@          
 @@@@        @@@.  @@@@    -@@@:        :@@@        *@@@          
  @@@=      @@@@  +@@@      %@@@        :@@@        *@@@     @@@@.
  %@@@     -@@@   @@@=    @@@@@@-       :@@@        *@@@   @@@@%  
   @@@%    @@@-   @@@  +@@@@@@@@*       :@@@        *@@@ #@@@@    
   -@@@   #@@@    @@@%@@@@=  @@@*       :@@@        *@@@@@@@      
    @@@@  @@@     @@@@@@     @@@-       :@@@        *@@@@@@@      
     @@@-@@@*     #@@@      :@@@        :@@@        *@@@ #@@@+    
     *@@@@@@       @@@@    -@@@-        :@@@        *@@@  .@@@@:  
      @@@@@.        @@@@@@@@@@:     @@@@@@@@@@@@:   *@@@    +@@@@ 
      .***-           #@@@@%:       +***********    .**:      ***-""".strip("\n").splitlines()

BAR_WIDTH = 50
ANIMATION_DELAY = 0.01

RESET = "\x1b[0m"
green_color = "\x1b[38;5;40m"
blue_color = "\x1b[38;5;12m"
red_color = "\x1b[38;5;196m"
yellow_color = "\x1b[38;5;226m"
program_name = f"[{blue_color}Custom Human Debug{RESET}]"
info = f"[{green_color}INF{RESET}]"
error = f"[{red_color}ERR{RESET}]"
warning = f"[{yellow_color}WRN{RESET}]"

current_percent = 0
process_history = []

logo_width = max(len(line) for line in LOGO)
logo_height = len(LOGO)

start_x = 30
start_y = 1

def SafeAddString(screen, y, x, text):
    height, width = screen.getmaxyx()
    if 0 <= y < height and 0 <= x < width:
        screen.addstr(y, x, text[: max(0, width - x - 1)])


def DrawLogoText(screen, start_y=1, start_x=2):
    height, _ = screen.getmaxyx()
    for i, line in enumerate(LOGO):
        y = start_y + i
        if y >= height:
            break
        SafeAddString(screen, y, start_x, line)
    return start_y + len(LOGO) + 1


def DrawFullLogo(screen):
    draw_logo_lowest = DrawLogoText(screen,start_y,start_x)
    hight, width = screen.getmaxyx()
    for i in range(logo_height):
        SafeAddString(screen, start_y + i, start_x - 2, "║")
    for i in range(logo_height):
        SafeAddString(screen, start_y + i, start_x + logo_width + 1, "║")

    SafeAddString(screen,draw_logo_lowest - 1,start_x - 2,"╚")#bottom left
    SafeAddString(screen,draw_logo_lowest - 1,start_x + logo_width + 1,"╝")#bottom right
    SafeAddString(screen,0,start_x - 2,"╔")#top left
    SafeAddString(screen,0,start_x + logo_width + 1,"╗")#top right

    SafeAddString(screen,draw_logo_lowest - 1,start_x - 1,"═"*(logo_width+2))#underline
    SafeAddString(screen,0,start_x - 1,"═"*(logo_width+2))#upperline
    return draw_logo_lowest


def DrawProgressBar(screen, percent, top_y):
    filled = int((percent / 100) * BAR_WIDTH)
    empty = BAR_WIDTH - filled
    bar = "[" + "█" * filled + "░" * empty + "]"

    SafeAddString(screen, top_y, 2, "Progress")
    SafeAddString(screen, top_y + 1, 2, f"{bar} {percent:3d}%")


def AddLog(level, message):
    level = level.upper()
    process_history.append((level, message))


def DrawProcessHistory(screen, start_y):
    height, width = screen.getmaxyx()
    available_lines = max(0, height - start_y - 1)
    visible = process_history[-available_lines:][::-1]

    for i in range(available_lines):
        y = start_y + i
        if y >= height:
            break
        SafeAddString(screen, y, 0, " " * (width - 1))

    for i, entry in enumerate(visible):
        y = start_y + i
        if y >= height:
            break

        level, message = entry

        if level == "INF":
            prefix = "[INF]"
            color = curses.color_pair(1)
        elif level == "WRN":
            prefix = "[WRN]"
            color = curses.color_pair(2)
        elif level == "ERR":
            prefix = "[ERR]"
            color = curses.color_pair(3)
        else:
            prefix = "[???]"
            color = curses.A_NORMAL

        screen.addstr(y, 2, prefix, color)
        SafeAddString(screen, y, 8, f" {message}")


def RedrawScreen(screen):
    screen.clear()
    next_y = DrawFullLogo(screen)
    DrawProgressBar(screen, current_percent, next_y)
    DrawProcessHistory(screen, next_y + 3) # one empty line below the bar, and then draw logs
    screen.refresh()


def UpdateBar(screen, percent, level=None, message=None):
    global current_percent

    percent = max(0, min(100, percent))

    if level and message:
        AddLog(level, message)

    while current_percent < percent:
        current_percent += 1
        RedrawScreen(screen)
        time.sleep(ANIMATION_DELAY)

    while current_percent > percent:
        current_percent -= 1
        RedrawScreen(screen)
        time.sleep(ANIMATION_DELAY)


def MainProgramStart(screen):
    curses.start_color()
    curses.use_default_colors()
    curses.init_pair(1, curses.COLOR_BLUE, -1)   # INF
    curses.init_pair(2, curses.COLOR_YELLOW, -1)  # WRN
    curses.init_pair(3, curses.COLOR_RED, -1)     # ERR
    curses.curs_set(0)
    RedrawScreen(screen)
    AddLog("INF","Finished load")
    # Examples:
    CheckScripts(screen)
    UpdateBar(screen, 10, "INF", "Started")
    time.sleep(1)
    UpdateBar(screen, 100, "INF", "Finished")

    #height, _ = screen.getmaxyx()
    #SafeAddString(screen, height - 1, 2, "Complete. Press any key to exit.")
    screen.refresh()
    #screen.getch()

    ClearScreen(screen)
    MainDashboardPage(screen)


    while True: # quit only on keypress
        key = screen.getch() 
        if key == ord('q'):
            break


def ClearScreen(screen):
    screen.clear()
    screen.refresh()

def MainDashboardPage(screen):
    DrawFullLogo(screen)
    screen.refresh()

def CheckScripts(screen): #Check if a file exists
    file_path = Path("TEMP.FILE")

    if file_path.is_file():
        UpdateBar(screen,30,"INF","File exists")
    else:
        UpdateBar(screen,0,"ERR","File does not exist")

if __name__ == "__main__":
    curses.wrapper(MainProgramStart)
