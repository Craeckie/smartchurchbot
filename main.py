import os
import re

import telegram.constants
from telegram import Update, ReplyKeyboardMarkup, ParseMode
from telegram.ext import CallbackContext, CommandHandler, MessageHandler, Filters, RegexHandler, ConversationHandler
from telegram.ext import Updater

from livisi.backend import Livisi
from livisi.config import Config
from utils import restricted, logging, print_exception, sort_floors

proxy = os.environ.get('PROXY')
request_kwargs = {
    'proxy_url': proxy
} if proxy and os.environ.get('PROXY_FOR_TELEGRAM', 'n').lower().startswith('y') \
    else None

updater = Updater(token=os.environ.get('BOT_TOKEN'), use_context=True, request_kwargs=request_kwargs)
dispatcher = updater.dispatcher

config = Config(
    base_url=os.environ.get('LIVISI_BASE_URL', 'https://api.services-smarthome.de/'),
    login_url=os.environ.get('LIVISI_LOGIN_URL', 'https://auth.services-smarthome.de/authorize?response_type=code&client_id=35903586&redirect_uri=https%3A%2F%2Fhome.livisi.de%2F%23%2Fauth&scope=&lang=de-DE&state=1065019c-f600-41d4-9037-c65830ad199a'),
    username=os.environ.get('LIVISI_USERNAME', 'admin'),
    password=os.environ.get('LIVISI_PASSWORD'),
    redis_host=os.environ.get('REDIS_HOST', 'localhost'),
    proxy=proxy
)
thermo_backend = Livisi(config)

NEWS_MARKUP = 'Nachrichten'
THERMOSTAT_LIST = 'Stockwerk'
MANUAL_THERMOSTATS = 'Manuelle Thermostate'
DEFECTIVE_THERMOSTATS = 'Durchlaufende'
MAX_TEMPERATURE = 'Max. Temperature einstellen'
MAIN_MARKUP = ReplyKeyboardMarkup([[NEWS_MARKUP], [THERMOSTAT_LIST, MANUAL_THERMOSTATS, DEFECTIVE_THERMOSTATS], [MAX_TEMPERATURE]])
OTHER_FLOOR = 'Andere'
FLOOR_MARKUP_VALUES = ['DG', 'OG', 'EG', 'KG', OTHER_FLOOR]
FLOOR_MARKUP = ReplyKeyboardMarkup([[floor] for floor in FLOOR_MARKUP_VALUES])
CANCEL_MARKUP = u'❌ Abbrechen'


@restricted
def start(update: Update, context: CallbackContext):
    update.message.reply_text('Willkommen beim SmartChurch-Bot', parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)


@restricted
def news(update: Update, context: CallbackContext):
    messages = None
    try:
        update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
        messages = thermo_backend.get_messages(byType=True)
    except Exception as e:
        update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)
    if not messages:
        msg = 'Keine Nachrichten gefunden'
    else:
        msg = ''
        for type, entries in messages.items():
            try:
                msg += f'<pre>{type}</pre>\n'
                for entry in sorted(entries, key=lambda e: sort_floors(e['location'])):
                    if entry['location']:
                        msg += f'{entry["location"]}: {entry["name"]}\n'
                    else:
                        msg += f'{entry["name"]}\n'
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
            if floor == OTHER_FLOOR:
                # If current location is not on any floor
                if any(floor for floor in set(FLOOR_MARKUP_VALUES) - set([OTHER_FLOOR])
                           if location_name.lower().startswith(floor.lower())):
                    continue
            elif not location_name.lower().startswith(floor.lower()):
                continue
            msg += f'<b>{location_name}</b>\n'
            firstDevice = True
            for device in devices:
                if not firstDevice:
                    msg += '\n'
                temp_actual = str(device["temperature_actual"]).rjust(4, ' ')
                temp_set = str(device["temperature_set"]).rjust(4, ' ')
                temp_min = str(device["temperature_min"]).rjust(4, ' ')
                temp_max = str(device["temperature_max"]).rjust(4, ' ')
                mode_style = 'code' if device['mode'] == 'Auto' else 'b'
                msg += f'{device["name"]}\n'
                msg += f'  🚦<{mode_style}> {device["mode"]}</{mode_style}>\n'
                msg += f'  🌡<code> {temp_actual}°C (ist)</code>\n'
                msg += f'  🌡<code> {temp_set}°C (soll)</code>\n'
                msg += f'  ⬆️<code> {temp_max}°C (max)</code>\n'
                msg += f'  ⬇️<code> {temp_min}°C (min)</code>\n'
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
        for location_name, devices in sorted(devices.items(), key=lambda d: sort_floors(d[0])):
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
def defective_devices(update: Update, context: CallbackContext):
    update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
    try:
        devices = thermo_backend.get_devices(minActualTemp=25)
        msg = f'<u>Wahrscheinlich durchlaufend</u>\n'
        for location_name, devices in sorted(devices.items(), key=lambda d: sort_floors(d[0])):
            msg += f'<b>{location_name}</b>\n'
            for device in devices:
                temp_actual = str(device["temperature_actual"]).rjust(4, ' ')
                temp_set = str(device["temperature_set"]).rjust(4, ' ')

                msg += f'<pre>{device["name"]}</pre>\n'
                msg += f'  🌡<code> {temp_actual}°C (ist)</code>\n'
                msg += f'  🌡<code> {temp_set}°C (soll)</code>\n'
                msg += f'   SN: {device["serial_number"]}\n'
        if not devices:
            msg += '<i>Keine durchlaufenden Thermostate gefunden</i>\n<i>(>= 25°C)</i>'
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
def device_max_temperature_ask(update: Update, context: CallbackContext):
    update.message.reply_text('Gib die Temperatur ein:',
                              parse_mode=ParseMode.HTML,
                              reply_markup=ReplyKeyboardMarkup([[CANCEL_MARKUP]]))
    return MAX_TEMPERATURE


