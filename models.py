import time
from peewee import *

from config import PROJECT_PATH

DATABASE = SqliteDatabase(PROJECT_PATH + 'storage.db')


class Trade(Model):
    order_date = TextField(null=True)
    order_time = TextField(null=True)
    signal_type = TextField(null=True)
    signal_id = TextField(null=True)
    symbol = TextField(null=True)
    side = TextField(null=True)
    price = FloatField(null=True)
    quantity = FloatField(null=True)
    quantity_asset = TextField(null=True)
    fee = FloatField(null=True)
    fee_asset = TextField(null=True)
    order_id = IntegerField(null=True)
    status = TextField(null=True)
    type = TextField(null=True)
    rsi_5m = FloatField(null=True)
    rsi_1h = FloatField(null=True)
    price_change_percent_difference = FloatField(null=True)
    order_timestamp = IntegerField(null=True)
    date_create = IntegerField(default=int(time.time()))

    class Meta:
        database = DATABASE


def initialize():
    DATABASE.connect()
    DATABASE.create_tables([Trade], safe=True)
    DATABASE.close()
