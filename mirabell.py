#!/usr/bin/env python3
# -*- coding: utf-8
import pydle
import json
import logging
import importlib
import pprint

logging.basicConfig(level=logging.DEBUG)

config = json.load(open("config.json"))

BaseClient = pydle.featurize(pydle.features.RFC1459Support, pydle.features.WHOXSupport,
                             pydle.features.AccountSupport, pydle.features.TLSSupport,
                             pydle.features.IRCv3_1Support)


class Mirabell(BaseClient):

    def __init__(self, nick, *args, **kwargs):
        super().__init__(nick, *args, **kwargs)
        # join main channel defined in config
        self.channel = config['channel']

    def on_connect(self):
        super().on_connect()
        # message.nick('NickServ', 'identify ' + config['nickserv_password'])
        self.join(self.channel)
        # join any other channels you want, defined in config
        for chan in config['auxchans']:
            self.join(chan)

    @pydle.coroutine
    def is_admin(self, nickname):

        admin = False

        if nickname in config['admin']:
            admin = True
        return admin

    @pydle.coroutine
    def on_message(self, target, source, message):
        super().on_message(target, source, message)

        # Tell a user if they are an administrator
        if message.startswith(config['token'] + "admin"):
            admin = yield self.is_admin(source)
            if admin:
                self.message(target, source + ': You are an administrator.')
            else:
                self.message(target, source + ': You are not an administrator.')

        if message.startswith(config['token'] + "help"):
            features = [
                "admin: tell a user if they have admin privileges or not.",
                "stuff: does stuff"
            ]
            self.message(target, "Here are the things I can do:")
            for feature in features:
                self.message(target, feature)


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
