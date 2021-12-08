from functools import wraps
import os

LIST_OF_ADMINS = [int(user_id.strip()) for user_id in os.environ.get('ADMIN_IDS', '').split(',')]


def restricted(func):
    @wraps(func)
    def wrapped(update, context, *args, **kwargs):
        user_id = update.effective_user.id
        if user_id not in LIST_OF_ADMINS:
            print("Unauthorized access denied for {}.".format(user_id))
            return
        return func(update, context, *args, **kwargs)

    return wrapped
