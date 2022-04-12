#
#
# This graphic user interface allows user to
# (1) set up data point positions, channel description and start data acquisition
#     (by calling Data_Run_2D.py or Data_Run_3D.py)
# (2) control the motor (by calling Motor_Control_2D.py or Motor_Control_3D.py)
# (3) view graphic display of the current probe position and data point positions in the chamber
#
#
# Author: Yuchen Qian
# Oct 2017
# Updated 2021-22, Rishabh Singh

import numpy as np
import math
import sys
import os
import os.path
import time
import subprocess
import datetime
from Motor_Control_ND import Motor_Control_ND
from LeCroy_Scope import LeCroy_Scope, WAVEDESC_SIZE
from LeCroy_Scope import EXPANDED_TRACE_NAMES
import tkinter
from tkinter import filedialog
import tkinter.messagebox
import h5py as h5py
dir_path=os.path.dirname(os.path.realpath(__file__))
version_number="02/22/2022 "            # update this when a change has been made

from PyQt5 import QtCore
# from PyQt5.QtWidgets import (QApplication, QBoxLayout, QCheckBox, QComboBox,
#          QDial, QGridLayout, QGroupBox, QHBoxLayout, QLabel, QScrollBar,
#          QSlider, QSpinBox, QStackedWidget, QWidget, QLineEdit, QPushButton, QSizePolicy, QMessageBox)
from PyQt5.QtGui import *
from PyQt5.QtWidgets import *
from PyQt5.QtCore import *

from mpl_toolkits.mplot3d import axes3d
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.figure import Figure
from scipy.linalg import norm

data_running = False
#############################################################################################
#############################################################################################


class MyMplCanvas(FigureCanvas):
    """Ultimately, this is a QWidget (as well as a FigureCanvasAgg, etc.)."""

    def __init__(self, parent=None, width=6, height=3, dpi=100):
        fig = Figure(figsize=(width, height), dpi=dpi)
        self.ax = fig.add_subplot(111,projection='3d')
        self.ax.grid()
        self.s = 1
 

        FigureCanvas.__init__(self, fig)
        self.setParent(parent)

        FigureCanvas.setSizePolicy(self,
                                   QSizePolicy.Expanding,
                                   QSizePolicy.Expanding)
        FigureCanvas.updateGeometry(self)

        self.ax.grid()
        #self.ax.add_patch(patches.Rectangle((-38, -50), 76, 100, fill = False, edgecolor = 'red'))

        self.matrix = self.ax.scatter(0, 0, 0, color = 'blue', marker = 'o')
        self.point = self.ax.scatter(0, 0, 0, color = 'red', marker = '*')
        self.initialize_visited_points()


        # self.ax.set_xticks(np.arange(-60,60,1))
        uss = np.linspace(0, 2 * np.pi, 32)
        zss = np.linspace(-100, 100, 2)

        uss, zss = np.meshgrid(uss, zss)

        xss = 50 * np.cos(uss)
        yss = 50 * np.sin(uss)
        self.ax.plot_surface(xss,yss,zss,alpha = 0.5, color = 'grey')

    def update_figure(self,x,y,z):
        with open('res.txt') as f:
            p = [float(l) for l in next(f).split()]

        s = min(p[0],p[1],p[2])
        self.s = s
        self.matrix = self.ax.scatter(x, y,z, color = 'blue', marker = 'o',s = self.s)
        self.draw()

    def update_probe(self, xnow, ynow):
        self.point = self.ax.scatter(xnow, ynow, 0, color = 'red', marker = '*', s = self.s)
        self.draw()

    def update_axis(self, x1, y1, x2, y2):
        self.ax.set_xlim(x2, x1)
        self.ax.set_ylim(y2, y1)

    def finished_positions(self, x, y):
        self.finished_x.append(x)
        self.finished_y.append(y)
        self.visited_points = self.ax.scatter(self.finished_x, self.finished_y,0, color = 'green', marker = 'o', s = self.s)
        self.draw()

    def initialize_visited_points(self):
        self.finished_x = []
        self.finished_y = []
        self.visited_points = self.ax.scatter(self.finished_x, self.finished_y,0, color = 'green', marker = 'o')





#############################################################################################
#############################################################################################


class Position_Controls(QGroupBox):
    def __init__(self):
        super().__init__()
        self.setTitle("Set up Motion List")




        self.ConfirmButton = QPushButton("Create List",self)
        self.UpdateButton = QPushButton("Update Diagram",self)

        controlsLayout = QGridLayout()

        controlsLayout.addWidget(self.ConfirmButton, 1, 1)
        controlsLayout.addWidget(self.ConfirmButton, 1, 2)
        self.setLayout(controlsLayout)




