import logging
import traceback
from functools import wraps
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)
ids = os.environ.get('ADMIN_IDS', '').split(',')
LIST_OF_ADMINS = [int(user_id.strip()) for user_id in ids] if ids[0] else []


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            logging.warning("Unauthorized access denied for {}.".format(user_id))
            update.message.reply_text(f'Zugriff verweigert. Deine ID ist {user_id}.')
            return
        return func(update, context, *args, **kwargs)

    return wrapped


def print_exception(e):
    trace = ''.join(traceback.format_exception(type(e), e, e.__traceback__))
    msg = f"Failed!\nException: {trace}"
    return msg


def sort_floors(location: str):
    return 5 if location is None else \
           3 if location.lower().startswith('kg') else \
           2 if location.lower().startswith('eg') else \
           1 if location.lower().startswith('og') else \
           0 if location.lower().startswith('dg') else 4
