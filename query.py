import socket
import logging
import types
import errno
from commonsocket import Socket


def query( serializer, who, what, logError = True, ignoreConnectionRefused = False, timeout = 3, bindToIP = None, peerClosesConnection = True ):
	LOG_LEVEL_IPC = 1
	sock = Socket()
	if bindToIP is not None:
		sock.bind( ( bindToIP, 0 ) )
	sock.settimeout( timeout )
	print what
	data = serializer.serialize( what )
	if type( who[ 0 ] ) is types.FunctionType:
		who = ( who[ 0 ](), who[ 1 ] )
	try:
		logging.log( LOG_LEVEL_IPC, "Query out: %s (to %s)" % ( data, who ) )
		sock.connect( who )
		sock.sendall( data )

		if peerClosesConnection:
			jsoned = _readEverything( sock )
		else:
			jsoned = _readEverythingWhenPeerDoesNotCloseConnection( sock )

		logging.log( LOG_LEVEL_IPC, "Query in: %s (from %s)" % ( jsoned, who ) )
		return serializer.deserialize( jsoned )
	except socket.error as e:
		if e.errno == errno.ECONNREFUSED and ignoreConnectionRefused:
			pass
		else:
			if logError:
				logging.exception( "Unable to perform query '%s' to '%s'. Exception: %s" % ( what, who, e ) )
			raise
	finally:
		sock.close()


def _readEverything( connection ):
	connection.shutdown( socket.SHUT_WR )

	everything = []
	while True:
		data = connection.recv( 4096 )
		if len( data ) > 0:
			everything.append( data )
		else:
			return "".join( everything )


def _readEverythingWhenPeerDoesNotCloseConnection ( connection ):
	everything = []
	data = connection.recv( 4096 )
	everything.append( data )
	connection.shutdown( socket.SHUT_RDWR )
	return "".join( everything )

