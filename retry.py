import logging
import time

class Retry:
	def __init__( self, count = 3, interval = 1, logExceptionMessage = None, callback = None ):
		self._count = count
		self._interval = interval
		self._callback = callback
		self._logExceptionMessage = logExceptionMessage

	def __call__( self, call ):
		def _retry( * args, ** kwargs ):
			for retry in xrange( self._count - 1 ):
				try:
					return call( * args, ** kwargs )
				except:
					if self._logExceptionMessage is not None:
						logging.exception( self._logExceptionMessage )
					if self._interval is not None:
						time.sleep( self._interval )
					if self._callback is not None:
						self._callback()
			return call( * args, ** kwargs )
		return _retry
