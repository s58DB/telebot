#!/usr/bin/python
# -*- coding: utf-8 -*-
import re, csv, requests, json, telepot, sys, os, time, datetime, psutil, RPi.GPIO as GPIO
from telepot.namedtuple import InlineKeyboardMarkup, InlineKeyboardButton
from telepot.loop import MessageLoop
from pprint import pprint

# Variablen aus der Config holen
from config import apikey
from config import grant
from config import owner
from config import botcall
from config import prozesse
from config import dmrid
from config import mmdvmlogs

logfile = "botlog.txt"
userfile = "users.csv"
unauthorized = "Ukaza ne mores izvrsiti! Nimas SysOp pravic!"
#grantfehler = "Du darfst das nicht!"
#mmdvmaufruf = "sudo systemctl start mmdvmhost.service"
mmdvmstart = "sudo systemctl start mmdvmhost.service"
mmdvmrestart = "sudo systemctl restart mmdvmhost.service"
ircddbgwstart = "sudo systemctl start ircddbgateway.service"
ircddbgwrestart = "sudo systemctl restart ircddbgateway.service"
ircddbgwstop = "sudo systemctl stop ircddbgateway.service"
ysfgwstart = "sudo /etc/init.d/YSFGateway.sh start"
ysfgwrestart = "sudo /etc/init.d/YSFGateway.sh restart"
#dmrgwaufruf = "/usr/bin/screen /home/pi/DMRGateway/DMRGateway /home/pi/DMRGateway/DMRGateway-DB0ASE.ini"

# GPIO Settings
GPIO.setwarnings(False)
GPIO.setmode(GPIO.BOARD)
GPIO.setup(13, GPIO.OUT)
GPIO.setup(15, GPIO.OUT)

# define pathes to 1-wire sensor data
sensors = [
  ["/sys/bus/w1/devices/28-0317237f89ff/w1_slave","Senzor v ohišju"]
]


# Log
def botlog(logtext):
    file = open(logfile, "a+")
    file.write(time.strftime("%d.%m. %H:%M:%S") + ": " + logtext + '\n')
    file.close()

# function to read temp-sensors
def read_sensor(path):
  value = "U"
  try:
      f = open(path[0], "r")
      line = f.readline()
      if re.match(r"([0-9a-f]{2} ){9}: crc=[0-9a-f]{2} YES", line):
          line = f.readline()
          m = re.match(r"([0-9a-f]{2} ){9}t=([+-]?[0-9]+)", line)
      if m:
          value = str(float(m.group(2)) / 1000.0)
      f.close()
  except (IOError), e:
    print time.strftime("%x %X"), "Error reading", path, ": ", e
  return path[1] + ": " + value

# Function Information about Botowner
def ownerinfo(msg,owner):
    for x in owner:
	try:
            bot.sendMessage(x,msg)
	except:
	    print("Benachrichtigung Owner ging schief")

# Lasthearedfunktion
def lastheared(suchstring):
    if suchstring == '':
       suchstring =  "received network voice header from"
    else:
       suchstring = "received RF voice header from " +suchstring
    heared = []
    dateiname = mmdvmlogs + "-"+(time.strftime("%Y-%m-%d"))+".log"
    file = open(dateiname, "r")
    for line in file:
        if line.find(suchstring) > 1:
	    string = (line.rstrip())
	    string = string.split(" ")
	    heared.append(string)
    file.close()
    if not heared:
	return "Danes še ni bilo prometa..."
    else:
        return heared[-1][2] + " " + heared[-1][4] + " " + heared[-1][5] + " " + heared[-1][11] + " " + heared[-1][13] + " " + heared[-1][14]

# Prozesskiller
def prockiller(prozess):
    os.system('pkill '+prozess)
	
# Funktion Ausgabe Befehle
def befehlsliste(id):
    if id in grant:
	return "\n" + befehlsliste_usr + befehlsliste_syop
    else:
	return "\n" + befehlsliste_usr

# Funktion zum Abruf der Abbonierten TG
def talkgroups():
    r = requests.get("http://api.brandmeister.network/v1.0/repeater/?action=profile&q=" + dmrid)
    try:
        data = r.json()
        pprint(data)
        tgs = 'Talkgroups:'
        for tg in data['staticSubscriptions']:
            tgs += "\n" + str(tg['talkgroup']) + " im TS" + str(tg['slot'])
        for tg in data['clusters']:
            tgs += "\n" + str(tg['talkgroup']) + " im TS" + str(tg['slot']) + " (" + str(tg['extTalkgroup']) + ")"
        for tg in data['timedSubscriptions']:
	    tgs += "\n" + str(tg['talkgroup']) + " im TS" + str(tg['slot'])
        if tgs == 'Talkgroups:':
            tgs = "Ni nastavljenih staticnih TG"
    except:
        print("Abruf der Talkgroups ging schief....")
    r.close()
    return tgs

