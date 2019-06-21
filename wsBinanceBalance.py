import json

from binance.websockets import BinanceSocketManager

from config import DATABASE, BALANCE, BINANCE


def process_message(message):
    # print(message)
    if message['e'] == 'outboundAccountInfo':
        balances = message['B']
        xd = []
        for balance in balances:
            xd.append({'asset': balance['a'], 'free': balance['f']})
            DATABASE.set(BALANCE, json.dumps(xd))
        print('WS: balances updated', len(xd))
        print(xd)


def launch():
    balances = BINANCE.get_account()['balances']

    if balances is not None:
        DATABASE.set(BALANCE, json.dumps(balances))
        print('balances', len(balances), balances)
    else:
        print('websocket bibox error balances')
        return

    DATABASE.set(BALANCE, json.dumps(balances))
    print('REST: balances updated', len(balances))
    bm = BinanceSocketManager(BINANCE)
    conn_key = bm.start_user_socket(process_message)
    print(conn_key)
    bm.start()


if __name__ == '__main__':
    try:
        launch()
    except KeyboardInterrupt:
        exit()
