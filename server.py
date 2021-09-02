import socket
from genericquerymodule import Serializer
from commonsocket import Socket, closeConnection
from ipc import HOST, PORT
import interruptibleselect
import measuredexecution
import select
import logging
import time

class Server:
	def __init__( self, port = 12700, handlers = {} ):
		self._handlers = dict( handlers )
		self._serializer = Serializer( self._handlers )
		self._initSocket()
		self._select = interruptibleselect.InterruptibleSelect()
		self._peerClosesConnection = True
		self.safeRun()

	def safeRun( self ):
		TIME_TO_SLEEP_UPON_ERROR_IN_SECONDS = 0.05
		while True:
			try:
				readReady, unused, exceptions = self._select.select( self._fileDescriptors, [], self._fileDescriptors )
				for connection in readReady:
					if self._clientConnection( connection ):
						self._incomingConnection( connection )
					else:
						self._accept()
				for connection in exceptions:
					if self._clientConnection( connection ):
						self._close( connection )
					else:
						self._initSocket()
			except socket.error as e:
				if e.errno == socket.EINTR:
					logging.info( 'Interrupted system call' )
					continue
				if e.errno == socket.EBADF:
					self._initSocket()
					continue
				return
			except select.error as e:
				logging.exception( 'Select Error - reinitializing. Error: %s' % e )
				time.sleep( TIME_TO_SLEEP_UPON_ERROR_IN_SECONDS )
				continue
			except ValueError as e:
				logging.warning( "IPC server failed to work. Exception: %s. Maybe file descriptors issue. FD list: %s" % ( e, [ fd.fileno() for fd in self._fileDescriptors ] ) )
				time.sleep( TIME_TO_SLEEP_UPON_ERROR_IN_SECONDS )
				continue
			except Exception as e:
				logging.exception( 'Server exception: %s' % e )
				time.sleep( TIME_TO_SLEEP_UPON_ERROR_IN_SECONDS )
				continue						

	def _accept( self ):
		connection, peer = self._socket.accept()
		self._fileDescriptors.append( connection )

	def _initSocket( self ):
		self._socket = Socket()
		self._socket.setsockopt( socket.SOL_SOCKET, socket.SO_REUSEADDR, 1 )
		self._socket.bind( ( HOST, PORT ) )
		self._socket.listen( 300 )
		self._fileDescriptors = [ self._socket ]
	
	def _clientConnection( self, connection ):
		return self._socket != connection

	def _close( self, connection ):
		self._fileDescriptors.remove( connection )
		closeConnection( connection )

	def _callHandler( self, handler, thing ):
		return measuredexecution.measureExecution( handler, 1, logging.WARNING, thing )

	def _incomingConnection( self, connection ):
		thing = None
		try:
			if self._peerClosesConnection:
				data = self._readEverything( connection )
			else:
				data = self._readEverythingWhenPeerDoesNotCloseConnection( connection )
			if len( data ) == 0:
				raise Exception( "connection closed by client" )

			thing = self._serializer.deserialize( data )
			response = None
			if thing.__class__ in self._handlers:
				response = self._callHandler( self._handlers[ thing.__class__ ], thing )

			self.__respond( thing, connection, response )
		except Exception as e:
			logging.exception( "Failed to handle incoming connection. Exception: %s" % e )
		finally:
			closeConnection( connection )
		self._fileDescriptors.remove( connection )

	def __respond( self, thing, connection, response ):
		jsoned = self._serializer.serialize( response )
		connection.send( jsoned )

	def _readEverything( self, connection ):
		everything = []
		while True:
			data = connection.recv( 4096 )
			if len( data ) > 0:
				everything.append( data )
			else:
				return "".join( everything )

	def _readEverythingWhenPeerDoesNotCloseConnection( self, connection ):
		everything = []
		data = connection.recv( 4096 )
		everything.append( data )
		return "".join( everything )

