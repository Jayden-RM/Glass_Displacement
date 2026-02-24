from email import message
import time,socket
import serial
import threading
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
from time import sleep
import csv
import time
import select
import socket
from serial.tools import list_ports


class AbortError(Exception):
    pass

class SkipPointError(Exception):
    """Raised when a point can't converge (stdev too high) within limits."""
    pass




class Motor:
    """Class for singular screw drive motor"""    

    def __init__(self, motornumber:int, debug:bool = False):

    
        self._lock = threading.Lock()

        """Initializes the motor class
        
        Args:
            motornumber (int): motor number
            debug (bool, optional): option to enter debug mode. Defaults to False.
        """

        # To connect to sockets:
            # 1. Setup motorList:
                # IP: static, set using selector switch on the motor controller
                # MAC: sticker on the motor contoller
                # name: doesnt matter
                # polarity: 1
                # udpPort: any 4 digit number not taken
            # 2. Modify local IP information:
                # navigate to ethernet adapter ethernet
                # dispable DHCP so IP is static
                # set computer IP to same IP address for first 3 parts: e.g. AAA.BBB.C.##
                # insist on IPv4 
            # 3. Hope
        
        # define required motor information
        self.number = motornumber
        motorList = [{"ip":"192.168.0.60","name":"Motor","MAC":"68-27-19-BA-A4-09","polarity":1,"udpPort":7777},
            {"ip":"192.168.0.70","name":"Motor","MAC":"68-27-19-BA-B4-ED","polarity":1,"udpPort":7778}] 
        self.motor = motorList[self.number-1]           
        self.localAddress="192.168.0.10" 
        #make sure self.localAddress is in the same subnet as the motor IP addresses. E.g. if motor IP is 192.18.0.60, then self.localAddress should be 192.168.0.##, where ## is any number between 1 and 255 that is not taken by another device on the network. Note that the first three parts of the IP address must match between the motor and the computer, but the last part can be different. Also note that the localAddress is only used for binding to the socket, so it does not have to be the same as the computer's actual IP address, but it must be in the same subnet as the motor IP addresses.
        self.DriveIP = self.motor["ip"]
        
        # set global for debug mode
        self.debug = debug


    def connect(self):
        sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        sock.setblocking(False)
        sock.bind(("0.0.0.0", self.motor["udpPort"]))  # 7777 / 7778 (unique per motor)
        self.motor["socket"] = sock



        


    def printMotor(self, motor:dict):
        """Prints motor information
        
        Args:
            motor (dict): motor
        """
        fieldPrint = {
            "name":"Motor name",
            "ip":"IP address",
            "udpPort":"UDP port",
            "MAC":"MAC address",
            "polarity":"Polarity"}
        for field in fieldPrint.keys():
            if field in motor.keys():
                print("\t"+fieldPrint[field]+": "+str(motor[field]))


    def command(self, message: str, motor: dict, timeout: float = 1.0) -> str:
        return self.send_cmd(message, motor, timeout=timeout, expect_reply=True) or ""





    def configureMotors(self, motornumber:int, speed: str):
        """Conifigure the motor for a given speed, acceleration, deceleration, and distance readout as decimal
        
        Args:
            motornumber (int): motor number
            speed (str): 'fast' or 'slow
        """
        
        # make input variables global
        self.number = motornumber
        self.speedSetting = speed
        
        # confirm we have a valid motor number
        if self.number ==1:
            
            # if 'fast': set speed as 1 rev/sec, acceleration/deceleration 0.5 revs/sec, set distance readout to decimal
            if self.speedSetting =='fast':
                self.command('VE2',self.motor)
                self.command('AC10',self.motor)
                self.command('DE10',self.motor)
                self.command('IFD', self.motor)
            
            # if 'slow': set speed as 0.5 rev/sec, acceleration/deceleration 0.5 revs/sec, set distance readout to decimal
            elif self.speedSetting =='slow':
                self.command('IFD', self.motor, timeout=2.0)
                self.command('VE1', self.motor, timeout=2.0)
                self.command('AC10', self.motor, timeout=2.0)
                self.command('DE10', self.motor, timeout=2.0)

        

        # confirm we have a valid motor number
        if self.number ==2:
            
            # if 'fast': set speed as 1 rev/sec, acceleration/deceleration 0.5 revs/sec, set distance readout to decimal
            if self.speedSetting =='fast':
                self.command('VE2',self.motor) #.3
                self.command('AC10',self.motor) #10
                self.command('DE10',self.motor) #10
                self.command('IFD', self.motor)
            
            # if 'slow': set speed as 0.5 rev/sec, acceleration/deceleration 0.5 revs/sec, set distance readout to decimal
            elif self.speedSetting =='slow':
                self.command('VE1',self.motor) #.1
                self.command('AC10',self.motor) # 10
                self.command('DE10',self.motor) # 10
                self.command('IFD', self.motor)


    def close(self):
        sock = self.motor.get("socket")
        if sock is not None:
            try:
                sock.close()
            finally:
                self.motor["socket"] = None

        
    def send_cmd(self, message: str, motor: dict, timeout: float = 1.0,
        expect_reply: bool = True, retries: int = 2) -> str | None:
        with self._lock:
            header = bytes([0x00, 0x07])
            end = bytes([0x0D])
            toSend = header + message.encode() + end

            sock = motor["socket"]

            # flush stale packets
            while True:
                try:
                    sock.recv(1024)
                except BlockingIOError:
                    break

            last_exc = None
            for attempt in range(retries + 1):
                sock.sendto(toSend, (motor["ip"], 7775))
                if not expect_reply:
                    return None

                deadline = time.time() + timeout
                while True:
                    remaining = deadline - time.time()
                    if remaining <= 0:
                        last_exc = TimeoutError(
                            f"No UDP reply from {motor['name']} at {motor['ip']} within {timeout}s "
                            f"(cmd={message}, attempt={attempt+1}/{retries+1})"
                        )
                        break

                    r, _, _ = select.select([sock], [], [], remaining)
                    if not r:
                        continue

                    resp = sock.recv(1024).decode(errors="replace").strip()
                    if resp == "%" or resp == "":
                        continue
                    return resp

            raise last_exc


    

    def _is_ack(self, s: str) -> bool:
        s = (s or "").strip()
        return s == "%" or s == ""  # add other known acks if you see them






