# RVisa Lightlab modifications

## `rvisa_object.py`
Created a class called `RVISAObject` that is functionally identical to `VISAObject` which is found inside `visa_object.py`. It inherits from the `VISAObject` class but replaces the connection methods with RVisa compatible versions (via overriding methdos). For someone with class-design experience (ie. someone who worked on the original package), this should be relatively simple to change (<1hr for me, and this was one of my first deep dives into `lightlab`).

This is found inside `lightlab.equipment.visa_bases`. I added a line under the `__init__.py` inside that folder as well to ensure my custom class is imported correctly:
```Python
from .rvisa_object import RVISAObject```

The main changes include:
- An added ".url" resource under the main class, with initialization happening inside the constructor
- `open()`, `close()`, `query()` since they relied on PyVISA error handling (replaced with a basic error handling on our end)
- Overriden `timeout()` and `termination()` since RVisa resource manager does not keep track of these as variables

This was testing with the following lines of code:
```Python
import lightlab.equipment.visa_bases as visa_obj
instr = visa_obj.RVISAObject("GPIB0::7::INSTR", url="https://1000000058948db1-api.nwtech.win/")
instr.url # 'https://1000000058948db1-api.nwtech.win/'
instr.open()
instr.instrID() # response: 'AGILENT TECHNOLOGIES,54622D,MY40005835,A.02.01'
instr.query("*OPT?",withTimeout=0) # asks for firmware version; response: 'N2757A,A.02.01'
```

This is based on what the `VISAObject` class would be used as when called locally instead of remotely. This also assumes that the user knows what instruments are hidden behind each interface.

## Inherited Drivers
To fully allow the existing inherited drivers to immediatley use RVisa back-end, there are some other "tricks" we need to do.

The existing instrument classes mostly inherit from `VISAInstrumentDriver` under `lightlab.equipment.lab_instruments`. This in turn is found in `lightlab.equipment.visa_bases.visa_driver.py` and placed under `lightlab.equipment.visa_bases`. The classes that will need to be modified should be:
- `InstrumentSession` and `VISAInstrumentDriver` which inherits the former.

Then, the instruments themselves have to utilize `RVISAInstrumentDriver` as opposed to `VISAInstrumentDriver`.
To do so, I added the following changes:
- Created a `rvisa_base.py` file that contains `RemoteSession` and `RVISAInstrumentDriver` classes
  - `RemoteSession` inherits from the `InstrumentSession` class, and it overrides the constructor to pass in an additional url for RVisa (much like `RVISAObject` requires)
  - `RVISAObject` inherits from `RemoteSession` and is functionally identical to `VISAInstrumentDriver` with an extra `url` portion
- Added `RVISAInstrumentDriver` under `__init__.py` inside `lightlab.equipment.visa_bases` for proper imports

Inside the actual instrument driver themselves, the following changes needed to be made:
- In the folder `lightlab.equipment.lab_instruments`, the `__init__.py` file needs to import `RVISAInstrumentDriver`
- Replace `VISAInstrumentDriver` with `RVISAInstrumentDriver` equivalents (ie. add a `url` like before)

I tested this step by step:
```Python
from lightlab.equipment.visa_bases.rvisa_driver import RVISAInstrumentDriver, RemoteSession
# RemoteSession
session = RemoteSession(address="GPIB0::7::INSTR", tempSess=False, url="https://1000000058948db1-api.nwtech.win/")
session.query('*IDN?') # Output: 'AGILENT TECHNOLOGIES,54622D,MY40005835,A.02.01'
session.close() # Output: RESOURCE SUCCESSFULLY CLOSED

# RVISAInstrumentDriver
driver = RVISAInstrumentDriver(address="GPIB0::7::INSTR", url="https://1000000058948db1-api.nwtech.win/", tempSess=False)
driver.query_ascii_values("measure:vaverage? channel1") # Output: [0.02726]
driver.url # Output: 'https://1000000058948db1-api.nwtech.win/'
driver.instrID() # Output: 'AGILENT TECHNOLOGIES,54622D,MY40005835,A.02.01'
driver.close() # Output: RESOURCE SUCCESSFULLY CLOSED

# Check importing from visa_bases
import lightlab.equipment.visa_bases as pack
b = pack.RVISAInstrumentDriver(address="GPIB0::7::INSTR", url="https://1000000058948db1-api.nwtech.win/", tempSess=False)
# can perform the same tests as above
```

