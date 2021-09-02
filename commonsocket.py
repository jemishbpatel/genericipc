import socket


class Socket( socket.socket ):
	def close( self ):
		try:
			self.shutdown( socket.SHUT_RDWR )
		except:
			pass
		super( Socket, self ).close()


def closeConnection( connection ):
	try:
		connection.shutdown( socket.SHUT_RDWR )
	except:
		pass
	try:
		connection.close()
	except:
		pass

