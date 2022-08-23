from numpy import arctan
from ta.trend import *
from ta.momentum import *
from ta.volatility import *
from algorithmETH import AlgorithmETH
from time import time
import requests
import urllib.parse
import hashlib
import hmac
import base64
from json import dumps,loads
from time import sleep, time
import pandas as pd
import os

class AGENT:
	def __init__(self):
		# dati api
		self.api_url = "https://api.kraken.com"
		self.api_key = os.environ['API_KEY']
		self.api_sec = os.environ['API_SEC']

		# parametri
		self.tassa = 0.0054
		self.moltiplicatore = 5
		self.invest = 1 # 100%

		# algoritmi
		self.ETH = AlgorithmETH(self.tassa,self.moltiplicatore)
		self.A = [self.ETH]

		# Parametri della simulazione
		self.staticMoney = 95
		self.staticETH = 0.03703

		self.strategia = "-"
		self.current = -1
		self.currentName = ["ETH"]
		self.currentNameResult = ["XETH"]

		self.money = 0
		self.stocks = 0
		self.get_balance()
		self.dentro = False
		self.entrata = 0
		self.ora = 0

	# ========================= funzioni di gestione ========================= #
	def buy(self, now, data, forced=False, which=-1):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		if (not self.dentro and self.A[0].check_buy(-1) == True):
			self.current = 0
			self.ora = time()-60
			self.get_balance()
			spesa = self.invest*self.money
			output = self.buy_order(0)

			k = 0
			while k<8:
				sleep(10)
				flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
				if flag:
					self.entrata = price
					break
				k += 1

			self.dentro = True
			self.get_balance()
			return [True,f"Buy: Crypto:{self.stocks} {self.currentName[self.current]}({costo}*{self.moltiplicatore}={costo*self.moltiplicatore}€) / Balance:{self.money}€ || {output}"]
		elif forced:
			self.current = which
			self.ora = time()-60
			self.get_balance()
			spesa = self.invest*self.money
			output = self.buy_order(0)

			print(output)
			while True:
				sleep(10)
				flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
				print(flag,costo,tassa,price)
				if flag:
					self.entrata = price
					break
			if costo!=0:
				self.dentro = True
			self.get_balance()
			return [True,f"Buy: Crypto:{self.stocks} {self.currentName[self.current]}({costo}*{self.moltiplicatore}={costo*self.moltiplicatore}€) / Balance:{self.money}€ || {output}"]
		return [False,""]

	def sell(self, now, data, forced=False):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		if (self.dentro and self.A[self.current].check_sell(-1, self.entrata) == True) or forced:
			self.dentro = False
			output = self.sell_order(0)

			sleep(10)
			self.get_balance()

			m = self.current
			self.current = -1
			return [True,f"Sell: Crypto:{self.stocks} {self.currentName[m]} / Balance:{round(self.money,2)}€ || {output}"]
		return [False,""]

	def get_total_balance(self):
		self.get_balance()
		return f"Balance: {self.money}€ / Crypto: {self.stocks} {self.currentName[self.current]}({self.get_price()*self.stocks}€)"


	def get_current_state(self, data):
		self.A[0].df = data[0].astype(float)
		self.A[0].analyzeDf()
		return f"{self.currentName[0]}: EMAb={round(self.A[0].df[f'EMA{self.A[0].periodiB}'][-1],2)} / EMAl={round(self.A[0].df[f'EMA{self.A[0].periodiL}'][-1],2)} / Psar>={self.A[0].df['psar_di'][-1]} / ADX={round(self.A[0].df['adx'][-1],2)} / Aroon={round(self.A[0].df['aroon_indicator'][-1],2)} / Bollinger={self.A[0].df['bollinger_pband'][-1]}"


	# ========================= funzioni di comunicazione ========================= #
	def get_kraken_signature(self, urlpath, data, secret):
		postdata = urllib.parse.urlencode(data)
		encoded = (str(data['nonce']) + postdata).encode()
		message = urlpath.encode() + hashlib.sha256(encoded).digest()

		mac = hmac.new(base64.b64decode(secret), message, hashlib.sha512)
		sigdigest = base64.b64encode(mac.digest())
		return sigdigest.decode()

	def kraken_request(self, url_path, data):
		headers = {"API-Key": self.api_key, "API-Sign": self.get_kraken_signature(url_path, data, self.api_sec)}
		resp = requests.post((self.api_url + url_path), headers=headers, data=data)
		return resp

	def get_price(self):
		return float(requests.get(f'https://api.kraken.com/0/public/Ticker?pair={self.currentName[self.current]}EUR').json()['result'][f'{self.currentNameResult[self.current]}ZEUR']['a'][0])



	# ========================= funzioni di richiesta ========================= #
	def get_balance(self):
		data = {"nonce":str(int(1000*time()))}
		resp = self.kraken_request("/0/private/Balance", data)
		data = resp.json()["result"]
		money = 0
		stocks= 0
		if "ZEUR" in data:
			money = float(data["ZEUR"])-self.staticMoney
		if self.currentNameResult[0] in data:
			stocks = float(data[self.currentNameResult[0]])-self.staticETH
		self.money = money
		self.stocks = stocks
		return money,stocks

	def get_trade_history(self, ora):
		data = {"nonce": str(int(1000*time())),"trades": True, "start": ora}
		resp = self.kraken_request('/0/private/TradesHistory', data)
		if resp.json()["result"]["count"]>0:
			v = []
			dic = {}
			for i in resp.json()["result"]["trades"]:
				v.append(resp.json()["result"]["trades"][i])
			dic["0"] = v
			dic = dumps(dic)
			df = pd.DataFrame.from_dict(loads(dic)["0"])
			df = df.set_index("time").sort_index(ascending=False)
			costo = df["cost"].astype(float).sum()
			tassa = df["fee"].astype(float).sum()
			volume = df["vol"].astype(float).sum()
			price = df["fee"].astype(float).mean()
			return True,costo,tassa,price,volume
		else:
			return False,0,0,0,0

	def get_volume(self):
		flag,costo,tassa,price,volume = self.get_trade_history(self.ora)
		return volume

	def buy_order(self, asset):
		print(f"{self.currentNameResult[asset]}EUR")
		volume = self.money/self.get_price()
		price = self.get_price()-0.01
		print(">",volume,price)
		data = {"nonce": str(int(1000*time())),"ordertype": "limit","type": "buy","volume": volume,"pair": f"{self.currentName[asset]}EUR", "price": price, "leverage": self.moltiplicatore, "expiretm": 60}
		resp = self.kraken_request('/0/private/AddOrder', data)
		return dumps(resp.json())

	def sell_order(self, asset):
		print(f"{self.currentNameResult[asset]}EUR")
		self.get_balance()
		volume = self.get_volume()
		price = self.get_price()
		print(">",volume,price)
		data = {"nonce": str(int(1000*time())),"ordertype": "limit","type": "sell","volume": volume,"pair": f"{self.currentName[asset]}EUR","price": price, "leverage": self.moltiplicatore}
		resp = self.kraken_request('/0/private/AddOrder', data)
		print(">>",resp.json())
		return dumps(resp.json())
