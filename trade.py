import json
import time
import traceback

from config import IGNORE_SL, DATABASE, BINANCE
from utils import get_current_candle, get_ma_value, get_current_price, get_quantity, save_trade, get_qty, to_general_log

signal_number = 0


def is_take_profit(symbol, side, take_profit):
    if side == 'buy':
        return True if get_current_price(symbol, 'bid') >= take_profit else False
    else:
        return True if get_current_price(symbol, 'ask') <= take_profit else False


def is_stop_loss(symbol, side, stop_loss):
    if side == 'buy':
        return True if get_current_price(symbol, 'bid') <= stop_loss else False
    else:
        return True if get_current_price(symbol, 'ask') >= stop_loss else False


def is_entrance(symbol, side, price):
    if side == 'buy':
        return True if get_current_price(symbol, 'ask') >= price else False
    else:
        return True if get_current_price(symbol, 'bid') <= price else False


def is_cancel(symbol, side):
    current_candle_open = float(get_current_candle(symbol, '5M')[1])
    current_candle_close = float(get_current_candle(symbol, '5M')[4])

    if side == 'buy':
        if min(current_candle_open, current_candle_close) < get_ma_value(symbol, '5M', 21):
            return True
    else:
        if max(current_candle_open, current_candle_close) > get_ma_value(symbol, '5M', 21):
            return True
    return False


def execute_stop_loss(symbol, side):
    return False if symbol in IGNORE_SL else True
    # return False if side == 'buy' and symbol in IGNORE_SL else True


def place_market_order(symbol, side, quantity):
    if quantity is None:
        to_general_log(symbol, 'ERROR Qty is NONE')
        return
    if side == 'buy':
        order = BINANCE.order_market_buy(symbol=symbol, quantity=quantity, recvWindow=10000000)
        to_general_log(symbol, 'Order {} > {}'.format(side, json.dumps(order)))
        return order
    else:
        order = BINANCE.order_market_sell(symbol=symbol, quantity=quantity, recvWindow=10000000)
        to_general_log(symbol, 'Order {} > {}'.format(side, json.dumps(order)))
        return order


def get_opposite_side(side):
    return 'sell' if side == 'buy' else 'buy'


def place_pending_order(symbol, signal_side, price, stop_loss, take_profit, precision):
    try:
        global signal_number
        signal_id = '{}_{}'.format(symbol.lower(), signal_number)

        while True:
            if is_cancel(symbol, signal_side):
                break

            # entrance point monitoring
            if is_entrance(symbol, signal_side, price):
                quantity = get_quantity(symbol, signal_side)
                if quantity is None:
                    return
                open_order = place_market_order(symbol, signal_side, quantity)
                signal_number += 1
                save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, open_order, 'Entry')
                cumulative_quote_qty = float(open_order['cummulativeQuoteQty'])
                order_side = get_opposite_side(signal_side)

                while True:

                    # stop loss monitoring
                    if is_stop_loss(symbol, signal_side, stop_loss):
                        if execute_stop_loss(symbol, signal_side):
                            qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, precision)
                            to_general_log(symbol, 'get_qty: qty {}'.format(qty))
                            close_order = place_market_order(symbol, order_side, qty)
                            save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, close_order, 'SL')
                            DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), price]))
                        else:
                            # to_log(symbol, 'Skip stop loss for buy signal')
                            to_general_log(symbol, 'Skip stop loss for buy signal')
                        break

                    # take profit targets monitoring
                    if is_take_profit(symbol, signal_side, take_profit):
                        qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, precision)
                        close_order = place_market_order(symbol, order_side, qty)
                        save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, close_order, 'TP')
                        DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), close_order['price']]))
                        break
                break
            time.sleep(.1)
    except:
        to_general_log(symbol, traceback.format_exc())
