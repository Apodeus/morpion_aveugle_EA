#!/usr/bin/env python3
from socket import *
from grid import *

import select
import threading
import random

import sys
import re

expect_answer = 0;

def displayStr(grid):
	grid_str = "$display $"
	for i in range(3):
			grid_str = grid_str + str(grid.cells[i*3]) +  str(grid.cells[i*3+1]) + str(grid.cells[i*3+2])
	return grid_str

class Client:

	cId = None
	socket = None
	score = 0
	name = "nameless"
	cType = 0 #0 = spectator, 1=player
	cSpec = -1

	def __init__(self, socket):
		self.socket = socket
		if socket != None:
			self.sendMessage("Connected.\ntype 'help' to display available commands.\n")

	def setId(self, cid):
		self.cId = cid

	def sendMessage(self, text):
		self.socket.send(str.encode(text))

	def setName(self, name):
		self.name = name

class Player:

	pGrid = None
	pClient = None
	pId = 0
	pIsAI = 0 # 0 if human, 1 if IA
	pGame = -2
	isWaiting = 0 #0 normal, 1 waiting for reconnection, -1 has disconnected

	def __init__(self, client):
		self.pGrid = grid()
		self.pClient = client

	def playAsIa(self):
		shot = random.randint(0,8)
		while(self.pGrid.cells[shot] != EMPTY):
			shot = random.randint(0,8)
		return shot

	def setId(self, pid):
		self.pId = pid

	def sendMessage(self, text):
		if self.pIsAI == 0:
			self.pClient.sendMessage(text)

	def getPlayerGrid(self):
		grid_str = displayStr(self.pGrid)
		return grid_str

	def displayGrid(self):
		self.sendMessage(self.getPlayerGrid())

class Host:

	listClient = []
	listSockets = []
	socketListener = None
	currentPlayer = []
	hGrid = []
	players = []
	specs = []

	def __init__(self, socketListener):
		self.socketListener = socketListener
		self.listSockets.append(socketListener)

	def isGameOver(self, game):
		if self.hGrid[game].gameOver() != -1 :
			self.currentPlayer[game] = -1
		return self.hGrid[game].gameOver()

	def playMove(self, game, case):	#returns True if ok
		if not(0 <= case <= 8):
			return False
		if self.hGrid[game].cells[case] == EMPTY: #If the case is empty, we can play the move correctly
			self.hGrid[game].play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].pGrid.play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].displayGrid()
			return True
		else: #else we can update his grid
			p = self.players[self.currentPlayer[game] - 1 + 2 * game]
			p.pGrid.cells[case] = self.hGrid[game].cells[case]
			p.displayGrid()
			p.sendMessage("$play")
			return False

	def switchPlayer(self, game):
		if self.currentPlayer[game] == -1:
			self.currentPlayer[game] += 1
		self.currentPlayer[game] = (self.currentPlayer[game] % 2 ) + 1
		player = self.players[2 * game + self.currentPlayer[game] - 1]
		if player.pIsAI == 0:
			player.sendMessage("$play")
		else:
			correct = False
			while correct == False:
				correct = self.playMove(game, player.playAsIa())
			for c in self.listClient:
				if c.cType != 1 and c.cSpec == player.pGame:
					c.sendMessage(displayStr(self.hGrid[player.pGame]))
			self.currentPlayer[game] = (self.currentPlayer[game] % 2 ) + 1
			player = self.players[2 * game + self.currentPlayer[game] - 1]
			player.sendMessage("$play")

	def addNewClient(self):
		(socket_recv, addr_recv) = self.socketListener.accept()
		c = Client(socket_recv)
		self.listClient.append(c)
		self.listSockets.append(socket_recv)
		c.setId(self.getNewClientId())

	def setNewPlayer(self, client):
		p = Player(client)
		self.players.append(p)
		p.setId(len(self.players))
		p.pGame = -1
		client.cType = 1
		client.cSpec = -1

	def setNewAIPlayer(self):
		client = Client(None)
		client.name = "AI"
		p = Player(client)
		self.players.append(p)
		p.setId(len(self.players))
		p.pGame = -1
		client.cType = 2
		client.cSpec = -1
		p.pIsAI = 1

	def getPlayerId(self, socket):
		for p in self.players:
			if p.pClient != None and socket == p.pClient.socket:
				return p.pId
		return -1

	def getPlayer(self, pid):
		for p in self.players:
			if pid == p.pId:
				return p
		return -1

	def getClientId(self, socket):
		for c in self.listClient:
			if socket == c.socket:
				return c.cId
		return -1

	def getClient(self, cid):
		for c in self.listClient:
			if cid == c.cId:
				return c
		return -1

	def getNewClientId(self):
		i = 0
		for c in self.listClient:
			if c.cId != None and c.cId > i:
				i = c.cId
		return i + 1

	def isGameReady(self):
		if len(self.players) > 1 and len(self.players)%2 == 0:
			return 1
		return 0

	def startGame(self):	####################	
		print("Game start")
		self.hGrid.append(grid())
		game = len(self.hGrid) - 1
		for p in self.players:#The game starts, we can display players' grids
			if p.pGame == -1:
				p.pGame = game
				if p.pClient.socket != None:
					p.sendMessage("$gamestart")
					p.displayGrid()
		self.currentPlayer.append(-1)
		self.switchPlayer(game)

	def getScores(self):
		l = sorted(self.listClient, key=lambda x: x.score, reverse=True)
		return l

	def getScoresString(self):
		l = self.getScores()
		s = ""
		for i in range(len(l)):
			if l[i].cType != 2:
				s += str(i + 1) + ":" + l[i].name + " with " + str(l[i].score) + " wins\n"
		return s

	def endGame(self, game):
		p1 = None
		p2 = None
		for p in self.players:
			if p.pGame == game:
				if p.pClient != None:
					p.pClient.cType = 0
				if p1 == None:
					p1 = p
				else:
					p2 = p

		if p1 != None:
			p1.pClient = None
		if p2 != None:
			p2.pClient = None
		self.hGrid[game] = grid()

	def getPlayers(self, game):
		p1 = None
		p2 = None
		for p in self.players:
			if p.pClient != None and p.pGame == game:
				if p1 == None:
					p1 = p
				else:
					p2 = p
		return (p1, p2)

	def checkForFreeName(self, name):
		for c in self.listClient:
			if c.name == name:
				return self.checkForFreeName(name + "_")
		return name


