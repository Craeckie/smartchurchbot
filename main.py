import os
import re

import telegram.constants
from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, RegexHandler
from telegram.ext import Updater

from livisi.backend import Livisi
from utils import restricted, logging, print_exception

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
THERMOSTAT_LIST = 'Thermostate'
MANUAL_THERMOSTATS = 'Manuelle Thermostate'
MAIN_MARKUP = ReplyKeyboardMarkup([[NEWS_MARKUP, THERMOSTAT_LIST], [MANUAL_THERMOSTATS]])
FLOOR_MARKUP_VALUES = ['DG', 'OG', 'EG', 'KG', 'Andere']
FLOOR_MARKUP = ReplyKeyboardMarkup([[floor] for floor in FLOOR_MARKUP_VALUES])


@restricted
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Willkommen beim SmartChurch-Bot', parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)


@restricted
def news(update: Update, context: CallbackContext):
    messages = None
    try:
        update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
        messages = thermo_backend.get_messages()
    except Exception as e:
        update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)
    if not messages:
        msg = 'Keine Nachrichten gefunden'
    else:
        msg = ''
        for device_name, entries in messages.items():
            try:
                msg += f'<pre>{device_name}</pre>\n'
                for entry in entries:
                    msg += f'- {entry["type"]}\n'
                msg += '\n'
            except Exception as e:
                update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)
    update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)


@restricted
def devices_floor_select(update: Update, context: CallbackContext):
    update.message.reply_text(str('Wähle ein Stockwerk'), parse_mode=ParseMode.HTML, reply_markup=FLOOR_MARKUP)


@restricted
def device_state(update: Update, context: CallbackContext):
    floor = update.message.text
    try:
        update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
        devices_by_location = thermo_backend.get_devices()
        msg = ''
        for location_name, devices in devices_by_location.items():
            if not location_name.lower().startswith(floor.lower()):
                continue
            msg += f'<b>{location_name}</b>\n'
            firstDevice = True
            for device in devices:
                if not firstDevice:
                    msg += '\n'
                temp_actual = str(device["temperature_actual"]).rjust(4, ' ')
                temp_set = str(device["temperature_set"]).rjust(4, ' ')
                msg += f'{device["name"]}\n'
                msg += f'  🚦<code> {device["mode"]}</code>\n'
                msg += f'  🌡<code> {temp_actual}°C (ist)</code>\n'
                msg += f'  🌡<code> {temp_set}°C (soll)</code>\n'
                msg += f'  💦<code> {device["humidity"]}%</code>\n'
                msg += f'  🆔<code> {device["serial_number"]}</code>\n'
                firstDevice = False

            msg += '\n'
        if not msg:
            msg = '<i>No devices found.</i>'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(print_exception(e)[:5000], reply_markup=MAIN_MARKUP)


@restricted
def manual_devices(update: Update, context: CallbackContext):
    update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
    try:
        devices = thermo_backend.get_devices(operationMode='Manu')
        msg = f'<u>Manuell</u>\n'
        for location_name, devices in devices.items():
            msg += f'<b>{location_name}</b>\n'
            for device in devices:
                msg += f'<pre>{device["name"]}</pre>\n'
                msg += f'   SN: {device["serial_number"]}\n'
                msg += f'Auf Automatisch stellen: /TA{device["local_index"]}\n'
        else:
            msg += '<i>Keine manuellen Thermostate gefunden</i>'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)


@restricted
def device_state_auto(update: Update, context: CallbackContext):
    update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
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
        update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)


@restricted
def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text('Unbekannter Befehl', reply_markup=MAIN_MARKUP)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(MessageHandler(Filters.text(NEWS_MARKUP), news))
dispatcher.add_handler(MessageHandler(Filters.text(THERMOSTAT_LIST), devices_floor_select))
dispatcher.add_handler(MessageHandler(Filters.text(FLOOR_MARKUP_VALUES), device_state))
dispatcher.add_handler(MessageHandler(Filters.regex(r'/TA[0-9]+'), device_state_auto))
dispatcher.add_handler(MessageHandler(Filters.text(MANUAL_THERMOSTATS), manual_devices))
dispatcher.add_handler(MessageHandler(~Filters.text(NEWS_MARKUP) &
                                      ~Filters.text(THERMOSTAT_LIST) &
                                      ~Filters.text(FLOOR_MARKUP_VALUES),
                                      unknown_command))
dispatcher.add_handler(start_handler)
updater.start_polling()
