# CryptoScalping test. Deploy on server Ubuntu 16

## INSTALL PYTHON & PIP

`sudo add-apt-repository ppa:jonathonf/python-3.6`  

> if it gives  ***add-apt-repository: command not found***   than use: `sudo apt-get install software-properties-common`

**Put each command separatly, one by one**
```
sudo apt update
sudo apt install python3.6
sudo apt install python3.6-dev
sudo apt install python3.6-venv
sudo apt-get install python3-distutils
sudo apt-get install build-essential
wget https://bootstrap.pypa.io/get-pip.py
sudo python3.6 get-pip.py
sudo ln -s /usr/bin/python3.6 /usr/local/bin/python3
sudo ln -s /usr/local/bin/pip /usr/local/bin/pip3
sudo ln -s /usr/bin/python3.6 /usr/local/bin/python
```



## Install cryptoscalping and Redis

```
sudo apt-get install git-core
git clone https://github.com/volkovartem77/cryptoscalping.git
mv cryptoscalping cryptoscalping_btc
sudo apt install redis-server
sudo chown redis:redis /var/lib/redis
```

> Check **project.conf**


## Creating virtualenv using Python 3.6

```
sudo pip install virtualenv
virtualenv -p /usr/bin/python3.6 ~/cryptoscalping_btc/venv
cd ~/cryptoscalping_btc; . venv/bin/activate
sudo nano project.conf
pip install -r requirements.txt
python configure.py
deactivate
mkdir log
```


## Install & config supervisor


```
sudo apt-get install supervisor
sudo cp cryptoscalping_btc.conf /etc/supervisor/conf.d/cryptoscalping_btc.conf
sudo mkdir /var/log/cryptoscalping_btc
sudo supervisorctl reread
sudo supervisorctl reload
```



## Start APP

You can put all these commands at once

**For BTC**

```
sudo supervisorctl start wsBinance1BTC
sudo sleep 5
sudo supervisorctl start wsBinance2BTC
sudo sleep 5
sudo supervisorctl start wsBinanceBalanceBTC
sudo sleep 1
sudo supervisorctl start pusherBTC
sudo sleep 1
sudo supervisorctl start monitorBTC
sudo sleep 1
sudo supervisorctl start notificationBTC
sudo sleep 1
sudo echo LAUNCHED
sudo supervisorctl status

```

**For BNB**
```
sudo supervisorctl start wsBinance1BNB
sudo sleep 5
sudo supervisorctl start wsBinance2BNB
sudo sleep 5
sudo supervisorctl start wsBinanceBalanceBNB
sudo sleep 1
sudo supervisorctl start pusherBNB
sudo sleep 1
sudo supervisorctl start monitorBNB
sudo sleep 1
sudo supervisorctl start notificationBNB
sudo sleep 1
sudo echo LAUNCHED
sudo supervisorctl status

```


## Useful commands

Generate log file
```
cd ~/cryptoscalping_btc; . venv/bin/activate; python generate_log_file.py; deactivate
```

Download log file
```
scp root@165.22.107.205:/root/cryptoscalping_btc/log/general.log ./
```

Download errors file
```
scp root@165.22.107.205:/root/cryptoscalping_btc/log/errors.log ./
```

Download storage.db (all trades made)
```
scp root@165.22.107.205:/root/cryptoscalping_btc/storage.db ./
```