class thread_r(threading.Thread): #Thread for Reception
	def __init__(self, s):
		threading.Thread.__init__(self)
		self.socket_client = s

	def run(self):
		while(True):
			data = bytes.decode(self.socket_client.recv(1024) ) #data from the server
			if (len(data) != 0):
				parsed_data = re.findall('\$[a-zA-Z0-9]+', data)
				if parsed_data:
					for i in range(len(parsed_data)):
						word = parsed_data[i]

						if word == "$gamestart":
							print("Game started")
						elif word == "$play":
							print("Play on a case (0 to 8):")

						elif word == "$display":
							i = i + 1
							word2 = parsed_data[i]
							#Displaying the grid
							grid_str = "-------------\n"
							for case_i in range(3):
								grid_str = grid_str + "| " + symbols[int(word2[case_i*3 + 1])] + " | " +  symbols[int(word2[case_i*3+1 + 1])] + " | " +  symbols[int(word2[case_i*3+2 + 1])] + " |\n" + "-------------\n"
							print(grid_str)

						elif word == "$end":
							i += 1
							word2 = parsed_data[i]
							if word2 == "$win":
								print("You win")
							elif word2 == "$loose":
								print("You loose")
							elif word2 == "$draw":
								print("Draw !")

				else:
					print(data)

class thread_s(threading.Thread):#Thread for Emission
	def __init__(self, s):
		threading.Thread.__init__(self)
		self.socket_client = s

	def run(self):
		while True:
			text = input("")
			if text == "help":
				print("Available commands : \n name:<name> \t Change your current name to <name>\n play \t\t Start a game against another player\n spec:<ID> \t Watch game <ID> \n playAI \t Start a game against the AI\n join:<name>\t Join an unfinished game against <name>\n quit\t\t Cancel a game")	
			self.socket_client.send(str.encode(text))

#_________________________END OF CLASS DECLARATION ____________________________________________________________________________

