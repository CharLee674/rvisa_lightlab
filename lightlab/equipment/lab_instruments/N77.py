import rvisa as visa
import matplotlib.pyplot as plt
import numpy as np
import time
#using documentation from https://literature.cdn.keysight.com/litweb/pdf/N7744-90C01.pdf?id=1656884

class N7744A(object):
    # Change this to the IDN string of your instrument
    # if you do not know this, then set this to ''
    name = ''
    rm = ''
    api = ''
    connected = False

    # Use this init function
    def __init__(self, api_addr=''):
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

    # Use this function
    def close(self, visaAddr):
        self.instr.close()

    # Optional function: returns IDN string
    def idn(self):
        return self.instr.query('*IDN?')

    def readPower(self,slot):#not sure if formatting is correct
        power=self.instr.query(f'read{slot}:pow?')
        return float(power)

    def setWavelength(self,slot,chan,wave):#include units e.g.(1600nm)
    	self.instr.write(f"SOUR{slot}:CHAN{chan}:WAV {wave}")

    def readWavelength(self,slot,chan):
    	return(self.instr.query(f"SOUR{slot}:CHAN{chan}:WAV?"))

    def setPWMPowerUnit(self, slot, chan, unit):#use DBM/Watt
    	self.instr.write(f"OUTP{slot}:CHAN{chan}:POW:UN {unit}")
    	#print("unit set to", self.instr.query(f"OUTP{slot}:CHAN{chan}:POW:UN?"))

    def setOutput(self,slot,chan,state):#0/1
    	self.instr.write(f"OUTP{slot}:CHAN{chan}:STAT {state}")
    	#print("Output set to", self.instr.query(f"OUTP{slot}:CHAN{chan}:STAT?"))