#!/usr/bin/env python3
import json
import random
helptext = "Outputs a random BOFH excuse."

excuseslist = json.load(open("lists/excuses.json"))
def doit():
  return random.choice(excuseslist)