def main_server():
	socket_listen = socket(AF_INET, SOCK_STREAM, 0)
	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	socket_listen.bind((gethostbyname(gethostname()), 7777))
	socket_listen.listen(1)

	print("Server is up at ( hostname = " + gethostname()+ " )"+gethostbyname(gethostname()) + "\n You can connect using either of those as argument for the client.")
	host = Host(socket_listen)

	while(1):
		for g in range(len(host.hGrid)):
			if (host.isGameOver(g) != -1): #if gameOver
				player1 = None
				player2 = None
				for player in host.players:
					if (player.pGame == g):
						if player1 == None:
							player1 = player
						else:
							player2 = player
				end_winner = host.isGameOver(g)
				if end_winner == EMPTY:#draw
					player.sendMessage(displayStr(host.hGrid[g]) + " $end $draw")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player1.pClient.name + " and " + player2.pClient.name + " ended their game on a draw.")

				if end_winner == J1:#player1 win
					player1.sendMessage(displayStr(host.hGrid[g]) + " $end $win")
					player2.sendMessage(displayStr(host.hGrid[g]) + " $end $loose")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player1.pClient.name + " won against " + player2.pClient.name + ".")
					player1.pClient.score += 1

				if end_winner == J2:#player2 win
					player2.sendMessage(displayStr(host.hGrid[g]) + " $end $win")
					player1.sendMessage(displayStr(host.hGrid[g]) + " $end $loose")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player2.pClient.name + " won against " + player1.pClient.name + ".")
					player2.pClient.score += 1

				host.endGame(g)

		(ready_sockets, [], []) = select.select(host.listSockets, [], [])
		for current_socket in ready_sockets:
			if current_socket == host.socketListener: #Connexion of a new client
				host.addNewClient()
				print("A new client connected")
			else:
				cId = host.getClientId(current_socket)
				pId = host.getPlayerId(current_socket)
				bytes_recv = bytes.decode(current_socket.recv(1024))
				if len(bytes_recv) == 0 :#DECONNEXION of a client
					client = host.getClient(host.getClientId(current_socket))
					for c in host.listClient:
						if c.cType != 1 and c.cId != client.cId:
							c.sendMessage(client.name + " disconnected.")
					if client.cType == 1:
						player = host.getPlayer(host.getPlayerId(current_socket))
						player.isWaiting = -1
						player.pClient = None
					for p in host.players:
						if p.pGame == player.pGame and p.pId != player.pId and p.pClient != None:
							p.sendMessage("Your opponent " + client.name + " has disconnected. You can wait for him to reconnect or quit by typing 'quit'.")
							p.isWaiting = 1
					host.listClient.remove(client)
					host.listSockets.remove(current_socket)
					current_socket.close()

				elif pId != -1:
					player = host.getPlayer(pId)
					if bytes_recv == "quit":
						(p1, p2) = host.getPlayers(player.pGame)
						log = "Match canceled by " + player.pClient.name
						for c in host.listClient:
							if c.cType != 1:
								c.sendMessage(log)
						if p1 != None and p1.pClient != None:
							p1.sendMessage(log)
						if p2 != None and p2.pClient != None:
							p2.sendMessage(log)
						host.endGame(player.pGame)
					if pId == host.currentPlayer[player.pGame] + 2 * player.pGame:
						try: #try to convert the message in an integer
							isMoveOk = host.playMove(player.pGame, int(bytes_recv))
						except ValueError:
							isMoveOk = False
							
						if isMoveOk: #if the move is good
							for c in host.listClient:
								if c.cType != 1 and c.cSpec == player.pGame:
									c.sendMessage(displayStr(host.hGrid[player.pGame]))
							host.switchPlayer(player.pGame)
				else:
					client = host.getClient(cId)
					if bytes_recv == "play":
						host.setNewPlayer(host.getClient(cId))
						if host.isGameReady() == 1:
							host.startGame()
							idGame = len(host.hGrid) - 1
							(p1, p2) = host.getPlayers(idGame)
							for c in host.listClient:
								if c.cType != 1 :
									c.sendMessage("A game started between " + p1.pClient.name + " and " + p2.pClient.name + " (ID:" + str(idGame) + ")")
						else:
							print(client.name + " is looking for an opponent")
							host.getClient(cId).sendMessage("Waiting for opponent...")
							for c in host.listClient:
								if c.cId != cId and c.cType != 1:
									c.sendMessage(client.name + " is looking for an opponent")
					if bytes_recv == "playAI":
						host.setNewPlayer(host.getClient(cId))
						host.setNewAIPlayer()
						if host.isGameReady() == 1:
							host.startGame()
							idGame = len(host.hGrid) - 1
							(p1, p2) = host.getPlayers(idGame)
							for c in host.listClient:
								if c.cType != 1 :
									c.sendMessage("A game started between " + p1.pClient.name + " and the AI (ID:" + str(idGame) + ")")
					if bytes_recv == "lead":
						client.sendMessage(host.getScoresString())
					if len(bytes_recv) > 4 and bytes_recv[4] == ':':				#commande
						command = bytes_recv.split(':')
						if len(command) == 2:
							if command[0] == "name": 			#set client name
								log = ""
								command[1] = host.checkForFreeName(command[1])
								if client.name == "nameless":
									log = command[1] + " joined"
								else:
									log = client.name + " changed name to " + command[1]
								client.setName(command[1])
								print(log)
								for c in host.listClient:
									if c.cType != 1 and c.cId != client.cId:
										c.sendMessage(log)
							if command[0] == "spec":			#spectate a game
								g = int(command[1])
								client.cSpec = g
							if command[0] == "join":
								for p in host.players:
									if p.pClient != None and p.pClient.name == command[1]:
										if p.isWaiting == 1:
											for p2 in host.players:
												if p2.isWaiting == -1 and p2.pGame == p.pGame:
													p2.pClient = client
													p2.isWaiting = 0
													p.isWaiting = 0
													client.cType = 1
													client.sendMessage("Reconnected against " + p.pClient.name)
													p.pClient.sendMessage("Your opponent " + client.name + " reconnected.")



#_______________________________________END MAIN_SERVEUR _________________________________________________________________________________

def main_client(ip, port):#Creating two threads, one for emission, one for reception
	socket_client = socket(AF_INET, SOCK_STREAM)
	socket_client.connect((ip, port))
	tr = thread_r(socket_client)
	ts = thread_s(socket_client)

	tr.start()
	ts.start()

def main():#If there is no argument, we start the server, else we start as a client
	argv = sys.argv
	if len(argv) == 1:
		main_server()
	else:
		ip = sys.argv[1]
		port = 7777
		main_client(ip, port)

main()
