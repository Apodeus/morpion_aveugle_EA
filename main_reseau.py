#!/usr/bin/env python3
from socket import *
from grid import *

import select
import threading
import random


class Client:

	cId = None
	socket = None
	score = 0
	name = "nameless"
	cType = 0 #0 = spec, 1=player

	def __init__(self, socket):
		self.socket = socket

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
	pIsIA = 1 # 1 si humain, 0 sinon
	pGame = -2

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
		if self.pIsIA == 1:
			self.pClient.sendMessage(text)

	def getPlayerGrid(self):
		grid_str = self.pGrid.displayStr()
		print(grid_str)
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
		print("game:" + str(game))
		print("case:" + str(case))
		if self.hGrid[game].cells[case] == EMPTY: #Si personne a joué cette case, alors on effectue le coup correctement
			self.hGrid[game].play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].pGrid.play(self.currentPlayer[game], case)
			self.players[2 * game + self.currentPlayer[game] - 1].displayGrid()
			return True
		else: #sinon on met a jour la grille du joueur et on lui redonne la main pour jouer
			p = self.players[self.currentPlayer[game] - 1]
			p.pGrid.cells[case] = self.hGrid[game].cells[case]
			p.displayGrid()
			p.sendMessage("$play")
			return False

	def switchPlayer(self, game):
		if self.currentPlayer[game] == -1:
			self.currentPlayer[game] += 1
		self.currentPlayer[game] = (self.currentPlayer[game] % 2 ) + 1
		self.players[2 * game + self.currentPlayer[game] - 1].sendMessage("$play")
		

	def addNewClient(self):
		(socket_recv, addr_recv) = self.socketListener.accept()
		c = Client(socket_recv)
		self.listClient.append(c)
		self.listSockets.append(socket_recv)
		c.setId(len(self.listClient))

	def setNewPlayer(self, client):
		p = Player(client)
		self.players.append(p)
		p.setId(len(self.players))
		p.pGame = -1
		client.cType = 1

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
			s += str(i + 1) + ":" + l[i].name + " with " + str(l[i].score) + " wins\n"
		return s

	def endGame(self, game):
		p1 = None
		p2 = None
		for p in self.players:
			if p.pGame == game:
				p.pClient.cType = 0
				if p1 == None:
					p1 = p
				else:
					p2 = p
		#self.players.remove(p1)
		#self.players.remove(p2)
		p1.pClient = None
		p2.pClient = None
		self.hGrid[game] = grid()

def main():
	socket_listen = socket(AF_INET6, SOCK_STREAM, 0)
	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	socket_listen.bind(('', 7777))
	socket_listen.listen(1)

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
					player.sendMessage("$end $draw")
				if end_winner == J1:#J1 a gagné
					player1.sendMessage("$end $win")
					player2.sendMessage("$end $loose")
					player1.pClient.score += 1
				if end_winner == J2:#J2 a gagné
					player2.sendMessage("$end $win")
					player1.sendMessage("$end $loose")
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
				print("Nouveau client connecté")
			else: 
				cId = host.getClientId(current_socket)
				pId = host.getPlayerId(current_socket)
				bytes_recv = bytes.decode(current_socket.recv(1024))
				if pId != -1:
					player = host.getPlayer(pId)
					if pId == host.currentPlayer[player.pGame] + 2 * player.pGame:
						isMoveOk = host.playMove(player.pGame, int(bytes_recv))
						if isMoveOk: #Si l'action s'est bien déroulé
							spec_message = player.pClient.name
							if spec_message == "nameless":
								spec_message = "Player" + str(host.currentPlayer[player.pGame])
							spec_message += " played on case " + bytes_recv + "\n"
							for client in host.listClient:
								if client.cType != 1:
									client.sendMessage(spec_message)
									print("data:" + host.hGrid[player.pGame].displayStr())
									client.sendMessage(host.hGrid[player.pGame].displayStr())
							host.switchPlayer(player.pGame)
				else:
					client = host.getClient(cId)
					if bytes_recv == "play":
						host.setNewPlayer(host.getClient(cId))
						if host.isGameReady() == 1:
							host.startGame()
						else:
							print(client.name + " is looking for an opponent")
							host.getClient(cId).sendMessage("Waiting for opponent...")
							for c in host.listClient:
								if c.cId != cId and c.cType != 1:
									c.sendMessage(client.name + " is looking for an opponent") 
					if bytes_recv == "lead":
						client.sendMessage(host.getScoresString())
					if len(bytes_recv) > 4 and bytes_recv[4] == ':':				#commande
						command = bytes_recv.split(':')
						if command[0] == "name": 			#set client name
							if client.name == "nameless":
								print(command[1] + " joined")
							else:
								print(client.name + " changed name to " + command[1])
							client.setName(command[1])



main()