@restricted
def device_max_temperature_change(update: Update, context: CallbackContext):
    update.message.reply_chat_action(action=telegram.ChatAction.TYPING)
    try:
        temperature = float(update.message.text)
        count = thermo_backend.change_devices_max_temperature(temperature)
        if count:
            msg = f'{count} Thermostate wurden erfolgreich auf die neue Maximal-Temperatur gestellt'
        else:
            msg = 'Es ist ein Fehler aufgetreten'
        update.message.reply_text(str(msg), parse_mode=ParseMode.HTML, reply_markup=MAIN_MARKUP)
    except Exception as e:
        update.message.reply_text(print_exception(e), reply_markup=MAIN_MARKUP)
    return ConversationHandler.END


@restricted
def cancel(update: Update, context: CallbackContext):
    update.message.reply_text('Aktion abgebrochen', reply_markup=MAIN_MARKUP)
    return ConversationHandler.END

@restricted
def unknown_command(update: Update, context: CallbackContext):
    update.message.reply_text('Unbekannter Befehl', reply_markup=MAIN_MARKUP)


start_handler = CommandHandler('start', start)
dispatcher.add_handler(MessageHandler(Filters.text(NEWS_MARKUP), news))
dispatcher.add_handler(MessageHandler(Filters.text(THERMOSTAT_LIST), devices_floor_select))
dispatcher.add_handler(MessageHandler(Filters.text(FLOOR_MARKUP_VALUES), device_state))
dispatcher.add_handler(MessageHandler(Filters.regex(r'/TA[0-9]+'), device_state_auto))
dispatcher.add_handler(MessageHandler(Filters.text(MANUAL_THERMOSTATS), manual_devices))
dispatcher.add_handler(MessageHandler(Filters.text(DEFECTIVE_THERMOSTATS), defective_devices))

max_temperature_handler = ConversationHandler(
    entry_points=[MessageHandler(Filters.text(MAX_TEMPERATURE), device_max_temperature_ask)],
    states={
        MAX_TEMPERATURE: [MessageHandler(Filters.text &
                                         ~Filters.command &
                                         ~Filters.text(CANCEL_MARKUP), device_max_temperature_change)],
    },
    fallbacks=[MessageHandler(Filters.text(CANCEL_MARKUP), cancel)]
)
dispatcher.add_handler(max_temperature_handler)

dispatcher.add_handler(MessageHandler(~Filters.text(NEWS_MARKUP) &
                                      ~Filters.text(THERMOSTAT_LIST) &
                                      ~Filters.text(FLOOR_MARKUP_VALUES),
                                      unknown_command))
dispatcher.add_handler(start_handler)
updater.start_polling()