# Funktion zum Testen, ob ein Prozess läuft
def prozesschecker(prozess):
    proc = ([p.info for p in psutil.process_iter(attrs=['pid','name']) if prozess in p.info['name']])
    if proc != []:
	status = "zagnan"
    else:
	status = "ni zagnan"
    return status

def handle(msg):
    content_type, chat_type, chat_id = telepot.glance(msg)
    #print(content_type, chat_type, chat_id)
    #pprint(msg)

    vorname = msg['from']['first_name']
	#name = msg['from']['first_name']
    username = msg['from']['username']
    id = msg['from']['id']
    msg['text'] = msg['text'].lower()

    # print(msg['text'])

    if msg['text'] in ["/start","/start start", "start", "hallo", "Hallo", "Hi", "Start", "Zdravo", "Zivijo", "zdravo", "zivijo"]:
	bot.sendMessage(chat_id, "Dobrodošel v " + botcall + ", " + vorname + "!" + \
				 "\nCe potrebujes pomoč vpisi /pomoc . Za dodatne informacije, predloge in pripombe sem dosegljiv na Telegramu: @s58db ali na email: s58db.danilo@gmail.com.")
				 
    elif msg['text'] in ["/pomoc", "pomoc","help","hilfe", "sos", "ayday"]:
	hilfetext = "Informacije in ukazi:\n/status Informacija o stanju repetitorja \n/pomoc Prikaze" \
                    " izvrsljive ukazov\n/tg Izpiše seznam staticnih TG na repetitorju \n/lheared Izpiše zadnjo postajo ki je oddajala"
        if id in grant:
            hilfetext += "\n\n/killmmdvm zaustavi MMDVMHost\n/startmmdvm zaženi MMDVMHost\n/restartmmdvm Znova zaženi MMDVMHost" \
			"\n/killircddbgw zaustavitev ircDDBGateway\n/startircddbgw zaženi ircDDBGateway\n/restartircddbgw Znova zaženi ircDDBGateway" \
			"\n/killysfgw zaustavitev YSFGateway\n/startysfgw zaženi YSFGateway\n/restartysfgw zaženi YSFGateway\n/reboot Ponovni zagon sistema" \
			# "\n/txan Schaltet den Sender an\n/txaus Schaltet den Sender aus\n/rxan Schaltet den RX ein" \
			# "\n/rxaus Schaltet den RX an\n/reboot start den Rechner neu"
        bot.sendMessage(chat_id,botcall + " " + hilfetext)

    elif msg['text'] in ["/tg"]:
	bot.sendMessage(chat_id, talkgroups())

    elif "/lheared" in msg['text']:
	if msg['text'] == "/lheared":
            heared = lastheared('')
            bot.sendMessage(chat_id,heared)
	else:
	    suche = msg['text'].split(" ")
	    heared = lastheared(suche[1].upper())
	    bot.sendMessage(chat_id,heared)

    elif msg['text'] in ["/killmmdvm"]:
	if id in grant:
	    prockiller("MMDVMHost")
	    bot.sendMessage(chat_id,"MMDVMHost se je zaustavil...")
        else:
	    bot.sendMessage(chat_id,unauthorized)

    elif msg['text'] in ["/startmmdvm"]:
        if id in grant:
            os.system(mmdvmstart)
            bot.sendMessage(chat_id,"MMDVMHost ustavljen... ")
        else:
            bot.sendMessage(chat_id,unauthorized)


    elif msg['text'] in ["/restartmmdvm"]:
        if id in grant:
            os.system(mmdvmrestart)
            bot.sendMessage(chat_id,"MMDVMHost se je ponovno zagnal... ")
        else:
            bot.sendMessage(chat_id,grantfehler)
            
    elif msg['text'] in ["/killircddbgw"]:
        if id in grant:
	    os.system(ircddbgwstop)
	    bot.sendMessage(chat_id,"ircDDBGateway se je zaustavil...")
	else:
            bot.sendMessage(chat_id,unauthorized)

    elif msg['text'] in ["/startircddbgw"]:
        if id in grant:
            os.system(ircddbgwstart)
            bot.sendMessage(chat_id,"rcDDBGateway se je zagnal...")
        else:
            bot.sendMessage(chat_id,grantfehler)

    elif msg['text'] in ["/restartircddbgw"]:
        if id in grant:
            os.system(ircddbgwrestart)
            bot.sendMessage(chat_id,"ircDDBGateway se je ponovno zagnal...")
        else:
            bot.sendMessage(chat_id,grantfehler)

    elif msg['text'] in ["/killysfgw"]:
        if id in grant:
            prockiller("YSFGateway")
            bot.sendMessage(chat_id,"YSFGateway se je zaustavil...")
        else:
            bot.sendMessage(chat_id,unauthorized)
    elif msg['text'] in ["/startysfgw"]:
        if id in grant:
            os.system(ysfgwstart)
            bot.sendMessage(chat_id,"YSFGateway se je zagnal...")
        else:
            bot.sendMessage(chat_id,grantfehler)
    elif msg['text'] in ["/restartysfgw"]:
        if id in grant:
            os.system(ysfgwrestart)
            bot.sendMessage(chat_id,"YSFGateway se je ponovno zagnal...")
        else:
            bot.sendMessage(chat_id,grantfehler)

    # elif msg['text'] in ["/killdmrgw"]:
    #    if id in grant:
    #        prockiller("DMRGateway")
    #        bot.sendMessage(chat_id,"Beende DMRGateway...")
    #    else:
    #        bot.sendMessage(chat_id,grantfehler)

    # elif msg['text'] in ["/startdmrgw"]:
    #    if id in grant:
    #        os.system(dmrgwaufruf)
    #        bot.sendMessage(chat_id,"Starte DMRGateway")
    #    else:
    #        bot.sendMessage(chat_id,grantfehler)

    elif msg['text'] in ["/status"]:
	status = ''
	# Eingänge lesen
    #    if GPIO.input(13) == GPIO.HIGH:
	#    status += "TX ist aus\n"
    #    else:
    #        status += "TX is an\n"
    #    if GPIO.input(15) == GPIO.HIGH:
    #        status += "RX ist aus"
    #    else:
    #        status += "RX ist an"
	# Laufende Prozesse testen
	for proc in prozesse:
	    status += "\n" + proc + " " + prozesschecker(proc)

	## Temperaturen
	# CPU-Temperaturen auslesen
	tFile = open('/sys/class/thermal/thermal_zone0/temp')
	temp = float(tFile.read())
	tempC = temp/1000
	status += "\nCPU Temperatur " + str(tempC)

        bot.sendMessage(chat_id, status)
	
	# read the sensors
	i = 0
	for row in sensors:
    	    status += '\n'
    	    status += read_sensor(sensors[i])
    	    i = i + 1

        bot.sendMessage(chat_id, status)

    #elif msg['text'] in ["/txaus"]:
    #    if id in grant:
    #        GPIO.output(13, GPIO.HIGH)
	#    bot.sendMessage(chat_id,"Sender ist aus!")
    #    else:
	#    bot.sendMessage(chat_id,grantfehler)
    #elif msg['text'] in ["/txan"]:
    #    if id in grant:
    #        GPIO.output(13, GPIO.LOW)
    #        bot.sendMessage(chat_id,"Sender ist wieder an!")
    #    else:
    #        bot.sendMessage(chat_id,grantfehler)

    #elif msg['text'] in ["/rxaus"]:
    #    if id in grant:
    #        GPIO.output(15, GPIO.HIGH)
    #        bot.sendMessage(chat_id,"Empfang ist aus!")
    #    else:
    #        bot.sendMessage(chat_id,grantfehler)
    #elif msg['text'] in ["/rxan"]:
    #    if id in grant:
    #        GPIO.output(15, GPIO.LOW)
    #        bot.sendMessage(chat_id,"Empfang ist wieder an!")
    #    else:
    #        bot.sendMessage(chat_id,grantfehler)

    elif msg['text'] in ["/reboot"]:
	if id in grant:
	    bot.sendMessage(chat_id,"Ponovni zagon sistema")
	    os.system('sudo reboot')
	else:
            bot.sendMessage(chat_id,unauthorized)
    else:
	bot.sendMessage(chat_id, 'Z "' + msg['text'] + '" ne morem storiti ničesar, '+ vorname + "!\nza seznam ukazov vnesi /pomoc.")

bot = telepot.Bot(apikey)

try:
    ownerinfo("Vrnil sem se...",owner)
    MessageLoop(bot,handle).run_as_thread()
except:
    print("Nekaj je narobe z Botom...")

try:
    while 1:
        time.sleep(10)

except:
    print("Nasvidenje...")
    ownerinfo("Bot se je ustavil...",owner)
    # GPIO.cleanup()
