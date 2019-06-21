import json
import os

import redis
from binance.client import Client

# directories
# os.path.abspath(os.curdir)
PROJECT_PATH = os.path.abspath(os.curdir) + '/'
PROJECT_FOLDER = PROJECT_PATH.split('/')[-2]


def get_config():
    ff = open(PROJECT_PATH + 'project.conf', "r")
    config = json.loads(ff.read())
    ff.close()
    return config


# Project config
MARKET = get_config()['market']
ROOT_PASS = get_config()['root_pass']


def get_preferences():
    ff = open(PROJECT_PATH + 'preferences_' + MARKET.lower() + '.txt', "r")
    preferences = json.loads(ff.read())
    ff.close()
    return preferences


# Preferences
API_KEY = get_preferences()['api_key']
SECRET_KEY = get_preferences()['secret_key']
SYMBOLS = get_preferences()['symbols']
IGNORE_SL = get_preferences()['ignore_stop_loss_buy']
MIN_QTY = float(get_preferences()['minimal_quantity'])
PREF_WALL = get_preferences()['preferred_wallet']
MEASURE = get_preferences()['measure_asset']
VOLUME_THRESHOLD = float(get_preferences()['volume24_threshold'])
VOLUME_UPDATE = int(get_preferences()['frequency_volume_update_sec'])
TRADE_FEE = float(get_preferences()['trade_fee'])
LOG_LENGTH = get_preferences()['max_log_length']
E_LOGIN = get_preferences()['email_login_yandex']
E_PASS = get_preferences()['email_password_yandex']
E_ADDRESS = get_preferences()['destination_address']
E_SCHEDULE = get_preferences()['notifications_schedule_utc']
E_TIME_RANGE = get_preferences()['time_range']
RSI_PERIOD = get_preferences()['rsi_period']

# Mem cache keys
GENERAL_LOG = 'general_log' + PREF_WALL
TICKERS = 'tickers' + PREF_WALL
EXCHANGE_INFO = 'exchange_info' + PREF_WALL
BALANCE = 'BinanceBalance' + PREF_WALL
RUN_MONITOR_FLAG = 'run_monitor' + MARKET

# Logging
LOG_PATH = PROJECT_PATH + 'log/'
ERR_LOG_PATH = LOG_PATH + 'errors.log'
CONF_PATH = PROJECT_PATH + PROJECT_FOLDER + '.conf'

# Other
DATABASE = redis.StrictRedis(host='localhost', port=6379, decode_responses=True)
BINANCE = Client(API_KEY, SECRET_KEY)
