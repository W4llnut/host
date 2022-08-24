import discord
from discord.ext import commands
import asyncio
from yfinance import download
from requests import get
from time import time
from pandas import DataFrame, to_datetime
from datetime import datetime
from math import floor
from agent import AGENT
import os

client = discord.Client()
SESSION = True
Last_update = datetime.fromtimestamp(time()).strftime("%H:%M:%S")
Agent = AGENT()

# id canali
generaleCH = 1005242726125678635
attivitaCH = 1005245873883713546
datiCH = 1005255394710528162
transazioniCH = 1005968395927293962
azioniCH = 1005245915931615393

def check_time():
	global Last_update
	now = datetime.fromtimestamp(time()).strftime("%H:%M:%S").split(":")
	soglia = Last_update.split(":")
	now = [int(i) for i in now]
	soglia = [int(i) for i in soglia]
	if soglia[1] >= 55:
		soglia[1] = -5
		soglia[0] = (soglia[0]+1)%24
	else:
		soglia[1] = floor(soglia[1]/5)*5

	if now[0] >= soglia[0] and now[1] >= soglia[1]+5 and now[2]>20:
		Last_update = datetime.fromtimestamp(time()).strftime("%H:%M:%S")
		return True

	return False

def get_data(asset):
	PERIODO = 5*60 # 5 minuti
	SPAN = 500 # < 720
	ORA = int(time())

	resp0 = get(f'https://api.kraken.com/0/public/OHLC?pair={asset[0]}EUR&interval=5&since={ORA-SPAN*PERIODO}')
	data0 = DataFrame(resp0.json()['result'][f'{Agent.currentNameResult[0]}ZEUR'])
	data0 = data0.rename(columns={0:"Datetime",1:"Open",2:"Low",3:"High",4:"Close",5:"Vwap",6:"Volume",7:"Count"})
	data0['Datetime'] = to_datetime(data0['Datetime'],unit="s",origin="unix")
	data0 = data0.set_index("Datetime").sort_index()

	return [data0]

def process_data(data):
	if not Agent.dentro:
		return Agent.buy(datetime.fromtimestamp(time()).strftime("%H:%M:%S"), data)
	else:
		return Agent.sell(datetime.fromtimestamp(time()).strftime("%H:%M:%S"), data)


@client.event
async def on_ready():
	for guild in client.guilds:

		print(
			f'{client.user} is connected to the following guild:\n'
			f'{guild.name}(id: {guild.id})'
		)


	await client.get_channel(attivitaCH).send("Starting Connection.")
	global SESSION
	while True:
		if SESSION==True:
			try:
				await asyncio.sleep(10)
				if check_time():
					now = datetime.fromtimestamp(time()).strftime("%H:%M")
					await client.get_channel(attivitaCH).send(f"Connection check({now}).")
					data = get_data(Agent.currentName)
					info0 = data[0].iloc[-1]
					await client.get_channel(datiCH).send(f"{Agent.currentName[0]}:{info0.name}| Open:{info0['Open']}/Low:{info0['Low']}/High:{info0['High']}/Close:{info0['Close']}")
					flag, r = process_data(data)
					if flag:
						await client.get_channel(transazioniCH).send(r)	
						allowed_mentions = discord.AllowedMentions(everyone = True)
						await client.get_channel(azioniCH).send(content="@everyone Stock transaction happened.", allowed_mentions=allowed_mentions)

			except Exception as e:
				print(e)
		elif SESSION==False:
			try:
				await asyncio.sleep(100)
			except Exception as e:
				print(e)
		elif SESSION==-1:
			break


@client.event
async def on_message(message):
	if message.author == client.user:
		return

	if message.channel.id==azioniCH:
		global SESSION
		if message.content=="shutdown" or message.content=="s":
			SESSION = not SESSION
			await message.channel.send(f"Execution is now set to {SESSION}")
		elif message.content=="ss":
			SESSION = -1
			await client.close()
		elif message.content=="help" or message.content=="h":
			await message.channel.send(f"help-h\nversion-v\nshutdown/execute-s\nbalance-b\nstate-c\nforce buy 0\nforce sell\nenter/exit e")
		elif message.content=="version" or message.content=="v":
			await message.channel.send(f"R1.0.4")
		elif message.content=="enter" or message.content=="exit" or message.content=="e":
			Agent.dentro = not Agent.dentro
			await message.channel.send(f"Stato corrente aggiornato: dentro={Agent.dentro}")
		elif message.content=="balance" or message.content=="b":
			await message.channel.send(Agent.get_total_balance())
		elif message.content=="state" or message.content=="c": # c di current state
			r = Agent.get_current_state(get_data(Agent.currentName))
			await message.channel.send(r)
		elif message.content=="force buy 0":
			if len(message.content.split(" "))!=3:
				await client.get_channel(azioniCH).send(f"Specificare quale comprare[0,1]: {Agent.currentName}")
			else:
				flag, r = Agent.buy(datetime.fromtimestamp(time()).strftime("%H:%M:%S"),get_data(Agent.currentName),True,int(message.content.split(" ")[2]))
				if flag:
					await client.get_channel(transazioniCH).send(r)
		elif message.content=="force sell":
			flag, r = Agent.sell(datetime.fromtimestamp(time()).strftime("%H:%M:%S"),get_data(Agent.currentName),True)
			if flag:
				await client.get_channel(transazioniCH).send(r)

	else:
		#print(message.channel.id)
		allowed_mentions = discord.AllowedMentions(everyone = True)
		await message.channel.send(content="@everyone owo", allowed_mentions=allowed_mentions)

client.run(os.environ['DISCORD_TOKEN'])
