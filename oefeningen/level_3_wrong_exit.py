# ==== Level 3 – Wrong Exit (simple, same behavior) ====
# Heenweg: rij vooruit, registreer tegels (kleur-buckets) tot obstakel.
# Kies de unieke kleur (count==1; de laatst-gezien wint bij meerdere).
# Terugweg: rij achteruit tot die tegel; draai en rij eruit; vier feest.

import time, math

# --- alvik ophalen (werkt los en via main.py) ---
try:
    alvik
except NameError:
    from arduino_alvik import ArduinoAlvik
    alvik = ArduinoAlvik(); alvik.begin()

# ============== Instellingen ==============
SPEED_FWD   = 22     # vooruit scannen
SPEED_BACK  = -18    # achteruit zoeken
SPEED_EXIT  = 26     # na bocht uitrijden
TURN_MS     = 700    # bocht duur
EXIT_RUN_MS = 1200   # rechtuit na bocht
SAMPLE_MS   = 40     # sample-interval
TILE_DWELL  = 4      # samples voor "stabiele tegel"
COLOR_H_BINS = 12    # hue buckets
COLOR_V_BINS = 2     # brightness buckets
DELTA_TILE_TOL = 1   # toleranties op buckets (±)
END_STOP_CM = 16     # obstakel-drempel voor einde
END_TIMEOUT_MS = 18000
BACK_TIMEOUT_MS = 18000
# ==========================================

# ------------- LEDs -------------
def _led(r,g,b):
    try:
        alvik.left_led.set_color(int(bool(r)), int(bool(g)), int(bool(b)))
        alvik.right_led.set_color(int(bool(r)), int(bool(g)), int(bool(b)))
    except:
        pass

def led_wait(): _led(0,0,1)  # blauw
def led_go():   _led(0,1,0)  # groen
def led_stop(): _led(1,0,0)  # rood
def led_turn(): _led(1,0,1)  # magenta
def led_scan(): _led(0,1,1)  # cyaan
def led_done(): _led(1,1,1)  # wit
def led_off():  _led(0,0,0)

def blink_done(n=6, on=120, off=120):
    for _ in range(n):
        led_done(); time.sleep_ms(on)
        led_off();  time.sleep_ms(off)

# ----------- Knoppen -----------
def ok_pressed():
    try:    return bool(alvik.get_touch_ok())
    except: return False

def cancel_pressed():
    try:    return bool(alvik.get_touch_cancel())
    except: return False

def wait_ok_press_release():
    """Wacht tot OK los is, dan op OK-druk om te starten."""
    while ok_pressed():
        time.sleep_ms(30)
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        time.sleep_ms(50)
    time.sleep_ms(120)  # debounce

def pause_if_cancel():
    """CANCEL = pauze (blauw) tot OK; True als gepauzeerd."""
    if not cancel_pressed():
        return False
    led_wait()
    try: alvik.brake()
    except: pass
    while not ok_pressed():
        time.sleep_ms(60)
    time.sleep_ms(120)
    led_go()
    return True

# ------------ Beweging ------------
def set_speed(l, r):
    try: alvik.set_wheels_speed(l, r)
    except: pass

def hard_stop():
    led_stop(); set_speed(0,0)
    try: alvik.brake()
    except: pass
    time.sleep_ms(120)

def pivot_left(ms=TURN_MS, spd=22):
    led_turn(); set_speed(-spd, spd); time.sleep_ms(ms); hard_stop()

def pivot_right(ms=TURN_MS, spd=22):
    led_turn(); set_speed( spd,-spd); time.sleep_ms(ms); hard_stop()

# --------- Afstand/einde ----------
def front_cm():
    """Min van (CL,C,CR) in cm; None als geen meting."""
    try:
        L,CL,C,CR,R = alvik.get_distance()
        xs=[]
        for v in (int(CL), int(C), int(CR)):
            if v > 1000: v //= 10
            if 2 <= v <= 400: xs.append(v)
        return min(xs) if xs else None
    except:
        return None