######################################################################################################
######################################################################################################


class Acquisition_Controls(QGroupBox):

    def __init__(self):
        super().__init__()
        self.DataRun = QPushButton("Start Data Acquisition", self)
        self.TestShot = QPushButton("Take Test Shot", self)

        ACLayout = QGridLayout()
        ACLayout.addWidget(self.DataRun, 0, 0)
        ACLayout.addWidget(self.TestShot, 0, 1)

        self.setLayout(ACLayout)


######################################################################################################
######################################################################################################


class Motor_Movement(QGroupBox):

    def __init__(self, x_ip_addr = None, y_ip_addr = None, MOTOR_PORT = None):
        super().__init__()
        self.setTitle("Motor Movement Control")

        self.x_ip_addr = x_ip_addr
        self.y_ip_addr = y_ip_addr
        self.MOTOR_PORT = MOTOR_PORT

        # (cm) Move probe to absolute position along the shaft counted by motor encoder
        self.xMoveLabel = QLabel("Move x motor to:")
        self.yMoveLabel = QLabel("Move y motor to:")
        self.xMoveInput = QLineEdit()
        self.yMoveInput = QLineEdit()

        # For 3D acquisition, need another feature to move the probe to absolute position.
        # this should be done by calling "move_to_position" function in Motor_Control_3D, with corresponding geometry calculation

        # Set velocity.
        self.xvLabel = QLabel("Set x velocity:")
        self.yvLabel = QLabel("Set y velocity:")
        self.xvInput = QLineEdit()
        self.yvInput = QLineEdit()


        self.MoveButton     = QPushButton("Move Motor", self)
        self.StopNowButton  = QPushButton("BUG don't click(StopNowButton)", self)
        self.SetZero        = QPushButton("Set Zero", self)
        self.SetVelocity = QPushButton("Set Velocity", self)
        self.MoveButton.clicked.connect(self.move_to_position)
        self.StopNowButton.clicked.connect(self.stop_now)
        self.SetZero.clicked.connect(self.zero)
        self.SetVelocity.clicked.connect(self.set_velocity)

        self.CurposLabel = QLabel("Current probe position (cm, deg):")
        self.CurposInput = QLineEdit(readOnly = True)
        self.velocityButton = QPushButton("Get motor speed (rpm):")
        self.velocityInput = QLineEdit(readOnly = True)
        self.velocityButton.clicked.connect(self.update_current_speed)

        MMLayout = QGridLayout()
        MMLayout.addWidget(self.xMoveLabel, 0, 0)
        MMLayout.addWidget(self.yMoveLabel, 0, 1)
        MMLayout.addWidget(self.xMoveInput, 1, 0)
        MMLayout.addWidget(self.yMoveInput, 1, 1)
        MMLayout.addWidget(self.MoveButton, 1, 2)
        MMLayout.addWidget(self.xvLabel, 2, 0)
        MMLayout.addWidget(self.yvLabel, 2, 1)
        MMLayout.addWidget(self.xvInput, 3, 0)
        MMLayout.addWidget(self.yvInput, 3, 1)
        MMLayout.addWidget(self.SetVelocity, 3, 2)
        MMLayout.addWidget(self.SetZero, 4, 0)
        MMLayout.addWidget(self.StopNowButton, 4, 1)
        MMLayout.addWidget(self.CurposLabel, 5, 0)
        MMLayout.addWidget(self.CurposInput, 5, 1, 1, 2)
        MMLayout.addWidget(self.velocityButton, 6, 0)
        MMLayout.addWidget(self.velocityInput, 6, 1, 1, 2)


        self.setLayout(MMLayout)

        self.mc = Motor_Control_ND(x_ip_addr = self.x_ip_addr, y_ip_addr = self.y_ip_addr)

