from arduino_alvik import ArduinoAlvik
from time import sleep_ms
import sys

alvik = ArduinoAlvik()
alvik.begin()

# Doelwaarde (referentieafstand in cm)
reference = 10.0

# Zet beide leds groen om te tonen dat de robot klaarstaat
alvik.left_led.set_color(0, 1, 0)
alvik.right_led.set_color(0, 1, 0)

# Wacht tot de OK-knop wordt losgelaten
while alvik.get_touch_ok():
    sleep_ms(50)

# Wacht tot de OK-knop wordt ingedrukt (startsignaal)
while not alvik.get_touch_ok():
    sleep_ms(50)

try:
    while True:
        # Hoofdloop: actief rijden totdat CANCEL wordt ingedrukt
        while not alvik.get_touch_cancel():
            # Zet leds uit tijdens metingen
            alvik.left_led.set_color(0, 0, 0)
            alvik.right_led.set_color(0, 0, 0)

            # Lees afstandssensoren (L=links, CL=centraal-links, C=midden, CR=centraal-rechts, R=rechts)
            L, CL, C, CR, R = alvik.get_distance()
            print(f'C: {C}')   # Debug: toon de centrale afstand in terminal

            # Bereken afwijking t.o.v. referentie
            error = C - reference

            # Zet wielsnelheden evenredig met de error
            # (positieve error → robot rijdt vooruit, negatieve error → achteruit)
            alvik.set_wheels_speed(error*10, error*10)

            sleep_ms(100)  # korte pauze

        # Als CANCEL is ingedrukt, wacht tot gebruiker weer OK drukt
        while not alvik.get_touch_ok():
            # Zet leds weer groen als "pauze" signaal
            alvik.left_led.set_color(0, 1, 0)
            alvik.right_led.set_color(0, 1, 0)

            # Rem de robot
            alvik.brake()
            sleep_ms(100)

except KeyboardInterrupt as e:
    # Als je Ctrl+C indrukt in de terminal → stop de robot netjes
    print('over')
    alvik.stop()
    sys.exit()
