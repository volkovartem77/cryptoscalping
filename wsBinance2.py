import datetime
import json
import time
import traceback

import websocket

from config import DATABASE, BINANCE, RUN_MONITOR_FLAG2, SYMBOLS
from utils import to_general_log, update_price_change_percent, init_price_change_percent, mem_cache_init_pusher


def mem_cache_init(symbol):
    time_now = datetime.datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S')
    history5m = BINANCE.get_klines(symbol=symbol, interval=BINANCE.KLINE_INTERVAL_5MINUTE)
    history1h = BINANCE.get_klines(symbol=symbol, interval=BINANCE.KLINE_INTERVAL_1HOUR)

    print(symbol, time_now, '5M')
    DATABASE.set(symbol + '5M', json.dumps(history5m))

    print(symbol, time_now, '1H')
    DATABASE.set(symbol + '1H', json.dumps(history1h))

    time.sleep(0.5)


def update_history(symbol, time_frame, kline):
    try:
        time_now = datetime.datetime.utcfromtimestamp(time.time()).strftime('%H:%M:%S')
        history = DATABASE.get(symbol + time_frame.upper())
        if history is not None:
            history = json.loads(history)
            history.pop(0)

            kline = [kline['t'], kline['o'], kline['h'],
                     kline['l'], kline['c'], kline['v'],
                     kline['T'], kline['q'], kline['n'],
                     kline['V'], kline['Q'], kline['B']]

            history.append(kline)

            print(symbol, time_now, time_frame.upper())
            DATABASE.set(symbol + time_frame.upper(), json.dumps(history))
    except:
        to_general_log(symbol, 'Connect timeout. Reconnection...')


def on_message(ws, message):
    try:
        message = json.loads(message)
        stream = message['stream']
        data = message['data']

        if '@kline' in stream:
            symbol = data['s']
            kline = data['k']
            if bool(kline['x']):
                update_history(symbol, kline['i'], kline)

        if '@ticker' in stream:
            symbol = stream.split('@')[0].upper()
            DATABASE.set(symbol, json.dumps({'bid': data['b'], 'ask': data['a']}))
            update_price_change_percent(symbol, data['P'])
            # if symbol == 'BNBBTC':
            #     print(symbol, json.dumps({'bid': data['b'], 'ask': data['a']}))

    except KeyboardInterrupt:
        pass
    except:
        print(traceback.format_exc())


def on_error(ws, error):
    to_general_log('wsBinance', f'{error}')


def on_close(ws):
    print("### closed ###")
    DATABASE.set(RUN_MONITOR_FLAG2, 'False')


def on_open(ws):
    print('### opened ###')
    mem_cache_init_pusher()
    for symbol in SYMBOLS[100:]:
        init_price_change_percent(symbol)
        mem_cache_init(symbol)
    DATABASE.set(RUN_MONITOR_FLAG2, 'True')
    print('### monitor is allowed ###')


def launch():
    while True:
        to_general_log('wsBinance', 'start websocket Binance')
        DATABASE.set(RUN_MONITOR_FLAG2, 'False')
        time.sleep(1)

        try:
            subs = ''
            count = 0
            for symbol in SYMBOLS[100:]:
                subs += symbol.lower() + '@kline_1h/'
                subs += symbol.lower() + '@kline_5m/'
                subs += symbol.lower() + '@ticker/'
                count += 1
            if subs != '':
                to_general_log('wsBinance', f'{count} pairs')
                ws = websocket.WebSocketApp(
                    "wss://stream.binance.com:9443/stream?streams={}".format(subs.strip('/')),
                    on_open=on_open,
                    on_message=on_message,
                    on_error=on_error,
                    on_close=on_close)
                ws.run_forever()
        except:
            print('wsBinance Error: websocket failed')
            print(traceback.format_exc())


if __name__ == '__main__':
    try:
        launch()
    except KeyboardInterrupt:
        exit()
