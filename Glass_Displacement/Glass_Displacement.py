from sympy import root
import PyQt5
from matplotlib.backends.backend_qt5agg import FigureCanvasQTAgg as FigureCanvas
from matplotlib.backends.backend_qt5agg import NavigationToolbar2QT as NavigationToolbar
from PyQt5.QtWidgets import QLabel


from PyQt5.QtWidgets import QMainWindow, QApplication, QCheckBox, QComboBox, QMessageBox, QVBoxLayout
from PyQt5.QtWidgets import QPushButton, QLineEdit, QFrame, QSizePolicy, QProgressBar, QFileDialog, QRadioButton
from PyQt5 import QtCore, uic, QtGui
from PyQt5.QtGui import QIntValidator, QDoubleValidator
from PyQt5 import QtCore
from PyQt5.QtWidgets import QMessageBox

import csv




from datetime import datetime
import time, os, sys
import matplotlib as mpl
import matplotlib.pyplot as plt
import numpy as np

from Glass_Displacement.GD import Displacement_Measurement, AbortError


ROOT_DIR = os.path.dirname(__file__)

# YAML = os.path.join(ROOT_DIR, "MJVC.yaml")
# with open(YAML, "r") as f:
#     constants = yaml.safe_load(f)


def GD_UI():
    """Launches JVC"""

    class MeasurementWorker(QtCore.QObject):
        finished = QtCore.pyqtSignal()
        error = QtCore.pyqtSignal(str)
        progress = QtCore.pyqtSignal(int)
        nan_report = QtCore.pyqtSignal(object)  # list of dicts


        def __init__(self, control, args):
            super().__init__()
            self.control = control
            self.args = args

        @QtCore.pyqtSlot()
        def run(self):
            try:
                self.control.clear_abort()  # make sure a prior abort doesn't poison the next run
                self.control.progress_callback = self.progress.emit
                nan_points = self.control.controlled_grid(*self.args)
                self.nan_report.emit(nan_points)

                self.finished.emit()
            except AbortError:
                # still report what we have so far (if controlled_grid returns it on abort)
                # if your controlled_grid raises AbortError before returning, then nan_points won't exist anyway
                self.nan_report.emit(getattr(self.control, "nan_points", []) or [])
                self.finished.emit()

            except Exception as e:
                self.error.emit(str(e))
            finally:
                self.control.progress_callback = None



    class JVC(QMainWindow):
        """UI package for JV scans using a Keithley"""


        def __init__(self, resolution='high', root_dir=r'C:\Users\TPV\Documents\Glass Displacement\\') -> None:

            """Initliazes the JVC class"""
            
            # set fontsize and makersize
            self.fontsize = 8
            self.textsize = 12
            self.markersize = 1
            self.root_dir = root_dir
            self.resolution = resolution

            # resolution for different monitors
            self.dimensions = {
                'low':{
                    '3d': {
                        'x' : 1700,
                        'y' : 1700,
                    },
                    '2d':{
                        'x': 1700,
                        'y': 700, #840
                    }
                },
                'high':{
                    '3d': {
                        'x' : 755,
                        'y' : 755,
                    },
                    '2d':{
                        'x': 755,
                        'y': 349,
                    }
                }
            }

            # plot variables
            self.plot_var = {
                'displacement': {
                    '3d':{
                        'x':'x',
                        'y':'y',
                        'z':'z'
                    },
                    'x':{
                        'x':'x',
                        'z(x)':'z(x)'
                    },
                    'y':{
                        'y':'y',
                        'z(y)':'z(y)'
                    }
                },
                'slope': {
                    '3d':{
                        'x':'x',
                        'y':'y',
                        'z':'z'
                    },
                    'x':{
                        'x':'dx',
                        'z(x)':'dz(x)'
                    },
                    'y':{
                        'y':'dy',
                        'z(y)':'dz(y)'
                    },
                },
                'curvature': {
                    '3d':{
                        'x':'x',
                        'y':'y',
                        'z':'z'
                    },
                    'x':{
                        'x':'ddx',
                        'z(x)':'ddz(x)'
                    },
                    'y':{
                        'y':'ddy',
                        'z(y)':'ddz(y)'
                    },
                }
            }
            
            # set start state to displacement
            # self.pv = self.plot_var['displacement']

            # load neccisary packages
            self.control = Displacement_Measurement()

            # load UI.ui file
            super(JVC, self).__init__()
            ui_path = os.path.join(ROOT_DIR, "Glass_Displacement.ui")
            print("LOADING UI FROM:", ui_path)   # <-- ADD THIS
            uic.loadUi(ui_path, self)
            
            # load UI.ui file options into python memory
            self.load_ui(resolution)   

            # show UI
            self.show()

        def set_colors(self, NUM_COLORS:int, cmap = 'hot') -> int:
            """Generate a color array for plotting

            Args:
                NUM_COLORS (int): number of colors
                cmap (str): color map

            Returns:
                int: number of colors
            """
            cm = plt.get_cmap(cmap) 
            colors = [cm(1.*i/NUM_COLORS) for i in range(NUM_COLORS)]
            ret_colors = []
            for i in range(int(np.ceil(NUM_COLORS/2))):
                ret_colors.append(colors[i])
                ret_colors.append(colors[NUM_COLORS-i-1])
            return ret_colors


        def load_ui(self, res = 'high') -> None:
            """Load UI into python memory"""
            
            # link variables
            self.motor_speed = self.findChild(QComboBox, 'motorspeed_dropdown')
            self.grid_width = self.findChild(QLineEdit, 'gridwidth_input')
            self.grid_length = self.findChild(QLineEdit, 'gridlength_input')
            self.grid_points = self.findChild(QLineEdit, 'gridpoints_input')
            self.integration = self.findChild(QLineEdit, 'integration_input')
            self.orientation = self.findChild(QComboBox, 'sampleside_dropdown')
            self.stdev_threshold = self.findChild(QLineEdit, 'stdevthreshold_input')

            # load info
            self.experiment = self.findChild(QLineEdit, 'experimentname_input')
            self.sample = self.findChild(QLineEdit, 'samplename_input')

            # graph buttons
            self.displacement = self.findChild(QRadioButton, 'displacement_radiobutton')
            self.curvature = self.findChild(QRadioButton, 'curvature_radiobutton')
            self.slope = self.findChild(QRadioButton, 'slope_radiobutton')
            self.displacement.setChecked(True)
            self.displacement.toggled.connect(self.on_radio_button_clicked)
            self.curvature.toggled.connect(self.on_radio_button_clicked)
            self.slope.toggled.connect(self.on_radio_button_clicked)

            # --- Stage position UI (NEW) ---
            self.x_position_label = self.findChild(QLabel, "x_position_label")
            self.y_position_label = self.findChild(QLabel, "y_position_label")
            self.sethome_button = self.findChild(QPushButton, "sethome_button")

            if self.sethome_button is not None:
                self.sethome_button.clicked.connect(self.set_home_here)

            # QTimer to refresh position readout
            self.position_timer = QtCore.QTimer(self)
            self.position_timer.timeout.connect(self.update_position_display)
            self.position_timer.start(200)  # ms


            # --- Jog UI (NEW) ---
            self.jog_step_input = self.findChild(QLineEdit, "jog_step_input")
            self.jog_x_minus = self.findChild(QPushButton, "jog_x_minus")
            self.jog_x_plus  = self.findChild(QPushButton, "jog_x_plus")
            self.jog_y_minus = self.findChild(QPushButton, "jog_y_minus")
            self.jog_y_plus  = self.findChild(QPushButton, "jog_y_plus")

            self.jog_x_minus.clicked.connect(lambda: self.jog(dx_sign=-1, dy_sign=0))
            self.jog_x_plus.clicked.connect(lambda: self.jog(dx_sign=+1, dy_sign=0))
            self.jog_y_minus.clicked.connect(lambda: self.jog(dx_sign=0, dy_sign=-1))
            self.jog_y_plus.clicked.connect(lambda: self.jog(dx_sign=0, dy_sign=+1))




            self.grid_width.setValidator(QIntValidator(0, 10000, self))
            self.grid_length.setValidator(QIntValidator(0, 10000, self))
            self.grid_points.setValidator(QIntValidator(1, 100000, self))
            self.integration.setValidator(QIntValidator(1, 100000, self))
            self.stdev_threshold.setValidator(QDoubleValidator(0.0, 1000.0, 6, self))

            # optional: set sane defaults so fields are never blank
            if not self.grid_width.text().strip(): self.grid_width.setText("100")
            if not self.grid_length.text().strip(): self.grid_length.setText("100")
            if not self.grid_points.text().strip(): self.grid_points.setText("10")
            if not self.integration.text().strip(): self.integration.setText("10")
            if not self.stdev_threshold.text().strip(): self.stdev_threshold.setText("0.05")



            # add dropdown items
            self.motor_speed.addItem('slow')
            self.motor_speed.addItem('fast')
            self.orientation.addItem('front')
            self.orientation.addItem('back')
            
            # link buttons
            self.measure_button = self.findChild(QPushButton, 'measure_button')
            self.measure_button.clicked.connect(self.run_test)
            self.clear_button = self.findChild(QPushButton, 'clear_button')
            self.clear_button.clicked.connect(self.clear)
            self.save_button = self.findChild(QPushButton, 'save_button')
            self.save_button.clicked.connect(self.save)
            self.load_button = self.findChild(QPushButton, 'load_button')
            self.load_button.clicked.connect(self.load)
            self.home_button = self.findChild(QPushButton, 'home_button')
            self.home_button.clicked.connect(self.go_home)
            

            # add abort button
            self.abort_button = QPushButton("Abort")
            self.abort_button.setEnabled(False)
            self.abort_button.clicked.connect(self.abort_measurement)

            # put it next to the measure button if there's a layout
            parent = self.measure_button.parentWidget()
            if parent is not None and parent.layout() is not None:
                parent.layout().addWidget(self.abort_button)
            else:
                # fallback: place it near measure_button
                g = self.measure_button.geometry()
                self.abort_button.setParent(self.measure_button.parentWidget())
                self.abort_button.setGeometry(g.x() + g.width() + 10, g.y(), g.width(), g.height())
                self.abort_button.show()



            # create 3d graph 
            self.graph_3d = self.findChild(PyQt5.QtWidgets.QFrame, "graph_3d")
            self.figure_3d = plt.figure()
            self.axes_3d = self.figure_3d.add_subplot(111, projection='3d')
            self.canvas_3d = FigureCanvas(self.figure_3d)
            self.canvas_3d.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.canvas_3d.updateGeometry()
            self.toolbar_3d = NavigationToolbar(self.canvas_3d, self.graph_3d)
            self.layout_3d = QVBoxLayout()
            self.layout_3d.addWidget(self.toolbar_3d)
            self.layout_3d.addWidget(self.canvas_3d)
            self.graph_3d.setLayout(self.layout_3d)
            self.axes_3d.set_xlabel('Width (mm)')
            self.axes_3d.set_ylabel('Length (mm)')
            self.axes_3d.set_zlabel('Height (mm)')
            self.axes_3d.xaxis.label.set_size(self.fontsize)
            self.axes_3d.yaxis.label.set_size(self.fontsize)
            self.axes_3d.zaxis.label.set_size(self.fontsize)

            self.canvas_3d.draw()
            self.canvas_3d.resize(self.dimensions[res]['3d']['x'],self.dimensions[res]['3d']['y'])

            # create x graph 
            self.graph_x = self.findChild(PyQt5.QtWidgets.QFrame, "graph_x")
            self.figure_x, self.axes_x = plt.subplots(1, tight_layout = True)
            self.canvas_x = FigureCanvas(self.figure_x)
            self.canvas_x.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.canvas_x.updateGeometry()
            self.toolbar_x = NavigationToolbar(self.canvas_x, self.graph_x)
            self.layout_x = QVBoxLayout()
            self.layout_x.addWidget(self.toolbar_x)
            self.layout_x.addWidget(self.canvas_x)
            self.graph_x.setLayout(self.layout_x)
            self.axes_x.set_title('Length (Y) v Height (Z)')
            self.axes_x.set_xlabel('Length (mm)')
            self.axes_x.set_ylabel('Height (mm)')
            self.axes_x.xaxis.label.set_size(self.fontsize)
            self.axes_x.yaxis.label.set_size(self.fontsize)
            self.canvas_x.draw()
            self.canvas_x.resize(self.dimensions[res]['2d']['x'],self.dimensions[res]['2d']['y'])

            # create y graph 
            self.graph_y = self.findChild(PyQt5.QtWidgets.QFrame, "graph_y")
            self.figure_y, self.axes_y = plt.subplots(1, tight_layout = True)
            self.canvas_y = FigureCanvas(self.figure_y)
            self.canvas_y.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Expanding)
            self.canvas_y.updateGeometry()
            self.toolbar_y = NavigationToolbar(self.canvas_y, self.graph_y)
            self.layout_y = QVBoxLayout()
            self.layout_y.addWidget(self.toolbar_y)
            self.layout_y.addWidget(self.canvas_y)
            self.graph_y.setLayout(self.layout_y)
            self.axes_y.set_title('Width (X) v Height (Z)')
            self.axes_y.set_xlabel('Width (mm)')
            self.axes_y.set_ylabel('Height (mm)')
            self.axes_y.xaxis.label.set_size(self.fontsize)
            self.axes_y.yaxis.label.set_size(self.fontsize)
            self.canvas_y.draw()
            self.canvas_y.resize(self.dimensions[res]['2d']['x'],self.dimensions[res]['2d']['y'])


            self.progress_bar = self.findChild(QProgressBar, "progress_bar")
            self.progress_bar.setValue(0)

        

        def on_zlims_change(self,event_ax):
            """Callback function executed when y-limits change."""

            axes_limits = event_ax.get_zlim()
            for surface in self.surfaces:
                surface.set_clim(axes_limits[0], axes_limits[1])
            
            event_ax.figure.canvas.flush_events()
            event_ax.figure.canvas.draw()
            


        def on_radio_button_clicked(self):
            """Gets self.pv (parameters to plot) based on radio button selection, chosing a sublist from self.plot_var. Replot"""
            
            # if we have data, plot it
            if self.control.data_averages:
                self.plot_2d()
                self.plot_3d()


        def go_home(self):
            self.control.connect()
            self.control.go_home()


        
        def jog(self, dx_sign: int, dy_sign: int):
            try:
                # make sure we’re connected
                self.control.connect()

                step = float(self.jog_step_input.text())
                speed = str(self.motor_speed.currentText())

                dx = step * dx_sign
                dy = step * dy_sign

                self.control.stage.jog(dx_mm=dx, dy_mm=dy, speed=speed)

                # update labels immediately
                self.update_position_display()

            except Exception as e:
                QMessageBox.warning(self, "Jog Error", str(e))




        def run_test(self):
            """Run test button. Starts measurement without freezing UI."""
            self.position_timer.stop()

            # prevent re-entry (safe even if thread got deleted)
            t = getattr(self, "_meas_thread", None)
            try:
                if t is not None and t.isRunning():
                    return
            except RuntimeError:
                # underlying C++ object is deleted; treat as not running
                self._meas_thread = None
                self._meas_worker = None


            try:
                max_x = int(self.grid_width.text().strip())
                max_y = int(self.grid_length.text().strip())
                npts  = int(self.grid_points.text().strip())
                speed = str(self.motor_speed.currentText())
                height_iters = int(self.integration.text().strip())
                orient = str(self.orientation.currentText())
                stdev = float(self.stdev_threshold.text().strip())

                args = (max_x, max_y, npts, speed, height_iters, orient, stdev)

            except Exception as e:
                QMessageBox.warning(self, "Input Error", str(e))
                self.position_timer.start(200)
                return

            # Disable button during measurement
            self.measure_button.setEnabled(False)
            self.measure_button.setText("Measuring...")
            self.abort_button.setEnabled(True)
            self.abort_button.setText("Abort")
            self.progress_bar.setValue(0)

            # Create thread + worker
            self._meas_thread = QtCore.QThread(self)
            self._meas_worker = MeasurementWorker(self.control, args)
            self._meas_worker.moveToThread(self._meas_thread)

            self._meas_thread.started.connect(self._meas_worker.run)
            self._meas_worker.progress.connect(self.progress_bar.setValue)
            self._last_nan_points = []

            def _on_nan_report(nan_points):
                self._last_nan_points = nan_points or []

            self._meas_worker.nan_report.connect(_on_nan_report)


            def _finish_ui(success=True, msg=None):
                self.control.progress_callback = None
                # reset buttons
                self.measure_button.setEnabled(True)
                self.measure_button.setText("Perform Measurement")
                self.abort_button.setEnabled(False)
                self.abort_button.setText("Abort")

                # restart position polling
                self.position_timer.start(200)

                if not success and msg:
                    QMessageBox.critical(self, "Measurement Error", msg)

                # only plot if we actually have new data
                if self.control.data_averages:
                    self.plot_3d()
                    self.plot_2d()

                # --- save NaN points CSV ---
                try:
                    nan_pts = getattr(self, "_last_nan_points", []) or []
                    if nan_pts:
                        root = os.path.normpath(self.root_dir)
                        exp_name = str(self.experiment.text())
                        module_id = str(self.sample.text())

                        # ensure dirs exist (same logic as save())
                        if not os.path.isdir(root):
                            root = QFileDialog.getExistingDirectory(self, "Select Directory")

                        if root and not os.path.isdir(root):
                            os.mkdir(root)

                        exp_pth = os.path.join(root, exp_name)
                        if not os.path.isdir(exp_pth):
                            os.mkdir(exp_pth)

                        module_pth = os.path.join(exp_pth, module_id)
                        if not os.path.isdir(module_pth):
                            os.mkdir(module_pth)

                        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
                        out_path = os.path.join(module_pth, f"{module_id}_NaN_points_{ts}.csv")

                        with open(out_path, "w", newline="") as f:
                            w = csv.writer(f)
                            w.writerow(["orientation", "x_mm", "y_mm"])
                            for p in nan_pts:
                                w.writerow([p.get("orientation", ""), p.get("x", ""), p.get("y", "")])

                        QMessageBox.information(self, "NaN CSV Saved", f"Saved {len(nan_pts)} skipped points to:\n{out_path}")

                except Exception as e:
                    # don't fail the UI if saving fails
                    QMessageBox.warning(self, "NaN CSV Save Error", str(e))


                self._meas_thread = None
                self._meas_worker = None

            def done_ok():
                _finish_ui(success=True)

            def done_err(msg):
                _finish_ui(success=False, msg=msg)

            # UI completion handlers
            self._meas_worker.finished.connect(done_ok)
            self._meas_worker.error.connect(done_err)

            # ensure thread stops when worker is done
            self._meas_worker.finished.connect(self._meas_thread.quit)
            self._meas_worker.error.connect(lambda _: self._meas_thread.quit())

            # safe cleanup (AFTER thread ends)
            self._meas_thread.finished.connect(self._meas_worker.deleteLater)
            self._meas_thread.finished.connect(self._meas_thread.deleteLater)

            self._meas_thread.start()



        def plot_3d(self, axes = None, plot_type = None):

            zmin = zmax = None

            # clear axes
            self.axes_3d.cla()
            self.surfaces = []

            # check if axes passed in, if not plot on UI
            draw = False
            if not axes:
                axes = self.axes_3d
                draw = True
                
                # calc axes
                self.pv = self.plot_var['displacement']
                zs = []
                for orientation in self.control.data_2d.keys():
                    zs.extend(self.control.data_2d[orientation][self.pv['3d']['z']])
                zmin = np.min(zs)
                zmax = np.max(zs)
            
            # plot 3d 
            for orientation in self.control.data_2d.keys():
                
                # if plot type not passed in, get from checked boxes
                if not plot_type:
                    if self.displacement.isChecked():
                        plot_type = 'displacement'
                    elif self.slope.isChecked():
                        plot_type = 'slope'
                    elif self.curvature.isChecked():
                        plot_type = 'curvature'
                
                # set pv
                self.pv = self.plot_var[plot_type]
                
                # plot depending on plot type
                if plot_type == 'displacement':
                    surface = axes.plot_surface(
                        self.control.data_2d[orientation][self.pv['3d']['x']], 
                        self.control.data_2d[orientation][self.pv['3d']['y']], 
                        self.control.data_2d[orientation][self.pv['3d']['z']], 
                        cmap='viridis',
                        antialiased=True,
                        vmin = zmin,
                        vmax = zmax
                        )
                
                elif plot_type == 'slope':
                    surface = axes.plot_surface(
                        self.control.data_2d[orientation][self.pv['3d']['x']], 
                        self.control.data_2d[orientation][self.pv['3d']['y']], 
                        self.control.data_2d[orientation][self.pv['3d']['z']], 
                        rstride=1, 
                        cstride=1,
                        facecolors=mpl.cm.jet(self.control.data_2d[orientation]['dz']),
                        antialiased=True, 
                        )
                
                elif plot_type == 'curvature':
                    surface = axes.plot_surface(
                        self.control.data_2d[orientation][self.pv['3d']['x']], 
                        self.control.data_2d[orientation][self.pv['3d']['y']], 
                        self.control.data_2d[orientation][self.pv['3d']['z']], 
                        rstride=1, 
                        cstride=1,
                        facecolors=mpl.cm.jet(self.control.data_2d[orientation]['ddz']),
                        antialiased=True, 
                        )
                
                self.surfaces.append(surface)

            # customize graph
            axes.set_xlabel('Width (mm)')
            axes.set_ylabel('Length (mm)')
            axes.set_zlabel('Height (mm)')
            axes.xaxis.label.set_size(self.fontsize)
            axes.yaxis.label.set_size(self.fontsize)
            axes.zaxis.label.set_size(self.fontsize)

            # connect function
            self.axes_3d.callbacks.connect('zlim_changed', self.on_zlims_change)

            # if we didnt pass in axes, draw canvas
            if draw:
                self.canvas_3d.draw()


        def plot_2d(self, axes = None, plot_type = None):
            
            # clear axes
            self.axes_y.cla()
            self.axes_x.cla()

            # check if axes passed in, if not plot on UI
            draw = False
            if not axes:
                axes_x = self.axes_x
                axes_y = self.axes_y
                draw = True
            else:
                axes_x = axes[0]
                axes_y = axes[1]

            # check if plot_type passed in, use that data type rather than what UI has selected
            if plot_type:
                self.pv = self.plot_var[plot_type]
            elif self.displacement.isChecked():
                self.pv = self.plot_var['displacement']
            elif self.slope.isChecked():
                self.pv = self.plot_var['slope']
            elif self.curvature.isChecked():
                self.pv = self.plot_var['curvature']

            # add lines for cells
            for scribe in self.control.locations['scribes']:
                axes_y.axvline(x= scribe, color = 'lightgrey')     

            # iterate through orientations
            for orientation in self.control.data_1d.keys():

                colors = self.set_colors(len(self.control.data[orientation][self.pv['y']['z(y)']]))

                # plot each trace
                for idx in range(len(self.control.data[orientation][self.pv['y']['z(y)']])):
                    axes_x.plot(
                        self.control.data[orientation][self.pv['y']['y']], 
                        self.control.data[orientation][self.pv['y']['z(y)']][idx], 
                        color = colors[idx],
                        linestyle = '--',
                        alpha = 0.6 
                        )

                # plot averages
                axes_x.plot(
                    self.control.data_averages[orientation][self.pv['y']['y']], 
                    self.control.data_averages[orientation][self.pv['y']['z(y)']], 
                    linewidth =2, 
                    color = 'black'
                    )

                # plot each trace
                for idx in range(len(self.control.data[orientation][self.pv['x']['z(x)']])):
                    axes_y.plot(
                        self.control.data[orientation][self.pv['x']['x']], 
                        self.control.data[orientation][self.pv['x']['z(x)']][idx], 
                        color = colors[idx],
                        linestyle = '--',
                        alpha = 0.6 
                        )

                # plot averages
                axes_y.plot(
                    self.control.data_averages[orientation][self.pv['x']['x']], 
                    self.control.data_averages[orientation][self.pv['x']['z(x)']],  
                    linewidth =2, 
                    color = 'black'
                    )

            # generate all data array
            all_data = []
            for orientation in self.control.calcuations.keys():
                all_data += self.control.data[orientation][self.pv['y']['z(y)']].tolist()
            all_data = np.array(all_data)
            masked_arr_y = np.where(np.isfinite(all_data), all_data, np.nan).flatten()

            all_data = []
            for orientation in self.control.calcuations.keys():
                all_data += self.control.data[orientation][self.pv['x']['z(x)']].tolist()
            all_data = np.array(all_data)
            masked_arr_x = np.where(np.isfinite(all_data), all_data, np.nan).flatten()

            # anotate the areas in the top left and bottom left sections of the axes
            for orientation in self.control.calcuations.keys():

                if orientation == 'front':
                    # axes_x.text(
                    #     np.min(self.control.data[orientation][self.pv['y']['y']]), 
                    #     np.nanmax(masked_arr_y),
                    #     f"{self.control.calcuations[orientation]['area (y)']:.1f} mm^3",
                    #     horizontalalignment='left',
                    #     verticalalignment='top',
                    #     fontsize = self.textsize
                    #     )
                    # axes_y.text(
                    #     np.min(self.control.data[orientation][self.pv['x']['x']]), 
                    #     np.nanmax(masked_arr_x),
                    #     f"{self.control.calcuations[orientation]['area (x)']:.1f} mm^3",
                    #     horizontalalignment='left',
                    #     verticalalignment='top',
                    #     fontsize = self.textsize
                    #     )
                    axes_x.text(
                        np.min(self.control.data[orientation][self.pv['y']['y']]), 
                        np.nanmax(masked_arr_y),
                        f"sum(z) = {self.control.calcuations[orientation]['area']:.1f} mm^3,\narea(y) = {self.control.calcuations[orientation]['area (y)']:.1f} mm^3",
                        horizontalalignment='left',
                        verticalalignment='top',
                        fontsize = self.textsize
                        )
                    axes_y.text(
                        np.min(self.control.data[orientation][self.pv['x']['x']]), 
                        np.nanmax(masked_arr_x),
                        f"sum(z) = {self.control.calcuations[orientation]['area']:.1f} mm^3,\narea(x) = {self.control.calcuations[orientation]['area (x)']:.1f} mm^3",
                        horizontalalignment='left',
                        verticalalignment='top',
                        fontsize = self.textsize
                        )
                    
                elif orientation == 'back':
                    # axes_x.text(
                    #     np.min(self.control.data[orientation][self.pv['y']['y']]), 
                    #     np.nanmin(masked_arr_y),
                    #     f"{self.control.calcuations[orientation]['area (y)']:.1f} mm^3",
                    #     horizontalalignment='left',
                    #     verticalalignment='bottom',
                    #     fontsize = self.textsize
                    #     )
                    # axes_y.text(
                    #     np.min(self.control.data[orientation][self.pv['x']['x']]), 
                    #     np.nanmin(masked_arr_x),
                    #     f"{self.control.calcuations[orientation]['area (x)']:.1f} mm^3",
                    #     horizontalalignment='left',
                    #     verticalalignment='bottom',
                    #     fontsize = self.textsize
                    #     )
                    axes_x.text(
                        np.min(self.control.data[orientation][self.pv['y']['y']]), 
                        np.nanmin(masked_arr_y),
                        f"sum(z) = {self.control.calcuations[orientation]['area']:.1f} mm^3,\narea(y) = {self.control.calcuations[orientation]['area (y)']:.1f} mm^3",
                        horizontalalignment='left',
                        verticalalignment='bottom',
                        fontsize = self.textsize
                        )
                    axes_y.text(
                        np.min(self.control.data[orientation][self.pv['x']['x']]), 
                        np.nanmin(masked_arr_x),
                        f"sum(z) = {self.control.calcuations[orientation]['area']:.1f} mm^3,\narea(x) = {self.control.calcuations[orientation]['area (x)']:.1f} mm^3",
                        horizontalalignment='left',
                        verticalalignment='bottom',
                        fontsize = self.textsize
                        )
            
            # relabel and draw
            axes_y.set_title('Width (X) v Height (Z)')
            axes_y.set_xlabel('Width (mm)')
            axes_y.set_ylabel('Height (mm)')
            axes_y.xaxis.label.set_size(self.fontsize)
            axes_y.yaxis.label.set_size(self.fontsize)
            rng = np.abs((np.nanmax(masked_arr_x) - np.nanmin(masked_arr_x))/8)
            axes_y.set_ylim(np.nanmin(masked_arr_x)-rng, np.nanmax(masked_arr_x)+rng)

            axes_x.set_title('Length (Y) v Height (Z)')
            axes_x.set_xlabel('Length (mm)')
            axes_x.set_ylabel('Height (mm)')
            axes_x.xaxis.label.set_size(self.fontsize)
            axes_x.yaxis.label.set_size(self.fontsize)
            rng = np.abs((np.nanmax(masked_arr_y) - np.nanmin(masked_arr_y))/8)
            axes_x.set_ylim(np.nanmin(masked_arr_y)-rng, np.nanmax(masked_arr_y)+rng)
            
            if draw:
                self.canvas_y.draw()
                self.canvas_x.draw()



        def clear(self):
            
            # reset y axes
            self.axes_y.cla()
            self.axes_y.set_title('Width (X) v Height (Z)')
            self.axes_y.set_xlabel('Width (mm)')
            self.axes_y.set_ylabel('Height (mm)')
            self.axes_y.xaxis.label.set_size(self.fontsize)
            self.axes_y.yaxis.label.set_size(self.fontsize)
            self.canvas_y.draw()

            # reset x axes
            self.axes_x.cla()
            self.axes_x.set_title('Length (Y) v Height (Z)')
            self.axes_x.set_xlabel('Length (mm)')
            self.axes_x.set_ylabel('Height (mm)')
            self.axes_x.xaxis.label.set_size(self.fontsize)
            self.axes_x.yaxis.label.set_size(self.fontsize)
            self.canvas_x.draw()

            # reset 3d plot
            self.axes_3d.cla()
            self.axes_3d.set_xlabel('Width (mm)')
            self.axes_3d.set_ylabel('Length (mm)')
            self.axes_3d.set_zlabel('Height (mm)')
            self.axes_3d.xaxis.label.set_size(self.fontsize)
            self.axes_3d.yaxis.label.set_size(self.fontsize)
            self.axes_3d.zaxis.label.set_size(self.fontsize)
            self.canvas_3d.draw()

            # reset master lists
            self.control.data_raw = {}
            self.control.data_1d = {}
            self.control.data_2d = {}
            self.control.data_averages = {}
            self.control.locations = {}
            self.control.calcuations = {}
            self.scribes = np.arange(10.1, 130 + 5, 5)


        def load(self):

            fname, _ = QFileDialog.getOpenFileName(
            filter="*csv", caption="Choose file to load", directory=os.getcwd()
            )
            self.control.load_data(fname)
            self.plot_3d()
            self.plot_2d()


        def save(self):

            # get type of graph
            gtype = 'Z'
            if self.displacement.isChecked():
                gtype = 'Z'
            elif self.slope.isChecked():
                gtype = 'dZ'
            elif self.curvature.isChecked():
                gtype = 'ddZ'

            # get info needed for path
            root = os.path.normpath(self.root_dir)
            exp_name = str(self.experiment.text())
            module_id = str(self.sample.text())

            # give user option to load another path if the root directory doesnt exist
            if not os.path.isdir(root):
                root = QFileDialog.getExistingDirectory(self, "Select Directory")

            # build directory
            if not os.path.isdir(root):
                os.mkdir(root)
            exp_pth = os.path.join(root, exp_name)
            if not os.path.isdir(exp_pth):
                os.mkdir(exp_pth)
            module_pth = os.path.join(exp_pth, module_id)
            if not os.path.isdir(module_pth):
                os.mkdir(module_pth)
            
            # make axes to plot on, cycle through each plot type, plot and save
            fig, ax = plt.subplots(1)
            fig2, ax2 = plt.subplots(1)
            fig3 = plt.figure()
            ax3 = fig3.add_subplot(111, projection='3d')

            for gtype in self.plot_var.keys():

                # plot 2d and 3d for each graph type
                self.plot_2d([ax,ax2], gtype)
                self.plot_3d(ax3,gtype)

                # make path, check if exists, increment sidx if exists
                sidx = 0
                pth = os.path.join(module_pth,f'{module_id}_X_{gtype}_{sidx}.png')
                while os.path.exists(pth):
                    sidx +=1
                    pth = os.path.join(module_pth,f'{module_id}_X_{gtype}_{sidx}.png') 

                # save figure
                ax.figure.savefig(os.path.join(module_pth,f'{module_id}_X_{gtype}_{sidx}.png'))
                ax2.figure.savefig(os.path.join(module_pth,f'{module_id}_Y_{gtype}_{sidx}.png'))
                ax3.figure.savefig(os.path.join(module_pth,f'{module_id}_3D_{gtype}_{sidx}.png'))
                
                # clear axes
                ax.cla()
                ax2.cla()
                ax3.cla()

            # save raw data
            self.control.save_data(os.path.join(module_pth, f'{module_id}_GD_{sidx}.csv'))



            

        def update_position_display(self):
            """Update X/Y labels from encoder position."""
            try:
                # only update if labels exist
                if not hasattr(self, "x_position_label") or self.x_position_label is None:
                    return
                if not hasattr(self, "y_position_label") or self.y_position_label is None:
                    return

                # stage may not be connected yet; just skip if it errors
                pos = self.control.stage.get_position_mm()  # returns {1: x_mm, 2: y_mm}

                self.x_position_label.setText(f"X: {pos[1]:.3f} mm")
                self.y_position_label.setText(f"Y: {pos[2]:.3f} mm")

            except Exception:
                # keep UI smooth; no spam
                pass


        def set_home_here(self):
            """Set software home (0,0) at current physical position."""
            try:
                # make sure hardware is connected
                self.control.connect()
                self.control.stage.set_home_here()

                # immediately refresh labels
                self.update_position_display()

                QMessageBox.information(self, "Home Set", "Current stage position set to (0,0).")

            except Exception as e:
                QMessageBox.warning(self, "Set Home Error", str(e))

        def abort_measurement(self):
            try:
                self.abort_button.setEnabled(False)
                self.abort_button.setText("Aborting...")
                self.measure_button.setText("Stopping...")   # <-- change text, don't just disable silently
                self.control.request_abort()
            except Exception as e:
                QMessageBox.warning(self, "Abort Error", str(e))






    # Create application (required for widget)
    app = QApplication(sys.argv)
    
    # Create UI, which is a widget
    window = JVC()
    
    # Start the application
    app.exec_()

