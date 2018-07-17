# -*- coding: utf-8 -*-
import pymysql
from datetime import datetime
import time
import traceback
import json as pyjson

from .actions import TelegramBotAction


conf = {}
with open('../config.json', 'r') as f:
    conf = pyjson.load(f)

DATABASE = conf['db']
BOT_API_KEY = conf['telegram']['trainer']


def connect_db():
    return pymysql.connect(host=DATABASE['host'], user=DATABASE['user'], password=DATABASE['password'], db=DATABASE['db'], charset='utf8', cursorclass=pymysql.cursors.DictCursor)


class TrainerBot(object):
    def __init__(self):
        self.conn = connect_db()

    def _readLastUpdate(self):
        try:
            with open('lastUpdate.txt', 'r') as f:
                number = f.read()

            return int(number)

        except:
            self._writeUpdate(0)
            return 0

    def _writeUpdate(self, number):
        with open('lastUpdate.txt', 'w') as f:
            f.write(str(number))

    def main(self):
        actionCtrl = TelegramBotAction(BOT_API_KEY)
        lastUpdate_id = self._readLastUpdate()
        updated_obj = actionCtrl.crawlUpdate(lastUpdate_id)

        new_lastUpdate_id = lastUpdate_id
    
        # Main logic
        for telegram_update in updated_obj:
            new_lastUpdate_id = max( new_lastUpdate_id, telegram_update.get("update_id") )
            now = datetime.utcnow()

            if telegram_update.get('message') is not None:
                # Except 'select language'
                message_obj = telegram_update['message']
                chat_id = message_obj['chat']['id']
                sentence = message_obj.get('text')
                username = message_obj['from'].get('username')
                id_external = message_obj['from'].get('id')

    
                #if username is None or username == "":
                #    message = "Oops! You've not set your Telegram username.\nPlease go to *[menu -> Setting -> Username]*, set your username, and type '/start' again."
                #    actionCtrl._sendNormalMessage(chat_id, message)
                #    return make_response("OK", 200)

                if sentence is None:
                    print("{} | {} | {} | Multimedia Error".format(now, id_external, username))
                    message = "Currently we only take text data!\nYour interest and invenstment will be our fuel to develop useful tool such as OCR contributor or text extractor from sound!"
                    actionCtrl._sendNormalMessage(chat_id, message)
    
                elif sentence == '/start':
                    print("{} | {} | {} | New user".format(now, id_external, username))
                    actionCtrl.newUser(chat_id, id_external, username)
                    actionCtrl.clearLastSourceTextId(id_external, username)
    
                    # Set source language
                    message = "Which language do you want to traslate from?"
                    data = actionCtrl.languageSelect()
                    actionCtrl._sendWithData(chat_id, message, params=data)
    
                elif sentence == 'Balance':
                    print("{} | {} | {} | Balance check".format(now, id_external, username))
                    actionCtrl.clearLastSourceTextId(id_external, username)
                    actionCtrl.checkBalance(chat_id, id_external, username)
    
                elif sentence == 'Translate':
                    print("{} | {} | {} | Get sentence".format(now, id_external, username))
                    actionCtrl.getSentence(chat_id, id_external, text_id=username)
    
                elif sentence == 'Set Language':
                    print("{} | {} | {} | Set language".format(now, id_external, username))
                    actionCtrl.clearLastSourceTextId(id_external, text_id=username)
                    ret = actionCtrl._getId(id_external, text_id=username)
                    message = "Current setting: *{}* -> *{}*\n\nWhich language do you want to traslate from?".format(ret['source_lang'], ret['target_lang'])
                    data = actionCtrl.languageSelect()
                    actionCtrl._sendWithData(chat_id, message, params=data)
    
                else:
                    print("{} | {} | {} | Set language".format(now, id_external, username))
                    ret = actionCtrl._getId(id_external, text_id=username)
                    # Translated sentence will input
                    actionCtrl.inputSentence(chat_id, id_external, sentence, text_id=username, tags="telegram")
                    actionCtrl.getSentence(chat_id, id_external, text_id=username)
    
            elif telegram_update.get('callback_query') is not None:
                # only for select language
                query_obj = telegram_update['callback_query']
                message_obj = query_obj['message']
    
                chat_id = message_obj['chat']['id']
                query_id = query_obj['id']
                username = query_obj['from'].get('username')
                id_external = query_obj['from'].get('id')
                data_arr = query_obj['data'].split('|')
                actionCtrl.clearLastSourceTextId(id_external, text_id=username)
    
                seq = data_arr[0]
                lang = data_arr[1]
    
                if seq == '1st':
                    print("{} | {} | {} | Choose first language".format(now, id_external, username))
                    ret = actionCtrl._getId(id_external, text_id=username)
                    # Store
                    actionCtrl.setSourceLanguage(chat_id, id_external, lang, username)
                    actionCtrl._answerCallbackQuery(query_id)
    
                    # Ask 2nd lang
                    message = "Cool! Then, please choose one language that you want to translate to!"
                    data = actionCtrl.languageSelect(source_lang=lang)
                    actionCtrl._sendWithData(chat_id, message, params=data)
    
                elif seq == '2nd':
                    print("{} | {} | {} | Choose second language".format(now, id_external, username))
                    # Store
                    actionCtrl.setTargetLanguage(chat_id, id_external, lang, username)
                    actionCtrl._answerCallbackQuery(query_id)
                    ret = actionCtrl._getId(id_external, text_id=username)
    
                    # Welcome message + show general keyboard
                    message  = "Settings are all done!\nCurrent setting: *{}* -> *{}*\n\nPlease press 'Translate' button below and earn point immediately!\n\n".format(ret['source_lang'], ret['target_lang'])
                    message += "*1. How to use it?*\n"
                    message += "Just press 'Translate' button and contribute data!\n\n"
    
                    message += "*2. How much point can I earn?*\n"
                    message += "Source sentence contributor: *0.1 Point*.\n"
                    message += "Translated sentence contributor: *1 Point*.\n"
                    message += "If 2 contributors are same user: *1.1 Points*.\n"
                    message += "If I translated a sentence contributed by anonymous user: *1.1 Points*.\n\n"
    
                    message += "*3. When can I use this point?*\n"
                    message += "Before launching LangChain, we'll take snapshot and give announcement about airdrop!\n"
                    keyboard = actionCtrl.normalKeyvoardSetting()
                    actionCtrl._sendWithData(chat_id, message, params=keyboard)
    
        if len(updated_obj) > 0:
            self._writeUpdate(new_lastUpdate_id+1)
            updated_obj = actionCtrl.crawlUpdate(lastUpdate_id+1)


if __name__ == "__main__":
    trainerBot = TrainerBot()
    while True:
        try:
            trainerBot.main()
        except:
            traceback.print_exc()

        time.sleep(0.5)
