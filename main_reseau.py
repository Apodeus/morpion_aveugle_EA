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
	currentPlayer = -1
	hGrid = None
	players = []
	specs = []

	def __init__(self, socketListener):
		self.socketListener = socketListener
		self.hGrid = grid()
		self.listSockets.append(socketListener)

	def isGameOver(self):
		if self.hGrid.gameOver() != -1 :
			self.currentPlayer = -1
		return self.hGrid.gameOver()

	def playMove(self, case):	#returns True if ok
		if self.hGrid.cells[case] == EMPTY: #Si personne a joué cette case, alors on effectue le coup correctement
			self.hGrid.play(self.currentPlayer, case)
			self.players[self.currentPlayer - 1].pGrid.play(self.currentPlayer, case)
			self.players[self.currentPlayer - 1].displayGrid()
			return True
		else: #sinon on met a jour la grille du joueur et on lui redonne la main pour jouer
			p = self.players[self.currentPlayer - 1]
			p.pGrid.cells[case] = self.hGrid.cells[case]
			p.displayGrid()
			p.sendMessage("$play")
			return False

	def switchPlayer(self):
		if self.currentPlayer == -1:
			self.currentPlayer += 1
		self.currentPlayer = (self.currentPlayer % 2 ) + 1
		self.players[self.currentPlayer - 1].sendMessage("$play")
		

	def addNewClient(self):
		(socket_recv, addr_recv) = self.socketListener.accept()
		c = Client(socket_recv)
		self.listClient.append(c)
		self.listSockets.append(socket_recv)
		c.setId(len(self.listClient))

	def setNewPlayer(self, client):
		if len(self.players) <= 1:
			p = Player(client)
			self.players.append(p)
			p.setId(len(self.players))
		else:
			return

	def getPlayerId(self, socket):
		for p in self.players:
			if socket == p.pClient.socket:
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
		if len(self.players) == 2:
			return 1
		return 0

	def startGame(self):
		print("Game start")
		self.hGrid = grid()
		for p in self.players:#la partie commence, on affiche les grilles de chaque joueur et on donne la main au 1er joueur
			p.sendMessage("$gamestart")
			p.displayGrid()
		self.switchPlayer()

	def getScores(self):
		l = sorted(self.listClient, key=lambda x: x.score, reverse=True)
		return l

	def getScoresString(self):
		l = self.getScores()
		s = ""
		for i in range(len(l)):
			s += str(i + 1) + ":" + l[i].name + " with " + str(l[i].score) + " wins\n"
		return s

	def endGame(self):
		self.players.remove(self.getPlayer(1))
		self.players.remove(self.getPlayer(2))
		self.hGrid = grid()



def printGridPlayer(socket, str_grid):
	socket.send(str.encode(str_grid))

def sendBegin(socket_j1, socket_j2):
	# print(current_player)
	global current_player
	if(socket_j1 == None or socket_j2 == None):
		return
	if(current_player == J1):
		socket_j1.send(str.encode("begin"))
	else:
		socket_j2.send(str.encode("begin"))

def playMove(bytes_recv, socket_player):
	global current_player 
	global grids 
	shot = int(bytes.decode(bytes_recv))
	if grids[0].cells[shot] != EMPTY: # Si la case est déjà prise alors on réactualise la grille du joueur et on la reaffiche
		grids[current_player].cells[shot] = grids[0].cells[shot]
		socket_player.send(str.encode( grids[current_player].displayStr() ))
		# sendBegin(socket_j1, socket_j2)
	else: #Sinon le coup est joué, on actualise les grilles et on réaffiche celle du joueur
		grids[current_player].cells[shot] = current_player
		grids[0].play(current_player, shot)
		socket_player.send(str.encode( grids[current_player].displayStr() ))
		current_player = current_player%2 + 1
		# sendBegin(socket_j1, socket_j2)
	print("c'est au tour du joueur " + str(current_player) )

