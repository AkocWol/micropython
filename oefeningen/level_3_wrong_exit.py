# ==== Level 3 – Wrong Exit (clean, single entry) ====
# Heenweg: kleuren (tegel-buckets) registreren tot obstakel.
# Unieke kleur (= precies 1x) kiezen (laatst gezien wint bij meerdere).
# Terugweg: achteruit tot de unieke tegel; dan afslaan en uitrijden.

_time  = __import__('time'); _math = __import__('math')
sleep_ms=_time.sleep_ms; ticks_ms=_time.ticks_ms; ticks_diff=_time.ticks_diff
atan2=_math.atan2; sqrt=_math.sqrt; pi=_math.pi; floor=_math.floor

# --- board ---
try: alvik
except NameError:
    ArduinoAlvik=__import__('arduino_alvik').ArduinoAlvik
    alvik=ArduinoAlvik(); alvik.begin()

# ---------------- Tunables ----------------
SPEED_FWD=22      # voorwaarts pad
SPEED_BACK=-18    # achteruit zoeken
SPEED_EXIT=26     # na bocht uitrijden
TURN_MS=700       # duur pivot
EXIT_RUN_MS=1200  # uitrijden na bocht
SAMPLE_MS=40
TILE_DWELL=4      # samples nodig om nieuwe tegel te bevestigen
COLOR_H_BINS=12   # hue bins
COLOR_V_BINS=2    # brightness bins
DELTA_TILE_TOL=1  # bin-tolerantie
END_STOP_CM=16    # einde-pad drempel
END_TIMEOUT_MS=18000
BACK_TIMEOUT_MS=18000
# ------------------------------------------

# -------- LEDs --------
def leds(r,g,b):
    try:
        alvik.left_led.set_color(1 if r else 0,1 if g else 0,1 if b else 0)
        alvik.right_led.set_color(1 if r else 0,1 if g else 0,1 if b else 0)
    except: pass
def led_wait(): leds(0,0,1)
def led_go():   leds(0,1,0)
def led_stop(): leds(1,0,0)
def led_turn(): leds(1,0,1)
def led_scan(): leds(0,1,1)
def led_done(): leds(1,1,1)
def led_off():  leds(0,0,0)
def blink_done(n=6,on=120,off=120):
    for _ in range(n): led_done(); sleep_ms(on); led_off(); sleep_ms(off)

# -------- Buttons --------
def ok_pressed():
    try: return bool(alvik.get_touch_ok())
    except: return False
def cancel_pressed():
    try: return bool(alvik.get_touch_cancel())
    except: return False
def wait_ok_released():
    while ok_pressed(): sleep_ms(40)
def wait_ok_pressed():
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        sleep_ms(50)
def pause_until_ok():
    while not ok_pressed():
        led_wait()
        try: alvik.brake()
        except: pass
        sleep_ms(80)
    led_go(); sleep_ms(120)

# -------- Motion --------
def set_speed(l,r):
    try: alvik.set_wheels_speed(l,r)
    except: pass
def hard_stop():
    led_stop(); set_speed(0,0)
    try: alvik.brake()
    except: pass
    sleep_ms(120)
def pivot_left(ms=TURN_MS, spd=20):  led_turn(); set_speed(-spd, spd); sleep_ms(ms); hard_stop()
def pivot_right(ms=TURN_MS, spd=20): led_turn(); set_speed( spd,-spd); sleep_ms(ms); hard_stop()

# -------- Distance / End --------
def front_cm():
    try:
        L,CL,C,CR,R = alvik.get_distance()
        xs=[]
        for v in (CL,C,CR):
            v=int(v)
            if v>1000: v//=10
            if 2<=v<=400: xs.append(v)
        return min(xs) if xs else None
    except: return None

def end_obstacle_detected():
    d=front_cm()
    if d is not None and d<=END_STOP_CM: return True
    for fn in ("get_bumpers","get_touch_front","is_bumper_pressed"):
        try:
            v=getattr(alvik,fn)()
            if isinstance(v,(tuple,list)):  return any(bool(x) for x in v)
            if isinstance(v,dict):          return any(bool(x) for x in v.values())
            return bool(v)
        except: pass
    return False

# -------- Color reading & buckets --------
def read_rgb01():
    for fn in ("get_color","get_rgb","get_color_rgb","get_line_color","read_color"):
        try:
            v=getattr(alvik,fn)()
            if isinstance(v,(tuple,list)) and len(v)>=3: r,g,b=float(v[0]),float(v[1]),float(v[2])
            elif isinstance(v,dict):
                r=float(v.get('r',v.get('red',0))); g=float(v.get('g',v.get('green',0))); b=float(v.get('b',v.get('blue',0)))
            else: continue
            mx=max(1.0,r,g,b)
            if mx>1.5: r/=255.0; g/=255.0; b/=255.0
            return max(0.0,min(1.0,r)), max(0.0,min(1.0,g)), max(0.0,min(1.0,b))
        except: pass
    try:
        ls=alvik.get_line_sensors() # (L,C,R)
        if isinstance(ls,(tuple,list)) and len(ls)>=3:
            r,g,b=float(ls[0]),float(ls[1]),float(ls[2])
            mx=max(1.0,r,g,b); r/=mx; g/=mx; b/=mx
            return r,g,b
    except: pass
    return 0.0,0.0,0.0

