import json
import time
import traceback

from requests.exceptions import ConnectionError

from config import IGNORE_SL, BINANCE, PERCENT_SL, PERCENT_TP
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


def is_close_to_take_profit(symbol, side, entrance_point, take_profit, percent):
    if side == 'buy':
        tp_trigger = entrance_point + ((take_profit - entrance_point) * percent / 100)
        # print(symbol, side, 'price', get_current_price(symbol, 'ask'), 'tp_trigger', tp_trigger)
        return True if get_current_price(symbol, 'ask') >= tp_trigger else False
    else:
        tp_trigger = entrance_point - ((entrance_point - take_profit) * percent / 100)
        print(symbol, side, 'price', get_current_price(symbol, 'bid'), 'sl_trigger', tp_trigger)
        return True if get_current_price(symbol, 'bid') <= tp_trigger else False


def is_close_to_stop_loss(symbol, side, entrance_point, stop_loss, percent):
    if side == 'buy':
        sl_trigger = entrance_point - ((entrance_point - stop_loss) * percent / 100)
        # print(symbol, side, 'price', get_current_price(symbol, 'ask'), 'sl_trigger', sl_trigger)
        return True if get_current_price(symbol, 'ask') <= sl_trigger else False
    else:
        sl_trigger = entrance_point + ((stop_loss - entrance_point) * percent / 100)
        print(symbol, side, 'price', get_current_price(symbol, 'bid'), 'sl_trigger', sl_trigger)
        return True if get_current_price(symbol, 'bid') >= sl_trigger else False


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


def place_market_order(symbol, side, quantity, marker):
    if quantity is None:
        to_general_log(symbol, 'ERROR Qty is NONE')
        return
    if side == 'buy':
        order = BINANCE.order_market_buy(symbol=symbol, quantity=quantity, recvWindow=10000000)
        to_general_log(symbol, '{} Market order placed ({}) > {}'.format(side, marker, json.dumps(order)))
        return order
    else:
        order = BINANCE.order_market_sell(symbol=symbol, quantity=quantity, recvWindow=10000000)
        to_general_log(symbol, '{} Market order placed ({}) > {}'.format(side, marker, json.dumps(order)))
        return order


def place_limit_order(symbol, side, quantity, price, marker):
    if quantity is None:
        to_general_log(symbol, 'ERROR Qty is NONE')
        return
    if side == 'buy':
        order = BINANCE.order_limit_buy(symbol=symbol, quantity=quantity, price=price, recvWindow=10000000)
        to_general_log(symbol, '{} Limit order placed ({}) > {}'.format(side, marker, json.dumps(order)))
        return order
    else:
        order = BINANCE.order_limit_sell(symbol=symbol, quantity=quantity, price=price, recvWindow=10000000)
        to_general_log(symbol, '{} Limit order placed ({}) > {}'.format(side, marker, json.dumps(order)))
        return order


def cancel_limit_order(symbol, side, order_id, marker):
    try:
        remove_orders_info('Binance', order_id)
        order = BINANCE.cancel_order(symbol=symbol, orderId=order_id)
        to_general_log(symbol, '{} Limit order canceled ({}) > {}'.format(side, marker, json.dumps(order)))
    except:
        pass


def get_opposite_side(side):
    return 'sell' if side == 'buy' else 'buy'


def new_signal_report(symbol, side, entrance_point, stop_loss, take_profit):
    text = 'NEW SIGNAL > {} {} at {}, SL: {}, TP: {}'.format(side, symbol, entrance_point, stop_loss, take_profit)
    to_general_log(symbol, text)


