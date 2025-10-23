# get_distance.py — afstand uitlezen via ArduinoAlvik of alternatieve sensorfunctie
try:
    from arduino_alvik import ArduinoAlvik
    _alvik = ArduinoAlvik()
    _alvik.begin()
except ImportError:
    _alvik = None

def get_distance():
    """
    Probeert de beschikbare afstandsfunctie te gebruiken.
    Geeft centrale afstand in cm terug, of None bij fout.
    """
    if _alvik is None:
        return None

    for fn in ("get_distance_cm", "get_ultrasonic_cm", "get_front_distance", "get_distance"):
        f = getattr(_alvik, fn, None)
        if callable(f):
            try:
                v = f()
                if v is None:
                    continue
                if isinstance(v, (tuple, list)):   # meerdere sensoren → neem middelste
                    v = v[len(v)//2]
                if v > 3000:                       # mogelijk mm
                    v = v / 10
                return int(v)
            except Exception:
                pass
    return None
