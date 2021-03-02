import rvisa as visa
import time
from ...__init__ import visalogger as logger
from .driver_base import InstrumentSessionBase
from .visa_object import VISAObject

OPEN_RETRIES = 5

CR = '\r'
LF = '\n'

# Note: this class inherits from the VISAObject class and simply overrides specific methods.
class RVISAObject(VISAObject):
    def __init__(self, address=None, tempSess=False, url=None, timeout=None):
        '''
            Args:
                tempSess (bool): If True, the session is opened and closed every time there is a command
                address (str): The full visa address
                url (str, required): the remote instrumentation server link
        '''
        self.tempSess = tempSess
        self.resMan = None
        self.mbSession = None
        self.address = address
        self._open_retries = 0
        self.__timeout = timeout
        self.__termination=None
        
        # RVisa edit:
        self.url = url
    
    def open(self):
        if self.mbSession is not None:
            return
        if self.address is None:
            raise RuntimeError("Attempting to open connection to unknown address.")
        if self.url is None:
            raise RuntimeError("Remote instrumentation connection is unset.")
        if self.resMan is None:
            self.resMan = visa.ResourceManager(self.url,self.__timeout)
        try:
            self.mbSession = self.resMan.open_resource(self.address)
            if not self.tempSess:
                logger.debug('Opened %s', self.address)
        except Exception as err:
            logger.warning(f"There was a problem connecting. Error:\n {err}")
            
    def close(self):
        if self.mbSession is None:
            return
        try:
            self.mbSession.close()            
        except Exception as err:
            print(err)
            logger.error(f"There was a problem connectin. Error:\n {err}")
            raise
        self.mbSession = None
        if not self.tempSess:
            logger.debug('Closed %s', self.address)
    
    def query(self, queryStr, withTimeout=None):
        retStr = None
        timeout = withTimeout
        try:
            self.open()
            logger.debug('%s - Q - %s', self.address, queryStr)
            try:
                if timeout is None:
                    retStr = self.mbSession.query(queryStr)
                else:
                    # TODO: test this timeout version
                    retStr = self.mbSession.query(queryStr,timeout)
            except Exception:
                logger.error('Problem querying to %s', self.address)
                # self.close()
                raise
            retStr = retStr.rstrip()
            logger.debug('Query Read - %s', retStr)
        finally:
            if self.tempSess:
                self.close()
        return retStr
    
    def write(self, writeStr):
        try:
            self.open()
            try:
                self.mbSession.write(writeStr)
            except Exception:
                logger.error('Problem writing to %s', self.address)
                raise
            logger.debug('%s - W - %s', self.address, writeStr)
        finally:
            if self.tempSess:
                self.close()


    
    @property
    def timeout(self):
        if self.__timeout is None:
            if self.mbSession is None:
                try:
                    self.open()
                finally:
                    if self.tempSess:
                        self.close()
            else:
                pass # NOTE: RVisa does not have a built-in attribute for timeouts under our ResourceManager. Timeouts are handled on a query-basis.
        return self.__timeout
        
    @property
    def termination(self):
        if self.mbSession is not None:
            self._termination = self.mbSession.write_termination
        return self._termination

    @termination.setter
    def termination(self, value):
        if value in (CR, LF, CR + LF, ''):
            self._termination = value
        else:
            raise ValueError("Termination must be one of these: CR, CRLF, LR, ''")
        if self.mbSession is not None:
            self.mbSession.write_termination = value