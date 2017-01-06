#!/usr/bin/env python3
from socket import *
from grid import *

import select
import threading
import random

import sys
import re



symbols = [' ', 'O', 'X']
EMPTY = 0
J1 = 1
J2 = 2
NB_CELLS=9


play_mode = 0;
expect_answer = 0;

class grid:
		cells = []
		def __init__(self):
				self.cells = []
				for i in range(NB_CELLS):
						self.cells.append(EMPTY)

		def play(self, player, cellNum):
				assert(0<= cellNum and cellNum < NB_CELLS)
				assert(self.cells[cellNum] == EMPTY)
				self.cells[cellNum] = player

		""" Display the state of the game
				Example of output : 
				-------
				|O| |X|
				-------
				|X|O| |
				-------
				| | |O| 
				-------
		"""
		def display(self):
				print("-------------")
				for i in range(3):
						print("|",symbols[self.cells[i*3]], "|",  symbols[self.cells[i*3+1]], "|",  symbols[self.cells[i*3+2]], "|");
						print("-------------")
						
		def displayStr(self):
				grid_str = "$display $"
				for i in range(3):
						grid_str = grid_str + str(self.cells[i*3]) +  str(self.cells[i*3+1]) + str(self.cells[i*3+2])
				return grid_str

		""" Test if 'player' wins the game"""
		def winner(self, player):
				assert(player==J1 or player==J2)
				# horizontal line
				for y in range(3): 
						if self.cells[y*3] == player and self.cells[y*3+1] == player and self.cells[y*3+2] == player:
										return True
				# vertical line
				for x in range(3): 
						if self.cells[x] == player and self.cells[3+x] == player and self.cells[6+x] == player:
										return True
				#diagonals :
				if self.cells[0] == player and self.cells[4] == player and self.cells[8] == player:
						return True
				if self.cells[2] == player and self.cells[4] == player and self.cells[6] == player:
						return True
				return False
		
		""" Return the state of the game: -1 if the game is not over, EMPTY if DRAW; J1 if player 1 wins and J2 if player 2 wins.
		"""
		def gameOver(self):
				if self.winner(J1):
						return J1
				if self.winner(J2):
						return J2
				for i in range(NB_CELLS):
						if(self.cells[i] == EMPTY):
								return -1
				return 0


class Client:

	cId = None
	socket = None
	score = 0
	name = "nameless"
	cType = 0 #0 = spec, 1=player
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
	pIsAI = 0 # 0 si humain, 1 sinon
	pGame = -2
	isWaiting = 0 #0 normal, 1 attends pour reco, -1 a deco

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
		grid_str = self.pGrid.displayStr()
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
		if self.hGrid[game].cells[case] == EMPTY: #Si personne a joué cette case, alors on effectue le coup correctement
			self.hGrid[game].play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].pGrid.play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].displayGrid()
			return True
		else: #sinon on met a jour la grille du joueur et on lui redonne la main pour jouer
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
					c.sendMessage(self.hGrid[player.pGame].displayStr())
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
		for p in self.players:#la partie commence, on affiche les grilles de chaque joueur et on donne la main au 1er joueur
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
		#self.players.remove(p1)
		#self.players.remove(p2)
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


class thread_r(threading.Thread):
	def __init__(self, s):
		threading.Thread.__init__(self)
		self.socket_client = s

	def run(self):
		while(True):
			data = bytes.decode(self.socket_client.recv(1024) )
			if (len(data) != 0):
				parsed_data = re.findall('\$[a-zA-Z0-9]+', data)
				if parsed_data:
					for i in range(len(parsed_data)):
						word = parsed_data[i]
						if word == "$gamestart":
							print("Game started")
						elif word == "$play":
							print("Play on a case (0 to 8):")
							play_mode = 1;

						elif word == "$display":
							i = i + 1
							word2 = parsed_data[i]
							# print(word2)
							grid_str = "-------------\n"
							for case_i in range(3):
								grid_str = grid_str + "| " + symbols[int(word2[case_i*3 + 1])] + " | " +  symbols[int(word2[case_i*3+1 + 1])] + " | " +  symbols[int(word2[case_i*3+2 + 1])] + " |\n" + "-------------\n"
							print(grid_str)

						elif word == "$end":
							i += 1
							play_mode = 0
							word2 = parsed_data[i]
							if word2 == "$win":
								print("You win")
							elif word2 == "$loose":
								print("You loose")
							elif word2 == "$draw":
								print("Draw !")

				else:
					print(data)

