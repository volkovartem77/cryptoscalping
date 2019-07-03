import json
import threading
import time

import websocket

from config import DATABASE, BALANCE, BINANCE
from trade import stream_keepalive, get_listen_key
from utils import format_status, update_orders_info, set_orders_info


def on_message(ws, message):
    # print(type(message), message)
    message = json.loads(message)
    if 'e' in message:
        if message['e'] == 'outboundAccountInfo':
            balances = message['B']
            xd = []
            for balance in balances:
                xd.append({'asset': balance['a'], 'free': balance['f']})
                DATABASE.set(BALANCE, json.dumps(xd))
            print('WS: balances updated', len(xd))
            print(xd)
        if message['e'] == 'executionReport':
            update_orders_info('Binance',
                               message['i'],
                               message['s'],
                               message['S'],
                               format_status(message['X']),
                               message['p'], message['q'], message['O'],
                               int(time.time() * 1000))
            print('Update orders', format_status(message['X']), message)


def on_error(ws, error):
    print(error)


def on_close(ws):
    print("### closed ###")


def on_open(ws):
    print('### opened ###')

    def keep_alive():
        while True:
            lk = stream_keepalive(listen_key)
            if lk:
                time.sleep(30 * 60)
            else:
                time.sleep(30)

    th = threading.Thread(target=keep_alive)
    th.start()


if __name__ == "__main__":
    try:
        while True:
            balances = BINANCE.get_account()['balances']
            set_orders_info('Binance')

            if balances is not None:
                DATABASE.set(BALANCE, json.dumps(balances))
                print('balances', len(balances), balances)
            else:
                print('websocket bibox error balances')
                continue

            DATABASE.set(BALANCE, json.dumps(balances))
            print('REST: balances updated', len(balances))

            listen_key = get_listen_key()
            print(listen_key)

            ws = websocket.WebSocketApp(
                f"wss://stream.binance.com:9443/ws/{listen_key}",
                on_open=on_open,
                on_message=on_message,
                on_error=on_error,
                on_close=on_close)

            ws.run_forever()
            time.sleep(1)
    except KeyboardInterrupt:
        exit()
