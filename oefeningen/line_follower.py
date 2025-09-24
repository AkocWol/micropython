from arduino_alvik import ArduinoAlvik
from time import sleep_ms
import sys


# Bereken de "centroid" (zwaartepunt) van de lijnsensoren
# left, center, right = waarden van de 3 lijnsensoren
# Output: error-waarde rond 0 (0 = netjes in het midden van de lijn)
def calculate_center(left: int, center: int, right: int):
    centroid = 0
    sum_weight = left + center + right               # totale "intensiteit"
    sum_values = left + 2 * center + 3 * right       # gewogen som voor positie
    if sum_weight != 0:                              # voorkom deling door nul
        centroid = sum_values / sum_weight           # bereken zwaartepunt
        centroid = 2 - centroid                      # hercentreer rond 0
    return centroid


# Initialiseer robot
alvik = ArduinoAlvik()
alvik.begin()

# PID-achtige variabelen (hier alleen P-regelaar)
error = 0
control = 0
kp = 50.0   # versterkingsfactor: hoe sterk de robot bijstuurt

# Zet beide leds blauw → wachtstand
alvik.left_led.set_color(0, 0, 1)
alvik.right_led.set_color(0, 0, 1)

# Wachten tot OK losgelaten is
while alvik.get_touch_ok():
    sleep_ms(50)

# Wachten tot gebruiker OK indrukt (startsignaal)
while not alvik.get_touch_ok():
    sleep_ms(50)

try:
    while True:
        # Hoofdloop: zolang CANCEL niet ingedrukt is
        while not alvik.get_touch_cancel():

            # Lees waarden van de lijnsensoren (tuple met 3 ints)
            line_sensors = alvik.get_line_sensors()
            print(f' {line_sensors}')   # debug-print naar terminal

            # Bereken error (afstand tot midden van de lijn)
            error = calculate_center(*line_sensors)

            # Simpele P-regelaar: corrigeer wielsnelheden
            control = error * kp

            # Feedback via leds:
            if control > 0.2:  # lijn zit meer naar rechts
                alvik.left_led.set_color(1, 0, 0)   # links rood
                alvik.right_led.set_color(0, 0, 0)
            elif control < -0.2:  # lijn zit meer naar links
                alvik.left_led.set_color(1, 0, 0)   # links rood
                alvik.right_led.set_color(0, 0, 0)
            else:                 # robot rijdt netjes in het midden
                alvik.left_led.set_color(0, 1, 0)   # beide groen
                alvik.right_led.set_color(0, 1, 0)

            # Pas motorsnelheden aan met correctie
            # basis = 30, stuur = ±control
            alvik.set_wheels_speed(30 - control, 30 + control)

            sleep_ms(100)

        # Als CANCEL is ingedrukt → pauzeer tot opnieuw OK gedrukt wordt
        while not alvik.get_touch_ok():
            alvik.left_led.set_color(0, 0, 1)   # blauw = pauze
            alvik.right_led.set_color(0, 0, 1)
            alvik.brake()                       # rem de motoren
            sleep_ms(100)

except KeyboardInterrupt as e:
    # Ctrl+C in terminal → stop motoren netjes en sluit af
    print('over')
    alvik.stop()
    sys.exit()
