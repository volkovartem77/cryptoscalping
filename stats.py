import os

from config import PROJECT_PATH


def to_excel_log(data):
    general_log_path = PROJECT_PATH + 'balances_log.csv'

    if os.path.exists(general_log_path) is False:
        header = ''
        for column in list(data.keys()):
            header += column + ';'
        f = open(general_log_path, "a")
        f.write(header + '\n')
        f.close()

    line = ''
    for column in list(data.keys()):
        line += data[column] + ';'
    if line != '':
        f = open(general_log_path, "a")
        f.write(line + '\n')
        f.close()


def update_balances(b_client):
    balances = b_client.get_account()['balances']
    data = dict({balance['asset']: balance['free'] for balance in balances})
    to_excel_log(data)
