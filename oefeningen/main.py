# === main.py — Levelmenu (OK=volgende, CANCEL=start) ===
import uos, time, sys
from arduino_alvik import ArduinoAlvik

# --- Robot starten ---
alvik = ArduinoAlvik()
alvik.begin()  # motoren, leds, sensoren klaar

# --- Terminalkleuren (alleen voor weergave) ---
CLR_RESET  = "\x1b[0m"
CLR_GREEN  = "\x1b[32m"
CLR_ORANGE = "\x1b[38;5;208m"
CLR_RED    = "\x1b[31m"
CLR_GRAY   = "\x1b[90m"

def color_for_level(name: str) -> str:
    """Kleur per levelnaam (alleen terminal)."""
    n = name.lower()
    if "level_1" in n: return CLR_GREEN
    if "level_2" in n: return CLR_ORANGE
    if "level_3" in n: return CLR_RED
    return ""

# --- LEDs ---
def _set_led_rgb(r, g, b):
    """Zet beide leds; probeer RGB, anders 0/1 fallback."""
    try:
        alvik.left_led.set_color(r, g, b)
        alvik.right_led.set_color(r, g, b)
    except:
        try:
            alvik.left_led.set_color(1 if r else 0, 1 if g else 0, 1 if b else 0)
            alvik.right_led.set_color(1 if r else 0, 1 if g else 0, 1 if b else 0)
        except:
            pass

def led_idle():  _set_led_rgb(0, 0, 1)  # blauw = menu
def led_run():   _set_led_rgb(0, 1, 0)  # groen = level draait
def led_error(): _set_led_rgb(1, 0, 0)  # rood  = fout

def led_menu_for_level(name: str):
    """Menu-LED: L1 groen, L2 oranje/geel, L3 rood, anders blauw."""
    n = name.lower()
    if   "level_1" in n: _set_led_rgb(0, 1, 0)
    elif "level_2" in n:
        try: _set_led_rgb(1.0, 0.5, 0.0)   # oranje (floats)
        except: _set_led_rgb(1, 1, 0)      # geel (fallback)
    elif "level_3" in n: _set_led_rgb(1, 0, 0)
    else:                led_idle()

# --- Touchknoppen ---
def ok_now():     return bool(alvik.get_touch_ok())
def cancel_now(): return bool(alvik.get_touch_cancel())

# --- Levels zoeken ---
def get_levels():
    """Alle 'level_*.py' (excl. main/boot) in alfabetische volgorde."""
    levels = []
    for f in uos.listdir():
        if f.startswith("level_") and f.endswith(".py") and f not in ("main.py", "boot.py"):
            levels.append(f)
    levels.sort()
    return levels

# --- Menu tonen ---
def show_menu(levels, idx):
    """Toon selectie in kleur, rest grijs (venster tot 7 regels)."""
    print("\n=== Kies een level (OK=volgende, CANCEL=start) ===")
    print("  [L1=groen, L2=oranje, L3=rood]")

    WINDOW = 7
    start = 0
    if len(levels) > WINDOW:
        half = WINDOW // 2
        start = max(0, min(idx - half, len(levels) - WINDOW))
    end = min(len(levels), start + WINDOW)

    for i in range(start, end):
        prefix = "> " if i == idx else "  "
        name = levels[i]
        if i == idx:
            c = color_for_level(name)
            line = (c + prefix + name + CLR_RESET) if c else (prefix + name)
        else:
            line = CLR_GRAY + prefix + name + CLR_RESET
        print(line)

    if len(levels) > WINDOW:
        print(f"  ({idx+1}/{len(levels)})")

# --- Level uitvoeren ---
def run_level(filename):
    """Lees en voer levelbestand uit; altijd remmen bij einde."""
    print("\n> Start:", filename)
    led_run()
    try:
        with open(filename, "r") as f:
            code = f.read()
        exec(code, {"__name__": "__main__"})
    except KeyboardInterrupt:
        print("[!] KeyboardInterrupt - terug naar menu")
    except Exception as e:
        led_error()
        print("[!] Fout:", e)
    finally:
        try: alvik.brake()
        except: pass
    print("\n[OK] Level beëindigd - terug naar menu\n")
    led_idle()

# --- Level kiezen (edge-detectie) ---
def choose_level(levels):
    """OK = volgende; CANCEL = start. Reageer 1x per tik (edge)."""
    i = 0
    last_shown = -1

    # eerst vingers los (geen spookinput)
    while ok_now() or cancel_now():
        time.sleep_ms(20)

    led_menu_for_level(levels[i])
    prev_ok = ok_now()
    prev_cancel = cancel_now()

    while True:
        if i != last_shown:
            show_menu(levels, i)
            last_shown = i

        cur_ok = ok_now()
        cur_cancel = cancel_now()

        if cur_ok and not prev_ok:            # volgende level
            i = (i + 1) % len(levels)
            led_menu_for_level(levels[i])
            show_menu(levels, i)

        if cur_cancel and not prev_cancel:     # start huidige
            return levels[i]

        prev_ok, prev_cancel = cur_ok, cur_cancel
        time.sleep_ms(25)  # simpele debounce

# --- Hoofdprogramma ---
def main():
    levels = get_levels()
    if not levels:
        led_error()
        print("[!] Geen level_*.py bestanden gevonden.")
        return

    led_idle()
    while True:
        filename = choose_level(levels)
        run_level(filename)
        time.sleep_ms(300)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("Stop.")
        try: alvik.stop()
        except: pass
        sys.exit()