class xy_stage():
    """Class for xy stage using two motors. Handles positions & distances"""

    def __init__(self):
        """Initializes the xy stage using two motor drive classes"""

        # counts per mm (you already use this everywhere)
        self.n = 20000 / 25.4

        # create a motor and position dictionary to make handling easier.
        self.motor_dict = {
            1: Motor(1),  # axis 1
            2: Motor(2)   # axis 2
        }

        # software-tracked position (mm)
        self.position_dict = {1: 0.0, 2: 0.0}
        self.previous_position_dict = {1: 0.0, 2: 0.0}

        # NEW: software home offsets (in raw ID counts)
        self.home_offset_counts = {1: 0, 2: 0}
        self.last_id_counts = {1: 0, 2: 0}

    def connect(self):
        """connects to the motors"""
        for motor in self.motor_dict.values():
            motor.connect()

    def waitForMotor(self, motor_numbers: list, abort_check=None, timeout_s=30):
        moving = True
        t0 = time.time()
        sleep(0.2)
        while moving:
            if abort_check:
                abort_check()

            if time.time() - t0 > timeout_s:
                raise TimeoutError("waitForMotor timed out waiting for motors to stop.")

            recieved_messages = [
                self.motor_dict[n].command('IV', self.motor_dict[n].motor, timeout=2.0)
                for n in motor_numbers
            ]
            if all(('IV=0' in msg) or ('IV=0000' in msg) for msg in recieved_messages):
                moving = False
            else:
                sleep(0.1)


    # ------------------------
    # NEW: robust ID parsing
    # ------------------------
    def _read_pos_counts(self, motor_num: int) -> int:
        m = self.motor_dict[motor_num]
        resp = m.command('IP', m.motor, timeout=2.0)  # <-- IP = absolute position
        s = resp.split('=')[-1].strip()

        # hex -> signed 32-bit
        if any(c.isalpha() for c in s):
            raw = int(s, 16)
            if raw >= 0x80000000:
                raw -= 0x100000000
            return raw

        return int(float(s))


    # ------------------------
        # NEW: software home
    def set_home_here(self):
        for axis in [1, 2]:
            counts = self._read_pos_counts(axis)
            self.home_offset_counts[axis] = counts
            self.last_id_counts[axis] = counts
            self.position_dict[axis] = 0.0
            self.previous_position_dict[axis] = 0.0

    def get_position_mm(self) -> dict:
        pos = {}
        for axis in [1, 2]:
            counts = self._read_pos_counts(axis)
            self.last_id_counts[axis] = counts
            pos[axis] = (counts - self.home_offset_counts[axis]) / self.n
        return pos




    # ------------------------
    # NEW: jog
    # ------------------------
    def jog(self, dx_mm: float = 0.0, dy_mm: float = 0.0, speed: str = "slow"):
        """Move relative by dx/dy in mm (software coordinates)."""
        dx_counts = int(round(dx_mm * self.n))
        dy_counts = int(round(dy_mm * self.n))

        moves = {1: dx_counts, 2: dy_counts}

        moving_axes = []
        for axis in [1, 2]:
            if moves[axis] == 0:
                continue
            m = self.motor_dict[axis]
            m.configureMotors(axis, speed)
            m.send_cmd(f"FL{moves[axis]}", m.motor, expect_reply=False)
            moving_axes.append(axis)

        if moving_axes:
            self.waitForMotor(moving_axes, abort_check=getattr(self, "_abort_check", None))


        # update software position from encoder
        pos = self.get_position_mm()
        self.position_dict[1] = round(pos[1], 3)
        self.position_dict[2] = round(pos[2], 3)

    # ------------------------
    # your existing functions
        # ------------------------
    def continuous_movement(self, distance_x: float, distance_y: float, speed: str):
        for motor_num in [1, 2]:
            self.previous_position_dict[motor_num] = 0.0

        distances = [0, distance_x, distance_y]
        for motor_num, motor in self.motor_dict.items():
            motor.configureMotors(motor_num, speed)
            motor.send_cmd(f"FL{distances[motor_num]}", motor.motor, expect_reply=False)


    def measure_locations(self):

        pos = self.get_position_mm()
        self.position_dict[1] = round(pos[1], 3)
        self.position_dict[2] = round(pos[2], 3)


    def goToPosition(self, positionX: float, positionY: float, home: bool = True, speed: str = 'fast'):
        """
        Move to a position (mm) in your software coordinate system.
        If home=True, it goes to (0,0) first (software home).
        """
        if home:
            self.goHome()

        # Only allow positive positions if that's your intended workspace rule
        positions = [0, positionX, positionY]
        positions_positive = [positions[idx] >= 0 for idx in [1, 2]]

        if all(positions_positive):
            # Move by relative deltas from current software position_dict
            dx = positionX - float(self.position_dict[1])
            dy = positionY - float(self.position_dict[2])
            self.jog(dx_mm=dx, dy_mm=dy, speed=speed)
        else:
            print('Invalid position!')

    def goHome(self):
        """
        SAFER HOME: go to software (0,0) relative to last set_home_here().
        This avoids slamming into hard stops.
        """
        self.goToPosition(0.0, 0.0, home=False, speed="slow")

    def close(self):
        for m in self.motor_dict.values():
            m.close()


