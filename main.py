import os
import re

import telegram.constants
from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.ext import Updater

from livisi.backend import Livisi
from utils import restricted, logging

proxy = os.environ.get('PROXY')
request_kwargs = {
    'proxy_url': proxy
} if proxy and os.environ.get('PROXY_FOR_TELEGRAM', 'n').lower().startswith('y') \
    else None

updater = Updater(token=os.environ.get('BOT_TOKEN'), use_context=True, request_kwargs=request_kwargs)
dispatcher = updater.dispatcher

thermo_backend = Livisi(username=os.environ.get('LIVISI_USERNAME'),
                        password=os.environ.get('LIVISI_PASSWORD'),
                        redis_host=os.environ.get('REDIS_HOST'),
                        proxy=proxy)

NEWS_MARKUP = 'Nachrichten'
MANUAL_THERMOSTATS = 'Manuelle Thermostate'
MAIN_MARKUP = ReplyKeyboardMarkup([[NEWS_MARKUP, MANUAL_THERMOSTATS]])


@restricted
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Willkommen beim SmartChurch-Bot', parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)


@restricted
def news(update: Update, context: CallbackContext):
    try:
        messages = thermo_backend.get_messages()
        if not messages:
            msg = 'Keine Nachrichten gefunden'
        else:
            msg = ''
            for device_name, entries in messages.items():
                msg += f'<pre>{device_name}</pre>\n'
                for entry in entries:
                    msg += f'- {entry["type"]}\n'
                msg += '\n'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(str(e), reply_markup=MAIN_MARKUP)


@restricted
def device_state(update: Update, context: CallbackContext):
    try:
        device_states = thermo_backend.get_device_states()
        msg = ''
        for mode, location_data in device_states.items():
            msg += f'<b>{mode.capitalize()}</b>\n'
            for location_name, devices in location_data.items():
                msg += f'<pre>{location_name}</pre>\n'
                for device in devices:
                    msg += f'{device["name"]}: /TA{device["local_index"]}\n'

                msg += '\n'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(str(e), reply_markup=MAIN_MARKUP)


@restricted
def device_state_auto(update: Update, context: CallbackContext):
    try:
        text = update.message.text
        index = int(re.match('/TA([0-9]+)', text).group(1))
        new_state = 'Auto'  # Auto / Manu
        if thermo_backend.change_device_state(index, state=new_state):
            msg = f'Thermostat wurde erfolgreich auf {new_state} gestellt'
        else:
            msg = 'Es ist ein Fehler aufgetreten'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(str(e), reply_markup=MAIN_MARKUP)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(MessageHandler(Filters.text(NEWS_MARKUP), news))
dispatcher.add_handler(MessageHandler(Filters.text(MANUAL_THERMOSTATS), device_state))
dispatcher.add_handler(MessageHandler(Filters.regex(r'/TA[0-9]+'), device_state_auto))
dispatcher.add_handler(start_handler)
updater.start_polling()
