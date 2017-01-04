#!/usr/bin/env python3
from socket import *
from grid import *

import select
import threading
import random


# def main():
# 	socket_listen = socket(AF_INET6, SOCK_STREAM, 0)

# 	socket_listen.setsockopt(SOL_SOCKET, SO_REUSEADDR, 1)
# 	socket_listen.bind(('', 7777))
# 	socket_listen.listen(1)

# 	list_clients = []
# 	list_clients.append(socket_listen)

# 	while(True):
# 		(ready_sockets, [], []) = select.select(list_clients, [], [])
# 		for i in range(len(ready_sockets)):
# 			if ready_sockets[i] == socket_listen :
# 				(socket_recv, addr_recv) = socket_listen.accept()
# 				list_clients.append(socket_recv)
# 			else:
# 				bytes_recv = ready_sockets[i].recv(4096)
# 				if len(bytes_recv) == 0: #deconnexion
# 					list_clients.remove(ready_sockets[i])
# 					ready_sockets[i].close()

# 				else:#envoi de message
# 					for j in range(len(list_clients)):
# #						if list_clients[j] != socket_listen and list_clients[j] != ready_sockets[i]:
# 						list_clients[j].send(bytes_recv)

# #!/usr/bin/python3

# from grid import *
# import  random

def printGridPlayer(socket, str_grid):
	socket.send(str.encode(str_grid))

def sendBegin(socket_j1, socket_j2, current_player):
	# print(current_player)
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
		# socket_player.send(str.encode("Choose another case."))
		sendBegin(socket_j1, socket_j2, current_player)
	else: #Sinon le coup est joué, on actualise les grilles et on réaffiche celle du joueur
		grids[current_player].cells[shot] = current_player
		grids[0].play(current_player, shot)
		socket_player.send(str.encode( grids[current_player].displayStr() ))
		current_player = current_player%2 + 1
	print("c'est au tour du joueur" + str(current_player) )

def main():
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
						sendBegin(socket_j1, socket_j2, current_player)

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
					sendBegin(socket_j1, socket_j2, current_player)

				elif ready_sockets[i] == socket_j2 and current_player == J2 : #si c'est au j2
					playMove(bytes_recv, socket_j2) # on joue le move
					sendBegin(socket_j1, socket_j2, current_player)

				else:
					print("something's wrong ...")
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





		



main()
