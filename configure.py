import subprocess

from config import CONF_PATH, MARKET, PROJECT_PATH, PROJECT_FOLDER

f = open(CONF_PATH, "w")
text = ''
programs = ['wsBinance1', 'wsBinance2', 'wsBinanceBalance', 'pusher', 'monitor', 'notification']
for program_name in programs:
    block = f'''
[program:{program_name + MARKET}]
command={PROJECT_PATH}venv/bin/python {PROJECT_PATH}{program_name}.py
stdout_logfile=/var/log/{PROJECT_FOLDER}/{program_name}.log
stderr_logfile=/var/log/{PROJECT_FOLDER}/{program_name}_ERR.log
stdout_logfile_maxbytes = 5MB
stderr_logfile_maxbytes = 5MB
stdout_logfile_backups = 0
stderr_logfile_backups = 0
autorestart = false
autostart = false
startsecs = 0
user=root
stopsignal=KILL
numprocs=1
\n\n\n\n'''
    text += block
f.write(text)
f.close()

command = f'''sed -i "s%os.path.abspath(os.curdir) + '/'%'{PROJECT_PATH}'%g" "config.py"'''
subprocess.call([command], shell=True)
