# === main.py — Levelmenu met ArduinoAlvik touch knoppen (OK=volgende, CANCEL=start) ===
import uos, time, sys
from arduino_alvik import ArduinoAlvik

# --- Robot starten ---
alvik = ArduinoAlvik()
alvik.begin()

# --- Kleuren voor terminal ---
CLR_RESET  = "\x1b[0m"
CLR_GREEN  = "\x1b[32m"
CLR_ORANGE = "\x1b[38;5;208m"   # 256-kleuren oranje
CLR_RED    = "\x1b[31m"
CLR_GRAY   = "\x1b[90m"         # grijs (bright black)

def color_for_level(name: str) -> str:
   """
    Kies een terminalkleur op basis van de bestandsnaam.
    Handig voor snel zien welk level geselecteerd is in de REPL/seriële monitor.
    """
    n = name.lower()
    if "level_1" in n: return CLR_GREEN
    if "level_2" in n: return CLR_ORANGE
    if "level_3" in n: return CLR_RED
    return ""  # geen kleur voor andere namen

# --- LED helpers ---
def _set_led_rgb(r, g, b):
    """Probeert de LEDs te zetten; accepteert ints (0-255) of floats (0..1)."""
    try:
        alvik.left_led.set_color(r, g, b)
        alvik.right_led.set_color(r, g, b)
    except:
        # fallback naar binaire waarden
        try:
            alvik.left_led.set_color(1 if r else 0, 1 if g else 0, 1 if b else 0)
            alvik.right_led.set_color(1 if r else 0, 1 if g else 0, 1 if b else 0)
        except:
            pass

def led_idle():
    # neutraal blauw in menu-idle
    _set_led_rgb(0, 0, 1)

def led_run():
    _set_led_rgb(0, 1, 0)

def led_error():
    _set_led_rgb(1, 0, 0)

def led_menu_for_level(name: str):
    """Kleur LEDs per level in het MENU."""
    n = name.lower()
    if "level_1" in n:
        _set_led_rgb(0, 1, 0)          # groen
    elif "level_2" in n:
        try:
            _set_led_rgb(1.0, 0.5, 0.0) # oranje (als floats werken)
        except:
            _set_led_rgb(1, 1, 0)       # fallback: geel
    elif "level_3" in n:
        _set_led_rgb(1, 0, 0)          # rood
    else:
        led_idle()

# --- Touchknoppen ---
def ok_now():
    return bool(alvik.get_touch_ok())

def cancel_now():
    return bool(alvik.get_touch_cancel())

# --- Levels ophalen ---
def get_levels():
    levels = []
    for f in uos.listdir():
        if f.startswith("level_") and f.endswith(".py") and f not in ("main.py", "boot.py"):
            levels.append(f)
    levels.sort()
    return levels

# --- Menu tonen (gekleurde selectie, grijze rest) ---
def show_menu(levels, idx):
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
        try:
            alvik.brake()
        except:
            pass
    print("\n[OK] Level beeindigd - terug naar menu\n")
    led_idle()

# --- Level kiezen met edge-detectie + LED feedback in menu ---
def choose_level(levels):
    i = 0
    last_shown = -1

    # voorkom auto-actie als vingers nog op touch zitten
    while ok_now() or cancel_now():
        time.sleep_ms(20)

    # Eerst scherm + LED voor beginselectie
    led_menu_for_level(levels[i])

    # Edge-detectie
    prev_ok = ok_now()
    prev_cancel = cancel_now()

    while True:
        if i != last_shown:
            show_menu(levels, i)
            last_shown = i

        cur_ok = ok_now()
        cur_cancel = cancel_now()

        # OK edge -> volgende (bladeren)
        if cur_ok and not prev_ok:
            i = (i + 1) % len(levels)
            led_menu_for_level(levels[i])  # LED kleur live met selectie
            show_menu(levels, i)

        # CANCEL edge -> START huidige
        if cur_cancel and not prev_cancel:
            return levels[i]

        prev_ok = cur_ok
        prev_cancel = cur_cancel
        time.sleep_ms(25)

# --- Hoofdprogramma ---
def main():
    levels = get_levels()
    if not levels:
        led_error()
        print("[!] Geen level_*.py bestanden gevonden in root van het device.")
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
        try:
            alvik.stop()
        except:
            pass
        sys.exit()
