# ==== Level 2 – Perfect Balance ====
# Rijdt over de kantelbrug: stopt in het midden, knippert, daalt af en stopt op vlakke tafel.

_time=__import__('time'); _math=__import__('math')
sleep_ms=_time.sleep_ms; ticks_ms=_time.ticks_ms; ticks_diff=_time.ticks_diff
atan2=_math.atan2; sqrt=_math.sqrt; pi=_math.pi

# --- board ---
try: alvik
except NameError:
    ArduinoAlvik=__import__('arduino_alvik').ArduinoAlvik
    alvik=ArduinoAlvik(); alvik.begin()

# ===================== Tunables =====================
DIR=1; TRIM_L=0.0; TRIM_R=0.0
SPEED_UP=28; SPEED_UP_SLOW=20; SPEED_DOWN=24
SAMPLE_DT_MS=15

# Midden-detectie
UP_MIN_DEG=4; UP_SLOW_DEG=10; TILT_DROP_DEG=7
MID_ZERO_DEG=5; MID_STABLE_SAMPLES=1; MID_WINDOW_MS=900

# Robuuste eind-detectie
DESC_MIN_DEG=6; DESC_SAMPLES_ARM=4
FINAL_ZERO_DEG=4; FINAL_STABLE_SAMPLES=5
DERIV_EPS=0.6; GYRO_STILL_DPS=8.0
# ====================================================

# ---------------- LEDs ----------------
def _led(rgb):
    try: r,g,b=rgb; alvik.left_led.set_color(r,g,b); alvik.right_led.set_color(r,g,b)
    except: pass
def led_wait():  _led((0,0,1))
def led_go():    _led((0,1,0))
def led_pause(): _led((1,1,0))
def led_done():  _led((1,1,1))

# -------------- Buttons --------------
def ok_pressed():
    try: return bool(alvik.get_touch_ok())
    except: return False
def cancel_pressed():
    try: return bool(alvik.get_touch_cancel())
    except: return False
def wait_ok():
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        sleep_ms(50)
    sleep_ms(120)
def pause_until_ok():
    stop_now(); led_pause()
    while not ok_pressed(): sleep_ms(40)
    sleep_ms(120); led_go()

# -------------- Motion ---------------
def stop_now():
    try: alvik.set_wheels_speed(0,0); alvik.brake()
    except: pass
def forward(v):
    L=DIR*v*(1.0+TRIM_L); R=DIR*v*(1.0+TRIM_R)
    try: alvik.set_wheels_speed(L,R)
    except: pass

# ----------- IMU helpers -------------
def _raw_pitch():
    for fn in ("get_euler","get_orientation"):
        try:
            e=getattr(alvik,fn)()
            if isinstance(e,(tuple,list)) and len(e)>=2: return float(e[1])
            if isinstance(e,dict) and "pitch" in e: return float(e["pitch"])
        except: pass
    ax=ay=az=None
    for fn in ("get_accelerometer","get_accel","accel"):
        try:
            a=getattr(alvik,fn)()
            if isinstance(a,(tuple,list)) and len(a)>=3:
                ax,ay,az=float(a[0]),float(a[1]),float(a[2]); break
            if isinstance(a,dict):
                ax=float(a.get("ax",a.get("x",0))); ay=float(a.get("ay",a.get("y",0))); az=float(a.get("az",a.get("z",0))); break
        except: pass
    if ax is None:
        try:
            imu=alvik.get_imu()
            if isinstance(imu,(tuple,list)) and len(imu)>=3:
                ax,ay,az=float(imu[0]),float(imu[1]),float(imu[2])
            elif isinstance(imu,dict):
                ax=float(imu.get("ax",imu.get("x",0))); ay=float(imu.get("ay",imu.get("y",0))); az=float(imu.get("az",imu.get("z",0)))
        except: pass
    if ax is None: return 0.0
    return atan2(-ax, sqrt(ay*ay+az*az))*(180.0/pi)

def get_pitch_deg():
    p=_raw_pitch()
    p = -p   # jouw IMU-as is omgekeerd (positief = omhoog)
    return p

def get_pitch_and_gyro():
    p=get_pitch_deg(); gx=gy=gz=None
    try:
        imu=alvik.get_imu()
        if isinstance(imu,(tuple,list)) and len(imu)>=6:
            gx,gy,gz=float(imu[3]),float(imu[4]),float(imu[5])
        elif isinstance(imu,dict):
            gx=float(imu.get("gx",0.0)); gy=float(imu.get("gy",0.0)); gz=float(imu.get("gz",0.0))
    except: pass
    return p,gx,gy,gz

# ================== Fase 1: midden ==================
def go_to_middle_and_blink():
    led_go(); forward(SPEED_UP)
    climbing=False; flat=0; crest=False
    prev=get_pitch_deg()
    while True:
        if cancel_pressed(): pause_until_ok(); forward(SPEED_UP)

        p=get_pitch_deg(); dp=p-(prev if prev is not None else p)
        if p>=UP_MIN_DEG: climbing=True
        forward(SPEED_UP_SLOW if p>=UP_SLOW_DEG else SPEED_UP)

        if climbing and not crest:
            if dp<=-TILT_DROP_DEG or (prev is not None and prev>p):
                crest=True; t_crest=ticks_ms()

        mid=False
        if climbing and abs(p)<=MID_ZERO_DEG:
            flat+=1
            if flat>=MID_STABLE_SAMPLES: mid=True
        else:
            flat=0
        if crest and ticks_diff(ticks_ms(),t_crest)<=MID_WINDOW_MS and abs(p)<=MID_ZERO_DEG:
            mid=True

        if mid:
            stop_now()
            for _ in range(3):
                led_done(); sleep_ms(100); led_go(); sleep_ms(100)
            return
        prev=p; sleep_ms(SAMPLE_DT_MS)

# ======== Fase 2: robuust vlak-einde ========
def run_until_final_flat_robust():
    led_go(); forward(SPEED_DOWN)
    armed=False; desc_cnt=0; stable_cnt=0
    prev_p,_,_,_=get_pitch_and_gyro()

    while True:
        if cancel_pressed(): pause_until_ok(); forward(SPEED_DOWN)

        p,gx,gy,gz=get_pitch_and_gyro()
        dp=p-(prev_p if prev_p is not None else p)

        if p<=-DESC_MIN_DEG:
            desc_cnt+=1
        else:
            if desc_cnt>0: desc_cnt-=1
        if not armed and desc_cnt>=DESC_SAMPLES_ARM:
            armed=True

        if armed:
            still_ok=abs(dp)<=DERIV_EPS
            gyro_ok=True
            if gx is not None and gy is not None and gz is not None:
                gyro_ok=(abs(gx)+abs(gy)+abs(gz))<=GYRO_STILL_DPS

            if (abs(p)<=FINAL_ZERO_DEG) and still_ok and gyro_ok:
                stable_cnt+=1
            else:
                stable_cnt=0

            if stable_cnt>=FINAL_STABLE_SAMPLES:
                stop_now()
                for _ in range(4):
                    led_done(); sleep_ms(120); led_go(); sleep_ms(120)
                return
        prev_p=p; sleep_ms(SAMPLE_DT_MS)

# ======================== MAIN ========================
def main():
    led_wait(); wait_ok()
    try:
        go_to_middle_and_blink()
        run_until_final_flat_robust()
    except KeyboardInterrupt:
        stop_now(); led_go()

if __name__=="__main__":
    main()