#----------------------------------------------------------------------

    def move_to_position(self):
        # Directly move the motor to their absolute position
        try:
            x_pos = float(self.xMoveInput.text())
            y_pos = float(self.yMoveInput.text())
            self.mc.move_to_position(x_pos, y_pos)
        except ValueError:
            QMessageBox.about(self, "Error", "Position should be valid numbers.")

    # def wait_for_motion_complete(self):
    #     self.mc.wait_for_motion_complete()


    def stop_now(self):
        # Stop motor movement now
        self.mc.stop_now()


    def zero(self):
        zeroreply=QMessageBox.question(self, "Set Zero",
            "You are about to set the current probe position to (0,0). Are you sure?",
            QMessageBox.Yes, QMessageBox.No)
        if zeroreply == QMessageBox.Yes:
            QMessageBox.about(self, "Set Zero", "Probe position is now (0,0).")
            self.mc.set_zero()


    def ask_velocity(self):
        return self.mc.ask_velocity()


    def set_velocity(self):
        xv = self.xvInput.text()
        yv = self.yvInput.text()
        self.mc.set_velocity(xv, yv)


    def current_probe_position(self):
        return self.mc.current_probe_position()

    def update_current_speed(self):
        self.speedx, self.speedy = self.ask_velocity()
        self.velocityInput.setText("(" + str(self.speedx) + " ," + str(self.speedy) +")")

    # def set_input_usage(self, usage):
    #     self.mc.set_input_usage(usage)



#############################################################################################
#############################################################################################


class Scope_Channel(QGroupBox):
    def __init__(self):
        super().__init__()
        self.titleLabel = QLabel("Enter channel descriptions")
        self.c1Label = QLabel("Channel 1:")
        self.c2Label = QLabel("Channel 2:")
        self.c3Label = QLabel("Channel 3:")
        self.c4Label = QLabel("Channel 4:")
        self.c1Input = QLineEdit()
        self.c2Input = QLineEdit()
        self.c3Input = QLineEdit()
        self.c4Input = QLineEdit()


        SCLayout = QGridLayout()
        SCLayout.addWidget(self.titleLabel, 0, 0, 1, 2)
        SCLayout.addWidget(self.c1Label, 1, 0)
        SCLayout.addWidget(self.c2Label, 2, 0)
        SCLayout.addWidget(self.c3Label, 3, 0)
        SCLayout.addWidget(self.c4Label, 4, 0)
        SCLayout.addWidget(self.c1Input, 1, 1)
        SCLayout.addWidget(self.c2Input, 2, 1)
        SCLayout.addWidget(self.c3Input, 3, 1)
        SCLayout.addWidget(self.c4Input, 4, 1)
        self.setLayout(SCLayout)


update_pos = None

#############################################################################################
#############################################################################################

class Software_Version(QGroupBox):
    def __init__(self):
        super().__init__()
        self.mod_timestr=(os.path.getmtime(dir_path))
        self.mod_datetime=datetime.datetime.fromtimestamp(self.mod_timestr).strftime('%Y-%b-%d %H:%M:%S %p')
        self.vLabel = QLabel("Last Modified: ")
        self.lastmodified = QLabel(self.mod_datetime)
        self.version = QLabel("Version: "+version_number)

        SVLayout = QGridLayout()
        SVLayout.addWidget(self.vLabel, 0, 0)
        SVLayout.addWidget(self.lastmodified, 1, 0)
        SVLayout.addWidget(self.version, 2, 0)
        self.setLayout(SVLayout)

#############################################################################################
#############################################################################################
class Signals(QObject):
    finished = pyqtSignal()
    updated_position = pyqtSignal(float, float)
    new_screen_dump = pyqtSignal()
    finished_position = pyqtSignal(float, float)
    cancel = pyqtSignal()