For testing purposes, I used the `Tektronix_DPO4034_Oscope` class with a modified `RVISAInstrumentDriver` class (appended as an additional class under the file it is placed in.). This is currently not fully working (not sure what the issue is). Here is the test code used:
```Python
from lightlab.equipment.lab_instruments.Tektronix_DPO4034_Oscope import Remote_Tektronix_DPO4034_Oscope

link = 'https://1000000058948db1-api.nwtech.win/'
a = Remote_Tektronix_DPO4034_Oscope(address="GPIB::7::INSTR", url=link)

a.url
a.query('*IDN?')
a._TekScopeAbstract__transferData(1) #THROWS error
```

NOTE: this is because `Configurable`, a class inherited in these drivers, utilize a "write" method based on which "back-end" is chosen. Thus, when writing the RVisa drivers, the "write" method must be overloaded as well.

To fix the imports, you should check the `__init__.py` file under `lightlab.equipment.lab_instruments`, and make the following adjustment:
```Python
from ..visa_bases import VISAInstrumentDriver
from ..visa_bases import RVISAInstrumentDriver # ADD THIS

# This imports all of the modules in this folder
# As well as all their member classes that are VISAInstrumentDriver
import importlib
import pkgutil


class BuggyHardware(Exception):
    ''' Not all instruments behave as they are supposed to.
        This might be lab specific. atait is not sure exactly how to deal with that.
    '''


for _, modname, _ in pkgutil.walk_packages(path=__path__,  # noqa
                                           prefix=__name__ + '.'):
    _temp = importlib.import_module(modname)
    for k, v in _temp.__dict__.items():
        if k[0] != '_' and type(v) is not type:
            try:
                mro = v.mro()
            except AttributeError:
                continue
            if VISAInstrumentDriver in mro:
                globals()[k] = v
            # ADD THE SECTION BELOW
            if RVISAInstrumentDriver in mro:
                globals()[k] = v
```

This has been fixed, and now I am able to utilize the in-built driver classes to run commands:
```Python
from lightlab.equipment.lab_instruments import Remote_Tektronix_DPO4034_Oscope
link = 'https://1000000058948db1-api.nwtech.win/'
remote = Remote_Tektronix_DPO4034_Oscope(address="GPIB::7::INSTR", url=link)
try:
    remote.acquire() # This will try to send the TekScope commands for acquisition
except:
    # Since I am testing this with an oscilloscope that is not Tektronix, it will not respond to it.
    # Querying the VISA error on the instrument will tell me that it is wrong
    print(remote.driver.query('SYST:ERR?'))
    # Output: -224,"Illegal parameter value"
```

## Next step: test with Keithley 2606B

### Debugging
- Some imports are not being loaded properly (namely, the `RVISAInstrumentDriver` class is not getting imported)
  - This is possibly due to the way I overrode the `InstrumentSession` class (the inheritance adds additional functional arguments that might not be supported by the parent class)
    - Note: https://stackoverflow.com/questions/6034662/python-method-overriding-does-signature-matter
  - Main reasons for errors:
    - Typos in my code
    - Getting a type error:
```Python
~/work/rvisa_lightlab/lightlab/equipment/lab_instruments/Tektronix_DPO4034_Oscope.py in __init__(self, name, address, url, **kwargs)
     47 
     48     def __init__(self, name='The DPO scope', address=None, url=None, **kwargs):
---> 49         RVISAInstrumentDriver.__init__(self, name=name, address=address, url=url, **kwargs)
     50         TekScopeAbstract.__init__(self)
     51 

~/work/rvisa_lightlab/lightlab/equipment/visa_bases/rvisa_driver.py in __init__(self, name, address, url, **kwargs)
     28         if 'tempSess' not in kwargs.keys():
     29             kwargs['tempSess'] = True
---> 30         super().__init__(address=address, url=url, **kwargs)
     31         self.__started = False
     32 

TypeError: unsupported operand type(s) for ** or pow(): 'str' and 'dict'
```

## Changes are currently in a Private Repo that I own