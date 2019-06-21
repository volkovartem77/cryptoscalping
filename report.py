from config import PREF_WALL
from database import get_total_profit, get_total_fees

print('PROFIT IN USDT', get_total_profit('USDT'))
print('FEES IN USDT', get_total_fees(PREF_WALL, 'USDT'))
