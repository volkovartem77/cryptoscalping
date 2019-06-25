from config import SYMBOLS, PREF_WALL
from models import Trade
from utils import split_symbol, get_current_price


def get_total_fees_for_asset(fee_asset):
    fees = Trade.select(Trade.fee).where(Trade.fee_asset == fee_asset).dicts()
    return sum(list(fee['fee'] for fee in fees))


def get_trades():
    return list(Trade.select().dicts())


# def get_total_profit_for_pair(symbol):
#     buy_prices = Trade.select(Trade.price).where(Trade.symbol == symbol, Trade.side == 'BUY').dicts()
#     sell_prices = Trade.select(Trade.price).where(Trade.symbol == symbol, Trade.side == 'SELL').dicts()
#     if len(buy_prices) <= 0 or len(sell_prices) <= 0:
#         return
#
#     buy_prices = list(price['price'] for price in buy_prices)
#     sell_prices = list(price['price'] for price in sell_prices)
#
#     buy_prices_average = sum(buy_prices) / len(buy_prices)
#     sell_prices_average = sum(sell_prices) / len(sell_prices)
#
#     price_difference = max(buy_prices_average, sell_prices_average) - min(buy_prices_average, sell_prices_average)
#
#     buy_qty = Trade.select(Trade.quantity).where(Trade.symbol == symbol, Trade.side == 'BUY').dicts()
#     sell_qty = Trade.select(Trade.quantity).where(Trade.symbol == symbol, Trade.side == 'SELL').dicts()
#     if len(buy_qty) <= 0 or len(sell_qty) <= 0:
#         return
#
#     buy_qty = list(qty['quantity'] for qty in buy_qty)
#     sell_qty = list(qty['quantity'] for qty in sell_qty)
#
#     buy_qty_sum = sum(buy_qty)
#     sell_qty_sum = sum(sell_qty)
#
#     executed_qty = min(buy_qty_sum, sell_qty_sum)
#     print(executed_qty, price_difference)
#     profit = price_difference * executed_qty
#
#     return profit

def get_total_profit_for_pair(symbol):
    buy_prices = Trade.select(Trade.price).where(Trade.symbol == symbol, Trade.side == 'BUY').dicts()
    sell_prices = Trade.select(Trade.price).where(Trade.symbol == symbol, Trade.side == 'SELL').dicts()
    if len(buy_prices) <= 0 or len(sell_prices) <= 0:
        return

    buy_prices = list(price['price'] for price in buy_prices)
    sell_prices = list(price['price'] for price in sell_prices)

    buy_prices_average = sum(buy_prices) / len(buy_prices)
    sell_prices_average = sum(sell_prices) / len(sell_prices)

    price_difference = sell_prices_average / buy_prices_average

    buy_qty = Trade.select(Trade.quantity).where(Trade.symbol == symbol, Trade.side == 'BUY').dicts()
    sell_qty = Trade.select(Trade.quantity).where(Trade.symbol == symbol, Trade.side == 'SELL').dicts()
    if len(buy_qty) <= 0 or len(sell_qty) <= 0:
        return

    buy_qty = list(qty['quantity'] for qty in buy_qty)
    sell_qty = list(qty['quantity'] for qty in sell_qty)

    buy_qty_sum = sum(buy_qty)
    sell_qty_sum = sum(sell_qty)

    executed_qty = min(buy_qty_sum, sell_qty_sum)
    profit = (price_difference - 1) * executed_qty

    return profit


def convert(asset, quantity, market):
    if quantity == 0:
        return 0
    if asset != market:
        for symbol in SYMBOLS:
            if symbol == asset + market:
                price = get_current_price(symbol, 'bid')
                return round(quantity * price, 8)
            elif symbol == market + asset:
                price = get_current_price(symbol, 'ask')
                return round(quantity / price, 8)
    else:
        return quantity


def get_total_profit(measure):
    pairs = list(set(list(pair['symbol'] for pair in Trade.select(Trade.symbol).dicts())))
    measure_quantity = []

    for pair in pairs:
        profit = get_total_profit_for_pair(pair)
        if profit is None:
            continue
        asset = split_symbol(pair)['base']
        preferred_wallet_quantity = convert(asset, profit, PREF_WALL)
        # print(pair, '{0:.10f}'.format(profit), 'in BTC:', '{0:.10f}'.format(preferred_wallet_quantity))
        measure_quantity.append(convert(PREF_WALL, preferred_wallet_quantity, measure))

    return sum(measure_quantity)


def get_total_fees(asset_fees, measure):
    fees = get_total_fees_for_asset(asset_fees)
    return convert(asset_fees, fees, measure)


# print(get_total_fees_for_asset('BNB'))
# print(get_total_profit_for_pair('NEOBNB'))
# print(get_total_profit_for_pair('BNBBTC'))
# print(get_total_profit_for_pair('BNBETH'))

# print(get_total_profit('USDT', Client(('127.0.0.1', 11211))))
# print(get_total_fees('BNB', 'USDT', Client(('127.0.0.1', 11211))))

# bnb = convert('ETH', 0.01, 'BNB', Client(('127.0.0.1', 11211)))
# print(bnb)
# print(convert('BNB', bnb, 'USDT', Client(('127.0.0.1', 11211))))

# print(get_trades(1559192158))
