#!/usr/bin/env python3
from socket import *
import select
import threading

from grid import *
import random
import sys

ip=''
port = 7777

def selectCase():

	choix = -1
	while(choix < 0 or choix > 8):
		choix = int(input("Quelle case allez vous jouer ? (0-8)"))

	return choix

def main():

	socket_client = socket(AF_INET6, SOCK_STREAM)
	socket_client.connect((ip, port))
	while(True):
		data = bytes.decode(socket_client.recv(1024) )
		shot = -1
		if data == "begin":
			shot = selectCase()
			socket_client.send( str.encode(str(shot) ))
			data = None
		else:
			if(len(data) != 0):
				print(data)
	socket_client.close()

main()