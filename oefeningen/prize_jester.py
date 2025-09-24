# Dit programma simuleert een eenvoudige interactieve robot:
# 1. Het begroet de gebruiker en vraagt naar zijn/haar naam via input().
# 2. Daarna vraagt het of de gebruiker de robot een naam wil geven.
# 3. De robot reageert met een compliment en doet alsof hij menselijker wordt.
# 4. Met sleep() worden korte pauzes ingebouwd zodat het gesprek natuurlijker aanvoelt.
# 5. Vervolgens maakt de robot een grap (met opbouw door vertragingen).
# Kortom: een kleine interactieve chatbot die gebruiker betrekt en humor toevoegt.

from time import sleep

print("Hello! I'm a talkative robot. What's your name?")
student_name = input("Wat is jouw naam?")

print("Great meeting you, " + student_name + "! Would you like to name me?")
robot_name = input("Hoe wil je mij noemen? ")

print(f"{robot_name} is a fantastic name! I feel more human already.")

sleep(2)  # Use sleep() to make interaction feel more natural
print(f"Okay, {student_name}, time for a quick laugh:")
sleep(2)
print("Have you heard of the robot that tried to swim?")
sleep(4)
print("It shocked everyone. :D")
sleep(5)

