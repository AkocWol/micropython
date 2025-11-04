# ==== Level 1 - No Way Out (wall-follow + corridor/gap detect) ====
# Volgt rechtermuur, herkent gang/doorgang (twee zijmuren + front open) en rijdt erdoor.
# Voorkomt eindeloos rondjes draaien met anti-spin fallback.
# CANCEL = pauze, OK = hervatten (zoals Level 2). ASCII-only.

import time

# --- board ophalen (werkt los en via main.py) ---
try:
    alvik
except NameError:
    from arduino_alvik import ArduinoAlvik
    alvik = ArduinoAlvik(); alvik.begin()

# ===================== Instellingen =====================
# Afstanden in cm
WALL_TARGET    = 14     # gewenst dicht bij rechtermuur
WALL_NEAR      = 28     # "er staat een muur" aan zijkant wanneer < WALL_NEAR
OPEN_SIDE_TH   = 38     # opening rechts wanneer > deze drempel
SAFE_FRONT     = 18     # te dicht voor -> ontwijken
GAP_AHEAD      = 60     # "voor ons open" voor corridor/gang
EXIT_THRESH    = 110    # buiten

# Snelheden / stuur
SPEED_FWD      = 22
SPEED_TURN     = 16
KP             = 1.0    # stuurversterking op rechtermuur
MAX_STEER      = 12
DT             = 20     # ms sample interval

# Stabiliteit / timers
STABLE_N       = 3      # hoeveel opeenvolgende metingen nodig (opening/gang/exit)
TURN_IN_MS     = 350    # tijd naar rechts insturen bij rechts opening
CORRIDOR_MS    = 500    # zo lang rechtuit duwen door de gang
ANTI_SPIN_MS   = 3500   # na zoveel ms zonder vooruitgang -> anti-spin fallback
PROBE_MS       = 400    # hoe lang voorwaarts "proben" bij anti-spin
# =======================================================

# -------------------- LED helpers ----------------------
def _led_rgb(r, g, b):
    try:
        alvik.left_led.set_color(r, g, b)
        alvik.right_led.set_color(r, g, b)
    except:
        pass

def led_wait():   _led_rgb(0, 0, 1)   # blauw
def led_go():     _led_rgb(0, 1, 0)   # groen
def led_pause():  _led_rgb(1, 1, 0)   # geel
def led_done():   _led_rgb(1, 1, 1)   # wit
def led_warn():   _led_rgb(1, 0, 0)   # rood

def blink_done(n=6, on=150, off=150):
    for _ in range(n):
        led_done(); time.sleep_ms(on)
        _led_rgb(0, 0, 0); time.sleep_ms(off)

# -------------------- Knoppen --------------------------
def ok_pressed():
    try:    return bool(alvik.get_touch_ok())
    except: return False

def cancel_pressed():
    try:    return bool(alvik.get_touch_cancel())
    except: return False

def wait_for_ok():
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        time.sleep_ms(50)
    time.sleep_ms(120)  # debounce

def pause_if_cancel():
    if cancel_pressed():
        stop_now(); led_pause()
        while not ok_pressed():
            time.sleep_ms(40)
        time.sleep_ms(120)
        led_go()
        return True
    return False

# -------------------- Motion ---------------------------
def stop_now():
    try:
        alvik.set_wheels_speed(0, 0); alvik.brake()
    except:
        pass

def set_speed(l, r):
    try:
        alvik.set_wheels_speed(l, r)
    except:
        pass

# ---------------- Afstand helpers ----------------------
def _to_cm(iv):
    iv = int(iv)
    return iv // 10 if iv > 1000 else iv

def get_dists_cm():
    """Return (L, CL, C, CR, R) in cm (2..400) of None per kanaal."""
    L = CL = C = CR = R = None
    try:
        data = alvik.get_distance()
        if isinstance(data, (tuple, list)) and len(data) >= 5:
            vals = [_to_cm(v) for v in data[:5]]
            L, CL, C, CR, R = [(v if 2 <= v <= 400 else None) for v in vals]
        elif isinstance(data, dict):
            L  = _to_cm(data.get("L",  data.get("left",         0)))
            CL = _to_cm(data.get("CL", data.get("center_left",   0)))
            C  = _to_cm(data.get("C",  data.get("center",        0)))
            CR = _to_cm(data.get("CR", data.get("center_right",  0)))
            R  = _to_cm(data.get("R",  data.get("right",         0)))
            L, CL, C, CR, R = [(v if 2 <= v <= 400 else None) for v in (L, CL, C, CR, R)]
    except:
        pass
    return L, CL, C, CR, R

def right_dist_cm():
    L, CL, C, CR, R = get_dists_cm()
    vals = [v for v in (CR, R) if v is not None]
    if not vals: return None
    return sum(vals) / len(vals)

def left_dist_cm():
    L, CL, C, CR, R = get_dists_cm()
    vals = [v for v in (L, ) if v is not None]
    if not vals: return None
    return sum(vals) / len(vals)

def front_center_cm():
    L, CL, C, CR, R = get_dists_cm()
    vals = [v for v in (CL, C, CR) if v is not None]
    return sum(vals)/len(vals) if vals else None

