import gc
import time
import displayio
import picodvi
import board
import busio
import framebufferio
import json
from adafruit_bitmap_font import bitmap_font
from adafruit_display_text.label import Label

displayio.release_displays()

fb = picodvi.Framebuffer(
    400,
    240,
    clk_dp=board.CKP,
    clk_dn=board.CKN,
    red_dp=board.D0P,
    red_dn=board.D0N,
    green_dp=board.D1P,
    green_dn=board.D1N,
    blue_dp=board.D2P,
    blue_dn=board.D2N,
    color_depth=8,
)

display = framebufferio.FramebufferDisplay(fb)
group = displayio.Group()
display.root_group = group

DIGITS_FONT = bitmap_font.load_font("/fonts/digits.bdf")
TEXT_FONT = bitmap_font.load_font("/fonts/chicago.bdf")
COLOR = [
    0x800000,
    0x008000,
    0x808000,
    0x000080,
    0x800080,
    0x008080,
    0xC0C0C0,
    0x808080,
    0xFF0000,
    0x00FF00,
    0xFFFF00,
    0x0000FF,
    0xFF00FF,
    0x00FFFF,
    0xFFFFFF,
    0x000000,
    0x303030,
    0xaf5f87
]

# Configure UART
uart = busio.UART(board.GP4, board.GP5, baudrate=115200, receiver_buffer_size=2048)


def display_text(string, font, c, ax, ay, x, y):
    global group
    label = Label(font, text=string, color=COLOR[c])
    label.anchor_point = (ax, ay)
    label.anchored_position = (x, y)
    # index = len(group)
    group.append(label)
    # print(f"#{index} is {string}")


def display_text_icon(icon_string, string, ic, c, x, y):
    global group
    display_text(icon_string, TEXT_FONT, ic, 0.0, 0.0, x, y)
    display_text(string, TEXT_FONT, c, 0.0, 0.0, x + 20, y)


def display_time(timeString, x, y):
    display_text(timeString, DIGITS_FONT, 2, 0.0, 0.0, x, y)


def display_weather(data, x, y):
    mem = round(gc.mem_free() / 1024)
    display_text_icon("\u0001", f"{data[0]}\u0008", 17, 7, x, y)
    display_text_icon("\u0000", f"{data[1]}\u0006", 12, 7, x, y + 32)
    display_text_icon("\u0003", f"{data[2]}\u0007", 13, 7, x, y + 64)
    display_text_icon("\u0002", f"{data[3]}%", 6, 7, x, y + 96)
    display_text_icon("\u000e", f"{mem}\u000f", 9, 7, x, y + 128)
    display_text_icon("\u000b", "\u000c", 8, 7, x, y + 160)

def display_sl(data, transport, x, y):
    """
    # Titles
    if transport == "train":
        icon = "\u0005"
    elif transport == "bus":
        icon = "\u0004"
    """    
    
    # Departures
    departures = ""
    lines = 1
    if len(data) == 0:
        departures = "No departure data from SL."
        color = 6
    else:
        display_text_icon("\u0005", f"{data[0]}", 5, 7, x, y)
        stringLength = len(data)
        for i in range(2, stringLength):
            if data[i - 1] != data[i]:  # Remove duplicates
                if len(departures) + len(data[i]) > 40 * lines:  # Check if fits in one line, or needs line break
                    lines += 1
                    departures += "\n"
                departures += data[i]
                if i < stringLength - 1:
                    departures += " \u00b7 "
            color = 10
    display_text(departures, TEXT_FONT, color, 0.0, 0.0, x, y + 18)


def clean_up(group_name):
    for _ in range(len(group_name)):
        group_name.pop()
    gc.collect()


# Function to receive data
def receive_data():
    uart.write(b"++\n")
    data = uart.readline()
    if data and data != b'\x00': # ignore the first b'\x00' incoming from UART if server did not send anything
        try:
            return json.loads(data.decode("utf-8"))
        except Exception as e:
            pass
    else:
        print(".")
    return None


def display_data_and_sleep(data):
    clean_up(group)
    display_time(data["T"], 20, 20)                     #0
    display_weather(
        data["W"],
        302,
        25,
    )                                                   #1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12
    display_sl(data["TR1"], "train", 24, 110)           #13, 14, 15
    display_sl(data["TR2"], "train", 24, 170)           #16, 17, 18
    # display_sl(data["B2"], "bus", 8, 180)
    timeout = data["TO"]
    data = ""
    gc.collect()
    time.sleep(timeout)


# Continuous receive, parse, and send confirmation
while True:
    parsed_data = receive_data()
    if parsed_data:
        print(f"<< {parsed_data}")
        display_data_and_sleep(parsed_data)
