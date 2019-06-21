import json

from config import DATABASE, GENERAL_LOG, LOG_PATH


def generate():
    log = DATABASE.get(GENERAL_LOG)
    if log is not None:
        log = json.loads(log)
        f = open(LOG_PATH + 'general.log', "w")
        for text in log:
            f.write(text + '\n')
            print(text)
        f.close()
        print('Done\nCheck {}'.format(LOG_PATH + 'general.log'))
    else:
        print('Log is empty')


if __name__ == '__main__':
    try:
        generate()
    except KeyboardInterrupt:
        exit()