def main_old():
	socket_listen = socket(AF_INET6, SOCK_STREAM, 0)
	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	socket_listen.bind(('', 7777))
	socket_listen.listen(1)
	global socket_j1, socket_j2
	socket_j1 = None
	socket_j2 = None
	list_clients = []
	list_clients.append(socket_listen)

	global current_player 
	global grids 
	current_player = J1
	grids = [grid(), grid(), grid()]

	while(grids[0].gameOver() == -1):
		(ready_sockets, [], []) = select.select(list_clients, [], [])
		for i in range(len(ready_sockets)):
			if ready_sockets[i] == socket_listen: # Connexion d'un client
				if socket_j1 == None or socket_j2 == None:
					(socket_recv, addr_recv) = socket_listen.accept()
					print("Connexion en cours avec un client...")

					if socket_j1 == None:
						print("joueur1 est connecté ..")
						socket_j1 = socket_recv
						list_clients.append(socket_recv)
						socket_j1.send(str.encode(grids[J1].displayStr() ))

					elif socket_j2 == None:
						print("joueur2 est connecté ..")
						socket_j2 = socket_recv
						list_clients.append(socket_recv)
						socket_j2.send(str.encode(grids[J2].displayStr() ))
						sendBegin(socket_j1, socket_j2)#Le joueur 2 a rejoint, on peut lancer le début

				else:
					socket_recv.send(str.encode("Server is full."))

			elif socket_j1 != None and socket_j2 != None : #Reception d'un message d'une socket joueur

				bytes_recv = ready_sockets[i].recv(1024) 
				# print(current_player)
				if len(bytes_recv) == 0: #Deconnexion
					list_clients.remove(ready_sockets[i])
					ready_sockets[i].close()
				elif ready_sockets[i] == socket_j1 and current_player == J1 : #Si c'est au joueur1
					playMove(bytes_recv, socket_j1) #on joue le move

				elif ready_sockets[i] == socket_j2 and current_player == J2 : #si c'est au j2
					playMove(bytes_recv, socket_j2) # on joue le move

				else:
					print("something's wrong ...")

				sendBegin(socket_j1, socket_j2)
	#FIN DE PARTIE / ANNONCE DES SCORES
	socket_j1.send(str.encode("GAME OVER !"))
	socket_j2.send(str.encode("GAME OVER !"))

	socket_j1.send(str.encode( grids[0].displayStr() ))
	socket_j2.send(str.encode( grids[0].displayStr() ))

	if grids[0].gameOver() == J1:
		socket_j1.send(str.encode( "YOU WIN !" ))
		socket_j2.send(str.encode( "YOU LOOSE !" ))

	elif grids[0].gameOver() == J2:
		socket_j2.send(str.encode( "YOU WIN !" ))
		socket_j1.send(str.encode( "YOU LOOSE !" ))
	else:
		socket_j1.send(str.encode("EGALITY"))
		socket_j2.send(str.encode("EGALITY"))

	socket_j1.close()
	socket_j2.close()


def main():
	socket_listen = socket(AF_INET6, SOCK_STREAM, 0)
	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
	socket_listen.bind(('', 7777))
	socket_listen.listen(1)

	host = Host(socket_listen)

	while(1):
		
		if (host.isGameOver() != -1): #Si la partie est fini
			end_winner = host.isGameOver()
			if end_winner == EMPTY:#draw
				for player in host.players:
					player.sendMessage("$end $draw")
			elif end_winner == J1:#J1 a gagné
				looser = host.getPlayer(J2)
				winner = host.getPlayer(J1)

			elif end_winner == J2:#J2 a gagné
				looser = host.getPlayer(J1)
				winner = host.getPlayer(J2)
				
			if end_winner != EMPTY :
				winner.sendMessage("$end $win")
				winner.pClient.score += 1
				looser.sendMessage("$end $loose")
				# looser.pClient.score += 1


			# winner = host.getPlayer(host.isGameOver())
			# winner.sendMessage("$end $win")
			# winner.pClient.score += 1
			# looser = host.getPlayer((host.isGameOver() % 2 )+ 1)
			# looser.sendMessage("$end $loose")
			host.endGame()

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
					if pId == host.currentPlayer:
						isMoveOk = host.playMove(int(bytes_recv))
						if isMoveOk: #Si l'action s'est bien déroulé
							spec_message = player.pClient.name
							if spec_message == "nameless":
								spec_message = "Player" + str(host.currentPlayer)
							spec_message += " played on case " + bytes_recv + "\n"
							for client in host.listClient:
								if client.cId != host.players[0].pClient.cId and client.cId != host.players[1].pClient.cId:
									client.sendMessage(spec_message)
									client.sendMessage(host.hGrid.displayStr())
							host.switchPlayer()
				else:
					client = host.getClient(cId)
					if bytes_recv == "play":
						host.setNewPlayer(host.getClient(cId))
						if host.isGameReady() == 1:
							host.startGame()
						else:
							print(client.name + " is looking for an opponent")
							host.getClient(cId).sendMessage("Waiting for opponent...")
							for client in host.listClient:
								if client.cId != cId:
									client.sendMessage(client.name + " is looking for an opponent") 
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
