# Dit programma gebruikt de Arduino-compatibele laag en de ArduinoAlvik-bibliotheek
# om de Alvik-robot eenvoudig te besturen met een Arduino-achtige structuur (setup/loop/cleanup).
#
# 1. Import: haalt alle Arduino-helperfuncties binnen + de ArduinoAlvik klasse.
# 2. Initialisatie: maakt een Alvik-instantie aan.
# 3. setup(): wordt één keer uitgevoerd bij de start.
#    - Initialiseert de robot met alvik.begin().
#    - Wacht kort (1 seconde) zodat alles goed klaarstaat.
# 4. loop(): wordt herhaald uitgevoerd zolang het programma draait.
#    - Zet beide LED’s rood aan.
#    - Wacht 1 seconde.
#    - Zet beide LED’s uit.
#    - Wacht 1 seconde.
#    => Resultaat: de LEDs knipperen aan/uit in een vaste cyclus.
# 5. cleanup(): wordt uitgevoerd bij het afsluiten (Ctrl+C of fout).
#    - Stopt de robot veilig met alvik.stop().
# 6. start(setup, loop, cleanup): 
#    - Start de Arduino-achtige runtime, roept eerst setup() aan,
#      herhaalt daarna loop() oneindig, en zorgt dat cleanup() wordt aangeroepen bij einde.

from arduino import *
from arduino_alvik import ArduinoAlvik

alvik = ArduinoAlvik()

def setup():
  alvik.begin()
  delay(1000)

def loop():
  alvik.left_led.set_color(1, 0, 0)
  alvik.right_led.set_color(1, 0, 0)
  delay(1000)
  alvik.left_led.set_color(0, 0, 0)
  alvik.right_led.set_color(0, 0, 0)
  delay(1000)

def cleanup():
  alvik.stop()

start(setup, loop, cleanup)