from Modbus import modbus_device
import TypeConversion as TC
from time import sleep
import configparser
import argparse
import json
from os import path, chdir
from datetime import datetime
import telepot
from telepot.loop import MessageLoop
import telepot.api
import urllib3
from re import findall as RegexFindAll

def readConfig(configFilePath):
    global bot_token, modbusServerIP, modbusServerPort, modbusServerRegister, dataFileName, args
    config = configparser.RawConfigParser(inline_comment_prefixes="#")
    readConfig = config.read(configFilePath)

    if not args.noBot:
        bot_token = config.get("telegrambot","token")

    modbusServerIP = config.get("modbusServer","ip")
    try:
        modbusServerPort = config.get("modbusServer","port")
    except:
        pass
    modbusServerRegisters = config.get("modbusServer","registers")
    modbusServerRegisters = modbusServerRegisters.split("\n")
    del modbusServerRegisters[0]
    modbusServerRegister = []
    for i in modbusServerRegisters:
        temp = i.split(", ")
        modbusServerRegister.append({"name": temp[0], "address": int(temp[1]), "length": int(temp[2]), "factor": float(temp[3]), "unit": temp[4]})

    dataFileName = config.get("dataFile","name")
    pass

def telegramBotInit():
    global bot

    telepot.api._pools = {
        'default': urllib3.PoolManager(num_pools=3, maxsize=10, retries=3, timeout=30),
    }
    telepot.api._onetime_pool_spec = (urllib3.PoolManager, dict(num_pools=1, maxsize=1, retries=3, timeout=30))

    bot = telepot.Bot(bot_token)
    botInfo = bot.getMe()
    MessageLoop(bot,telegramBotHandle).run_as_thread()
    print("Bot is listening ...")

def dataJsonInit():
    global data, dataFileName
    try:
        with open(dataFileName) as json_file:
            data = json.load(json_file)
            if not data:
                data["clients"] = {}
            pass
    except:
        data = {}
        data["clients"] = {}
        pass
    pass

def writeJSON(fileName, data):
    try:
        with open(fileName, "w") as outfile:
            json.dump(data, outfile)
        pass
    except:
        print("Error writing to file" + Exception)

def clientsHandle(msg):
    global data, dataFileName
    client_missing = True

    if str(msg['chat']['id']) in data["clients"]:
        client_missing = False
        
    if client_missing:
        data["clients"][str(msg['chat']['id'])] = {"name": msg['chat']['first_name']+" "+msg['chat']['last_name'], "timeAdded": msg["date"]}
        writeJSON(dataFileName, data)
    pass

def parseTelegramCommand(messageText):
    messageTextList = messageText.split(" ")
    commandDict = {}
    current_command = ""
    for i in messageTextList:
        command_temp = RegexFindAll("^\/\S+", i)
        if command_temp:
            current_command = command_temp[0]
            commandDict[current_command] = {}
        else:
            argument_temp = i.split("=")
            if len(argument_temp) == 2:
                commandDict[current_command][argument_temp[0]] = argument_temp[1]
            elif len(argument_temp) == 1:
                commandDict[current_command] = argument_temp[0]
            pass
    return commandDict

def telegramBotHandle(msg):
    global bot, data
    chat_id = msg['chat']['id']
    messageText = msg['text']
    content_type, _, _ = telepot.glance(msg)
    print(str(datetime.now())+': Got message: '+str(messageText))    
    clientsHandle(msg)
    commandDict = parseTelegramCommand(messageText)
    try: 
        send_string = ""

        if "/all" in commandDict:
            data = HeizungModbusServer.read_all()
            interString = []
            for i in data:
                interString.append("{}: {}{}".format(*i)) 
            send_string = "\n".join(interString)
            pass

        if "/showertemp" in commandDict:
            if commandDict["/showertemp"]:
                data["clients"][str(msg['chat']['id'])]["shower"] = {}
                data["clients"][str(msg['chat']['id'])]["shower"]["temperature"] = round(float(commandDict["/showertemp"]),2)
                data["clients"][str(msg['chat']['id'])]["shower"]["LastNotification"] = str(datetime.now())
                writeJSON(dataFileName, data)
                send_string += "Shower temperature set to "+str(data["clients"][str(msg['chat']['id'])]["shower"]["temperature"])+"°C\n"
            else:
                if "shower" in data["clients"][str(msg['chat']['id'])]:
                    send_string += "Current shower temperature is "+str(data["clients"][str(msg['chat']['id'])]["shower"]["temperature"])+"°C\n"
                else:
                    send_string += "No shower temperature set\n"
            pass
        
        if not send_string:
            send_string = "not recognized command"

        bot.sendMessage(chat_id, send_string)
    except:
        bot.sendMessage(chat_id, "Error reading modbus")
    pass

def argsParse():
    global args
    parser = argparse.ArgumentParser(description='SMA Inverter Modbus reader.')
    parser.add_argument("--debug", help="Run with debug features", action="store_true")
    parser.add_argument("--noBot", help="Don't run telegramBot", action="store_true")
    args = parser.parse_args()

def main():
    global HeizungModbusServer, registerData    
    readConfig("config.cfg")

    HeizungModbusServer = modbus_device(ipAddress=modbusServerIP, port=modbusServerPort)
    for i in modbusServerRegister:
        HeizungModbusServer.newRegister(name=i["name"], address=i["address"], length=i["length"], factor=i["factor"], unit=i["unit"])
        HeizungModbusServer.read_string(name=i["name"])        
    
    dataJsonInit()
    if not args.noBot:
        telegramBotInit()
    pass

if __name__ == "__main__":
    argsParse()
    if args.debug:
        chdir("Modbus-Project/Heizung")
    main()
    while not args.noBot:
        sleep(20)
    if args.noBot:
        print(str(HeizungModbusServer.read_all()))
        print("Done.")