class Data_Run_Thread(QRunnable):

    def __init__(self, hdf5_filename, channel_description, ip_addrs):
        super(Data_Run_Thread, self).__init__()

        self.hdf5_filename = hdf5_filename
        # self.pos_param = pos_param
        self.channel = channel_description
        self.ip_addrs = ip_addrs
        self.signals = Signals()

    def get_channel_description(self, tr) -> str:
        """ callback function to return a string containing a description of the data in each recorded channel """

        #user: assign channel description text here to override the default:
        if tr == 'C1':
            return self.channel["C1"]
        if tr == 'C2':
            return self.channel["C2"]
        if tr == 'C3':
            return self.channel["C3"]
        if tr == 'C4':
            return self.channel["C4"]

        # otherwise, program-generated default description strings follow
        if tr in EXPANDED_TRACE_NAMES.keys():
            return 'no entered description for ' + EXPANDED_TRACE_NAMES[tr]

        return '**** get_channel_description(): unknown trace indicator "'+tr+'". How did we get here?'




    def get_hdf5_filename(self) -> str:

        avoid_overwrite = True     # <-- setting this to False will allow overwriting an existing file without a prompt

        fn = self.hdf5_filename
        if fn == None  or len(fn) == 0  or  (avoid_overwrite  and  os.path.isfile(fn)):
            # if we are not allowing possible overwrites as default, and the file already exists, use file open dialog
            tk = tkinter.Tk()
            tk.withdraw()        # prevent tk GUI from popping up
            fnoptions={}
            fnoptions['title'] = 'Save file as ...'
            fnoptions['defaultextension'] = '.hdf5'
            fnoptions['filetypes'] = [("Hierarchical Data Format",'*.hdf5'), ("All files",'*.*')]
            fn = filedialog.asksaveasfilename(**fnoptions)
            if not fn:         # if user pressed 'cancel', fn = None
                print("\nUser cancelled save file input.")
                # if len(fn) == 0:
                #     #raise SystemExit(0)
                #     fn = exit
            tk.destroy()

        self.hdf5_filename = fn    # save it for later
        return fn

    def acquire_displayed_traces(self, scope, datasets, hdr_data, pos_ndx):
        """ worker for below :
            acquire enough sweeps for the averaging, then read displayed scope trace data into HDF5 datasets
        """
        timeout = 2000 # seconds
        timed_out, N = scope.wait_for_max_sweeps(str(pos_ndx)+': ', timeout)  # leaves scope not triggering

        if timed_out:
            print('**** averaging timed out: got '+str(N)+' at %.6g s' % timeout)

        traces = scope.displayed_traces()

        for tr in traces:
            try:
                NPos,NTimes = datasets[tr].shape
                datasets[tr][pos_ndx,0:NTimes] = scope.acquire(tr)[0:NTimes]    # sometimes for 10000 the scope hardware returns 10001 samples, so we have to specify [0:NTimes]
                #?# datasets[tr].flush()
            except KeyError:
                print(tr + ' is displayed on the scope but not recorded. To record this channel, please display the trace before starting the data run.')
                continue

        for tr in traces:
            try:
                hdr_data[tr][pos_ndx] = np.void(scope.header_bytes())    # valid after scope.acquire()
                #?# hdr_data[tr].flush()
                #?# are there consequences in timing or compression size if we do the flush()s recommend for the SWMR function?
            except KeyError:
                continue

        scope.set_trigger_mode('NORM')   # resume triggering

    #----------------------------------------------------------------------------------------

    def create_sourcefile_dataset(self, grp, fn):
        """ worker for below:
            create an HDF5 dataset containing the contents of the specified file
            add attributes file name and modified time
        """
        fds_name = os.path.basename(fn)
        fds = grp.create_dataset(fds_name, data=open(fn, 'r').read())
        fds.attrs['filename'] = fn
        fds.attrs['modified'] = time.ctime(os.path.getmtime(fn))

    #----------------------------------------------------------------------------------------

    def run(self):
        # The main data acquisition routine
        #
        #     Arguments are user-provided callback functions that return the following:
        #         get_hdf5_filename()          the output HDF5 filename,
        #         get_positions()              the positions array,
        #         get_channel_description(c)   the individual channel descriptions (c = 'C1', 'C2', 'C3', 'C4'),
        #         get_ip_addresses()           a dict of the form {'scope':'10.0.1.122', 'x':'10.0.0.123', 'y':'10.0.0.124', 'z':''}
        #                                           if a key is not specified, no motion will be attempted on that axis
        #
        #     Creates the HDF5 file, creates the various groups and datasets, adds metadata (see "HDF5 OUTPUT FILE SETUP")
        #
        #     Iterates through the positions array (see "MAIN ACQUISITION LOOP"):
        #         calls motor_control.set_position(pos)
        #         Waits for the scope to average the data, as per scope settings
        #         Writes the acquired scope data to the HDF5 output file
        #
        #     Closes the HDF5 file when done
        #
        #============================
        # list of files to include in the HDF5 data file
    #    thispath = os.path.realpath(__file__)
#src_files = [thispath,           # ASSUME this file is in the same directory as the next two:
        #            os.path.dirname(thispath)+os.sep+'LeCroy_Scope.py',
#os.path.dirname(thispath)+os.sep+'Motor_Control_2D.py'
            #       ]
        #for testing, list these:s