class thread_s(threading.Thread):
	def __init__(self, s):
		threading.Thread.__init__(self)
		self.socket_client = s

	def run(self):
		while True:
			text = input("")
			if text == "help":
				print("Available commands : \n name:<name> \t Change your current name to <name>\n play \t\t Start a game against another player\n spec:<ID> \t Watch game <ID> \n playAI \t Start a game against the AI\n join:<name>\t Join an unfinished game against <name>\n quit\t\t Cancel a game")
			elif play_mode == 1:
				self.socket_client.send(str.encode(text))
			else:
				self.socket_client.send(str.encode(text))

#_________________________FIN DES CLASSES____________________________________________________________________________

def main_server():
	socket_listen = socket(AF_INET, SOCK_STREAM, 0)
	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	socket_listen.bind((gethostbyname(gethostname()), 7777))
	socket_listen.listen(1)

	print("Servers up at ( hostname = " + gethostname()+ " )"+gethostbyname(gethostname()) + "\n You can connect using either of those as argument for the client.")
	host = Host(socket_listen)

	while(1):
		for g in range(len(host.hGrid)):
			if (host.isGameOver(g) != -1): #Si la partie est fini
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
					player.sendMessage(host.hGrid[g].displayStr() + " $end $draw")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player1.pClient.name + " and " + player2.pClient.name + " ended their game on a draw.")
				if end_winner == J1:#J1 a gagné
					player1.sendMessage(host.hGrid[g].displayStr() + " $end $win")
					player2.sendMessage(host.hGrid[g].displayStr() + " $end $loose")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player1.pClient.name + " won against " + player2.pClient.name + ".")
					player1.pClient.score += 1
				if end_winner == J2:#J2 a gagné
					player2.sendMessage(host.hGrid[g].displayStr() + " $end $win")
					player1.sendMessage(host.hGrid[g].displayStr() + " $end $loose")
					for c in host.listClient:
						if c.cId != cId and c.cType != 1:
							c.sendMessage(player2.pClient.name + " won against " + player1.pClient.name + ".")
					player2.pClient.score += 1
				# looser.pClient.score += 1


				# winner = host.getPlayer(host.isGameOver())
				# winner.sendMessage("$end $win")
				# winner.pClient.score += 1
				# looser = host.getPlayer((host.isGameOver() % 2 )+ 1)
				# looser.sendMessage("$end $loose")
				host.endGame(g)

		(ready_sockets, [], []) = select.select(host.listSockets, [], [])
		for current_socket in ready_sockets:
			if current_socket == host.socketListener: #Connexion d'un nouveau client
				host.addNewClient()
				print("A new client connected")
			else:
				cId = host.getClientId(current_socket)
				pId = host.getPlayerId(current_socket)
				bytes_recv = bytes.decode(current_socket.recv(1024))
				if len(bytes_recv) == 0 :#DECONNEXION D UN CLIENT
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
						try:
							isMoveOk = host.playMove(player.pGame, int(bytes_recv))
						except ValueError:
							isMoveOk = False
							
						# isMoveOk = host.playMove(player.pGame, int(bytes_recv))
						if isMoveOk: #Si l'action s'est bien déroulé
							for c in host.listClient:
								if c.cType != 1 and c.cSpec == player.pGame:
									c.sendMessage(host.hGrid[player.pGame].displayStr())
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



#_______________________________________FIN MAIN SERVEUR _________________________________________________________________________________

def main_client(ip, port):
	socket_client = socket(AF_INET, SOCK_STREAM)
	socket_client.connect((ip, port))
	tr = thread_r(socket_client)
	ts = thread_s(socket_client)

	tr.start()
	ts.start()

def main():
	argv = sys.argv
	if len(argv) == 1:
		main_server()
	else:
		ip = sys.argv[1]
		port = 7777
		main_client(ip, port)

main()