def end_obstacle_detected():
    """Einde pad via afstand of bumpers."""
    d = front_cm()
    if d is not None and d <= END_STOP_CM:
        return True
    for fn in ("get_bumpers","get_touch_front","is_bumper_pressed"):
        try:
            v = getattr(alvik, fn)()
            if isinstance(v,(tuple,list)): return any(bool(x) for x in v)
            if isinstance(v,dict):         return any(bool(x) for x in v.values())
            return bool(v)
        except:
            pass
    return False

# --------- Kleur / buckets ----------
def read_rgb01():
    """RGB genormaliseerd 0..1 (probeert meerdere API’s)."""
    for fn in ("get_color","get_rgb","get_color_rgb","get_line_color","read_color"):
        try:
            v = getattr(alvik, fn)()
            if isinstance(v,(tuple,list)) and len(v)>=3:
                r,g,b = float(v[0]), float(v[1]), float(v[2])
            elif isinstance(v,dict):
                r = float(v.get('r', v.get('red', 0)))
                g = float(v.get('g', v.get('green', 0)))
                b = float(v.get('b', v.get('blue', 0)))
            else:
                continue
            mx = max(1.0, r, g, b)
            if mx > 1.5:  # waarschijnlijk 0..255 → schaal naar 0..1
                r/=255.0; g/=255.0; b/=255.0
            return max(0,min(1,r)), max(0,min(1,g)), max(0,min(1,b))
        except:
            pass
    # fallback met 3-lijnsensoren als pseudo-RGB
    try:
        ls = alvik.get_line_sensors()  # (L,C,R)
        if isinstance(ls,(tuple,list)) and len(ls)>=3:
            r,g,b = float(ls[0]), float(ls[1]), float(ls[2])
            mx = max(1.0, r, g, b)
            return r/mx, g/mx, b/mx
    except:
        pass
    return 0.0, 0.0, 0.0

def rgb_to_bucket(r,g,b):
    """Projecteer naar (hue_bin, value_bin)."""
    x = (2*r - g - b)
    y = (math.sqrt(3.0)*(g - b))
    ang = math.atan2(y, x)
    if ang < 0: ang += 2*math.pi
    h_deg = math.degrees(ang)          # 0..360
    hbin = int((h_deg/360.0) * COLOR_H_BINS)
    if hbin >= COLOR_H_BINS: hbin = COLOR_H_BINS - 1
    v = max(r,g,b)
    vbin = 0 if v < 0.35 else 1        # donker/licht
    return (hbin, vbin)

def read_bucket():
    r,g,b = read_rgb01()
    return rgb_to_bucket(r,g,b)

# ---- Tegel-detectie (hysterese) ----
_last_bucket = None
_dwell = 0

def detect_tile_change():
    """
    True precies 1x als we stabiel op een (nieuwe/dezelfde) tegel staan.
    Retourneert (is_new, bucket).
    """
    global _last_bucket, _dwell
    cur = read_bucket()

    if _last_bucket is None:
        _last_bucket = cur; _dwell = 1
        return False, cur

    same = (abs(cur[0]-_last_bucket[0]) <= DELTA_TILE_TOL and
            abs(cur[1]-_last_bucket[1]) <= DELTA_TILE_TOL)

    if same:
        if _dwell < TILE_DWELL:
            _dwell += 1
            if _dwell == TILE_DWELL:
                return True, cur   # meldt 1x “stabiel op tegel”
        return False, cur

    # nieuwe bucket gezien → reset dwell
    _last_bucket = cur; _dwell = 1
    return False, cur