def place_pending_order(symbol, signal_side, entrance_point, precision, price_precision):
    try:
        global signal_number
        signal_id = '{}_{}'.format(symbol.lower(), signal_number)

        while True:
            if is_cancel(symbol, signal_side):
                break

            # entrance point monitoring
            if is_entrance(symbol, signal_side, entrance_point):
                signal_side = get_opposite_side(signal_side)

                if signal_side == 'buy':
                    stop_loss = round(entrance_point * (1 - (PERCENT_SL / 100)), price_precision)
                    take_profit = round(entrance_point * (1 + (PERCENT_TP / 100)), price_precision)
                else:
                    stop_loss = round(entrance_point * (1 + (PERCENT_SL / 100)), price_precision)
                    take_profit = round(entrance_point * (1 - (PERCENT_TP / 100)), price_precision)

                new_signal_report(symbol, signal_side.upper(), entrance_point, stop_loss, take_profit)

                quantity = get_quantity(symbol, signal_side)
                if quantity is None:
                    return
                open_order = place_market_order(symbol, signal_side, quantity, 'Entry')
                signal_number += 1
                save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, open_order, 'Entry')
                cumulative_quote_qty = float(open_order['cummulativeQuoteQty'])
                order_side = get_opposite_side(signal_side)

                current_sl_order = 0
                current_tp_order = 0

                while True:

                    # stop loss monitoring
                    if is_close_to_stop_loss(symbol, signal_side, entrance_point, stop_loss, 80):
                        if current_sl_order == 0:

                            # cancel existed TP order
                            if current_tp_order != 0:
                                cancel_limit_order(symbol, order_side, current_tp_order['orderId'], 'TakeProfit')

                            # place SL limit order
                            if execute_stop_loss(symbol, signal_side):
                                qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, stop_loss, precision)
                                to_general_log(symbol, 'get_qty: qty {}'.format(qty))

                                current_sl_order = place_limit_order(symbol, order_side, qty, stop_loss, 'StopLoss')
                            # else:
                            #     to_general_log(symbol, 'Skip stop loss for buy signal')

                        elif is_order_filled('Binance', current_sl_order['orderId']):
                            remove_orders_info('Binance', current_sl_order['orderId'])
                            to_general_log(symbol, '{} Limit order filled (StopLoss)'.format(order_side))
                            save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, current_sl_order, 'SL')
                            break

                            # take profit monitoring
                    if is_close_to_take_profit(symbol, signal_side, entrance_point, take_profit, 80):
                        if current_tp_order == 0:

                            # cancel existed SL order
                            if current_sl_order != 0:
                                cancel_limit_order(symbol, order_side, current_sl_order['orderId'], 'StopLoss')

                            # place TP limit order
                            qty = get_qty(symbol, signal_side, quantity, cumulative_quote_qty, take_profit, precision)
                            to_general_log(symbol, 'get_qty: qty {}'.format(qty))

                            current_tp_order = place_limit_order(symbol, order_side, qty, take_profit, 'TakeProfit')

                        elif is_order_filled('Binance', current_tp_order['orderId']):
                            remove_orders_info('Binance', current_tp_order['orderId'])
                            to_general_log(symbol, '{} Limit order filled (TakeProfit)'.format(order_side))
                            save_trade('{}_SIGNAL'.format(signal_side.upper()), signal_id, current_tp_order, 'TP')
                            break
                    time.sleep(0.3)
                break
            time.sleep(.1)
    except:
        to_general_log(symbol, traceback.format_exc())


# set_orders_info('Binance')
# print(place_limit_order('BNBBTC', 'buy', 1.2, 0.0028372))
# print(is_order_filled('Binance', 213819278))
# print(cancel_limit_order('BNBBTC', 213819278))

# symbol = 'LTCBNB'
# side = 'buy'
#
# precision = get_precision(symbol)
# pip = get_pip(symbol)
# price_precision = len('{0:.10f}'.format(pip).split('.')[1].split('1')[0]) + 1
# entrance_point = round(get_current_price(symbol, 'ask' if side == 'buy' else 'bid'), price_precision)
#
# # SELL signal
# if side == 'sell':
#     stop_loss = round(entrance_point * (1 + (PERCENT_SL / 100)), price_precision)
#     take_profit = round(entrance_point * (1 - (PERCENT_TP / 100)), price_precision)
# else:
#     # BUY signal
#     stop_loss = round(entrance_point * (1 - (PERCENT_SL / 100)), price_precision)
#     take_profit = round(entrance_point * (1 + (PERCENT_TP / 100)), price_precision)
#
# print(symbol, side, 'entrance_point', entrance_point,
#       'stop_loss', stop_loss,
#       'take_profit', take_profit, 'precision', precision)
# place_pending_order(symbol, side, entrance_point, stop_loss, take_profit, prSELLecision)
#
# print('---------------------------')
# print(is_close_to_stop_loss(symbol, side, entrance_point, stop_loss, 80))
# print(is_close_to_take_profit(symbol, side, entrance_point, take_profit, 80))
# print(BINANCE.get_asset_balance('BTC'))
