import os
import logging

from telegram import Update, ReplyKeyboardMarkup
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters
from telegram.ext import Updater

from livisi.backend import Livisi
from livisi.utils import login

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

updater = Updater(token=os.environ.get('BOT_TOKEN'), use_context=True)
dispatcher = updater.dispatcher

thermo_backend = Livisi(os.environ.get('LIVISI_USERNAME'), os.environ.get('LIVISI_PASSWORD'))

NEWS_MARKUP = 'Nachrichten'
MANUAL_THERMOSTATS = 'Manuelle Thermostate'
MAIN_MARKUP = ReplyKeyboardMarkup([[NEWS_MARKUP, MANUAL_THERMOSTATS]])


def start(update: Update, context: CallbackContext):
    update.message.reply_text('Willkommen beim SmartChurch-Bot', parse_mode='HTML', reply_markup=MAIN_MARKUP)


def news(update: Update, context: CallbackContext):
    messages = thermo_backend.get_messages()
    if not messages:
        msg = 'Keine Nachrichten gefunden'
    else:
        msg = '\n'.join(messages)
    update.message.reply_text(msg, reply_markup=MAIN_MARKUP)


def manual_thermostats(update: Update, context: CallbackContext):
    device_states = thermo_backend.get_device_states()
    msg = ''
    for mode in device_states.keys():
        msg += f'<b>{mode.capitalize()}</b>\n'
        for device in device_states[mode]:
            msg += f'{device["name"]}\n'  # {device["cap_id"]}\n'

        msg += '\n'
    update.message.reply_text(msg, parse_mode='HTML', reply_markup=MAIN_MARKUP)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(MessageHandler(Filters.text(NEWS_MARKUP), news))
dispatcher.add_handler(MessageHandler(Filters.text(MANUAL_THERMOSTATS), manual_thermostats))
dispatcher.add_handler(start_handler)
updater.start_polling()
