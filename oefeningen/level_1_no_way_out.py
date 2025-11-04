# ==== Level 1 - No Way Out ====
# Zoekt een opening, rijdt eruit, stopt en knippert.
_time = __import__('time')
sleep_ms   = _time.sleep_ms
ticks_ms   = _time.ticks_ms
ticks_diff = _time.ticks_diff

# --- board ---
try:
    alvik
except NameError:
    ArduinoAlvik = __import__('arduino_alvik').ArduinoAlvik
    alvik = ArduinoAlvik(); alvik.begin()

# ===================== Tunables =====================
OPEN = 40       # cm: wat als 'opening' telt
SAFE = 25       # cm: te dicht -> terug & draai
EXIT = 110      # cm: buiten
SCAN = 16       # draaisnelheid tijdens scannen
SPEED = 22      # rijsnelheid vooruit
OK_OPEN = 3     # stabiele open metingen
OK_EXIT = 3     # stabiele 'buiten' metingen
SAMPLE_DT_MS = 20
# ====================================================

# ---------------- LEDs ----------------
def _led(rgb):
    try:
        r, g, b = rgb
        alvik.left_led.set_color(r, g, b)
        alvik.right_led.set_color(r, g, b)
    except:
        pass

def led_wait():   _led((0, 0, 1))   # blauw
def led_go():     _led((0, 1, 0))   # groen
def led_pause():  _led((1, 1, 0))   # geel
def led_done():   _led((1, 1, 1))   # wit
def led_warn():   _led((1, 0, 0))   # rood

def blink_done(n=6, on=150, off=150):
    for _ in range(n):
        led_done(); sleep_ms(on)
        _led((0, 0, 0)); sleep_ms(off)

# -------------- Buttons --------------
def ok_pressed():
    try:
        return bool(alvik.get_touch_ok())
    except:
        return False

def cancel_pressed():
    try:
        return bool(alvik.get_touch_cancel())
    except:
        return False

def wait_ok():
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        sleep_ms(50)
    sleep_ms(120)  # debounce

def pause_until_ok():
    # Pauze: stop motoren, gele leds; hervat met OK
    stop_now(); led_pause()
    while not ok_pressed():
        sleep_ms(40)
    sleep_ms(120)
    led_go()

# -------------- Motion ---------------
def stop_now():
    try:
        alvik.set_wheels_speed(0, 0); alvik.brake()
    except:
        pass

def set_spd(l, r):
    try:
        alvik.set_wheels_speed(l, r)
    except:
        pass

# ------------- Afstand ---------------
def dist_min_cm():
    """Retourneert dichtstbijzijnde geldige afstand in cm, of None."""
    try:
        # vaak: (L, CL, C, CR, R)
        data = alvik.get_distance()
        vals = []
        for v in data:
            iv = int(v)
            # soms mm -> in cm normaliseren grofweg
            if iv > 1000:
                iv = iv // 10
            if 2 <= iv <= 400:
                vals.append(iv)
        return min(vals) if vals else None
    except:
        return None

# -------------- Gedrag ----------------
def scan_for_opening():
    # Draai op de plek tot er OK_OPEN keer een 'open' meting is
    led_wait()
    set_spd(SCAN, -SCAN)
    ok = 0
    while True:
        if cancel_pressed():
            pause_until_ok()
            set_spd(SCAN, -SCAN)

        d = dist_min_cm()
        ok = ok + 1 if (d is not None and d > OPEN) else 0
        if ok >= OK_OPEN:
            stop_now()
            return True
        sleep_ms(SAMPLE_DT_MS)

def drive_until_exit():
    # Rij vooruit; ontwijk obstakel; stop als we EXIT bereiken
    led_go()
    set_spd(SPEED, SPEED)
    exit_ok = 0
    while True:
        if cancel_pressed():
            pause_until_ok()
            set_spd(SPEED, SPEED)

        d = dist_min_cm()
        if d is None:
            sleep_ms(SAMPLE_DT_MS)
            continue

        # Te dicht -> stukje achteruit + draai, dan herstart scan
        if d < SAFE:
            led_warn(); stop_now()
            set_spd(-SPEED, -SPEED); sleep_ms(500)
            set_spd(-SCAN, SCAN);    sleep_ms(600)
            stop_now()
            return False

        # Buiten?
        if d > EXIT:
            exit_ok += 1
            if exit_ok >= OK_EXIT:
                stop_now()
                blink_done()
                return True
        else:
            exit_ok = 0

        sleep_ms(SAMPLE_DT_MS)

# ======================== MAIN ========================
def main():
    print("[L1] Start: No Way Out")
    led_wait(); wait_ok()      # zelfde startlogica als Level 2

    try:
        while True:
            if scan_for_opening():
                if drive_until_exit():
                    print("[L1] Klaar - terug naar menu")
                    return
            sleep_ms(10)
    except KeyboardInterrupt:
        stop_now(); led_go()

if __name__ == "__main__":
    main()
