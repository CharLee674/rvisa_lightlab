from . import VISAInstrumentDriver, RVISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from . import VISAInstrumentDriver, RVISAInstrumentDriver
from lightlab.equipment.abstract_drivers import TekScopeAbstract
from lightlab.laboratory.instruments import Oscilloscope
import numpy as np

class Remote_Agilent_Oscope(RVISAInstrumentDriver, TekScopeAbstract):
    ''' Slow DPO scope. See abstract driver for description

        `Manual <http://websrv.mece.ualberta.ca/electrowiki/images/8/8b/MSO4054_Programmer_Manual.pdf>`__

        Usage: :any:`/ipynbs/Hardware/Oscilloscope.ipynb`

    '''
    instrument_category = Oscilloscope

    totalChans = 2
    _recLenParam = 'ACQUIRE:COUNT'
    _clearBeforeAcquire = False
    _measurementSourceParam = None
    _runModeParam = None
    _runModeSingleShot = None
    _yScaleParam = 'WAVEFORM:YINCREMENT'

    def __init__(self, name='The Agilent scope', address=None, url=None, **kwargs):
        RVISAInstrumentDriver.__init__(self, name=name, address=address, url=url, **kwargs)
        TekScopeAbstract.__init__(self)
        self.host = url
        

    # Functions from TekScopeAbstract to override
    def timebaseConfig(self, avgCnt=None, duration=None, position=None, nPts=None):
        ''' Timebase and acquisition configure

            Args:
                avgCnt (int): averaging done by the scope
                duration (float): time, in seconds, for data to be acquired
                position (float): trigger delay
                nPts (int): number of samples taken

            Returns:
                (dict) The present values of all settings above
        '''
        if avgCnt is not None and avgCnt > 1:
            self.setConfigParam('ACQUIRE:TYPE AVERAGE')
            self.setConfigParam('ACQUIRE:COUNT', avgCnt, forceHardware=True)
        if duration is not None:
            self.setConfigParam('TIMEBASE:SCALE', duration / 10)
        if position is not None:
            self.setConfigParam('TIMEBASE:WINDOW:POSITION', position)
        if nPts is not None:
            self.setConfigParam(self._recLenParam, nPts)
            self.setConfigParam('DIG')
            self.setConfigParam('*WAI')

        presentSettings = dict()
        presentSettings['avgCnt'] = self.getConfigParam('ACQUIRE:TYPE AVERAGE;COUNT', forceHardware=True)
        presentSettings['duration'] = self.getConfigParam('TIMEBASE:SCALE', forceHardware=True)
        presentSettings['position'] = self.getConfigParam('TIMEBASE:WINDOW:POSITION', forceHardware=True)
        presentSettings['nPts'] = self.getConfigParam(self._recLenParam, forceHardware=True)
        return presentSettings

    def acquire(self, chans=None, timeout=None, **kwargs):
        ''' Get waveforms from the scope.

            If chans is None, it won't actually trigger, but it will configure.

            If unspecified, the kwargs will be derived from the previous state of the scope.
            This is useful if you want to play with it in lab while working with this code too.

            Args:
                chans (list): which channels to record at the same time and return
                avgCnt (int): number of averages. special behavior when it is 1
                duration (float): window width in seconds
                position (float): trigger delay
                nPts (int): number of sample points
                timeout (float): time to wait for averaging to complete in seconds
                    If it is more than a minute, it will do a test first


            Returns:
                list[Waveform]: recorded signals
        '''
        self.timebaseConfig(**kwargs)
        if chans is None:
            return

        for c in chans:
            if c > self.totalChans:
                raise Exception('Received channel: ' + str(c) +
                                '. Max channels of this scope is ' + str(self.totalChans))

        # Channel select
        for ich in range(1, 1 + self.totalChans):
            thisState = 1 if ich in chans else 0
            self.setConfigParam('WAVEFORM:SOURCE CHANNEL' + str(ich), thisState)

        isSampling = kwargs.get('avgCnt', 0) == 1
        wfms = [None] * len(chans)
        for i, c in enumerate(chans):
            vRaw = self.__transferData(c)
            t, v = self.__scaleData(vRaw, chans)
            # Optical modules might produce 'W' instead of 'V'
            unit = self.__getUnit()
            wfms[i] = Waveform(t, v, unit=unit)

        return wfms

    def _setupSingleShot(self, isSampling, forcing=False):
        print('Single shot is not implemented on this oscilloscope.')
        pass

    def _triggerAcquire(self, timeout=None):
        ''' Sends a signal to the scope to wait for a trigger event.
            Waits until acquisition completes or timeout (in seconds).

            If timeout is very long, it will try a test first
        '''
        if timeout is None:
            timeout = self.timeout / 1e3
        if timeout > 60:
            logger.warning('Long timeout %s specified, testing', timeout)
            old_avgCnt = self.timebaseConfig()['avgCnt']
            self.timebaseConfig(avgCnt=2)
            self._triggerAcquire(timeout=10)
            logger.warning('Test succeeded. Doing long average now')
            self.timebaseConfig(avgCnt=old_avgCnt)
        if self._clearBeforeAcquire:
            self.write('MEASURE:CLEAR')  # clear out average history
        # self.write('ACQUIRE:STATE 1')  # activate the trigger listener
        # Bus and entire program stall until acquisition completes. Maximum of 30 seconds
        self.wait(int(timeout * 1e3))

    def __transferData(self, chan):
        ''' Returns the raw data pulled from the scope as time (seconds) and voltage (Volts)
            Args:
                chan (int): one channel at a time

            Returns:
                :mod:`data.Waveform`: a time, voltage paired signal

            Todo:
                Make this binary transfer to go even faster
        '''
        chStr = 'CH' + str(chan)
        self.setConfigParam('WAVEFORM:FORMAT', 'ASCII')
        self.setConfigParam('WAVEFORM:SOURCE CHANNEL', chStr)
        
        self.write('WAVEFORM:DATA?')
        self._session_object.mbSession.read_bytes(10)
        voltRaw = self._session_object.mbSession.read_ascii_values('f')
        return voltRaw

    def __scaleData(self, voltRaw, ch):
        ''' Scale to second and voltage units.

            DSA and DPO are very annoying about treating ymult and yscale differently.
            TDS uses ymult not yscale

            Args:
                voltRaw (ndarray): what is returned from ``__transferData``

            Returns:
                (ndarray): time in seconds, centered at t=0 regardless of timebase position
                (ndarray): voltage in volts

            Notes:
                The formula for real voltage should be (Y - YOFF) * YSCALE + YZERO.
                The Y represents the position of the sampled point on-screen,
                YZERO, the reference voltage, YOFF, the offset position, and
                YSCALE, the conversion factor between position and voltage.
        '''
        get = lambda param: float(self.getConfigParam(f"CHANNEL{ch}:UNITS" + param, forceHardware=True))
        voltage = (np.array(voltRaw) - get("WAVEFORM:YREFERENCE")) \
            * get(self._yScaleParam(ch)) \
            + get('WAVEFORM:YORIGIN')

        timeDivision = float(self.getConfigParam('HORIZONTAL:MAIN:SCALE', forceHardware=True))
        time = np.linspace(-1, 1, len(voltage)) / 2 * timeDivision * 10

        return time, voltage

    def __getUnit(self, chStr):
        ''' Gets the unit of the waveform as a string.
            Args:
                chStr (str): what channel you want to scale to
                
            Normally, this will be '"V"', which can be converted to 'V'
        '''

        yunit_query = self.getConfigParam(f"CHANNEL{chStr}:UNITS", forceHardware=True)
        return yunit_query.replace('"', '')

    def wfmDb(self, chan, nWfms, untriggered=False):
        raise NotImplementedError()

    def run(self, continuousRun=True):
        ''' Sets the scope to continuous run mode, so you can look at it in lab,
            or to single-shot mode, so that data can be acquired

            Args:
                continuousRun (bool)
        '''
        self.setConfigParam(self._runModeParam,
                            'RUN' if continuousRun else self._runModeSingleShot,
                            forceHardware=True)

    def setMeasurement(self, measType):
        '''
            Args:
                measType (str): can be 'PK2PK', 'MEAN', etc.
        '''
        self.setConfigParam("ACQUIRE:TYPE "+measType,forceHardware=True)

    def measure(self, measIndex):
        '''
            Args:
                measIndex (int): used to refer to this measurement itself. 1-indexed

            Returns:
                (float)
        '''
        raise NotImplementedError()

    def autoAdjust(self, chans):
        ''' Adjusts offsets and scaling so that waveforms are not clipped '''
        # Save the current measurement status. They will be restored at the end.
        self.saveConfig(dest='+autoAdjTemp', subgroup='MEASUREMENT')

        for ch in chans:
            chStr = 'CHANNEL ' + str(ch)

            # Set up measurements
            self.setMeasurement(1, ch, 'PEAK')
            self.setMeasurement(2, ch, 'AVERAGE')

            for _ in range(100):
                # Acquire new data
                self.acquire(chans=[ch], avgCnt=1)

                # Put measurements into measResult
                pk2pk = self.measure(1)
                mean = self.measure(2)

                span = float(self.getConfigParam(chStr + ':SCALE'))
                offs = float(self.getConfigParam(chStr + ':OFFSET'))

                # Check if scale is correct within the tolerance
                newSpan = None
                newOffs = None
                if pk2pk < 0.7 * span:
                    newSpan = pk2pk / 0.75
                elif pk2pk > 0.8 * span:
                    newSpan = 2 * span
                if newSpan < 0.1 or newSpan > 100:
                    raise Exception('Scope channel ' + chStr + ' could not be adjusted.')

                # Check if offset is correct within the tolerance
                if abs(mean) > 0.05 * span:
                    newOffs = offs - mean

                # If we didn't set the new variables, then we're good to go
                if newSpan is not None and newOffs is not None:
                    break

                # Adjust settings
                self.setConfigParam(chStr + ':SCALE', newSpan / 10)
                self.setConfigParam(chStr + ':OFFSET', newOffs)

        # Recover the measurement setup from before adjustment
        self.loadConfig(source='+autoAdjTemp', subgroup='MEASUREMENT')
        self.config.pop('autoAdjTemp')