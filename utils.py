import json
import time
import traceback
from datetime import datetime
from decimal import Decimal

import math

from pyti.stochrsi import stochrsi as rsi
from pyti.simple_moving_average import simple_moving_average as sma

from config import ERR_LOG_PATH, GENERAL_LOG, LOG_LENGTH, TICKERS, DATABASE, RSI_PERIOD, PREF_WALL, VOLUME_THRESHOLD, \
    EXCHANGE_INFO, BALANCE, MIN_QTY, ORDERS_INFO, PRICE_CHANGE_PERCENT, PRICE_CHANGE_PERCENT_DIFFERENCE_TIME_RANGE
from models import Trade


def to_err_log(symbol='', details='', error=''):
    f = open(ERR_LOG_PATH, "a")
    dt = datetime.now().replace(microsecond=0).isoformat().replace('T', ' ')
    log = dt + ' ' + symbol + ' ' + details + '\n' + error + '\n'
    f.write(log)
    print(log)


def clear_general_log():
    DATABASE.set(GENERAL_LOG, '[]')


def to_general_log(symbol, text):
    log = DATABASE.get(GENERAL_LOG)
    if log is None:
        log = '[]'
    log = json.loads(log)
    if len(log) > LOG_LENGTH:
        log = log[-(len(log) - 1):]

    dt = datetime.now().replace(microsecond=0).isoformat().replace('T', ' ')
    log.append(dt + ' ' + symbol + ': ' + text)
    DATABASE.set(GENERAL_LOG, json.dumps(log))
    print(dt + ' ' + symbol + ': ' + text)


def get_24_volume(symbol):
    tickers = DATABASE.get(TICKERS)
    if tickers is None:
        return
    tickers = json.loads(tickers)
    for ticker in tickers:
        if ticker['symbol'] == symbol:
            if split_symbol(symbol)['base'] == PREF_WALL:
                return float(ticker['volume'])
            return float(ticker['quoteVolume'])


def is_allowed(symbol):
    volume = get_24_volume(symbol)
    if volume is not None:
        if volume > VOLUME_THRESHOLD:
            return True
    return False


def get_pip(symbol):
    exchange_info = DATABASE.get(EXCHANGE_INFO)
    if exchange_info is None:
        return
    exchange_info = json.loads(exchange_info)
    symbols = exchange_info['symbols']
    for symbol_info in symbols:
        if symbol_info['symbol'] == symbol:
            return float(symbol_info['filters'][0]['tickSize'])


def split_symbol(symbol):
    exchange_info = DATABASE.get(EXCHANGE_INFO)
    if exchange_info is not None:
        symbols_info = json.loads(exchange_info)['symbols']
        for symbol_info in symbols_info:
            if symbol_info['symbol'] == symbol:
                return {'base': symbol_info['baseAsset'], 'quote': symbol_info['quoteAsset']}


def round_dwn(value, param=1):
    try:
        if param == 0:
            return int(value)
        return math.floor(value * math.pow(10, param)) / math.pow(10, param)
    except TypeError:
        to_err_log(f'value: {value}, param: {param}', traceback.format_exc())


def round_up(value, param=1):
    return int(value) if param == 0 else math.ceil(value * math.pow(10, param)) / math.pow(10, param)


def get_balance2(asset):
    balances = DATABASE.get(BALANCE)
    if balances is not None:
        balances = json.loads(balances)
        # print(balances)
        for balance in balances:
            if balance['asset'] == asset:
                return float(balance['free'])


def get_current_price(symbol, s):
    price = DATABASE.get(symbol)
    return float(json.loads(price)[s])


def get_min_notional(symbol):
    exchange_info = DATABASE.get(EXCHANGE_INFO)
    if exchange_info is None:
        return
    exchange_info = json.loads(exchange_info)
    symbols = exchange_info['symbols']
    for s in symbols:
        if s['symbol'] == symbol:
            for f in s['filters']:
                if f['filterType'] == 'MIN_NOTIONAL':
                    return float(f['minNotional'])


def get_precision(symbol):
    exchange_info = DATABASE.get(EXCHANGE_INFO)
    if exchange_info is None:
        return
    exchange_info = json.loads(exchange_info)
    symbols = exchange_info['symbols']
    for s in symbols:
        if s['symbol'] == symbol:
            for f in s['filters']:
                if f['filterType'] == 'LOT_SIZE':
                    step_size = Decimal(f['stepSize']).normalize()
                    return len(str(step_size).split('.')[1]) if '.' in str(step_size) else 0


def get_current_candle(symbol, time_frame):
    try:
        return json.loads(DATABASE.get(symbol + time_frame))[-2]
    except (TypeError, KeyError):
        to_err_log(symbol, f'{time_frame}', traceback.format_exc())


