# ==== Level 2 – Perfect Balance (simple, zelfde gedrag) ====
# Over de kantelbrug: stop in het midden (knipper), daal af en stop op vlak.

import time, math

# --- alvik ophalen (werkt los en via main.py) ---
try:
    alvik
except NameError:
    from arduino_alvik import ArduinoAlvik
    alvik = ArduinoAlvik(); alvik.begin()

# ============== Instellingen ==============
# Rijden/trim
DIR = 1
TRIM_L = 0.0
TRIM_R = 0.0
SPEED_UP = 28          # snelheid omhoog
SPEED_UP_SLOW = 20     # trager als steil
SPEED_DOWN = 24        # snelheid omlaag/uitrollen
SAMPLE_DT_MS = 15

# Midden-detectie (top/plateau)
UP_MIN_DEG = 4         # helling vanaf wanneer we "klimmen"
UP_SLOW_DEG = 10       # drempel om trager te rijden
TILT_DROP_DEG = 7      # scherpe daling na de top
MID_ZERO_DEG = 5       # "vlak genoeg" rond 0°
MID_STABLE_SAMPLES = 1 # aantal samples vlak voor midden
MID_WINDOW_MS = 900    # tijdsvenster na crest om midden te vangen

# Einde detectie (robuust vlak)
DESC_MIN_DEG = 6          # voldoende neerwaartse helling
DESC_SAMPLES_ARM = 4      # aantal samples neerwaarts om "armed" te worden
FINAL_ZERO_DEG = 4        # vlak drempel aan het eind
FINAL_STABLE_SAMPLES = 5  # aantal stabiele vlak-samples
DERIV_EPS = 0.6           # |dp| bijna nul → stil/constant
GYRO_STILL_DPS = 8.0      # som |gx|+|gy|+|gz| klein → weinig beweging
# =========================================

# ------------- LED's (kort) -------------
def _led_rgb(r, g, b):
    try:
        alvik.left_led.set_color(r, g, b)
        alvik.right_led.set_color(r, g, b)
    except:
        pass

def led_wait():  _led_rgb(0, 0, 1)  # blauw = wachten
def led_go():    _led_rgb(0, 1, 0)  # groen = rijden
def led_pause(): _led_rgb(1, 1, 0)  # geel = pauze
def led_done():  _led_rgb(1, 1, 1)  # wit  = highlight

# ------------- Knoppen ------------------
def ok_pressed():
    try:    return bool(alvik.get_touch_ok())
    except: return False

def cancel_pressed():
    try:    return bool(alvik.get_touch_cancel())
    except: return False

def wait_for_ok():
    """Wacht op OK (veilig, remmen en blauw)."""
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        time.sleep_ms(50)
    time.sleep_ms(120)  # debounce

def pause_if_cancel():
    """Als CANCEL: pauzeer tot OK en ga verder."""
    if cancel_pressed():
        stop_now(); led_pause()
        while not ok_pressed():
            time.sleep_ms(40)
        time.sleep_ms(120)
        led_go()
        return True
    return False

# ------------- Beweging -----------------
def stop_now():
    try:
        alvik.set_wheels_speed(0, 0); alvik.brake()
    except:
        pass

def forward(v):
    """Rij vooruit met trims (links/rechts)."""
    L = DIR * v * (1.0 + TRIM_L)
    R = DIR * v * (1.0 + TRIM_R)
    try:
        alvik.set_wheels_speed(L, R)
    except:
        pass

# ------------- IMU / Pitch --------------
def _raw_pitch():
    """Lees pitch (graden). Valt terug op accelerometer als euler niet bestaat."""
    # 1) Probeer pitch uit euler/orientation
    for fn in ("get_euler", "get_orientation"):
        try:
            e = getattr(alvik, fn)()
            if isinstance(e, (tuple, list)) and len(e) >= 2: return float(e[1])
            if isinstance(e, dict) and "pitch" in e:         return float(e["pitch"])
        except:
            pass
    # 2) Valt terug op accelerometer → pitch uit ax,ay,az
    ax = ay = az = None
    for fn in ("get_accelerometer", "get_accel", "accel"):
        try:
            a = getattr(alvik, fn)()
            if isinstance(a, (tuple, list)) and len(a) >= 3:
                ax, ay, az = float(a[0]), float(a[1]), float(a[2]); break
            if isinstance(a, dict):
                ax = float(a.get("ax", a.get("x", 0)))
                ay = float(a.get("ay", a.get("y", 0)))
                az = float(a.get("az", a.get("z", 0))); break
        except:
            pass
    if ax is None:
        try:
            imu = alvik.get_imu()
            if isinstance(imu, (tuple, list)) and len(imu) >= 3:
                ax, ay, az = float(imu[0]), float(imu[1]), float(imu[2])
            elif isinstance(imu, dict):
                ax = float(imu.get("ax", imu.get("x", 0)))
                ay = float(imu.get("ay", imu.get("y", 0)))
                az = float(imu.get("az", imu.get("z", 0)))
        except:
            pass
    if ax is None:
        return 0.0
    # pitch uit accel (graden)
    return math.degrees(math.atan2(-ax, math.sqrt(ay*ay + az*az)))