#print('Files to record in the hdf5 archive:')
#print('    invoking file (this file)     =', src_files[0])
    #    print('    LeCroy_Scope file  =', src_files[1])
    #    print('    motor control file =', src_files[2])

        #============================
        # position array given by paintergui.py:
        x,y,z = [],[],[]
        with open('file.txt','r') as f:
            x,y,z = zip(*[l.split() for l in f])
            x = list(x)
            y = list(y)
            z = list (z)
            x[:] = [float(i)/5 for i in x]
            y[:] = [float(i)/5 for i in y]
            z[:] = [float(i)/5 for i in z]
            positions = list(zip(x,y,z)) #in cm
        #============================

        mc = Motor_Control_ND(x_ip_addr = self.ip_addrs['x'], y_ip_addr = self.ip_addrs['y'])
        nowx, nowy = (-999, -999)

        ######### HDF5 OUTPUT FILE SETUP #########

        # Open hdf5 file for writing (user callback for filename):

        # ofn = self.get_hdf5_filename()      # callback arg to the current function
        # if not ofn:        #if user pressed cancel during input file name
        #     self.signals.cancel.emit()
        #     pass
        # else:
        #     f = h5py.File(ofn,  'w')  # 'w' - overwrite (we should have determined whether we want to overwrite in get_hdf5_filename())
        #     # f = h5py.File(ofn,  'x')  # 'x' - no overwrite

        #     #============================
        #     # create HDF5 groups similar to those in the legacy format:

        #     acq_grp    = f.create_group('/Acquisition')              # /Acquisition
        #     acq_grp.attrs['run_time'] = time.ctime()                                       # not legacy
        #     scope_grp  = acq_grp.create_group('LeCroy_scope')        # /Acquisition/LeCroy_scope
        #     header_grp = scope_grp.create_group('Headers')                                 # not legacy

        #     ctl_grp    = f.create_group('/Control')                  # /Control
        #     pos_grp    = ctl_grp.create_group('Positions')           # /Control/Positions

        #     meta_grp   = f.create_group('/Meta')                     # /Meta                not legacy
        #     script_grp = meta_grp.create_group('Python')             # /Meta/Python
        #     scriptfiles_grp = script_grp.create_group('Files')       # /Meta/Python/Files

        #     # in the /Meta/Python/Files group:
        #     for src_file in src_files:
        #         self.create_sourcefile_dataset(scriptfiles_grp, src_file)

        #     # I don't know how to get this information from the scope:
        #     scope_grp.create_dataset('LeCroy_scope_Setup_Arrray', data=numpy.array('Sorry, this is not included', dtype='S'))

        #     pos_ds = pos_grp.create_dataset('positions_setup_array', data=positions)
        #     pos_ds.attrs['xpos'] = x                                                     # not legacy
        #     pos_ds.attrs['ypos'] = y
        #                                           # not legacy                                                     # not legacy

        #     # create the scope access object, and iterate over positions
        #     with LeCroy_Scope(self.ip_addrs['scope'], verbose=False) as scope:
        #         if not scope:
        #             print('Scope not found at '+self.ip_addrs['scope'])      # I think we have raised an exception if this is the case, so we never get here
        #             return

        #         scope_grp.attrs['ScopeType'] = scope.idn_string

        #         NPos = len(positions)
        #         NTimes = scope.max_samples()

        #         datasets = {}
        #         hdr_data = {}

        #         # create 4 default data sets, empty.  These will all be populated for compatibility with legacy format hdf5 files.

        #         datasets['C1'] = scope_grp.create_dataset('Channel1', shape=(NPos,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
        #         datasets['C2'] = scope_grp.create_dataset('Channel2', shape=(NPos,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
        #         datasets['C3'] = scope_grp.create_dataset('Channel3', shape=(NPos,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
        #         datasets['C4'] = scope_grp.create_dataset('Channel4', shape=(NPos,NTimes), fletcher32=True, compression='gzip', compression_opts=9)

        #         # create other datasets, one for each displayed trace (but not C1-4, which we just did)
        #         # todo: should we maybe just ignore these?  or have a user option to include them?

        #         traces = scope.displayed_traces()
        #         for tr in traces:
        #             name = scope.expanded_name(tr)
        #             if tr not in ('C1','C2','C3','C4'):
        #                 ds = scope_grp.create_dataset(name, (NPos,NTimes), chunks=(1,NTimes), fletcher32=True, compression='gzip', compression_opts=9)
        #                 datasets[tr] = ds

        #         # For each trace we are storing, we will write one header per position (immediately after
        #        #    the data for that position has been acquired); these compress to an insignificant size
        #         # For whatever stupid reason we need to write the header as a binary blob using an "HDF5 opaque" type - here void type 'V346'  (otherwise I could not manage to avoid invisible string processing and interpretation)
        #         for tr in traces:
        #             name = scope.expanded_name(tr)
        #             hdr_data[tr] = header_grp.create_dataset(name, shape=(NPos,), dtype="V%i"%(WAVEDESC_SIZE), fletcher32=True, compression='gzip', compression_opts=9)  # V346 = void type, 346 bytes long

        #         # create "time" dataset
        #         time_ds = scope_grp.create_dataset('time', shape=(NTimes,), fletcher32=True, compression='gzip', compression_opts=9)

        #         # at this point all datasets should be created, so we can
        #         # switch to SWMR mode
        #         #?# f.swmr_mode = True    # SWMR MODE: DO NOT CREATE ANY MORE DATASETS AFTER THIS
        #         #?# check effects of flushing...see above

                # try:  # try-catch for Ctrl-C keyboard interrupt

                    ######### BEGIN MAIN ACQUISITION LOOP #########
        print('starting acquisition loop at', time.ctime())
        acquisition_loop_start_time = time.time()
        i = 1
        for pos in positions:
            if nowx!=pos[0] or nowy!=pos[1]:
                        # move to next position
                        print('position index =', i , '  x =', pos[0], '  y =', pos[1], end='')

                        mc.move_to_position(pos[0], pos[1])
                        #mc.wait_for_motion_complete()
                        self.signals.updated_position.emit(pos[0], pos[1])
                        nowx, nowy = (pos[0], pos[1])
                        x_encoder, y_encoder = mc.current_probe_position()
                        self.signals.updated_position.emit(x_encoder, y_encoder)

                        # Disable the motor current output when taking the data
                        mc.disable()

                        if i > 1:
                            print ('Estimated remaining time:%6.2f'%((len(positions) - i) * (time.time()-acquisition_loop_start_time)/i / 3600))
                        else:
                            print ('')

                        # print('------------------', scope.gaaak_count, '-------------------- ',i,sep='')

        #                scope.autoscale('C3')  # for now can only _increase_ the V/div

                        # do averaging, and copy scope data for each trace on the screen to the output HDF5 file
                        # self.acquire_displayed_traces(scope, datasets, hdr_data, i-1)   # argh the pos[0] index is 1-based

                        # Show plot traces on GUI
                        # try:
                            # scope.screen_dump()
                            # self.signals.new_screen_dump.emit()
                        # except VisaIOError: #VisaIOError undefined?
                        #     print ('Unable to grab screen due to VisaIOError')
                        #     continue
                        # except:
                            # print ('Unable to grab screen due to unknown Error')
                            # continue

                        self.signals.finished_position.emit(x_encoder, y_encoder)
                        mc.enable()

                        # at least get one time array recorded for swmr functions
                        # if i == 1:
                        #     time_ds[0:NTimes] = scope.time_array()[0:NTimes]
                        #     #time_ds.flush()

                        i += 1

                    ######### END MAIN ACQUISITION LOOP #########

                # except KeyboardInterrupt:
                #     print('\n______Halted due to Ctrl-C______', '  at', time.ctime())

                # # copy the array of time values, corresponding to the last acquired trace, to the times_dataset
                # time_ds[0:NTimes] = scope.time_array()[0:NTimes]      # specify number of points, sometimes scope return extras
                # if type(time_ds) == 'stupid':
                #     print(' this is only included to make the linter happy, otherwise it thinks time_ds is not used')

                # Set any unused datasets to 0 (e.g. any C1-4 that was not acquired); when compressed they require negligible space
                # Also add the text descriptions.    Do these together to be able to be able to make a note in the description
            #     for tr in traces:
            #         if datasets[tr].len() == 0:
            #             datasets[tr] = numpy.zeros(shape=(NPos,NTimes))
            #             datasets[tr].attrs['description'] = 'NOT RECORDED: ' + self.get_channel_description(tr)           # callback arg to the current function
            #             datasets[tr].attrs['recorded']    = False
            #         else:
            #             datasets[tr].attrs['description'] = self.get_channel_description(tr)                              # callback arg to the current function
            #             datasets[tr].attrs['recorded']    = True

            # f.close()  # close the HDF5 file

        self.signals.finished.emit()
            #done



