# -*- coding: utf-8 -*-
"""

@author: Marc Ruch
"""

import numpy as np
import scipy.signal as signal
from numpy import mean, sqrt, square

class Waveform:
    def __init__(self, samples, polarity, baselineOffset, nBaselineSamples):
        self.samples          = samples
        self.polarity         = polarity
        self.baselineOffset   = baselineOffset
        self.nBaselineSamples = nBaselineSamples
        self.maxIndex         = np.argmax(samples)
        self.baseline         = -1
        self.blsSamples       = -1
        self.height           = -1
        self.badPulse         = False
        self.baselined        = False

    def SetSamples(self,newSamples):
        self.samples    = newSamples
        self.maxIndex   = -1
        self.baseline   = -1
        self.blsSamples = -1
        self.badPulse   = False
        self.baselined  = False

    def BaselineSubtract(self):
        if self.polarity > 0: # Positive pulse
            self.maxIndex = np.argmax(self.samples)
            # Check for enough room to calculate baseline
            if(self.maxIndex < self.baselineOffset+self.nBaselineSamples):
                self.badPulse = True
                return
            self.baseline = np.average(self.samples[self.maxIndex-self.baselineOffset-self.nBaselineSamples:self.maxIndex-self.baselineOffset])
            self.blsSamples = self.samples - self.baseline
        else: # Negative pulse
            self.maxIndex = np.argmin(self.samples)
            # Check for enough room to calculate baseline
            if (self.maxIndex < self.baselineOffset + self.nBaselineSamples):
                self.badPulse = True
                return
            self.baseline = np.average(self.samples[
                                       self.maxIndex - self.baselineOffset - self.nBaselineSamples:self.maxIndex - self.baselineOffset])
            self.blsSamples = self.baseline - self.samples
        self.baselined = True

    def ApplyCRRC4(self, samplingTime, shapingTime):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        T = samplingTime

        # Pre-compute
        a = 1/shapingTime
        alpha = np.exp(-T/shapingTime)
        b = np.array([0,
                      alpha*T**3*(4-a*T),
                      alpha**2*T**3*(12-11*a*T),
                      alpha**3*T**3*(-12-11*a*T),
                     alpha**4*T**3*(-4-a*T)])
        a = np.array([24, -120*alpha, 240*alpha**2,
                      -240*alpha**3, 120*alpha**4, -24*alpha**5])
        self.blsSamples = signal.lfilter(b, a, self.blsSamples)
        self.maxIndex = np.argmax(self.blsSamples)

    def GetMax(self):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        return  self.blsSamples[self.maxIndex]

    def GetRMSbls(self,nBaselineSamples):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        return  sqrt(mean(square(self.blsSamples[:nBaselineSamples])))

    def GetIntegralFromPeak(self,startIndex,endIndex):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        return np.sum(self.blsSamples[self.maxIndex+startIndex:self.maxIndex+endIndex]+1)

    def GetIntegralToZeroCrossing(self):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        negativeSamples = np.nonzero(self.blsSamples[self.maxIndex:]<0)[0]
        if len(negativeSamples)==0:
            return -1
        zeroCrossing = negativeSamples[0]+self.maxIndex
        return np.sum(self.blsSamples[self.maxIndex-self.baselineOffset:zeroCrossing])


    def GetCFDTime(self, CFDFraction, movingAverageLength=1):
        if not self.baselined:
            self.BaselineSubtract()
        if self.badPulse:
            return -1
        # Apply filter if needed
        if movingAverageLength>1:
            tSamples = np.convolve(self.blsSamples,np.ones(movingAverageLength)/movingAverageLength,'same')
        else:
            tSamples = self.blsSamples
        tMax = np.argmax(tSamples)
        targetVal = CFDFraction*tSamples[tMax]
        loopIndex = tMax
        while loopIndex > 0:
            loopIndex -= 1
            if tSamples[loopIndex] < targetVal:
                return (targetVal-tSamples[loopIndex])/(tSamples[loopIndex+1]-tSamples[loopIndex]) + loopIndex
        return -1

    def GetPSD(self):
      total = np.sum( self.samples[np.where(self.samples > 0  )] )
      tail = self.GetIntegralToZeroCrossing()
      return(tail / total)

    def isDouble(self):
      if not self.baselined:
        self.BaselineSubtract()
      if self.badPulse:
        return -1
      if self.height == -1:
        self.height = np.max(self.samples)
      delta_y = 0.05 * self.height
      delta_x = 3
      x0 , xf = 0 , len(self.samples)
      y0 , yf = self.samples[x0] , self.samples[xf]
      x1 , y1 = self.maxIndex , self.height
      # get slope from max to end of pulse
      s1 = (yf + delta_y - y1)  / (xf - (x1 + delta_x))
      # get slope from max to beginning of pulse
      s2 = (y1 - (y0 + delta_y)) / ((x1 - delta_x) - x0 )

      for x , y in enumerate(self.samples[:x1-delta_x]):
        if y > y0 + s2 * x:
          self.badPulse == True
          return(True)

      for x , y in enumerate(self.samples[x1+delta_x:]):
        if y > (y1 + s1 * (x - (x1 + delta_x))):
          self.badPulse == True
          return(True)




