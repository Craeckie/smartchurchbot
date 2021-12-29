import logging
from functools import wraps
import os

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)

LIST_OF_ADMINS = [int(user_id.strip()) for user_id in os.environ.get('ADMIN_IDS', '').split(',')]


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
