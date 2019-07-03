import threading
import time
import traceback

import models
from config import *
from trade import place_pending_order
from utils import get_candles, get_current_candle, get_ma_value, is_allowed, get_pip, get_current_price, \
    get_precision, to_general_log, to_err_log, clear_general_log


def is_allowed_to_run():
    run_monitor = DATABASE.get(RUN_MONITOR_FLAG)
    return False if run_monitor is None or run_monitor == 'False' else True


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


def new_signal_report(symbol, side, risk, entrance_point, stop_loss, take_profit):
    text = 'NEW SIGNAL > {} {} risk: {}, entrance: {}, SL: {}, TP: {}' \
        .format(side, symbol, risk, entrance_point, stop_loss, take_profit, take_profit)
    to_general_log(symbol, text)


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
            risk_threshold = 2.1 * int(get_current_price(symbol, 'bid') * (TRADE_FEE / 100) * 2 / pip)
            ma8 = get_ma_value(symbol, '5M', 8)
            ma21 = get_ma_value(symbol, '5M', 21)

            current_candle_open = float(get_current_candle(symbol, '5M')[1])
            current_candle_close = float(get_current_candle(symbol, '5M')[4])

            # looking for BUY signal
            if ma21 < ma8 < min(current_candle_open, current_candle_close) and check_anchor_chart(symbol, 'buy'):

                # waiting trigger bar for BUY
                while True:
                    current_candle = get_current_candle(symbol, '5M')
                    current_candle_close = float(current_candle[4])
                    ma8 = get_ma_value(symbol, '5M', 8)

                    if current_candle_close < ma8:
                        # to_log(symbol, 'Trigger bar for BUY')

                        # Buy stop = 3 pips above high last 5 bars
                        entrance_point = round(last_bars_extremum(symbol, 5, 'buy') + (30 * pip), price_precision)
                        # Stop loss = 3 pips below trigger bar low
                        stop_loss = round(entrance_point * (1 - (PERCENT_SL / 100)), price_precision)
                        # initial risk R
                        risk = round(entrance_point - stop_loss, price_precision)
                        # TP = risk X 1
                        take_profit = round(entrance_point * (1 - (PERCENT_TP / 100)), price_precision)

                        if risk < risk_threshold * pip:
                            # to_log(symbol, 'Risk is too low. {} < {}'.format(risk, risk_threshold))
                            break

                        if check_the_last_order(symbol, 'BUY', entrance_point) is False:
                            break

                        # trigger_bar_report(symbol, stop_loss, entrance_point, risk, take_profit)
                        new_signal_report(symbol, 'BUY', risk, entrance_point, stop_loss, take_profit)

                        place_pending_order(symbol, 'buy', entrance_point, stop_loss, take_profit, precision)
                        break

            # looking for SELL signal
            if ma21 > ma8 > max(current_candle_open, current_candle_close) and check_anchor_chart(symbol, 'sell'):

                # waiting trigger bar for SELL
                while True:
                    current_candle = get_current_candle(symbol, '5M')
                    current_candle_open = float(current_candle[1])
                    ma8 = get_ma_value(symbol, '5M', 8)

                    if current_candle_open > ma8:
                        # to_log(symbol, 'Trigger bar for SELL')

                        # Sell stop = 3 pips below low last 5 bars
                        entrance_point = round(last_bars_extremum(symbol, 5, 'sell') - (30 * pip),
                                               price_precision)
                        # Stop loss = 3 pips above trigger bar high
                        stop_loss = round(entrance_point * (1 + (PERCENT_SL / 100)), price_precision)
                        # initial risk R
                        risk = round(stop_loss - entrance_point, price_precision)
                        # TP1 = risk X 1
                        take_profit = round(entrance_point * (1 - (PERCENT_TP / 100)), price_precision)

                        if risk < risk_threshold * pip:
                            # to_log(symbol, 'Risk is too low. {} < {}'.format(risk, risk_threshold))
                            break

                        if check_the_last_order(symbol, 'BUY', entrance_point) is False:
                            break

                        # trigger_bar_report(symbol, stop_loss, entrance_point, risk, take_profit)
                        new_signal_report(symbol, 'SELL', risk, entrance_point, stop_loss, take_profit)

                        place_pending_order(symbol, 'sell', entrance_point, stop_loss, take_profit, precision)
                        break

            time.sleep(1)
    except:
        to_err_log(symbol, traceback.format_exc())


def launcher():
    clear_general_log()

    while not is_allowed_to_run():
        print('Waiting...')
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