def get_candles(symbol, time_frame):
    try:
        return json.loads(DATABASE.get(symbol + time_frame))
    except (TypeError, KeyError):
        to_err_log(symbol, f'{time_frame}', traceback.format_exc())


def get_ma_value(symbol, time_frame, period):
    try:
        k_lines = json.loads(DATABASE.get(symbol + time_frame.upper()))
        res = list(sma(list(float(x[4]) for x in k_lines), period))
        return round(float(res[-1]), 8)
    except (TypeError, KeyError):
        to_err_log(symbol, f'{time_frame} {period}', traceback.format_exc())


def get_rsi_value(symbol, time_frame):
    try:
        k_lines = json.loads(DATABASE.get(symbol + time_frame.upper()))
        res = rsi(list(float(x[4]) for x in k_lines), RSI_PERIOD)
        return round(float(res[-1]), 2)
    except (TypeError, KeyError):
        to_err_log(symbol, f'{time_frame}', traceback.format_exc())


def get_qty(symbol, signal_side, quantity, cumulative_quote_qty, price, precision):
    to_general_log(symbol, 'get_qty: signal {}; quantity {}; precision {}'.format(signal_side, quantity, precision))
    if signal_side == 'sell' and get_symbol_type(symbol):  # BNB BTC
        quantity = cumulative_quote_qty / price
    return round_dwn(quantity, precision)


def get_symbol_type(symbol):
    return split_symbol(symbol)['base'] == PREF_WALL


def normalize_symbol(asset1, asset2):
    exchange_info = DATABASE.get(EXCHANGE_INFO)
    if exchange_info is None:
        return
    exchange_info = json.loads(exchange_info)
    symbols = list(x['symbol'] for x in exchange_info['symbols'])
    if asset1 + asset2 in symbols:
        return asset1 + asset2
    if asset2 + asset1 in symbols:
        return asset2 + asset1


def get_quantity(symbol, side):
    base = split_symbol(symbol)['base']
    quote = split_symbol(symbol)['quote']
    min_notional = get_min_notional(symbol)
    precision = get_precision(symbol)

    if side == 'buy':
        ask_price = get_current_price(symbol, 'ask')
        min_limit = round_up(min_notional / ask_price, precision)  # in base currency
        balance_quote = get_balance2(quote)

        if get_symbol_type(symbol):  # BNB BTC
            if MIN_QTY < min_limit:
                to_general_log(symbol,
                               'Minimal quantity ({} {}) is too low. Rise minimal BNB quantity up to {} {} at least'
                               .format(MIN_QTY, base, "{0:.8f}".format(min_limit), base))
                return
            min_quantity = round(MIN_QTY * ask_price, 8)
            quantity_quote = balance_quote
        else:  # LTC BNB
            if round_dwn(MIN_QTY / ask_price, precision) < min_limit:
                to_general_log(symbol,
                               'Minimal quantity ({} {}) is too low. Rise minimal BNB quantity up to {} {} at least'
                               .format(MIN_QTY, quote,
                                       "{0:.8f}".format(round_up(min_limit * ask_price, precision)), quote))
                return
            min_quantity = MIN_QTY
            quantity_quote = min_quantity

        quantity_base = round_dwn(quantity_quote / ask_price, precision)

        if balance_quote > min_quantity:
            return quantity_base
        else:
            to_general_log(symbol, 'Not enough balance. You have {} {}, but required {} {} at least'
                           .format("{0:.8f}".format(balance_quote), quote, "{0:.8f}".format(min_quantity), quote))

    if side == 'sell':
        bid_price = get_current_price(symbol, 'bid')
        min_limit = round_up(min_notional / bid_price, precision)  # in base currency
        balance_base = get_balance2(base)

        if get_symbol_type(symbol):  # BNB BTC
            if MIN_QTY < min_limit:
                to_general_log(symbol,
                               'Minimal quantity ({} {}) is too low. Rise minimal BNB quantity up to {} {} at least'
                               .format(MIN_QTY, base, "{0:.8f}".format(min_limit), base))
                return
            min_quantity = round(MIN_QTY, 8)
            quantity_base = round_dwn(min_quantity, precision)
        else:  # LTC BNB
            if round_dwn(MIN_QTY / bid_price, precision) < min_limit:
                to_general_log(symbol,
                               'Minimal quantity ({} {}) is too low. Rise minimal BNB quantity up to {} {} at least'
                               .format(MIN_QTY, quote,
                                       "{0:.8f}".format(round_up(min_limit * bid_price, precision)), quote))
                return
            min_quantity = round(MIN_QTY / bid_price, 8)
            quantity_base = round_dwn(balance_base, precision)

        if balance_base > min_quantity:
            return quantity_base
        else:
            to_general_log(symbol, 'Not enough balance. You have {} {}, but required {} {} at least'
                           .format("{0:.8f}".format(balance_base), base, "{0:.8f}".format(min_quantity), base))


