# Dit programma bestuurt de Alvik-robot met een eenvoudige reeks bewegingen
# in een eindeloze loop via de Arduino-achtige structuur (setup/loop/cleanup).
#
# 1. Import:
#    - from arduino import * → brengt Arduino-achtige functies binnen (delay, start, etc.).
#    - from arduino_alvik import ArduinoAlvik → haalt de robotklasse binnen.
#
# 2. Initialisatie:
#    - alvik = ArduinoAlvik() maakt een instantie van de robot aan.
#
# 3. setup():
#    - Wordt één keer uitgevoerd bij de start.
#    - Initialiseert de robot met alvik.begin().
#    - Wacht kort (1 seconde) zodat de robot klaar is.
#
# 4. loop():
#    - Wordt oneindig herhaald.
#    - Laat de robot:
#        a) 2 seconden vooruit rijden (beide wielen snelheid 10).
#        b) 2 seconden links draaien (linkerwiel stil, rechterwiel snelheid 20).
#        c) 2 seconden rechts draaien (rechterwiel stil, linkerwiel snelheid 20).
#        d) 2 seconden achteruit rijden (beide wielen snelheid -10).
#    - Herhaalt deze cyclus eindeloos.
#
# 5. cleanup():
#    - Wordt aangeroepen bij afsluiten (Ctrl+C of fout).
#    - Stopt de robot veilig met alvik.stop().
#
# 6. start(setup, loop, cleanup):
#    - Start de runtime:
#      * Roept setup() één keer aan.
#      * Herhaalt loop() eindeloos.
#      * Roept cleanup() aan bij afsluiten.

from arduino import *
from arduino_alvik import ArduinoAlvik

alvik = ArduinoAlvik()

def setup():
  alvik.begin()
  delay(1000)

def loop():
  # Drive forward
  alvik.set_wheels_speed(10,10)
  delay(2000)
  # Turn left
  alvik.set_wheels_speed(0,20)
  delay(2000)
  # Turn right
  alvik.set_wheels_speed(20,0)
  delay(2000)
  # Drive backwards
  alvik.set_wheels_speed(-10,-10)
  delay(2000)

def cleanup():
  alvik.stop()

start(setup, loop, cleanup)