import genericquerymodule
import ipctongue

HOST = '127.0.0.1'
PORT = 12700
genericquerymodule.genericQueryModule( tongue = ipctongue, callerGlobals = globals() )