class Displacement_Sensor():
    """Class for dispalcement sensor"""
    
    def __init__(self, port=None, timeout=1, debug=False):

        """Initialize the displacement sensor class
        
        Args:
            port (str, optional): COM port. Defaults to 'COM4'.
            timeout (int, optional): timeout in secconds. Defaults to 1.
            debug (bool, optional): option to enter debug mode. Defaults to False.
        """
        
        # define unicode 
        self.stx = chr(2) # Unicode code point 2, which is a control character known as "Start of Text" (STX).
        self.etx = chr(3) # Unicode code point 3, which is a control character known as "End of Text" (STX).
        self.sep = chr(32) # Unicode code point 32, which is a space.
        
        # make input variables globals
        self.port = port
        self.timeout = timeout
        self.debug = debug


       



    def _auto_port(self):
        for p in list_ports.comports():
            hwid = (p.hwid or "")
            if "VID:PID=0403:6001" in hwid and "SER=6" in hwid:
                return p.device
        raise FileNotFoundError("Displacement sensor not found (FTDI SER=6).")






    def connect(self):
        # If we already have a serial object and it's open, don't reopen it
        if hasattr(self, "ser") and self.ser is not None and self.ser.is_open:
            return
        
        if not self.port:
            self.port = self._auto_port()

    


        # Create + open the serial port with the correct baudrate
        self.ser = serial.Serial(
            port=self.port,
            baudrate=921600,
            timeout=self.timeout,
            write_timeout=self.timeout
        )

        # Clear buffers AFTER opening
        self.ser.reset_input_buffer()
        self.ser.reset_output_buffer()

        # initialize head settings (REMOVE BAUD command)
        self.sendCmd(self.makeCommand(['HEAD', 'MEASURE_A', 'FRONT']))
        self.sendCmd(self.makeCommand(['HEAD', 'SHIFT_A', '0.0']))
        self.sendCmd(self.makeCommand(['HEAD', 'SPAN_A', '1.0']))
        self.sendCmd(self.makeCommand(['HEAD', 'LASER_A', '5']))
        self.sendCmd(self.makeCommand(['HEAD', 'SENS_A', 'Maximum']))
        self.sendCmd(self.makeCommand(['HEAD', 'THRESH_A', '7']))
        self.sendCmd(self.makeCommand(['HEAD', 'AVE_A', '512']))
        self.sendCmd(self.makeCommand(['HEAD', 'ALARM_A', 'CLAMP']))
        # self.sendCmd(self.makeCommand(['HEAD', 'BAUD_A', '921.6 K']))  # <- keep removed
        self.sendCmd(self.makeCommand(['HEAD', 'SAMP_A', 'Auto']))
        self.sendCmd(self.makeCommand(['HEAD', 'INTER', 'OFF']))

        # set head operation to measure
        self.sendCmd(self.makeCommand(['HEAD', 'OPERATION', 'MEASURE']))


    def open(self):
        if not hasattr(self, "ser") or self.ser is None:
            self.connect()
        elif not self.ser.is_open:
            self.ser.open()


    def close(self):
        if hasattr(self, "ser") and self.ser is not None and self.ser.is_open:
            self.ser.close()



    def sendCmd(self, command:str) -> str:
        """Send command 
        
        Args:
            command (str): command
        
        Returns:
            str: response from machine
        """
        if self.debug: print('sending '+str(command))
        self.ser.write(command)
        s = self.readALine()
        if self.debug: print(s)
        return s


    def readALine(self) -> bytes:
            stx = self.stx.encode("ascii")
            etx = self.etx.encode("ascii")

            # overall deadline (seconds)
            deadline = time.time() + max(1.0, float(self.timeout) if self.timeout else 1.0)

            # 1) wait for STX
            while True:
                if time.time() > deadline:
                    raise TimeoutError("readALine: timed out waiting for STX (wrong COM/baud or device not responding).")
                b = self.ser.read(1)
                if b == stx:
                    msg = b
                    break
                # ignore b'' and junk

            # 2) read until ETX
            while True:
                if time.time() > deadline:
                    raise TimeoutError("readALine: timed out waiting for ETX (incomplete response).")
                b = self.ser.read(1)
                if not b:
                    continue
                msg += b
                if b == etx:
                    return msg



    def makeCommand(self,vals:list) -> str:
        """Generate command 
        
        Args:
            vals (list): commands organized into a list
        
        Returns:
            str: command string
        """
        commandList = [val.encode('ascii') for val in vals]
        command = self.sep.encode('ascii').join(commandList)
        command = self.stx.encode('ascii')+command+self.etx.encode('ascii')
        if self.debug: print('makeCommand: got '+str(vals)+', returning '+str(command))
        return command      


    def parseOutput(self, returnBytes:bytes) -> str:
        """Parse system output
        
        Args:
            returnBytes (bytes): message to decode
        
        Returns:
            str: decoded message
        """
        return returnBytes[1:-1].decode('ascii')



    

    def measure_height(
        self,
        iters: int = 25,
        forced_stdev: float = 0.02,
        starting_threshold: int = 13,
        abort_check=None,
        max_time_s: float = 5.0,
        max_total_iters: int = 200,
        on_fail: str = "nan",   # "nan" or "raise"
    ) -> float:

        """Measures the height of the displacment sensor
        
        Args:
            iters (int, optional): number of measurements. Defaults to 25.
            forced_stdev (float, optional): forced standard deviation to consider measurment made. Defaults to 0.02
            starting_threshold (int, optional): starting threshold value for sesnsor. Defaults to 11. 
            
        Returns:
            float: height value
        """
        og_iters = iters
        val = starting_threshold

        t_start = time.time()
        total_target_iters = iters  # tracks how big 'iters' has grown

        while True:
            if abort_check:
                abort_check()

            # ---- HARD STOP CONDITIONS ----
            if (time.time() - t_start) > max_time_s or total_target_iters > max_total_iters:
                if on_fail == "raise":
                    raise SkipPointError(
                        f"Point did not converge: time>{max_time_s}s or iters>{max_total_iters} "
                        f"(last target iters={total_target_iters}, thresh={val})"
                    )
                return float("nan")

            heights = []
            idx = 0

            self.change_threshold(val)
            time.sleep(0.2)

            while idx < iters:
                if abort_check:
                    abort_check()

                # also time-cap INSIDE the inner loop
                if (time.time() - t_start) > max_time_s:
                    break

                s = self.sendCmd(self.makeCommand(['MEASURE', 'A']))
                height = float(self.parseOutput(s).removeprefix('+'))

                if abs(height) > 2000:
                    val -= 1
                    break
                elif abs(height) < 2:
                    heights.append(height)
                    idx += 1

            if len(heights) == iters:
                chopoff = int(np.round(iters / 5))
                heights = np.array(sorted(heights)[chopoff:len(heights)-chopoff])
                mean = np.mean(heights)
                stdev = np.std(heights)

                if stdev < forced_stdev:
                    return float(mean)

                # stdev still too high -> try more iters, BUT bounded by max_total_iters
                iters += og_iters
                total_target_iters = iters

            if val == 0:
                val = starting_threshold


    def change_threshold(self, val:int) -> str:
        """Changes measurement threshold

        Args:
            val (int): threshold value

        Returns:
            str: response from machine
        """
        reply = self.sendCmd(self.makeCommand(['HEAD', 'THRESH_A', str(val)]))
        return reply


    def calibrate(self):
        """Calibrate sensor head to current height"""
        
        val = 11
        continue_bool = True
        while continue_bool:
            self.change_threshold(val)
            time.sleep(0.5)
            s = self.sendCmd(self.makeCommand(['MEASURE', 'A']))
            height = float(self.parseOutput(s).removeprefix('+'))
        
            if abs(height) < 20:
                    continue_bool = False

        self.sendCmd(self.makeCommand(['ZERO', 'A']))


