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