def rgb_to_hvbin(r,g,b):
    x=(2*r - g - b); y=(sqrt(3.0)*(g-b))
    ang=atan2(y,x); 
    if ang<0: ang+=2*pi
    h=ang*(180.0/pi)                 # 0..360
    hbin=int(floor((h/360.0)*COLOR_H_BINS))
    if hbin>=COLOR_H_BINS: hbin=COLOR_H_BINS-1
    v=max(r,g,b); vbin=0 if v<0.35 else 1
    return hbin,vbin

def color_bucket():
    r,g,b=read_rgb01()
    return rgb_to_hvbin(r,g,b)

# -------- Tile detection with hysteresis --------
_last_bucket=None; _dwell=0
def detect_tile_change():
    """
    Retourneert (is_new, bucket) wanneer we stabiel op een NIEUWE tegel staan.
    Geeft True exact 1x bij het bereiken van TILE_DWELL.
    """
    global _last_bucket,_dwell
    cur=color_bucket()
    if _last_bucket is None:
        _last_bucket=cur; _dwell=1
        return False,cur
    # dezelfde bin (bin-tolerantie)
    if abs(cur[0]-_last_bucket[0])<=DELTA_TILE_TOL and abs(cur[1]-_last_bucket[1])<=DELTA_TILE_TOL:
        if _dwell < TILE_DWELL:
            _dwell += 1
            if _dwell == TILE_DWELL: return True,cur
        return False,cur
    # nieuwe bin
    _last_bucket=cur; _dwell=1
    return False,cur

# -------- Core behaviours --------
def forward_across_and_record(colors_list, counts_dict):
    led_scan()
    t0=ticks_ms()
    set_speed(SPEED_FWD,SPEED_FWD)
    _=detect_tile_change()  # seed
    while True:
        if cancel_pressed():
            hard_stop(); pause_until_ok()
            led_scan(); set_speed(SPEED_FWD,SPEED_FWD)

        new,bucket=detect_tile_change()
        if new:
            colors_list.append(bucket)
            counts_dict[bucket]=counts_dict.get(bucket,0)+1

        if end_obstacle_detected():
            hard_stop(); return True
        if ticks_diff(ticks_ms(),t0)>END_TIMEOUT_MS:
            hard_stop(); return True

        sleep_ms(SAMPLE_MS)

def pick_unique_color(counts_dict, colors_list):
    # kies de LAATST GEZIENE unieke (count == 1)
    for b in reversed(colors_list):
        if counts_dict.get(b,0)==1:
            return b
    return None

def reverse_until_bucket(target_bucket):
    led_go()
    set_speed(SPEED_BACK,SPEED_BACK)
    t0=ticks_ms()
    global _last_bucket,_dwell
    _last_bucket=None; _dwell=0  # reset detectie voor terugweg

    while True:
        if cancel_pressed():
            hard_stop(); pause_until_ok()
            set_speed(SPEED_BACK,SPEED_BACK)

        new,bucket=detect_tile_change()
        # zodra we stabiel op eender welke tegel staan, check op target-match
        if _dwell>=TILE_DWELL:
            if abs(bucket[0]-target_bucket[0])<=DELTA_TILE_TOL and abs(bucket[1]-target_bucket[1])<=DELTA_TILE_TOL:
                hard_stop(); return True

        if ticks_diff(ticks_ms(),t0)>BACK_TIMEOUT_MS:
            hard_stop(); return False

        sleep_ms(SAMPLE_MS)

def exit_turn_and_go(direction="auto"):
    # kies kant met iets meer ruimte (best-effort) of forceer via parameter
    go_left=True
    if direction=="auto":
        l_ok=r_ok=0
        try:
            L,CL,C,CR,R=alvik.get_distance()
            l_ok=int(L) if isinstance(L,(int,float)) else 0
            r_ok=int(R) if isinstance(R,(int,float)) else 0
        except: pass
        go_left=(l_ok>=r_ok)
    elif direction=="right":
        go_left=False

    if go_left: pivot_left(ms=TURN_MS, spd=22)
    else:       pivot_right(ms=TURN_MS, spd=22)

    led_go(); set_speed(SPEED_EXIT,SPEED_EXIT); sleep_ms(EXIT_RUN_MS)
    hard_stop(); return True

def celebrate():
    for _ in range(3): leds(1,1,1); sleep_ms(120); led_off(); sleep_ms(80)
    for _ in range(3): set_speed(26,-26); sleep_ms(250); set_speed(-26,26); sleep_ms(250)
    hard_stop(); blink_done(6,120,120)

# ---------------- Main ----------------
def main():
    led_wait(); wait_ok_released(); wait_ok_pressed()
    try:
        while True:
            while not cancel_pressed():
                colors_list=[]; counts_dict={}
                if not forward_across_and_record(colors_list, counts_dict):
                    continue

                target=pick_unique_color(counts_dict, colors_list)
                if target is None:
                    if colors_list:
                        target=colors_list[-1]  # fallback: laatste tegel
                    else:
                        blink_done(3,160,160); return

                if reverse_until_bucket(target):
                    exit_turn_and_go("auto")
                    celebrate()
                    return
                else:
                    hard_stop(); blink_done(4,140,140); return

            hard_stop(); pause_until_ok()
    except KeyboardInterrupt:
        try: alvik.stop()
        except: pass

if __name__=="__main__":
    main()
