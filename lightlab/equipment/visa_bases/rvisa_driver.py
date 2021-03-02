from ...__init__ import visalogger as logger #from the commented section to the actual code #from lightlab import visalogger
from .visa_driver import DriverMeta
import inspect

from .visa_driver import InstrumentSession, _AttrGetter
from .rvisa_object import RVISAObject

class RemoteSession(InstrumentSession):
    _session_object = None
    
    def __init__(self, address=None, tempSess=False, url=None, **kwargs):
        self.reinstantiate_session(address=address, tempSess=tempSess, url=url)
        self.tempSess = tempSess
        self.address = address
        self.url = url
    
    def reinstantiate_session(self, address=None, tempSess=None, url=None, **kwargs):
        self._session_object = RVISAObject(address=address, tempSess=tempSess, url=url)
    
    
class RVISAInstrumentDriver(RemoteSession, metaclass=DriverMeta):
    instrument_category = None

    def __init__(self, name='Default Driver', address=None, url=None, **kwargs):
        # pylint: disable=unused-argument
        self.name = name
        self.address = address
        self.url = url
        kwargs.pop('directInit', False)
        if 'tempSess' not in kwargs.keys():
            kwargs['tempSess'] = False
        super().__init__(address=address, url=url, **kwargs)
        self.__started = False

    def startup(self):
        visalogger.debug("%s.startup method empty", self.__class__.__name__)

    def open(self):
        super().open()
        if not self.__started:
            self.__started = True
            self.startup()

    def close(self):
        super().close()
        self.__started = False