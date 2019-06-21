import json
import time
import traceback
from datetime import datetime
from decimal import Decimal

import math

from pyti.stochrsi import stochrsi as rsi
from pyti.simple_moving_average import simple_moving_average as sma

from config import ERR_LOG_PATH, GENERAL_LOG, LOG_LENGTH, TICKERS, DATABASE, RSI_PERIOD, PREF_WALL, VOLUME_THRESHOLD, \
    EXCHANGE_INFO, BALANCE, MIN_QTY
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


def get_balance2(asset):
    balances = DATABASE.get(BALANCE)
    if balances is not None:
        balances = json.loads(balances)
        print(balances)
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


def check_quantity(symbol, min_quantity, balance, min_notional, quantity_quote, asset, quantity_base, base):
    if min_quantity > balance:
        to_general_log(symbol, 'Not enough balance. {} {} Required {} {}'.format(balance, asset, min_quantity, asset))
        return False

    if quantity_quote < min_notional:
        to_general_log(symbol, 'Quantity is too low. {} {} Rise minimal BNB quantity'.format(quantity_base, base))
        return False
    return True


def get_qty(symbol, side, quantity, cumulative_quote_qty, precision):
    to_general_log(symbol, 'get_qty: {} quantity {} precision {}'.format(side, quantity, precision))
    if side == 'sell' and get_symbol_type(symbol):
        ask_price = get_current_price(symbol, 'ask')
        if ask_price is None:
            return
        quantity = cumulative_quote_qty / ask_price
    return round_dwn(quantity, precision)


def get_symbol_type(symbol):
    return split_symbol(symbol)['base'] == PREF_WALL


def get_quantity(symbol, side):
    base = split_symbol(symbol)['base']
    quote = split_symbol(symbol)['quote']
    min_notional = get_min_notional(symbol)
    precision = get_precision(symbol)

    if side == 'buy':
        ask_price = get_current_price(symbol, 'ask')
        balance_quote = get_balance2(quote)
        print('BUY balance_quote', balance_quote)

        if quote == PREF_WALL:
            min_quantity = round(MIN_QTY, 8)
            quantity_quote = min_quantity
        else:
            min_quantity = round(MIN_QTY * ask_price, 8)
            quantity_quote = balance_quote

        quantity_base = round_dwn(quantity_quote / ask_price, precision)

        if check_quantity(symbol, min_quantity, balance_quote, min_notional,
                          quantity_quote, quote, quantity_base, base):
            print('quantity_base', quantity_base)
            return quantity_base

    if side == 'sell':
        bid_price = get_current_price(symbol, 'bid')
        balance_base = get_balance2(base)
        print('SELL balance_base', balance_base)

        if quote == PREF_WALL:
            min_quantity = round(MIN_QTY / bid_price, 8)
            quantity_base = round_dwn(balance_base, precision)
        else:
            min_quantity = round(MIN_QTY, 8)
            quantity_base = round_dwn(min_quantity, precision)

        quantity_quote = quantity_base * bid_price

        if check_quantity(symbol, min_quantity, balance_base, min_notional,
                          quantity_quote, base, quantity_base, base):
            print('quantity_base', quantity_base)
            return quantity_base


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
            order_timestamp=order['transactTime'],
            date_create=int(time.time())
        )
        trade.save()
