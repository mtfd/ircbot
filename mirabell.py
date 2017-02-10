#!/usr/bin/env python3
# -*- coding: utf-8
import pydle
import json
import logging
import importlib
import sqlite3
import pprint
import re
from lxml import html
import requests

loggingFormat = '%(asctime)s %(levelname)s:%(name)s: %(message)s'
logging.basicConfig(level=logging.DEBUG)

config = json.load(open("config.json"))

BaseClient = pydle.featurize(pydle.features.RFC1459Support, pydle.features.WHOXSupport,
                             pydle.features.AccountSupport, pydle.features.TLSSupport,
                             pydle.features.IRCv3_1Support)

LOG = logging.getLogger(__name__)
aliases = sqlite3.connect('aliases.db')


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

    # @pydle.coroutine
    def changeToken(self, message, source):
        if len(message.split()) > 2:
            return "Token cannot contain spaces."
        token = message.split(' ')[1]
        if not token:
            return "Token must not be empty."
        # admin = yield self.isAdmin(source)

        if self.isAdmin(source):
            print('block firing')
            # Open config.json, edit token, and save
            with open('config.json', 'r') as data_file:
                config = json.load(data_file)
                config['token'] = token
            with open('config.json', 'w') as f:
                f.write(json.dumps(config))
            config = json.load(open("config.json"))
            pprint.pprint(self.config)
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
            LOG.info('Help')
            self.message(target, "help, admin, token, aliaslist, alias add, alias rm, " + config['nick'] + ': token?')
            return

        # Say what the token is currently set to
        if message.startswith(config['nick'] + ': token?'):
            self.message(target, "Token is currently set to: " + config['token'])
            return

        # Tell a user if they are an administrator
        if message.startswith(config['token'] + "admin"):
            LOG.info('Admin check')
            admin = yield self.isAdmin(source)
            if admin:
                self.message(target, source + ': You are an administrator.')
            else:
                self.message(target, source + ': You are not an administrator.')
            return

        # Change the preceding character before commands
        if message.startswith(config['token'] + "token"):
            LOG.info('Token Change')
            response = yield self.changeToken(message, source)
            # response is a list of tuples, so
            response = [i for sub in response for i in sub]
            self.message(target, response)
            return

        # List of aliases
        if message.startswith(config['token'] + 'aliaslist'):
            LOG.info('Sending list of aliases to ' + source)
            aliases = self.get_all_aliases(target)
            # aliases is a list of tuples, so
            aliases = [i for sub in aliases for i in sub]
            LOG.info(aliases)
            msg = 'These are my aliases for this channel: ' + ', '.join(aliases)
            self.message(target, msg)

        # URL scraper
        if 'http://' in message or 'https://' in message:
            LOG.info('Trying to parse out URL from message')
            match = re.search('(http|https)://([\w_-]+(?:(?:\.[\w_-]+)+))([\w.,@?^=%&:/~+#-]*[\w@?^=%&/~+#-])?', message)
            if match is not None:
                url_title = self.scrape_url(match.group())
                self.message(target, url_title)

        # DB Alias control
        if message.startswith(config['token'] + "alias"):
            LOG.info('DB Alias control')
            parts = message.split(' ')
            if parts[1] == 'add':
                # Adding an alias
                LOG.info('Trying to add a new alias.')
                new_alias = parts[2]
                result = self.find_db_alias(target, new_alias)
                if result is not None:
                    if result[2] != source:
                        self.message(target, source + ': ' + config['token'] + new_alias +
                                     ' is already owned by ' + result[2] + ' in this channel.')
                        return
                    else:
                        self.delete_db_alias(target, new_alias)

                del parts[0:3]
                definition = ' '.join(parts)
                LOG.info([new_alias, definition, source])
                self.add_db_alias(target, new_alias, source, definition)
                self.message(target, source + ': alias added.')

                return
            elif parts[1] == 'rm':
                # Removing an alias
                alias = parts[2]
                result = self.find_db_alias(target, alias)
                if result is not None:
                    if result[2] != source:
                        LOG.info('User does not own this alias.')
                        if self.isAdmin(source) is not True:
                            LOG.info('User is not admin.')
                            self.message(target, source + ': ' + config['token'] + alias +
                                         ' is already owned by ' + result[2] + ' in this channel.')
                        else:
                            self.message(target, source + ': Not implemented yet.')
                        return
                    self.delete_db_alias(target, alias)

            else:
                self.unknown_command(target, source, message)

            return

        # Possible DB alias
        if message.startswith(config['token']):
            LOG.info('Trying to see if this is a DB alias that exists.')
            parts = message.replace(config['token'], '').split(' ')
            LOG.info(parts)
            result = self.find_db_alias(target, parts[0])
            if result is not None:
                self.message(target, result[3])
                return

            self.unknown_command(target, source, message)

    def unknown_command(self, target, source, message):
        self.message(target, source + ': Alias does not exist.')
        return

    def find_db_alias(self, channel, alias):
        LOG.info('Trying to find DB alias ' + alias)
        c = aliases.cursor()
        c.execute('select * from aliases where channel = ? and alias = ?', [channel, alias])
        result = c.fetchone()
        LOG.info(result)
        return result

    def add_db_alias(self, channel, alias, owner, definition):
        c = aliases.cursor()
        LOG.info('Trying to insert an alias')
        LOG.debug([alias, owner, definition])
        c.execute("insert into aliases (channel, alias, owner, definition) values (?, ?, ?, ?)",
                  [channel, alias, owner, definition])
        aliases.commit()

    def delete_db_alias(self, channel, alias):
        result = self.find_db_alias(channel, alias)
        if result is not None:
            c = aliases.cursor()
            c.execute('delete from aliases where channel = ? and alias = ? limit 1', [channel, alias])
            aliases.commit()
            self.message(channel, 'Alias deleted.')

    def get_all_aliases(self, channel):
        LOG.info('Selecting all aliases for ' + channel)
        c = aliases.cursor()
        c.execute('select alias from aliases where channel = ?', [channel])
        results = c.fetchall()
        return results

    def scrape_url(self, url):
        page = requests.get(url)
        tree = html.fromstring(page.content)
        title = tree.xpath('//title/text()')
        return ' '.join(title)

client = Mirabell(config['nick'], sasl_username=config['nickserv_username'],
                  sasl_password=config['nickserv_password'])
client.connect(config['server'], config['port'], tls=config['tls'])

try:
    client.handle_forever()
except KeyboardInterrupt:
    if client.connected:
        try:
            client.quit(config['nick'] + ' out.')
        except:
            client.quit(importlib.import_module('extcmd.excuses').doit())
