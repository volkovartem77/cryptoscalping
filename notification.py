import datetime
import smtplib as smtp
import statistics
import subprocess
import time
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from config import ROOT_PASS, E_LOGIN, E_ADDRESS, E_PASS, PREF_WALL, E_SCHEDULE, E_TIME_RANGE
from database import get_trades, convert, get_total_profit, get_total_fees
from utils import split_symbol, get_rsi_value


def get_supervisor_status():
    sudo_password = ROOT_PASS
    command = 'supervisorctl status'
    command = command.split()

    cmd1 = subprocess.Popen(['echo', sudo_password], stdout=subprocess.PIPE)
    cmd2 = subprocess.Popen(['sudo', '-S'] + command, stdin=cmd1.stdout, stdout=subprocess.PIPE)

    return cmd2.stdout.read().decode().splitlines()


def send_email(trades):
    message = MIMEMultipart("alternative")
    message["Subject"] = "Report"
    message["From"] = E_LOGIN
    message["To"] = E_ADDRESS

    # Create the plain-text and HTML version of your message
    text = """\
    Hi, over the past 12 hours, the bot made the following trades"""

    component = """"""
    for trade in trades:
        block = '''
            <tr>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
                <td>{}</td>
            </tr>'''.format(
            trade['asset'],
            trade['b_price'],
            trade['s_price'],
            'Yes' if trade['sl'] else 'No',
            trade['profit'],
            trade['rsi_5m_entry'],
            trade['rsi_1h_entry'],
            trade['rsi_5m_exit'],
            trade['rsi_1h_exit'],
            trade['price_change_percent_difference_entry'],
            trade['price_change_percent_difference_exit']
        )
        component += block

    statuses = ''
    lines = get_supervisor_status()
    for line in lines:
        block = f'<p>{line}</p>'
        statuses += block

    html = """\
    <html>
      <body>
        <p>Over the past 12 hours, the bot made {} USDT and spend {} USDT for fees<p>
        <p>The bot made the following trades<p>
        <div>
          <tr>
            <td><h3>Asset</h3></td>
            <td><h3>* Buying Price *</h3></td>
            <td><h3>Selling Price</h3></td>
            <td><h3>* Stop Loss *</h3></td>
            <td><h3>Profit</h3></td>
            <td><h3>RSI 5M Entry</h3></td>
            <td><h3>RSI 1H Entry</h3></td>
            <td><h3>RSI 5M Exit</h3></td>
            <td><h3>RSI 1H Exit</h3></td>
            <td><h3>Price change % diff Entry</h3></td>
            <td><h3>Price change % diff Exit</h3></td>
          </tr>
          {}
        </div>
        <div>
          {}
        </div>
      </body>
    </html>
    """.format('{0:.4f}'.format(get_total_profit('USDT')), '{0:.4f}'.format(get_total_fees(PREF_WALL, 'USDT')), component, statuses)

    # Turn these into plain/html MIMEText objects
    part1 = MIMEText(text, "plain")
    part2 = MIMEText(html, "html")

    # Add HTML/plain-text parts to MIMEMultipart message
    # The email client will try to render the last part first
    message.attach(part1)
    message.attach(part2)

    server = smtp.SMTP_SSL('smtp.yandex.com')
    server.set_debuglevel(1)
    server.ehlo(E_LOGIN)
    server.login(E_LOGIN, E_PASS)
    server.auth_plain()
    server.sendmail(E_LOGIN, E_ADDRESS, message.as_string())
    server.quit()


def make_stats(hours):
    timestamp = int(time.time()) - hours * 3600
    trades = get_trades()
    signals = list(dict.fromkeys(list(x['signal_id'] for x in trades)))
    signals_list = []
    for signal in signals:
        s_time = 9999999999
        s_symbol = ''
        buy_prices = []
        sell_prices = []
        is_stop_loss = False
        s_rsi_5m_entry = 0
        s_rsi_1h_entry = 0
        s_rsi_5m_exit = 0
        s_rsi_1h_exit = 0
        price_change_percent_difference_entry = 0
        price_change_percent_difference_exit = 0
        for trade in trades:
            if trade['signal_id'] == signal:
                s_symbol = trade['symbol']
                if trade['date_create'] < s_time:
                    s_time = trade['date_create']
                if trade['side'] == 'BUY':
                    buy_prices.append(trade['price'])
                if trade['side'] == 'SELL':
                    sell_prices.append(trade['price'])
                if trade['type'] == 'SL':
                    is_stop_loss = True
                if trade['type'] == 'Entry':
                    s_rsi_5m_entry = str(trade['rsi_5m'])
                    s_rsi_1h_entry = str(trade['rsi_1h'])
                    price_change_percent_difference_entry = str(trade['price_change_percent_difference'])
                if trade['type'] == 'SL' or trade['type'] == 'TP':
                    s_rsi_5m_exit = str(trade['rsi_5m'])
                    s_rsi_1h_exit = str(trade['rsi_1h'])
                    price_change_percent_difference_exit = str(trade['price_change_percent_difference'])

        if s_time >= timestamp:
            s_buy_price = statistics.mean(buy_prices) if buy_prices != [] else 0
            s_sell_price = statistics.mean(sell_prices) if sell_prices != [] else 0
            s_profit = "{0:.6f}".format(convert(split_symbol(s_symbol)['base'], s_sell_price - s_buy_price, PREF_WALL))
            signals_list.append({
                'asset': s_symbol,
                'b_price': s_buy_price,
                's_price': s_sell_price,
                'sl': is_stop_loss,
                'profit': s_profit,
                'rsi_5m_entry': s_rsi_5m_entry,
                'rsi_1h_entry': s_rsi_1h_entry,
                'rsi_5m_exit': s_rsi_5m_exit,
                'rsi_1h_exit': s_rsi_1h_exit,
                'price_change_percent_difference_entry': price_change_percent_difference_entry,
                'price_change_percent_difference_exit': price_change_percent_difference_exit
            })
    return signals_list


def launch():
    print('### notification started ###')
    flag = True
    while True:
        time.sleep(1)
        time_now = datetime.datetime.utcnow().strftime('%H:%M')
        if time_now in E_SCHEDULE:
            if flag:
                stats = make_stats(E_TIME_RANGE)
                if stats:
                    send_email(stats)
                    flag = False
        else:
            flag = True


if __name__ == '__main__':
    try:
        launch()
    except KeyboardInterrupt:
        exit()

# stats = make_stats(E_TIME_RANGE,  redis.StrictRedis(host='localhost', port=6379, decode_responses=True))
# send_email(stats)
# print(get_supervisor_status())
# print(make_stats(1200))