def front_min_cm():
    L, CL, C, CR, R = get_dists_cm()
    vals = [v for v in (CL, C, CR) if v is not None]
    return min(vals) if vals else None

def any_min_cm():
    L, CL, C, CR, R = get_dists_cm()
    vals = [v for v in (L, CL, C, CR, R) if v is not None]
    return min(vals) if vals else None

# --------------- Detectie helpers ---------------------
def corridor_ahead():
    """
    Gang/doorgang: beide zijkanten 'muur dichtbij' EN vooraan duidelijk open.
    Concreet:
      - left_dist < WALL_NEAR en right_dist < WALL_NEAR
      - front_center > GAP_AHEAD
    """
    ld = left_dist_cm()
    rd = right_dist_cm()
    fc = front_center_cm()
    if ld is None or rd is None or fc is None:
        return False
    return (ld < WALL_NEAR) and (rd < WALL_NEAR) and (fc > GAP_AHEAD)

# ------------------- Gedrag ---------------------------
def wall_follow_with_corridor_and_exit():
    """
    Rechter-muur volgen met P-sturing + corridor detectie.
    - Corridor: twee zijmuren (links en rechts dichtbij) + front open -> rechtuit push.
    - Opening rechts: d_right > OPEN_SIDE_TH, STABLE_N samples -> rechts insturen.
    - Te dicht voor -> ontwijken.
    - Exit (alles ver) -> blink + return.
    - Anti-spin: als te lang geen corridor/opening/exit -> korte voorwaartse probe.
    """
    led_go()
    open_cnt = 0
    corridor_cnt = 0
    exit_cnt = 0

    t_last_progress = time.ticks_ms()  # voortgang = corridor/opening/exit/ontwijk

    while True:
        if pause_if_cancel():
            # hervat
            pass

        # veiligheidscheck voor
        d_front_min = front_min_cm()
        if d_front_min is not None and d_front_min < SAFE_FRONT:
            led_warn()
            set_speed(-SPEED_FWD, -SPEED_FWD); time.sleep_ms(220)
            set_speed(-SPEED_TURN, SPEED_TURN); time.sleep_ms(300)
            led_go()
            open_cnt = corridor_cnt = 0
            t_last_progress = time.ticks_ms()
            continue

        # exit (buiten is alles ver weg -> min afstand groot)
        d_any = any_min_cm()
        if d_any is not None and d_any > EXIT_THRESH:
            exit_cnt += 1
            if exit_cnt >= STABLE_N:
                stop_now(); blink_done()
                return True
        else:
            exit_cnt = 0

        # corridor/gang voor ons?
        if corridor_ahead():
            corridor_cnt += 1
            if corridor_cnt >= STABLE_N:
                # duw recht vooruit door de gang
                set_speed(SPEED_FWD, SPEED_FWD)
                time.sleep_ms(CORRIDOR_MS)
                corridor_cnt = 0
                t_last_progress = time.ticks_ms()
                continue
        else:
            corridor_cnt = 0

        # opening rechts?
        d_right = right_dist_cm()
        if d_right is not None and d_right > OPEN_SIDE_TH:
            open_cnt += 1
        else:
            open_cnt = 0

        if open_cnt >= STABLE_N:
            # duidelijke opening rechts -> insturen
            set_speed(SPEED_TURN, -SPEED_TURN); time.sleep_ms(TURN_IN_MS)
            set_speed(SPEED_FWD, SPEED_FWD)
            open_cnt = 0
            t_last_progress = time.ticks_ms()
            time.sleep_ms(200)
            continue

        # normaal: P-sturing op rechtermuur
        if d_right is not None:
            err = (WALL_TARGET - d_right)  # positief -> te ver van muur -> stuur naar rechts
            steer = KP * err
            if steer >  MAX_STEER: steer =  MAX_STEER
            if steer < -MAX_STEER: steer = -MAX_STEER
            L = SPEED_FWD + steer
            R = SPEED_FWD - steer
            set_speed(L, R)
        else:
            # muur even kwijt -> rustig rechtsom draaien
            set_speed(SPEED_TURN, -SPEED_TURN)

        # anti-spin: als we te lang niets “nuttigs” zagen, forceer progressie
        if time.ticks_diff(time.ticks_ms(), t_last_progress) > ANTI_SPIN_MS:
            # korte forward probe
            set_speed(SPEED_FWD, SPEED_FWD); time.sleep_ms(PROBE_MS)
            # kleine bias rechtsom om niet in midden te blijven
            set_speed(SPEED_TURN, -SPEED_TURN); time.sleep_ms(200)
            t_last_progress = time.ticks_ms()

        time.sleep_ms(DT)

# --------------------- MAIN --------------------------
def main():
    print("[L1] Start: No Way Out (wall-follow + corridor)")
    led_wait()
    wait_for_ok()  # druk OK om te beginnen

    try:
        if wall_follow_with_corridor_and_exit():
            print("[L1] Klaar - terug naar menu")
            return
    except KeyboardInterrupt:
        stop_now(); led_go()

if __name__ == "__main__":
    main()
