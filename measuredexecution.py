import logging
import time


class MeasuredExecution:
	def __init__( self, warnIfExecutionExceeds = 1, level = logging.WARNING ):
		self._warnIfExecutionExceeds = warnIfExecutionExceeds
		self._level = level

	def __call__( self, call ):
		def _measuredExecution( * args, ** kwargs ):
			started = time.time()
			try:
				return call( * args, ** kwargs )
			finally:
				elapsed = time.time() - started
				if elapsed > self._warnIfExecutionExceeds:
					logging.log( self._level, "Handler took: %s seconds for (%s, %s)" % ( elapsed, call.func_name, call ) )
		return _measuredExecution


def measureExecution( call, warnIfExecutionExceeds = 1, level = logging.WARNING, * args, ** kwargs ):
	return MeasuredExecution( warnIfExecutionExceeds, level )( call )( * args, ** kwargs )
