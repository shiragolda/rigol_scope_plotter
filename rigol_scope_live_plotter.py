import os
import numpy as np
import matplotlib.pyplot as plt
import matplotlib.animation as animation
import matplotlib.patches as mpatches
from matplotlib import rcParams
rcParams.update({'figure.autolayout':True})

#from rigol_scope.RigolInstruments import *

class USBTMC:
    """Simple implementation of a USBTMC device driver, in the style of visa.h"""

    def __init__(self, device):
        self.device = device
        self.file = os.open(device, os.O_RDWR)

        # TODO: Test that the file opened

    def write(self, command):
        os.write(self.file, command.encode())

    def read(self, length=4000):
        return os.read(self.file, length)

    def getName(self):
        self.write("*IDN?")
        return self.read(300)

    def sendReset(self):
        self.write("*RST")


class RigolScope:
    """Class to control a Rigol DS1000 series oscilloscope"""
    def __init__(self, device):
        self.meas = USBTMC(device)

        self.name = self.meas.getName()

        print(self.name)

    def write(self, command):
        """Send an arbitrary command directly to the scope"""
        self.meas.write(command)

    def read(self, command):
        """Read an arbitrary amount of data directly from the scope"""
        return self.meas.read(command)

    def reset(self):
        """Reset the instrument"""
        self.meas.sendReset()

class ScopePlotter:
    def __init__(self,addr):
        self.scope = RigolScope(addr)

        self.get_scales()

    def get_scales(self):
        self.scope.write(":CHAN1:SCAL?") # Get the voltage scale
        self.voltscale1 = float(self.scope.read(20)) # And the voltage offset

        self.scope.write(":CHAN1:OFFS?")
        self.voltoffset1 = float(self.scope.read(20))

        self.scope.write(":CHAN2:SCAL?")
        self.voltscale2 = float(self.scope.read(20))

        self.scope.write(":CHAN2:OFFS?")
        self.voltoffset2 = float(self.scope.read(20))
        
        self.scope.write(":TIM:SCAL?")
        self.timescale = float(self.scope.read(20))
        
        # Get the timescale offset
        self.scope.write(":TIM:OFFS?")
        self.timeoffset = float(self.scope.read(20))
        
        self.t_data = np.arange(-300.0/50*self.timescale, 300.0/50*self.timescale, self.timescale/50.0)

    def scope_bits_to_volts(self,bits,channel):
        if channel==1:
            voltscale = self.voltscale1
            voltoffset = self.voltoffset1
        elif channel==2:
            voltscale = self.voltscale2
            voltoffset = self.voltoffset2

        decoded_bits = np.frombuffer(bits, 'B')
        volts = decoded_bits * -1 + 255 # First invert the data
        volts = (volts - 130.0 - voltoffset/voltscale*25) / 25 * voltscale

        return volts


    def get_traces(self):
        self.scope.write(":WAV:DATA? CHAN1")
        rawdata1 = self.scope.read(9000)
        data1 = self.scope_bits_to_volts(rawdata1,1)
        data1 = data1[-600:]

        self.scope.write(":WAV:DATA? CHAN2")
        rawdata2 = self.scope.read(9000)
        data2 = self.scope_bits_to_volts(rawdata2,2)
        data2 = data2[-600:] #sometimes there are some garbage bits at the front

        return data1, data2


    
    def create_animation(self,t_refresh=60):
        self.get_scales()
       
        tr1,tr2 = self.get_traces()

        self.fig = plt.figure(figsize=(8,6))
        self.ax1 = self.fig.add_subplot(111)
        self.line1 = self.ax1.plot(self.t_data,tr1,label="Channel 1",color='C0')[0]
        self.ax1.set_ylabel('Channel 1 (V)')
        
        self.ax2 = self.ax1.twinx()
        self.line2 = self.ax2.plot(self.t_data,tr2,label="Channel 2",color='C1')[0]
        self.ax2.set_ylabel('Channel 2 (V)')
        
        self.ax1.set_xlabel("time(s)") #the last one

        self.ax1.set_ylim(self.voltscale1*-4-self.voltoffset1,self.voltscale1*4-self.voltoffset1)
        self.ax2.set_ylim(self.voltscale2*-4-self.voltoffset2,self.voltscale2*4-self.voltoffset2)

        self.text_template = 'Channel %i    Avg: %.3f, RMS: %.3f'
        p1 = mpatches.Patch(color='C0',label=self.text_template%(1,*self.avg_rms(tr1)))
        p2 = mpatches.Patch(color='C1',label=self.text_template%(2,*self.avg_rms(tr2)))
        plt.legend(handles=[p1,p2],loc=0)
                
        ani = animation.FuncAnimation(self.fig,self.animate,interval=200,frames=50,blit=False)
        plt.tight_layout()
        plt.show()

    def avg_rms(self,data):
        avg = np.mean(data)
        rms = np.sqrt(np.mean(np.square(data-avg)))
        
        return avg,rms
        
    def animate(self,i):
        tr1,tr2 = self.get_traces()
        
        self.line1.set_data(self.t_data,tr1)
        self.line2.set_data(self.t_data,tr2)
        
        p1 = mpatches.Patch(color='C0',label=self.text_template%(1,*self.avg_rms(tr1)))
        p2 = mpatches.Patch(color='C1',label=self.text_template%(2,*self.avg_rms(tr2)))
        plt.legend(handles=[p1,p2],loc=0)
        
        return self.line1, self.line2

if __name__ == '__main__':
    sp = ScopePlotter('/dev/GrapefruitScope')
    sp.create_animation()
    