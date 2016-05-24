#!/usr/bin/env python3
# -*- coding: utf-8
import pydle
import json
import logging
import threading
import random
import time
from pyfiglet import Figlet
import copy
import operator
import peewee
import importlib
import subprocess

logging.basicConfig(level=logging.DEBUG)

config = json.load(open("config.json"))

BaseClient = pydle.featurize(pydle.features.RFC1459Support, pydle.features.WHOXSupport,
                             pydle.features.AccountSupport, pydle.features.TLSSupport, 
                             pydle.features.IRCv3_1Support)

class Saklobot(BaseClient):
		def __init__(self, nick, *args, **kwargs):
				super().__init__(nick, *args, **kwargs)

				self.channel = config['channel']

		def on_connect(self):
				super().on_connect()
				self.join(self.channel)
				for chan in config['auxchans']:
						self.join(chain)


client = Saklobot(config['nick'], sasl_username=config['nickserv_username'],
                sasl_password=config['nickserv_password'])
client.connect(config['server'], config['port'], tls=config['tls'])
try:
    client.handle_forever()
except KeyboardInterrupt:
    if client.connected:
        try:
            client.quit(importlib.import_module('extcmd.excuse').doit())
        except:
            client.quit('BRB NAPPING')