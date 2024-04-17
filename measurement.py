import pyvisa
import time
import threading

from keithley2600 import Keithley2600


class Session(threading.Thread):
    def __init__(self, file, NPLC, V_max, symmetric, iLimit, points, parent):
        threading.Thread.__init__(self)
        self.init = threading.Event()  # set if the device is connected
        self.smu: Keithley2600 = None  # source meter
        self.file = file
        self.NPLC = NPLC
        self.V_max = V_max
        if symmetric:
            self.V_min = -V_max
        else:
            self.V_min = 0
        self.iLimit = iLimit
        self.points = points
        self.parent = parent
        self.f = None  # plot window
        self.data = []
        self.alive = False

        flag = self.connect_to_device()
        if flag == 0:
            self.init.set()

    def update_plot(self, x, y):
        """
        Add a new point to the monitoring plot and update it.
        :param x: point x
        :param y: point y
        :return: -1 if plotting window is closed, 0 otherwise
        """
        flag = self.f.update_plot(x, y)
        if flag == -1:
            self.alive = False

    def connect_to_device(self, n=0):
        """
        Find available devices and connect to one of them
        :param n: index of the device
        :return:
        """
        rm = pyvisa.ResourceManager()
        devs = rm.list_resources()
        print(f'Found devices: {devs}')
        try:
            self.smu = Keithley2600(rm.open_resource(devs[n]))
        except IndexError:
            print('No device found. Please connect one.')
            return -1

        print(f'Connected to {devs[0]}')
        return 0

    def run(self):
        self.alive = True
        if self.file:
            f = open(self.file, 'w')
            f.write("#measurement started at " + str(time.ctime()) + " with Keithley 2636A")
            f.writelines(["# U ( V ) \t I ( A ) \n"])
        self.smu.output = True
        levelv = self.V_min
        self.smu.level_v = levelv
        for i in range(10):
            _, _ = self.smu.measure_iv()
        for i in range(self.points):
            if not self.alive:
                self.smu.reset_device()
                if self.file:
                    f.close()
                return
            delta_v = (self.V_max - self.V_min) / self.points
            levelv += delta_v
            self.smu.level_v = levelv
            try:
                values = self.smu.measure_iv()
            except Exception as e:
                print('Resetting instrument...', end='')
                self.smu.reset_device()
                print('done.')
                self.smu.setup_for_IV_measurement(self.iLimit, self.NPLC)
                self.smu.level_v = levelv
                break
            v = float(values[1])
            i = float(values[0])
            if self.file:
                f.writelines([str(v), '\t', str(i), '\n'])
            self.data.append([v, i])
            self.update_plot(v, i)

    def finish(self):
        self.alive = False


if __name__ == '__main__':
    # Usage: Create an instance of Session and start the measurement
    pass
