import rvisa as visa
import matplotlib.pyplot as plt
import numpy as np
import time
'''
using documentation from https://literature.cdn.keysight.com/litweb/pdf/08164-90B65.pdf?id=118032
functions that aren't added:
#############
force sending commands even if they don't do anything 
enable auto error check
get slot info
return list of indexes and detector numbers
register/unregister mainframe
return # of registered PWM channels
return # of sweeping channels
setting range
setting sweep speed
read power
return first TLS slot
list all TLS
set TLS output
set PWM units
set PWM range
turn TLS output on/off
set TLS wavelength
set TLS power
find names of each instrument in slots
findClostestValidx??????????????
##########
some of these are related to the driver's personal sweep function. idk if we'd even want to add these
'''
class hp816(object):
    # Change this to the IDN string of your instrument
    # if you do not know this, then set this to ''
    name = ''
    rm = ''
    api = ''
    connected = False

    # Use this init function
    def __init__(self, api_addr=" "):
        self.rm = visa.ResourceManager(api_addr)
        self.api = api_addr
        self.connected = self.rm.CONNECTED

    # Optional: if you want to automatically find out what addresses the instrument is on
    def find(self):
        has_instr = list()
        if self.connected:
            resources = self.rm.list_resources()
            for res in resources:
                ID = self.rm.open_resource(res).query('*IDN?')
                if ID == self.name:
                    has_instr.append(res)
            return tuple(has_instr)
        else:
            raise Exception('Not connected!')
    
    # Use this function
    def connect(self, visaAddr):
        self.instr = self.rm.open_resource(visaAddr)
        self.instr.write('SOUR:POW:ATT:AUTO 1')###ADDED THIS FUNCTION DON"T KNOW IF IT WORKS

    # Use this function
    def close(self, visaAddr):
        self.instr.close()

    # Optional function: returns IDN string
    def idn(self):
        return self.instr.query('*IDN?')
    
    def query(self,quer):
        return self.instr.query(str(quer))

    def setTLSState(self,state):
        self.instr.write('SOUR:POW:STAT '+str(state))

    def getTLSState(self):
        return(self.instr.query('SOUR:POW:STAT?'))
    
    def setWavelength(self,wavelength):#(need to write wavelength as '1550NM','1650NM',etc)
        self.instr.write('SOUR:WAV '+str(wavelength))

    def getWavelength(self):
        return(self.instr.query('SOUR:WAV?'))
   
    def setOutputPower(self,power):#tpower is in db
        self.instr.write('SOUR:POW '+str(power))

    def getOutputPower(self):
        return(self.instr.query('SOUR:POW?'))

    def readPWM(self):#Pretty sure this is just getOutputPower want to test though 
        return(self.instr.query('SOUR:POW?'))


