import threading
import time
import traceback

import models
from config import *
from trade import place_pending_order
from utils import get_candles, get_current_candle, get_ma_value, is_allowed, get_pip, get_precision, to_general_log, \
    to_err_log, clear_general_log, get_price_change_percent_difference


def is_allowed_to_run():
    run_monitor1 = DATABASE.get(RUN_MONITOR_FLAG1)
    run_monitor2 = DATABASE.get(RUN_MONITOR_FLAG2)
    return False if (run_monitor1 is None or run_monitor1 == 'False'
                     or run_monitor2 is None or run_monitor2 == 'False') else True


def check_the_last_order(symbol, side, price):
    cache = DATABASE.get(symbol + '_last_order')
    if cache is not None:
        last_order = json.loads(cache)
        last_order_side = last_order[0]
        last_order_price = float(last_order[1])
        if side == 'BUY':
            if last_order_side == 'SELL' and last_order_price < price:
                return False
        if side == 'SELL':
            if last_order_side == 'BUY' and last_order_price > price:
                return False
    return True


def last_bars_extremum(symbol, number, side):
    last_candles = get_candles(symbol, '5M')[499 - number:499]

    if side == 'buy':
        # return max high
        return max(list(float(x[2]) for x in last_candles))

    if side == 'sell':
        # return min low
        return min(list(float(x[3]) for x in last_candles))


def check_anchor_chart(symbol, side):
    ma8 = get_ma_value(symbol, '1H', 8)
    ma21 = get_ma_value(symbol, '1H', 21)

    current_candle_high = float(get_current_candle(symbol, '1H')[2])
    current_candle_low = float(get_current_candle(symbol, '1H')[3])

    if side == 'buy':
        if ma21 < ma8 < current_candle_low:
            return True

    if side == 'sell':
        if ma21 > ma8 > current_candle_high:
            return True

    return False


def launch(symbol):
    try:
        precision = get_precision(symbol)
        pip = get_pip(symbol)
        price_precision = len('{0:.10f}'.format(pip).split('.')[1].split('1')[0]) + 1

        to_general_log(symbol, 'Start monitoring')

        while is_allowed(symbol):

            # looking for BUY signal
            if get_price_change_percent_difference(symbol) > 2:
                place_pending_order(symbol, 'buy', precision, price_precision)
                break

            # looking for SELL signal
            if get_price_change_percent_difference(symbol) > 2:
                place_pending_order(symbol, 'sell', precision, price_precision)
                break

            time.sleep(1)
    except:
        to_err_log(symbol, traceback.format_exc())


def launcher():
    clear_general_log()

    while not is_allowed_to_run():
        # to_general_log('Bot', 'monitor waiting...')
        time.sleep(5)

    for symbol in SYMBOLS:
        th = threading.Thread(target=launch, kwargs={"symbol": symbol})
        th.start()


if __name__ == '__main__':
    try:
        models.initialize()
        launcher()
    except KeyboardInterrupt:
        exit()