class Test_Shot_Thread(QRunnable):

    def __init__(self, ip_addrs):
        super(Test_Shot_Thread, self).__init__()
        self.signals = Signals()
        self.ip_addrs = ip_addrs

    def acquire_displayed_traces(self, scope):
        """ worker for below :
            acquire enough sweeps for the averaging, then read displayed scope trace data into HDF5 datasets
        """
        timeout = 2000 # seconds
        timed_out, N = scope.wait_for_max_sweeps('Test shot: ', timeout)  # leaves scope not triggering

        if timed_out:
            print('**** averaging timed out: got '+str(N)+' at %.6g s' % timeout)

        scope.screen_dump()
        self.signals.new_screen_dump.emit()
        scope.set_trigger_mode('NORM')   # resume triggering

    def run(self):
        with LeCroy_Scope(self.ip_addrs['scope'], verbose=False) as scope:
            if not scope:
                print('Scope not found at '+self.ip_addrs['scope'])      # I think we have raised an exception if this is the case, so we never get here
                return
            self.acquire_displayed_traces(scope)   # argh the pos[0] index is 1-based
        self.signals.finished.emit()

#############################################################################################
#############################################################################################


class Window(QWidget):

    def __init__(self):
        super(Window, self).__init__()

        self.pc = Position_Controls()
        self.canvas = MyMplCanvas()
        self.ac = Acquisition_Controls()
        # self.axc = Axis_Controls()
        self.sv = Software_Version()
        self.sc = Scope_Channel()
        self.x_ip = "192.168.0.70"
        self.y_ip = "192.168.0.80"
        self.scope_ip = "192.168.0.60"
        self.port_ip = int(7776)
        self.mm = Motor_Movement(x_ip_addr = self.x_ip, y_ip_addr = self.y_ip, MOTOR_PORT = self.port_ip)
        # self.mm.set_input_usage(3)



        self.pc.ConfirmButton.clicked.connect(self.update_list)
        self.pc.UpdateButton.clicked.connect(self.update_geometry)
        self.ac.DataRun.clicked.connect(self.start_data_run)
        self.ac.TestShot.clicked.connect(self.start_test_shot)