def get_pitch_deg():
    """Pitch met jouw as-correctie (positief = omhoog)."""
    p = _raw_pitch()
    return -p  # as is omgekeerd in jouw setup

def get_pitch_and_gyro():
    """(pitch, gx, gy, gz) — gyro kan None zijn."""
    p = get_pitch_deg()
    gx = gy = gz = None
    try:
        imu = alvik.get_imu()
        if isinstance(imu, (tuple, list)) and len(imu) >= 6:
            gx, gy, gz = float(imu[3]), float(imu[4]), float(imu[5])
        elif isinstance(imu, dict):
            gx = float(imu.get("gx", 0.0))
            gy = float(imu.get("gy", 0.0))
            gz = float(imu.get("gz", 0.0))
    except:
        pass
    return p, gx, gy, gz

# ======= Fase 1: naar midden (knipper) =======
def go_to_middle_and_blink():
    """Klim, vind de crest/plateau → midden → kort knipperen."""
    led_go(); forward(SPEED_UP)
    climbing = False
    flat = 0
    crest = False
    prev = get_pitch_deg()

    while True:
        if pause_if_cancel():
            forward(SPEED_UP)

        p = get_pitch_deg()
        dp = p - (prev if prev is not None else p)

        # zijn we aan het klimmen?
        if p >= UP_MIN_DEG:
            climbing = True

        # trager als steiler
        forward(SPEED_UP_SLOW if p >= UP_SLOW_DEG else SPEED_UP)

        # crest detectie (top) → daling of knik
        if climbing and not crest:
            if dp <= -TILT_DROP_DEG or (prev is not None and prev > p):
                crest = True
                t_crest = time.ticks_ms()

        # midden is "vlak genoeg" rond 0°
        mid = False
        if climbing and abs(p) <= MID_ZERO_DEG:
            flat += 1
            if flat >= MID_STABLE_SAMPLES:
                mid = True
        else:
            flat = 0

        # extra: na crest, binnen window én vlak → midden
        if crest and time.ticks_diff(time.ticks_ms(), t_crest) <= MID_WINDOW_MS and abs(p) <= MID_ZERO_DEG:
            mid = True

        if mid:
            stop_now()
            for _ in range(3):
                led_done(); time.sleep_ms(100)
                led_go();   time.sleep_ms(100)
            return

        prev = p
        time.sleep_ms(SAMPLE_DT_MS)

# ==== Fase 2: afdalen en stabiel vlak stoppen ====
def run_until_final_flat_robust():
    """Daal af; zodra vlak + stil (pitch & gyro) ×N samples → stop + blink."""
    led_go(); forward(SPEED_DOWN)
    armed = False         # pas "eind-zoekmodus" als we echt dalen
    desc_cnt = 0
    stable_cnt = 0
    prev_p, _, _, _ = get_pitch_and_gyro()

    while True:
        if pause_if_cancel():
            forward(SPEED_DOWN)

        p, gx, gy, gz = get_pitch_and_gyro()
        dp = p - (prev_p if prev_p is not None else p)

        # genoeg neerwaarts? (armen)
        if p <= -DESC_MIN_DEG:
            desc_cnt += 1
        else:
            if desc_cnt > 0: desc_cnt -= 1
        if not armed and desc_cnt >= DESC_SAMPLES_ARM:
            armed = True

        if armed:
            # bijna geen verandering in pitch?
            still_ok = abs(dp) <= DERIV_EPS
            # gyro rustig?
            gyro_ok = True
            if gx is not None and gy is not None and gz is not None:
                gyro_ok = (abs(gx) + abs(gy) + abs(gz)) <= GYRO_STILL_DPS

            # vlak + stil genoeg, meerdere samples
            if (abs(p) <= FINAL_ZERO_DEG) and still_ok and gyro_ok:
                stable_cnt += 1
            else:
                stable_cnt = 0

            if stable_cnt >= FINAL_STABLE_SAMPLES:
                stop_now()
                for _ in range(4):
                    led_done(); time.sleep_ms(120)
                    led_go();   time.sleep_ms(120)
                return

        prev_p = p
        time.sleep_ms(SAMPLE_DT_MS)

# ====================== MAIN ======================
def main():
    led_wait(); wait_for_ok()      # druk OK om te starten
    try:
        go_to_middle_and_blink()   # Fase 1
        run_until_final_flat_robust()  # Fase 2
    except KeyboardInterrupt:
        stop_now(); led_go()

if __name__ == "__main__":
    main()
