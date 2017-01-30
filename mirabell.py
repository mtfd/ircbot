#!/usr/bin/env python3
# -*- coding: utf-8
import pydle
import json
import logging
import importlib

loggingFormat = '%(asctime)s %(levelname)s:%(name)s: %(message)s'
logging.basicConfig(level=logging.DEBUG)

config = json.load(open("config.json"))

BaseClient = pydle.featurize(pydle.features.RFC1459Support, pydle.features.WHOXSupport,
                             pydle.features.AccountSupport, pydle.features.TLSSupport,
                             pydle.features.IRCv3_1Support)


class Mirabell(BaseClient):

    def __init__(self, nick, *args, **kwargs):
        super().__init__(nick, *args, **kwargs)
        self.channel = config['channel']  # Main channel set in config
        self.currentChannels = []  # List of current channels the bot is in

    def on_connect(self):
        super().on_connect()
        self.join(self.channel)
        # join any other channels you want, defined in config
        for chan in config['auxchans']:
            self.join(chan)
            self.currentChannels.append(chan)

    @pydle.coroutine
    def changeToken(self, message, source):
        if len(message.split()) > 2:
            return "Token cannot contain spaces."
        token = message.split(' ')[1]
        if not token:
            return "Token must not be empty."
        admin = yield self.isAdmin(source)

        if admin:
            return "Token changed to " + token
        else:
            return "You must be an admin to change the token."

    @pydle.coroutine
    def isAdmin(self, nickname):
        admin = False
        if nickname in config['admin']:
            admin = True
        return admin

    @pydle.coroutine
    def on_message(self, target, source, message):
        super().on_message(target, source, message)

        # Display a list of all bot features.
        if message.startswith(config['token'] + "help"):
            features = [
                "admin: tell a user if they have admin privileges or not.",
                "token: change bot token if admin"
            ]
            self.message(target, "Here are the things I can do:")
            for feature in features:
                self.message(target, feature)

        # Tell a user if they are an administrator
        if message.startswith(config['token'] + "admin"):
            admin = yield self.isAdmin(source)
            if admin:
                self.message(target, source + ': You are an administrator.')
            else:
                self.message(target, source + ': You are not an administrator.')

        # Change the preceding character before commands
        if message.startswith(config['token'] + "token"):
            response = yield self.changeToken(message, source)
            self.message(target, response)


client = Mirabell(config['nick'], sasl_username=config['nickserv_username'], sasl_password=config['nickserv_password'])
client.connect(config['server'], config['port'], tls=config['tls'])

try:
    client.handle_forever()
except KeyboardInterrupt:
    if client.connected:
        try:
            client.quit(config['nick'] + ' out.')
        except:
            client.quit(importlib.import_module('extcmd.excuses').doit())