# ------------- Gedrag -------------
def forward_across_and_record(colors, counts):
    """Rij vooruit; bij nieuwe stabiele tegel → log & tel; stop bij einde/timeout."""
    led_scan()
    set_speed(SPEED_FWD, SPEED_FWD)
    t0 = time.ticks_ms()
    _ = detect_tile_change()  # seed

    while True:
        if pause_if_cancel():
            set_speed(SPEED_FWD, SPEED_FWD)

        new, bucket = detect_tile_change()
        if new:
            colors.append(bucket)
            counts[bucket] = counts.get(bucket, 0) + 1

        if end_obstacle_detected():
            hard_stop(); return True
        if time.ticks_diff(time.ticks_ms(), t0) > END_TIMEOUT_MS:
            hard_stop(); return True

        time.sleep_ms(SAMPLE_MS)

def pick_unique_last(colors, counts):
    """Laatst-gezien bucket met count==1, of None."""
    for b in reversed(colors):
        if counts.get(b, 0) == 1:
            return b
    return None

def reverse_until_bucket(target_bucket):
    """Rij achteruit tot we stabiel op target-bucket staan (met hysterese)."""
    led_go()
    set_speed(SPEED_BACK, SPEED_BACK)
    t0 = time.ticks_ms()

    # reset tegel-detectie richting terugweg
    global _last_bucket, _dwell
    _last_bucket = None; _dwell = 0

    while True:
        if pause_if_cancel():
            set_speed(SPEED_BACK, SPEED_BACK)

        new, bucket = detect_tile_change()

        if _dwell >= TILE_DWELL:  # pas checken als stabiel
            same_target = (abs(bucket[0]-target_bucket[0]) <= DELTA_TILE_TOL and
                           abs(bucket[1]-target_bucket[1]) <= DELTA_TILE_TOL)
            if same_target:
                hard_stop(); return True

        if time.ticks_diff(time.ticks_ms(), t0) > BACK_TIMEOUT_MS:
            hard_stop(); return False

        time.sleep_ms(SAMPLE_MS)

def exit_turn_and_go(direction="auto"):
    """Kies kant met meer ruimte (links/rechts) of forceer richting."""
    go_left = True
    if direction == "auto":
        l_ok = r_ok = 0
        try:
            L, CL, C, CR, R = alvik.get_distance()
            l_ok = int(L) if isinstance(L,(int,float)) else 0
            r_ok = int(R) if isinstance(R,(int,float)) else 0
        except:
            pass
        go_left = (l_ok >= r_ok)
    elif direction == "right":
        go_left = False

    if go_left: pivot_left(ms=TURN_MS, spd=22)
    else:       pivot_right(ms=TURN_MS, spd=22)

    led_go(); set_speed(SPEED_EXIT, SPEED_EXIT)
    time.sleep_ms(EXIT_RUN_MS)
    hard_stop()
    return True

def celebrate():
    """Korte blink + kleine spin-dans."""
    for _ in range(3):
        led_done(); time.sleep_ms(120)
        led_off();  time.sleep_ms(80)
    for _ in range(3):
        set_speed(26, -26); time.sleep_ms(250)
        set_speed(-26, 26); time.sleep_ms(250)
    hard_stop(); blink_done(6, 120, 120)

# --------------- MAIN ---------------
def main():
    led_wait()
    wait_ok_press_release()    # druk OK om te starten

    try:
        while True:
            # Heenweg: kleuren opnemen tot einde
            colors, counts = [], {}
            ok = forward_across_and_record(colors, counts)
            if not ok:
                continue

            # Unieke kleur kiezen (laatst-gezien unieke)
            target = pick_unique_last(colors, counts)
            if target is None:
                # fallback: laatste tegel als niets uniek is
                if colors:
                    target = colors[-1]
                else:
                    blink_done(3,160,160); return

            # Terugweg: achteruit tot target-tegel
            if reverse_until_bucket(target):
                exit_turn_and_go("auto")
                celebrate()
                return
            else:
                hard_stop(); blink_done(4,140,140); return

    except KeyboardInterrupt:
        try: alvik.stop()
        except: pass

if __name__ == "__main__":
    main()
