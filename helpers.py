import hashlib
import hmac
import random
from string import letters
from google.appengine.ext import db

secret = 'far654654dsfiuoiuisfdt'


def make_salt(length=5):
    return ''.join(random.choice(letters) for _ in xrange(length))


def make_pw_hash(email, pw, salt=None):
    if not salt:
        salt = make_salt()
    h = hashlib.sha256(email + pw + salt).hexdigest()
    return '%s,%s' % (salt, h)


def valid_pw(email, password, h):
    salt = h.split(',')[0]
    return h == make_pw_hash(email, password, salt)


def users_key(group='default'):
    return db.Key.from_path('users', group)


### cookies
def make_secure_val(val):
    return '%s|%s' % (val, hmac.new(secret, val).hexdigest())


def check_secure_val(secure_val):
    val = secure_val.split('|')[0]
    if secure_val == make_secure_val(val):
        return val


def main_key(name='default'):
    return db.Key.from_path('budgets', name)


def get_float(string):  # remove all spaces and ,->.
    correct_str = string.replace(',', '.').replace(u'\xa0', '').replace(' ', '').replace('\n', '')
    return float(correct_str)


def budget_line(line):
    return [line.title, line.total, line.total_sub, line.key().id()]


def table_line(line):
    return [line.title, line.razdel, line.podrazdel, line.statya, line.vid, line.total, line.total_sub]