class Displacement_Measurement():
    """Class for displacement measurment"""


    def __init__(self, debug = False):
        """Initializes class for dispalcment measurment"""

        self.stage = xy_stage()
        self.sensor = Displacement_Sensor()
        self.debug = debug
        self.data_raw = {}
        self.data_1d = {}
        self.data = {}
        self.data_2d = {}
        self.data_averages = {}
        self.locations = {}
        self.calcuations = {}

        self.scribes = np.arange(10.1, 130 + 5, 5)

        self.connected = False
        self.abort_requested = False
        # --- stabilization tuning (NEW) ---
        self.post_move_settle_s = 3.0      # seconds to wait after each move
        self.throwaway_samples = 20        # dummy sensor reads

    def _stabilize_after_move(self):
        """Allow mechanics + sensor to settle after stage motion."""
        # mechanical settle
        time.sleep(self.post_move_settle_s)

        # optional sensor throwaway reads
        if self.throwaway_samples > 0:
            for _ in range(self.throwaway_samples):
                try:
                    s = self.sensor.sendCmd(
                        self.sensor.makeCommand(['MEASURE', 'A'])
                    )
                    _ = float(self.sensor.parseOutput(s).removeprefix('+'))
                except Exception:
                    pass



    

    def connect(self):
        """Connects to the hardware to make a scan"""

        if not self.connected:
            self.stage.connect()
            self.sensor.connect()
            self.connected = True

    
    def go_home(self):
        self.connect()
        self.stage.goHome()

    def request_abort(self):
        self.abort_requested = True

    def clear_abort(self):
        self.abort_requested = False

    def _check_abort(self):
        if self.abort_requested:
            raise AbortError("Aborted by user.")


    def controlled_grid(
            self, 
            max_x:int, 
            max_y:int, 
            iter:int, 
            speed:str = 'slow', 
            height_meas_iter = 25, 
            orientation:str= 'front',
            forced_stdev = 0.02
            ):
        """Measures displacement across the surface using a controlled grid

        Args:
            max_x (int): max x dimension in mm (left/right looking at instrument)
            max_y (int): max y dimension in mm (up/down looking at instrument)
            iter (int): number of spaces to make within the grid
            speed (str, optional): speed to move motors. Defaults to 'slow'.
            height_meas_iter (int, optional): number of measurements to make at each location. Defaults to 25.
            orientation (str, optional): orientaiton of package ('back' or 'front'). Defaults to 'front'.
            forced_stdev (float, optional): required standard deviation of hieght measurement before proceeding. Defaults to 0.002.
        """

        #
        if not self.connected:
            self.connect()

        # open serial connection
        self.sensor.open()

        # create globals for xvalues, yvalues, heights
        self.data_raw[orientation] = {
            'x': [],
            'y': [],
            'z': []
        }

        nan_points = []   # list of dicts: {"x":..., "y":..., "orientation":...}
        self.nan_points = nan_points



        # home stage, wait for vibrations to dampen. Calibrate sensor head (call this point 0)
        self.stage.goHome()
        time.sleep(1)
        # self.sensor.calibrate() # NEW NEW

        # calculate spacing of grid
        xs = np.linspace(0, max_x, iter)
        ys = np.linspace(0, max_y, iter)
        total_points = len(xs) * len(ys)
        done = 0


        # iterate through y values, reinitialized yvalues, xvalues, heights for each line
        for idy, y in enumerate(ys):
            xvalues = []
            yvalues = []
            heights = []

            # if regular oreintation do scan and join arrays
            if idy%2 == 0:
                for x in xs:

                    self._check_abort()
                    self.stage.goToPosition(x, y, False, speed)
                    self._check_abort()

                    # NEW: force mechanical + sensor stabilization
                    self._stabilize_after_move()

                    self.stage.measure_locations()
                    

                    xvalues.append(self.stage.position_dict[1])
                    yvalues.append(self.stage.position_dict[2])
                    self._check_abort()
                    
                    z = self.sensor.measure_height(
                        height_meas_iter,
                        forced_stdev,
                        abort_check=self._check_abort,
                        max_time_s=5.0,
                        max_total_iters=200,
                        on_fail="nan"
                    )

                    bad = not np.isfinite(z)
                    if bad:
                        nan_points.append({
                            "orientation": orientation,
                            "x": float(self.stage.position_dict[1]),
                            "y": float(self.stage.position_dict[2]),
                        })
                        # fill so reshape/analyze won't break
                        z = heights[-1] if heights else 0.0

                    heights.append(z)




                    done += 1
                    pct = int(done * 100 / total_points)
                    cb = getattr(self, "progress_callback", None)
                    if cb:
                        cb(pct)

                
                # flip x values if on back side to account for rotation
                if orientation == 'back':
                    xvalues.reverse()

                self.data_raw[orientation]['y'] += yvalues
                self.data_raw[orientation]['x'] += xvalues
                self.data_raw[orientation]['z'] += heights
            
            # if opposite, do everything in reverse
            else: 
                for x in reversed(xs):
                    self.stage.goToPosition(x, y, False, speed)
                    self._check_abort()

                    # NEW: force mechanical + sensor stabilization
                    self._stabilize_after_move()

                    self.stage.measure_locations()

                    xvalues.append(self.stage.position_dict[1])
                    yvalues.append(self.stage.position_dict[2])
                    self._check_abort()
                    z = self.sensor.measure_height(
                        height_meas_iter,
                        forced_stdev,
                        abort_check=self._check_abort,
                        max_time_s=5.0,
                        max_total_iters=200,
                        on_fail="nan"
                    )

                    bad = not np.isfinite(z)
                    if bad:
                        nan_points.append({
                            "orientation": orientation,
                            "x": float(self.stage.position_dict[1]),
                            "y": float(self.stage.position_dict[2]),
                        })
                        # fill so reshape/analyze won't break
                        z = heights[-1] if heights else 0.0

                    heights.append(z)

                    done += 1
                    pct = int(done * 100 / total_points)
                    cb = getattr(self, "progress_callback", None)
                    if cb:
                        cb(pct)
                
                # flip x values if on back side to account for rotation
                if orientation == 'back':
                    xvalues.reverse()

                # flip all values as we are moving in reverse                
                self.data_raw[orientation]['y'] += reversed(yvalues)
                self.data_raw[orientation]['x'] += reversed(xvalues)
                self.data_raw[orientation]['z'] += reversed(heights)

        # close serial connection
        self.sensor.close()

        # analyze the data
        self.analyze_data(orientation)
        return nan_points



    def save_data(self, fpath:str):
        """Save the data at given filepath

        Args:
            fpath (str): filepath to save
        """

        # flatten dict for output
        output_data = {}
        for orientation in self.data_raw.keys():
            for param in self.data_raw[orientation].keys():
                output_data[f'{orientation} {param}'] = self.data_raw[orientation][param]
        
        # open file
        with open(fpath, "w", newline="") as f:
            writer = csv.writer(f, delimiter=',')

            # write header
            keys = list(output_data.keys())
            writer.writerow(keys)
            
            # write data
            for idx in range(len(output_data[keys[0]])):
                writer.writerow([output_data[p][idx] for p in keys])




    def load_data(self, fpth:str):
        """Load data from previous experiment

        Args:
            fpth (str): filepath to load
        """

        # get headers
        with open(fpth, 'r') as file:
            csv_reader = csv.reader(file)
            header = next(csv_reader)

        # grab and orientations, start dictionary
        orientations = list(set([h.split(' ')[0] for h in header]))
        for orientation in orientations:
            self.data_raw[orientation] = {}

        # load csv file row_1 -> row_n, transpose 
        data = np.loadtxt(fpth, skiprows=1, delimiter = ',').transpose()
        
        # fill dictionary
        for idx, column in enumerate(data):
            orientation = header[idx].split(' ')[0]
            param = header[idx].removeprefix(f'{orientation} ')
            self.data_raw[orientation][param] = column.tolist()

        # analyze data
        for orientation in orientations:
            self.analyze_data(orientation)


    def analyze_data(self, orientation:str = 'front', stdev_mult:float = 3.0):
        """Analyze the data and create a dataframe of it

        Args:
            orientation (str, optional): orientation to analyze ('front' or 'back'). Defaults to 'front'
            stdev_mult (float, optional): multiplier to consider an outlier and fill with neighboring values
        """

        # create numpy arrays
        xs = np.array(np.round(self.data_raw[orientation]['x'], decimals = 1))
        ys = np.array(np.round(self.data_raw[orientation]['y'], decimals = 1))
        zs = np.array(np.round(self.data_raw[orientation]['z'], decimals = 6))

        # level data using plane fit
        A = np.column_stack((xs,ys,np.ones_like(xs)))
        coeffs, _, _, _ = np.linalg.lstsq(A,zs,rcond=None)
        a,b,c = coeffs
        zs -= a*xs + b*ys + c

        # get list of x values and y values for mesh
        x = np.unique(xs)
        y = np.unique(ys)
        z = zs

        # flip x values if working on backside as np.unique will be ordered from low to high
        if orientation == 'back':
            x = np.flip(x)

        # convert x,y,z in 2d data, create 2d df
        X, Y = np.meshgrid(x, y)
        Z = z.reshape(Y.shape)

        # remove outliers outside mean +/- stdev_mult*stdev
        item_removed = True
        while item_removed:
            item_removed = False
            mean = np.mean(z)
            stdev = np.std(z)
            for row_idx, row in enumerate(Z):
                for col_idx in range(len(row)):
                    if (Z[row_idx][col_idx] > mean + stdev_mult*stdev) or (Z[row_idx][col_idx] < mean - stdev_mult*stdev):
                        values = []
                        try:
                            values.append(Z[row_idx-1][col_idx])
                        except:
                            pass
                        try:
                            values.append(Z[row_idx+1][col_idx])
                        except:
                            pass
                        try:
                            values.append(Z[row_idx][col_idx-1])
                        except:
                            pass
                        try:
                            values.append(Z[row_idx][col_idx+1])
                        except:
                            pass
                        value = float(np.mean(values))
                        Z[row_idx][col_idx] = value
                        item_removed = True
            
            # flatted z axes, update df, create 2d df
            z = [item for sublist in Z for item in sublist]


        # smooth again based on F''(x)
        item_removed = True
        while item_removed:
            item_removed = False

            # calc f''(x), mean, stdev
            Gx, Gy = np.gradient(Z, x, y, edge_order=2)
            Gx, Gy = np.gradient(Gx, x, y, edge_order=2) 
            G = Gx
            DZ = G - np.min(G)
            DZ = DZ/DZ.max()
            dz = DZ.flatten()
            mean = np.mean(dz)
            stdev = np.std(dz)

            for row_idx, row in enumerate(DZ):
                for col_idx in range(len(row)):
                    if (DZ[row_idx][col_idx] > mean + stdev) or (DZ[row_idx][col_idx] < mean - stdev):
                        values = []
                        try:
                            values.append(Z[row_idx][col_idx-1])
                        except:
                            pass
                        try:
                            values.append(Z[row_idx][col_idx+1])
                        except:
                            pass

                        # if value is different, fix
                        value = float(np.mean(values))
                        if np.round(Z[row_idx][col_idx],2) != np.round(value,2):
                            Z[row_idx][col_idx] = value
                            item_removed = True

        # flatten list
        z = [item for sublist in Z for item in sublist]

        # handle orientation flip for front/back
        z = np.array(z)
        z -= np.min(z)
        if orientation == 'back':
            z = -1*(z)
        elif orientation == 'front':
            z = z

        # relevel with plane fit
        A = np.column_stack((xs,ys,np.ones_like(xs)))
        coeffs, _, _, _ = np.linalg.lstsq(A,z,rcond=None)
        a,b,c = coeffs
        zs -= a*xs + b*ys + c

        # reshape
        Z = z.reshape(Y.shape)

        # calculate gradients
        Gx, Gy = np.gradient(Z, x, y, edge_order=2) 
        G = (Gx**2+Gy**2)**0.5  
        dz = G - np.min(G)
        m = DZ.max()
        if m > 0:
            DZ = DZ / m
        else:
            DZ = np.zeros_like(DZ)


        # calculate double gradients
        dx, dy = np.gradient(Z, x, y, edge_order=2)
        d2x, _ = np.gradient(dx, x, y, edge_order=2)
        _, d2y = np.gradient(dy, x, y, edge_order=2)
        GG = (d2x**2+d2y**2)**0.5
        ddz = GG - np.nanmin(GG)
        m = np.nanmax(ddz)
        if np.isfinite(m) and m > 0:
            ddz = ddz / m
        else:
            ddz = np.zeros_like(ddz)


        # put scalar x,y,z data in dictionary
        self.data_1d[orientation] = {
            "x": xs, 
            "y": ys, 
            "z": zs,
            }
        
        # put 2d arays in dictionary
        self.data_2d[orientation] = {
            "x": X,
            "y": Y, 
            "z": Z,
            "dz": dz,
            "ddz": ddz
            }

        # put data split by x and y and z in dictionary
        self.data[orientation] = {
            "x" : X[0],
            "y" : Y.transpose()[0],
            "z(x)" : Z,
            "z(y)" : Z.transpose(),
        }

        # calc f', f''
        self.data[orientation]["dz(x)"] = np.array([np.gradient(self.data[orientation]['z(x)'][idx], edge_order = 2) for idx in range(len(self.data[orientation]['z(x)']))])
        self.data[orientation]["dz(y)"] = np.array([np.gradient(self.data[orientation]['z(y)'][idx], edge_order = 2) for idx in range(len(self.data[orientation]['z(y)']))])
        self.data[orientation]["ddz(x)"] = np.array([np.gradient(self.data[orientation]['dz(x)'][idx], edge_order = 2) for idx in range(len(self.data[orientation]['dz(x)']))])
        self.data[orientation]["ddz(y)"] = np.array([np.gradient(self.data[orientation]['dz(y)'][idx], edge_order = 2) for idx in range(len(self.data[orientation]['dz(y)']))])
        self.data[orientation]["dx"] = self.data[orientation]['x']
        self.data[orientation]["dy"] = self.data[orientation]['y']
        self.data[orientation]["ddx"] = self.data[orientation]['x']
        self.data[orientation]["ddy"] = self.data[orientation]['y']

        # average over x or y traces, calc f', f''
        self.data_averages[orientation] = {}
        self.data_averages[orientation]['z(x)'] = self.data_2d[orientation]['z'].mean(axis = 0)
        self.data_averages[orientation]['z(y)'] = self.data_2d[orientation]['z'].mean(axis = 1)
        self.data_averages[orientation]['x'] = self.data_2d[orientation]['x'].mean(axis = 0)
        self.data_averages[orientation]['y'] = self.data_2d[orientation]['y'].mean(axis = 1)
        self.data_averages[orientation]["dz(x)"] = np.gradient(self.data_averages[orientation]['z(x)'], edge_order = 2)
        self.data_averages[orientation]["dz(y)"] = np.gradient(self.data_averages[orientation]['z(y)'], edge_order = 2)
        self.data_averages[orientation]["ddz(x)"] = np.gradient(self.data_averages[orientation]['dz(x)'], edge_order = 2)
        self.data_averages[orientation]["ddz(y)"] = np.gradient(self.data_averages[orientation]['dz(y)'], edge_order = 2)
        self.data_averages[orientation]["dx"] = self.data_averages[orientation]['x']
        self.data_averages[orientation]["dy"] = self.data_averages[orientation]['y']
        self.data_averages[orientation]["ddx"] = self.data_averages[orientation]['x']
        self.data_averages[orientation]["ddy"] = self.data_averages[orientation]['y']
        
        # generate scribe and cell center locations
        scribes = np.arange(10.1, np.max(self.data_averages[orientation]['x']) + 5, 5)
        if len(scribes)> 21:
            scribes = self.scribes[:21]
        cell_center = [(self.scribes[idx+1] +self.scribes[idx])/2 for idx in range(len(self.scribes)-1)]
        self.locations['scribes'] = scribes
        self.locations['cell center'] = cell_center
        
        # generate slope and concavity in center of each scribe
        interp_heights = np.interp(self.scribes,self.data_averages[orientation]['x'], self.data_averages[orientation]['z(x)'])
        slopes = np.diff(interp_heights)/np.diff(self.scribes)
        den = np.diff(self.scribes, n=2)
        num = np.diff(interp_heights, n=2)
        concavity = np.divide(num, den, out=np.zeros_like(num), where=den!=0)


        # calc area under averaged curve
        area_x = np.trapz(self.data_averages[orientation]['z(x)'], self.data_averages[orientation]['x'])
        area_x -= np.trapz(
            [self.data_averages[orientation]['z(x)'][0], self.data_averages[orientation]['z(x)'][-1]],
            [self.data_averages[orientation]['x'][0], self.data_averages[orientation]['x'][-1]]
        )
        area_x *= (np.max(self.data_averages[orientation]['y'])-np.min(self.data_averages[orientation]['y']))

        area_y = np.trapz(self.data_averages[orientation]['z(y)'], self.data_averages[orientation]['y'])
        area_y -= np.trapz(
            [self.data_averages[orientation]['z(y)'][0], self.data_averages[orientation]['z(y)'][-1]],
            [self.data_averages[orientation]['y'][0], self.data_averages[orientation]['y'][-1]]
        )
        area_y *= (np.max(self.data_averages[orientation]['x'])-np.min(self.data_averages[orientation]['x']))

        # flip area y (area x will already be flipped from x axes being inreverse)
        if orientation == 'back':
            area_y *= -1

        # save calculations
        self.calcuations[orientation] = {}
        self.calcuations[orientation]['cell center'] = cell_center
        self.calcuations[orientation]['slope'] = slopes
        self.calcuations[orientation]['concavity'] = concavity
        self.calcuations[orientation]['area (x)'] = area_x
        self.calcuations[orientation]['area (y)'] = area_y
        self.calcuations[orientation]['area'] = np.sum(np.sum(self.data_2d[orientation]['z']))
        self.calcuations[orientation]['area'] *= np.abs(self.data_2d[orientation]['x'][0][1]-self.data_2d[orientation]['x'][0][0])
        self.calcuations[orientation]['area'] *= np.abs(self.data_2d[orientation]['y'][1][0]-self.data_2d[orientation]['y'][0][0])
        self.calcuations[orientation]['area']

        if orientation == 'back':
            self.calcuations[orientation]['area'] *= -1
