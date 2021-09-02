import os
import select
import errno


class InterruptibleSelect:
	def __init__( self ):
		read, write = os.pipe()
		self._read = os.fdopen( read, "r" )
		self._write = os.fdopen( write, "w" )
		self._stopped = False
		self._interrupted = False

	def __del__( self ):
		self._safeClose()

	def interrupt( self ):
		self._interrupted = True
		os.write( self._write.fileno(), "x" )

	def interrupted( self ):
		return self._interrupted

	def __enter__( self ):
		return self

	def __exit__( self, * args ):
		self._safeClose()

	def select( self, read, * args ):
		self._interrupted = False
		assert isinstance( read, list ), "Need to pass a 'read' list to select function"
		while True:
			try:
				readReady, writeReady, exceptionReady = select.select( read + [ self._read ], * args )
				break
			except select.error, e:
				errorCode, message = e
				if errorCode == errno.EINTR:
					if self._interrupted:
						return
					continue
				raise

		if self._read in readReady:
			os.read( self._read.fileno(), 8 )
			readReady.remove( self._read )
		return readReady, writeReady, exceptionReady

	def _safeClose( self ):
		if not self._stopped:
			self.stop()

	def stop( self ):
		assert not self._stopped, "stopped twice"
		self._stopped = True
		self._read.close()
		self._write.close()

