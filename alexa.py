from flask import Flask
from flask_ask import Ask, statement, question, session
from nethelper import *
from self_healing import *
import json, subprocess
import requests
import time

app = Flask(__name__)
ask = Ask(app, "/")





@app.route("/")
def homepage():
   return "hi there, how ya doin?"

@ask.launch
def start_skill():
   welcome_message = 'Hello there, what would you like to do?'
   return question(welcome_message)

@ask.intent("TopologyIntent")
def share_headlines():
   hi_text = 'Topology file generated'
   draw_topology()
   return statement(hi_text)

@ask.intent("HealingIntent")
def share_headlines():
   hi_text = 'Detected and resolved network issues'
   heal_my_network() 
   return statement(hi_text)



@ask.intent("PortStatsIntent")
def share_headlines():
   return statement(switch_stats())


@ask.intent("HigestLinkIntent")
def share_headlines():
   return statement(highest_utilized_link())


@ask.intent("HighestSwitchIntent")
def share_headlines():
   return statement(highest_utilized_switch())




@ask.intent("NoIntent")
def no_intent():
   bye_text = 'I am not sure why you asked me to run then, but okay... bye'
   return statement(bye_text)


if __name__ == '__main__':
   app.run(debug=True)