def get_price_change_percent_difference(symbol):
    price_change_percents = get_price_change_percent(symbol)
    first = float(price_change_percents[str(min(list(int(x) for x in price_change_percents.keys())))])
    last = float(price_change_percents[str(max(list(int(x) for x in price_change_percents.keys())))])
    return round(max(first, last) - min(first, last), 3)


def save_trade(signal_type, signal_id, order, trade_type):
    order_date = datetime.utcfromtimestamp(order['transactTime'] / 1000).strftime('%Y-%m-%d')
    order_time = datetime.utcfromtimestamp(order['transactTime'] / 1000).strftime('%H:%M:%S')

    for fill in order['fills']:
        trade = Trade(
            order_date=order_date,
            order_time=order_time,
            signal_type=signal_type,
            signal_id=signal_id,
            symbol=order['symbol'],
            side=order['side'],
            price=float(fill['price']),
            quantity=float(fill['qty']),
            quantity_asset=split_symbol(order['symbol'])['base'],
            fee=float(fill['commission']),
            fee_asset=fill['commissionAsset'],
            order_id=order['orderId'],
            status=order['status'],
            type=trade_type,
            rsi_5m=get_rsi_value(order['symbol'], '5M'),
            rsi_1h=get_rsi_value(order['symbol'], '1H'),
            price_change_percent_difference=get_price_change_percent(order['symbol']),
            order_timestamp=order['transactTime'],
            date_create=int(time.time())
        )
        trade.save()


def format_status(status):
    if status == 'NEW':
        return False
    if status == 'FILLED':
        return True
    if status == 'CANCELED':
        return True
    if status == 'PARTIALLY_FILLED':
        return False
    if status == 'REJECTED':
        return True


def get_orders_info(exchange):
    return json.loads(DATABASE.get(exchange + ':' + ORDERS_INFO))


def set_orders_info(exchange):
    DATABASE.set(exchange + ':' + ORDERS_INFO, json.dumps({}))


def update_orders_info(exchange, order_id, symbol, side, status, price, amount, date, timestamp):
    orders = get_orders_info(exchange)

    orders.update({
        order_id: {
            'symbol': symbol,
            'side': side,
            'status': status,
            'price': price,
            'amount': amount,
            'date': date,
            'timestamp': timestamp
        }
    })
    DATABASE.set(exchange + ':' + ORDERS_INFO, json.dumps(orders))


def remove_orders_info(exchange, order_id):
    orders = get_orders_info(exchange)
    orders.pop(order_id, None)
    DATABASE.set(exchange + ':' + ORDERS_INFO, json.dumps(orders))


def is_order_filled(exchange, order_id):
    orders = get_orders_info(exchange)
    if str(order_id) in orders:
        return orders[str(order_id)]['status']


def init_price_change_percent(symbol):
    DATABASE.set(symbol + ':' + PRICE_CHANGE_PERCENT, json.dumps({}))


def get_price_change_percent(symbol):
    return json.loads(DATABASE.get(symbol + ':' + PRICE_CHANGE_PERCENT))


def set_price_change_percent(symbol, values):
    DATABASE.set(symbol + ':' + PRICE_CHANGE_PERCENT, json.dumps(values))


def update_price_change_percent(symbol, value):
    price_change_percents = json.loads(DATABASE.get(symbol + ':' + PRICE_CHANGE_PERCENT))
    remove = []
    for price_change_percent in price_change_percents:
        if int(price_change_percent) + PRICE_CHANGE_PERCENT_DIFFERENCE_TIME_RANGE < int(time.time()):
            remove.append(price_change_percent)

    for x in remove:
        price_change_percents.pop(x)

    price_change_percents.update({int(time.time()): value})
    set_price_change_percent(symbol, price_change_percents)
    # if symbol == 'BNBBTC':
    #     print(symbol, len(price_change_percents), price_change_percents)


# print(get_price_change_percent_difference('BNBBTC'))
# print(normalize_symbol('BNB', 'TUSD'))
# print(round_up(2.334, 2))
# print(get_quantity('BNBBTC', 'buy'))
# print(get_quantity('LTCBNB', 'buy'))
# print(get_quantity('BNBBTC', 'sell'))
# print(get_quantity('LTCBNB', 'sell'))
# print(get_current_price('BNBBTC', 'ask'))