#self.ScopeScreen = QLabel(self)
#self.update_screen_dump()


        layout = QGridLayout()
        layout.addWidget(self.canvas, 0, 0, 1, 2)
        # layout.addWidget(self.axc, 1, 0, 1, 2)            #axes control
        layout.addWidget(self.mm, 2, 0, 2, 1)                    #motor movement
        layout.addWidget(self.pc, 2, 1, 2, 1)                    #position control
        layout.addWidget(self.ac, 2, 2)                    #acquisition control
        layout.addWidget(self.sc, 2, 3, 2, 1)                    #scope channel comments
        layout.addWidget(self.sv, 3, 2)
#layout.addWidget(self.ScopeScreen, 0, 2 , 2, 2)
        self.setLayout(layout)

        self.setWindowTitle("180E Data Acquisition System for Z-Theta Probe drives")
        self.resize(1600, 700)

        self.threadpool = QThreadPool()

        # Set timer to update current probe position and instant motor velocity
        self.timer = QtCore.QTimer(self)
        self.timer.timeout.connect(self.update_current_position)
        self.timer.start(500)

    # def update_timer(self):
    #     if data_running == False:
    #         self.timer = QtCore.QTimer(self)
    #         self.timer.timeout.connect(self.update_current_position)
    #         self.timer.start(500)
    #     else:
    #         pass

    # def axis_change(self):
    #     xup = self.axc.xupInput.value()
    #     yup = self.axc.yupInput.value()
    #     xlow = self.axc.xlowInput.value()
    #     ylow = self.axc.ylowInput.value()
    #     self.canvas.update_axis(xup,yup,xlow,ylow)


    def update_current_position(self):
        if data_running == False:
            self.xnow, self.ynow = self.mm.current_probe_position()
            self.canvas.point.remove()
            self.canvas.update_probe(self.xnow, self.ynow)
            self.mm.CurposInput.setText(
                f"({round(self.xnow[0], 2)} ,{round(self.ynow[0], 2)})"
            )

        else:
            pass

    def update_current_position_during_data_run(self, xnow, ynow):
        if data_running == True:
            self.xnow = xnow
            self.ynow = ynow
            self.canvas.point.remove()
            self.canvas.update_probe(self.xnow, self.ynow)
            self.mm.CurposInput.setText("(" + str(round(self.xnow, 2)) + " ," + str(round(self.ynow, 2)) +")")
        else:
            print("Why is this called when data_running == False ?")

    def update_screen_dump(self):
        self.pixmap = QPixmap("scope_screen_dump.png")
        self.ScopeScreen.setPixmap(self.pixmap)

    def mark_finished_positions(self, x, y):
        if data_running == True:
            self.xdone = x
            self.ydone = y
            self.canvas.visited_points.remove()
            self.canvas.finished_positions(self.xdone, self.ydone)
        else:
            print("Why is this called when data_running == False ?")

    def update_current_speed(self):
            self.speedx, self.speedy = self.mm.ask_velocity()
            self.velocityInput.setText("(" + str(self.speedx) + " ," + str(self.speedy) +")")

    def update_list(self):
        subprocess.call(" python paintergui.py 1", shell = True)

    def update_geometry(self):
        x,y,z = [],[],[]
        with open('file.txt','r') as f:
            x,y,z = zip(*[l.split() for l in f])
            x = list(x)
            y = list(y)
            z = list (z)
            x[:] = [float(i)/5 for i in x]
            y[:] = [float(i)/5 for i in y]
            z[:] = [float(i)/5 for i in z]
        self.canvas.matrix.remove()
        self.canvas.update_figure(x,y,z)

    def update_channel_information(self):
        self.channel_info = {}

        self.channel_info["C1"] = self.sc.c1Input.text()
        self.channel_info["C2"] = self.sc.c2Input.text()
        self.channel_info["C3"] = self.sc.c3Input.text()
        self.channel_info["C4"] = self.sc.c4Input.text()

        return self.channel_info

    def start_data_run(self):
        # start data_run threading
        self.hdf5_filename = None

        #self.pos_param = self.update_parameters()

        self.channel_description = self.update_channel_information()

        self.ip_addrs = {}
        self.ip_addrs['x'] = self.x_ip
        self.ip_addrs['y'] = self.y_ip
        self.ip_addrs['scope'] = self.scope_ip

        self.data_run = Data_Run_Thread(self.hdf5_filename,  self.channel_description, self.ip_addrs)
        self.freeze_all_controls()
        self.data_run.signals.finished.connect(self.data_run_finished)
        self.data_run.signals.cancel.connect(self.acquisition_canceled)
        self.data_run.signals.updated_position.connect(self.update_current_position_during_data_run)
        self.data_run.signals.finished_position.connect(self.mark_finished_positions)
        #self.data_run.signals.new_screen_dump.connect(self.update_screen_dump)
        self.threadpool.start(self.data_run)

    def acquisition_canceled(self):
        QMessageBox.about(self, "Acquisition Status", "Data acquisition cancelled.")
        self.enable_all_controls()

    def data_run_finished(self):
        QMessageBox.about(self, "Acquisition Status", "Data acquisition complete.")
        self.enable_all_controls()
        self.canvas.visited_points.remove()
        self.canvas.initialize_visited_points()
        # self.canvas.finished_x = []
        # self.canvas.finished_y = []

    def test_shot_finished(self):
        QMessageBox.about(self, "Take Test Shot", "Test shot is finished.")
        self.enable_all_controls()
        # global data_running
        # data_running = False
        # self.pc.setEnabled(True)
        # self.ac.setEnabled(True)
        # self.sc.setEnabled(True)
        # self.mm.setEnabled(True)

    def freeze_all_controls(self):
        global data_running
        data_running = True
        # self.pc.setEnabled(False)
    #    self.ac.setEnabled(False)
        self.sc.setEnabled(False)
        self.mm.MoveButton.setEnabled(False)
        self.mm.SetZero.setEnabled(False)
        self.mm.SetVelocity.setEnabled(False)
        self.mm.velocityButton.setEnabled(False)

    def enable_all_controls(self):
        global data_running
        data_running = False
        # self.pc.setEnabled(True)
        # self.ac.setEnabled(True)
        self.sc.setEnabled(True)
        self.mm.MoveButton.setEnabled(True)
        self.mm.SetZero.setEnabled(True)
        self.mm.SetVelocity.setEnabled(True)
        self.mm.velocityButton.setEnabled(True)

    def start_test_shot(self):
        self.ip_addrs = {}
        self.ip_addrs['scope'] = self.scope_ip
        self.test_shot = Test_Shot_Thread(self.ip_addrs)
        self.test_shot.signals.finished.connect(self.test_shot_finished)
        self.test_shot.signals.new_screen_dump.connect(self.update_screen_dump)
        self.threadpool.start(self.test_shot)


    def fileQuit(self):
        self.close()

    def closeEvent(self, ce):
        '''Call function to close socket, maybe other things later'''
        super(QtGui.QMainWindow, self).closeEvent(*args, **kwargs)
        self.fileQuit()
        self.mc.close_connection()


if __name__ == '__main__':

    app = QApplication(sys.argv)
    window = Window()
    window.show()

    sys.exit(app.exec_())
