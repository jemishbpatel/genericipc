from server import Server
import ipctongue

class QueryHandler:
	def __init__( self ):
		self.__ipcServer = Server( handlers = { ipctongue.SetupAccessPoint : self._handleSetupAccessPoint } )

	def _handleSetupAccessPoint( self, parameters ):
		print "Receivied parameters"
		print parameters.wifiConfiguration
		return "OK"
def main():
        queryHandler = QueryHandler()

if __name__ == "__main__":
        main()

