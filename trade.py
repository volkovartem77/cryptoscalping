import json
import time
import traceback
from requests.exceptions import ConnectionError

from config import IGNORE_SL, DATABASE, BINANCE
from utils import get_current_candle, get_ma_value, get_current_price, get_quantity, save_trade, get_qty, \
    to_general_log, is_order_filled, remove_orders_info

signal_number = 0


def get_listen_key():
    return BINANCE.stream_get_listen_key()


def stream_keepalive(listen_key):
    try:
        BINANCE.stream_keepalive(listen_key)
        return True
    except ConnectionError:
        return False


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


def place_limit_order(symbol, side, quantity, price):
    if quantity is None:
        to_general_log(symbol, 'ERROR Qty is NONE')
        return
    if side == 'buy':
        order = BINANCE.order_limit_buy(symbol=symbol, quantity=quantity, price=price, recvWindow=10000000)
        to_general_log(symbol, 'Order {} > {}'.format(side, json.dumps(order)))
        return order
    else:
        order = BINANCE.order_limit_sell(symbol=symbol, quantity=quantity, price=price, recvWindow=10000000)
        to_general_log(symbol, 'Order {} > {}'.format(side, json.dumps(order)))
        return order


def cancel_limit_order(symbol, order_id):
    try:
        remove_orders_info('Binance', order_id)
        return BINANCE.cancel_order(symbol=symbol, orderId=order_id)
    except:
        pass


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

                # place SL limit order
                if execute_stop_loss(symbol, signal_side):
                    qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, precision)
                    to_general_log(symbol, 'get_qty: qty {}'.format(qty))
                    sl_order = place_limit_order(symbol, order_side, qty, stop_loss)
                    # save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, sl_order, 'SL')
                    # DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), price]))
                else:
                    # to_log(symbol, 'Skip stop loss for buy signal')
                    to_general_log(symbol, 'Skip stop loss for buy signal')
                    sl_order = 0

                # place TP limit order
                qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, precision)
                tp_order = place_limit_order(symbol, order_side, qty, take_profit)
                # save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, tp_order, 'TP')
                # DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), tp_order['price']]))

                while True:
                    # exit monitoring
                    if sl_order != 0:
                        if is_order_filled('Binance', sl_order['orderId']):
                            remove_orders_info('Binance', sl_order['orderId'])
                            cancel_limit_order(symbol, tp_order['orderId'])
                            save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, sl_order, 'SL')
                            DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), price]))
                            break

                    if is_order_filled('Binance', tp_order['orderId']):
                        remove_orders_info('Binance', tp_order['orderId'])
                        if sl_order != 0:
                            cancel_limit_order(symbol, sl_order['orderId'])
                        save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, tp_order, 'SL')
                        DATABASE.set(symbol + '_last_order', json.dumps([order_side.upper(), price]))
                        break
                break
            time.sleep(.1)
    except:
        to_general_log(symbol, traceback.format_exc())


# set_orders_info('Binance')
# print(place_limit_order('BNBBTC', 'buy', 1.2, 0.0028372))
# print(is_order_filled('Binance', 213819278))
# print(cancel_limit_order('BNBBTC', 213819278))
