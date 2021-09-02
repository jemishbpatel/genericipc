import types
import json
import retry
import query
from inspect import getmembers
import logging

class _Query:
	def __init__( self, callerGlobals, klass ):
		self._callerGlobals = callerGlobals
		self._klass = klass

	def _queryReturnsDefaultOnError( self ):
		return hasattr( self._klass, "DEFAULT" )

	def _parseKwargs( self, kwargs ):
		logError = not self._queryReturnsDefaultOnError()
		if 'logError' in kwargs:
			logError = kwargs[ 'logError' ]
			del kwargs[ 'logError' ]
		DEFAULT_TIMEOUT_SECONDS = 3
		timeout = DEFAULT_TIMEOUT_SECONDS
		if 'timeout' in kwargs:
			timeout = kwargs[ 'timeout' ]
			del kwargs[ 'timeout' ]
		host = self._callerGlobals.get( 'HOST', 'localhost' )
		if type( host ) is types.FunctionType:
			host = host()
		if 'overrideHost' in kwargs:
			host = kwargs[ 'overrideHost' ]
			del kwargs[ 'overrideHost' ]
		port = self._callerGlobals[ 'PORT' ]
		_packagePath = self._callerGlobals.get( 'PACKAGE_PATH' )
		if _packagePath is not None and os.path.exists( _packagePath ):
			with open( _packagePath, 'r' ) as f:
				port = int( f.read().strip() )
		if 'overridePort' in kwargs:
			port = kwargs[ 'overridePort' ]
			del kwargs[ 'overridePort' ]
		destination = ( host, port )
		if 'overrideDestination' in kwargs:
			destination = kwargs[ 'overrideDestination' ]
			del kwargs[ 'overrideDestination' ]
		bindToIP = None
		if 'bindToIP' in kwargs:
			bindToIP = kwargs[ 'bindToIP' ]
			del kwargs[ 'bindToIP' ]
		queryRetries = 1
		if 'queryRetries' in kwargs:
			queryRetries = kwargs[ 'queryRetries' ]
			del kwargs[ 'queryRetries' ]
		ignoreConnectionRefused = False
		if 'ignoreConnectionRefused' in kwargs:
			ignoreConnectionRefused = kwargs[ 'ignoreConnectionRefused' ]
			del kwargs[ 'ignoreConnectionRefused' ]
		return logError, timeout, host, port, destination, bindToIP, queryRetries, ignoreConnectionRefused

	def __call__( self, * args, ** kwargs ):
		logError, timeout, host, port, destination, bindToIP, queryRetries, ignoreConnectionRefused = self._parseKwargs( kwargs )
		ignoreConnectionRefused = self._callerGlobals.get( 'IGNORE_ECONNREFUSED', False ) or ignoreConnectionRefused

		queryWithRetries = retry.Retry( count = queryRetries, interval = None )( query.query )
		try:
			response = queryWithRetries(	serializer = self._callerGlobals[ '_JSONSerializer' ],
										who = destination,
										what = self._klass( * args, ** kwargs ),
										logError = logError,
										ignoreConnectionRefused = ignoreConnectionRefused,
										timeout = timeout,
										bindToIP = bindToIP )
		#	if isinstance( response, IpcException ):
		#		raise response
			return response
		except:
			if self._queryReturnsDefaultOnError():
				return self._klass.DEFAULT
			raise

def genericQueryModule( tongue, callerGlobals, knownClasses = [], packagePath = None ):
	allTongues = dict( tongue.__dict__ )
	l = [ c for c in allTongues.values() if isinstance( c, types.ClassType ) ]
	serializer = Serializer( l ) 
	callerGlobals[ '_JSONSerializer' ] = serializer
	callerGlobals[ 'PACKAGE_PATH' ] = packagePath
	for className, klass in allTongues.iteritems():
		if not isinstance( klass, types.ClassType ):
			continue
		decamelCased = className[ 0 ].lower() + className[ 1 : ]
		callerGlobals[ decamelCased ] = _Query( callerGlobals, klass )

class _JSONEncoder( json.JSONEncoder ):
	def __init__( self, knownClasses ):
		self._knownClasses = knownClasses
		json.JSONEncoder.__init__( self, separators = ( ',', ':' ), ensure_ascii = True )

	def _serializeMembers( self, obj ):
		DEFAULT_CLASS_ATTRIBUTES_TO_BE_EXCLUDED_FROM_SERIALIZATION = [ "__module__", "__doc__" ]
		toSerialize = { k:v for k,v in getmembers( obj, lambda member: type( member ) != types.MethodType )
						if k not in DEFAULT_CLASS_ATTRIBUTES_TO_BE_EXCLUDED_FROM_SERIALIZATION }
		return toSerialize

	def default( self, obj ):
		print "Debug Default called now"
		if type( obj ) is types.ClassType and obj.__name__ in self._knownClasses:
			print "Debug in if"
			toSerialize = self._serializeMembers( obj )
			print toSerialize
			print obj.__name__
			toSerialize[ '_klass' ] = obj.__name__
			return toSerialize
		elif obj.__class__.__name__ in self._knownClasses:
			print "Debug in elif"
			toSerialize = self._serializeMembers( obj )
			toSerialize[ '_klass' ] = obj.__class__.__name__
			print toSerialize
			return toSerialize
		return json.JSONEncoder.default( self, obj )

class Serializer:
	def __init__( self, classes ):
		self._knownClasses = { klass.__name__: klass for klass in classes }
		for klass in classes:
			self._decorateClassInit( klass )
		self._encoder = _JSONEncoder( self._knownClasses )
		self._decoder = json.JSONDecoder( object_hook = self._decodeObject, encoding = 'ascii' )

	def _decorateClassInit( self, klass ):
		init = klass.__dict__.get( '__init__', None )
		if getattr( init, '_JSON_Serialization_bypassable', False ):
			return
		def decorated( * args, ** kwargs ):
			if kwargs.get( '_bypassConstructionForJSONDeserialization', False ):
				return
			if init is None:
				return
			else:
				return init( * args, ** kwargs )
		decorated._JSON_Serialization_bypassable = True
		klass.__dict__[ '__init__' ] = decorated

	def _decodeObject( self, dct ):
		klassName = dct.get( '_klass', None )
		if klassName is None:
			return dct
		else:
			klass = self._knownClasses.get( klassName, None )
			if klass is None:
				raise Exception( "Unknown class name in JSON deserialization: %s" % klassName )
			del dct[ '_klass' ]
			obj = klass( _bypassConstructionForJSONDeserialization = True )
			obj.__dict__ = { str( k ): v for ( k, v ) in dct.iteritems() }
			return obj

	def serialize( self, value ):
		print "In serialize method"
		return self._encoder.encode( value )

	def deserialize( self, string ):
		try:
			return self._decoder.decode( string )
		except:
			logging.error( "Deserialization failed for string of length %d, starting with '%s'" % ( len( string ), string[ : 60 ] ) )
			raise
