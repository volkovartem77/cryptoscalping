import json
import time
import traceback

import requests

from config import VOLUME_UPDATE, EXCHANGE_INFO, TICKERS, BINANCE, DATABASE
from utils import to_err_log

t_volume = time.time() - VOLUME_UPDATE
to_mi = 200
t_mi = time.time() - to_mi


def push_market_info():
    try:
        global t_mi
        if time.time() - t_mi > to_mi:
            exchange_info = BINANCE.get_exchange_info()
            if exchange_info is not None:
                DATABASE.set(EXCHANGE_INFO, json.dumps(exchange_info))
                print('exchange_info', len(exchange_info), exchange_info)
            t_mi = time.time()
            time.sleep(0.5)
    except requests.exceptions.ConnectionError as e:
        print(type(e))
        print(traceback.format_exc())


def push_volume():
    try:
        global t_volume
        if time.time() - t_volume > VOLUME_UPDATE:
            tickers = BINANCE.get_ticker()
            if tickers is not None:
                DATABASE.set(TICKERS, json.dumps(tickers))
                print('tickers', len(tickers), tickers)
            t_volume = time.time()
            time.sleep(0.5)
    except requests.exceptions.ConnectionError as e:
        print(type(e))
        print(traceback.format_exc())


def launch():
    while True:
        try:
            push_volume()
            push_market_info()
            time.sleep(0.01)
        except KeyboardInterrupt:
            break
        except:
            to_err_log('', 'pusher error ', traceback.format_exc())
            time.sleep(5)


if __name__ == '__main__':
    try:
        launch()
    except KeyboardInterrupt:
        exit()
