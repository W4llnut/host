from numpy import linspace, meshgrid, array, arctan
from ta.trend import *
from ta.momentum import *
from ta.volatility import *
import pandas as pd

class AlgorithmETH:
	def __init__(self, tassa, moltiplicatore):
		self.df = -1

		# parametri
		self.tassa = tassa
		self.moltiplicatore = moltiplicatore

		# stop calls
		self.stopWinMACD = self.tassa+0.4/self.moltiplicatore
		self.stopLossMACD = (0.04)/self.moltiplicatore
		self.stopWinMACDs = self.tassa+0.4/self.moltiplicatore
		self.stopLossMACDs = (0.02)/self.moltiplicatore
		self.stopWinBollinger = self.tassa+0.4/self.moltiplicatore
		self.stopLossBollinger = (0.01)/self.moltiplicatore

		# parametri periodi
		self.ADXperiodo = 14
		self.periodiB = 6
		self.periodiL = 66
		self.Periodo = 25
		self.longPeriod = 3*self.Periodo

		self.Breve = self.periodiB
		self.Lunga = self.periodiL

		self.strategia = "-"


	# ========================= funzioni dell'algoritmo ========================= #
	def check_buy(self, t):
		macd = self.df[f'EMA{self.Breve}'][t]>self.df[f'EMA{self.Lunga}'][t]
		rocMACD = 0.3<self.df['rocM'][t] and self.df['rocBreve'][t]<1.5
		aroonMACD = self.df['aroon_indicator'][t]>50
		sarM = self.df['psar_di'][t]==False
		bollingerMACD = self.df['bollinger_wband'][t] > 1.5
		
		Smacd = self.df[f'EMA{self.Breve}'][t]<self.df[f'EMA{self.Lunga}'][t]
		SrocMACD = -2<self.df['rocM'][t]<0.3 and self.df['rocLungo'][t]<-0.5 and -2<self.df['rocBreve'][t]<-0.3
		SaroonMACD = self.df['aroon_indicator'][t]<-40
		Sbollinger = self.df['bollinger_pband'][t-10]-self.df['bollinger_pband'][t]<0.1 and self.df['bollinger_pband'][t]>0.3
		SsarM = self.df['psar_di'][t]==True
		
		if macd and rocMACD and aroonMACD:
			adx = self.df['adx'][t]>40
			if sarM and adx:
				self.strategia = "MACD"
		elif Smacd and SrocMACD and SaroonMACD and Sbollinger and False:
			adx = self.df['adx'][t]>20
			if SsarM and adx:
				self.short = True
				self.strategia = "MACDshort"
		return self.strategia != "-"

	def check_sell(self, t, entrata):
		if self.strategia == "MACD":
			if self.df[f'EMA{self.Breve}'][t]<self.df[f'EMA{self.Lunga}'][t] or self.stopCallMacd(t,entrata):
				self.strategia = "-"
		elif self.strategia == "MACDshort":
			if self.df[f'EMA{self.Breve}'][t]>self.df[f'EMA{self.Lunga}'][t] or self.stopCallMacdshort(t,entrata):
				self.strategia = "-"
		return self.strategia == "-"

	def stopCallMacd(self, t, entrata):
		sar = self.moltiplicatore*(self.df['Close'][t]*(1-self.tassa)-entrata)/entrata>=0 and self.df['psar_di'][t]==True
		upper = self.df['Close'][t]>entrata*(1+self.stopWinMACD)#*(1+self.df['atr_perc'][t]))
		lower = self.df['Close'][t]<entrata*(1-self.stopLossMACD)#*(1+self.df['atr_perc'][t]))
		return upper or lower or sar

	def stopCallMacdshort(self, t, entrata):
		sar = self.moltiplicatore*(self.df['Close'][t]*(1+self.tassa/2)-entrata*(1-self.tassa/2))/entrata<=0 and self.df['psar_di'][t]==False
		lower = self.df['Close'][t]<entrata*(1-self.stopWinMACDs)#*(1+self.df['atr_perc'][t]))
		upper = self.df['Close'][t]>entrata*(1+self.stopLossMACDs)#*(1+self.df['atr_perc'][t]))
		return upper or lower or sar

	def analyzeDf(self):
		# EMA
		self.df[f'EMA{self.periodiB}'] = ema_indicator(self.df['Close'], self.periodiB, False)
		self.df[f'EMA{self.periodiL}'] = ema_indicator(self.df['Close'], self.periodiL, False)
		macd = MACD(self.df['Close'])
		self.df['macd'] = macd.macd()
		self.df['signal'] = macd.macd_signal()

		# ADX
		adxI = ADXIndicator(self.df['High'],self.df['Low'],self.df['Close'], self.ADXperiodo, False)
		self.df['pos_directional_indicator'] = adxI.adx_pos()
		self.df['neg_directional_indicator'] = adxI.adx_neg()
		self.df['adx'] = adxI.adx()

		# Bollinger Bands
		bollinger = BollingerBands(self.df['Close'],200)
		self.df['bollinger_wband'] = bollinger.bollinger_wband()
		self.df['bollinger_pband'] = bollinger.bollinger_pband()

		# Parabolic SAR
		parabolicSar = PSARIndicator(self.df['High'],self.df['Low'],self.df['Close'])
		self.df['psar'] = parabolicSar.psar()
		self.df['psar_di'] = self.df['psar']>self.df['Close']

		# Aroon
		aroon = AroonIndicator(self.df['Close'])
		self.df['aroon_indicator'] = aroon.aroon_indicator()

		# roc
		rocM = ROCIndicator(self.df['Close'])
		self.df['rocM'] = rocM.roc()
		rocBreve = ROCIndicator(self.df['Close'],2)
		self.df['rocBreve'] = rocBreve.roc()
		rocLungo = ROCIndicator(self.df['Close'],95)
		self.df['rocLungo'] = rocLungo.roc()
		
