"""Render arrivals to a 64x32 image and send it to a display.

The same Pillow image goes to every backend, so what you see in the
preview PNG on your computer is what the LED matrix will show.
"""

import time

from PIL import Image, ImageDraw, ImageFont

WIDTH, HEIGHT = 64, 32
ROW_HEIGHT = HEIGHT // 2
BULLET = 13  # route circle diameter in pixels

ROUTE_COLORS = {
    **dict.fromkeys("123", (238, 53, 46)),
    **dict.fromkeys("456", (0, 147, 60)),
    "7": (185, 51, 173),
    **dict.fromkeys("ACE", (0, 57, 166)),
    **dict.fromkeys("BDFM", (255, 99, 25)),
    "G": (108, 190, 69),
    **dict.fromkeys("JZ", (153, 102, 51)),
    "L": (167, 169, 172),
    **dict.fromkeys("NQRW", (252, 204, 10)),
    "S": (128, 129, 131),
    "SI": (0, 57, 166),
}
DARK_TEXT_ROUTES = set("NQRW")
TEXT_COLOR = (255, 160, 0)  # amber, like the station countdown clocks

FONT = ImageFont.load_default()  # Pillow's built-in font, 10px


def route_label(route_id):
    """Map GTFS route IDs to what's printed on the bullet: 6X -> 6, GS/FS/H -> S."""
    if route_id in ("GS", "FS", "H"):
        return "S"
    if route_id == "SI":
        return route_id
    return route_id.rstrip("X")


def short_destination(name):
    """'Coney Island-Stillwell Av' -> 'Coney Island'."""
    return name.split("-")[0].strip()


def text_width(text):
    """Width of the pixels actually drawn with antialiasing off.

    textlength() measures the smooth outline, which can be narrower.
    """
    bbox = FONT.getmask(text, mode="1").getbbox()
    return bbox[2] if bbox else 0


def fit_text(text, max_width):
    while text and text_width(text) > max_width:
        text = text[:-1]
    return text.rstrip()


def draw_row(draw, y, arrival, now):
    label = route_label(arrival.route)
    color = ROUTE_COLORS.get(label, (128, 128, 128))
    top = y + (ROW_HEIGHT - BULLET) // 2
    draw.ellipse((0, top, BULLET - 1, top + BULLET - 1), fill=color)
    text_color = (0, 0, 0) if label in DARK_TEXT_ROUTES else (255, 255, 255)
    draw.text((BULLET / 2, top + BULLET / 2), label, font=FONT, fill=text_color, anchor="mm")

    minutes = f"{arrival.minutes(now)}m"
    minutes_width = text_width(minutes)
    draw.text((WIDTH - minutes_width, y + ROW_HEIGHT / 2), minutes, font=FONT, fill=TEXT_COLOR, anchor="lm")

    dest_x = BULLET + 2
    dest = fit_text(short_destination(arrival.destination), WIDTH - dest_x - minutes_width - 4)
    draw.text((dest_x, y + ROW_HEIGHT / 2), dest, font=FONT, fill=TEXT_COLOR, anchor="lm")


def render(arrivals, now=None):
    """Draw the next two arrivals, one per row."""
    now = now or time.time()
    image = Image.new("RGB", (WIDTH, HEIGHT))
    draw = ImageDraw.Draw(image)
    draw.fontmode = "1"  # no antialiasing: each LED is either on or off
    if not arrivals:
        draw.text((WIDTH / 2, HEIGHT / 2), "No trains", font=FONT, fill=TEXT_COLOR, anchor="mm")
    for row, arrival in enumerate(arrivals[:2]):
        draw_row(draw, row * ROW_HEIGHT, arrival, now)
    return image


class PreviewDisplay:
    """Writes a scaled-up PNG so you can develop without the hardware."""

    def __init__(self, path="preview.png", scale=10):
        self.path = path
        self.scale = scale

    def show(self, image):
        image.resize((WIDTH * self.scale, HEIGHT * self.scale), Image.NEAREST).save(self.path)


class MatrixDisplay:
    """Adafruit 64x32 panel driven by the RGB Matrix Bonnet on a Raspberry Pi."""

    def __init__(self, brightness=60, gpio_slowdown=4):
        from rgbmatrix import RGBMatrix, RGBMatrixOptions  # only installed on the Pi

        options = RGBMatrixOptions()
        options.rows = HEIGHT
        options.cols = WIDTH
        options.hardware_mapping = "adafruit-hat"  # "adafruit-hat-pwm" if you did the GPIO4-18 solder mod
        options.brightness = brightness
        options.gpio_slowdown = gpio_slowdown  # raise if the image flickers or glitches
        self.matrix = RGBMatrix(options=options)
        self.canvas = self.matrix.CreateFrameCanvas()

    def show(self, image):
        self.canvas.SetImage(image)
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
