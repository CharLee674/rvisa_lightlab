import rvisa as visa
import matplotlib.pyplot as plt
import numpy as np
import time
#Using documentation from https://www.manualslib.com/manual/1228418/Keithley-2600a-Series.html
class Ke26XX(object):
    # Change this to the IDN string of your instrument
    # if you do not know this, then set this to ''
    
    ## TODO: ADD CHANNELS TO IT
    name = 'Keithley Instruments Inc., Model 2602, 1061545, 1.4.2'
    rm = ''
    api = ''
    connected = False

    # Use this init function
    def __init__(self, api_addr=""):
        self.rm = visa.ResourceManager(api_addr)
        self.api = api_addr
        self.connected = self.rm.CONNECTED

    # Optional: if you want to automatically find out what addresses the instrument is on
    def find(self):
        has_instr = []
        if self.connected:
            resources = self.rm.list_resources()
            for res in resources:
                ID = self.rm.open_resource(res).query('*IDN?')
                if str(ID) == self.name:
                    has_instr.append(res)
            return tuple(has_instr)
        else:
            raise Exception('Not connected!')
    
    # Use this function
    def connect(self, visaAddr):
        self.instr = self.rm.open_resource(visaAddr)

    # Use this function
    def close(self, visaAddr):
        self.instr.close()

    # Optional function: returns IDN string
    def idn(self):
        return self.instr.query('*IDN?')
    
    def setVoltage(self,Voltage):
        self.instr.write('smua.source.levelv='+str(Voltage))
        #print(self.instr.query("SYST:ERR?"))
        
    def getVoltage(self):
        self.instr.write('voltage=smua.measure.v()')
        return self.instr.query('print(voltage)')
    
    def outputenable(self,Value):
        if Value==True:
            self.instr.write("smua.source.output=smua.OUTPUT_ON")
            #print(self.instr.query("SYST:ERR?"))
        else:
            self.instr.write("smua.source.output=smua.OUTPUT_OFF")
            #print(self.instr.query("SYST:ERR?"))
            
    def setCurrent(self,Current):
        self.instr.write('smua.source.levei='+str(Current))
        #print(self.instr.query("SYST:ERR?"))
        
    def getCurrent(self):
        self.instr.write('current=smua.measure.i()')
        return self.instr.query('print(current)')
    
    def setCurrentLimit(self,limit):
        self.instr.write('smua.trigger.source.limiti='+str(limit))
    
    def setVoltageLimit(self,limit):
        self.instr.write('smua.trigger.source.limitv='+str(limit))
        
    def setCurrentMeasurementRange(self,limit):
        self.instr.write("smua.measure.rangei="+str(limit))
        
    def setVoltageMeasurementRange(self,limit):
        self.instr.write("smua.measure.rangev="+str(limit))     
    
    def errorCheck(self):
        if self.instr.query("*STB?")==0:
            pass
        else:
            for i in range(self.instr.query("*STB?")):
                return(self.instr.query("SYST:ERR?"))