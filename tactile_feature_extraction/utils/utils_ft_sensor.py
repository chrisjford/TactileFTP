import NetFT, Pyro4, time
from threading import Thread, Lock

@Pyro4.expose
class ATIMINI(object):
    def __init__(self):
        self.ip = '192.168.1.1'
        self.FT18690 = NetFT.Sensor(self.ip)
        print('Connected to ATI Mini 40')
        self.calibrate()

        self.FxNewtons = None
        self.FyNewtons = None
        self.FzNewtons = None

        self.threadRun = False
        self.gatherData = False

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print('Exiting...')
        self.close()

    def start(self):
        self.FT18690.startStreaming(handler=True)
        print('FT Stream Started.')

        self.dataThread = Thread(None, self.__dataStream__, daemon=True)
        self.threadRun = True
        self.gatherData = True
        self.dataThread.start()
        print('Data stream started')

    def calibrate(self):
        print('Calibrating sensor...')
        self.FT18690.tare(1000) #   Subtracts the mean average of 1000 samples from new data to
        print('Calibration complete')
    
    def tare(self):
        print('Calibrating sensor...')
        self.gatherData = False
        self.FT18690.stopStreaming()
        lock.acquire()
        self.FT18690.tare(n=10) 
        print('Calibration complete')
        lock.release()
        time.sleep(0.5)
        self.FT18690.startStreaming(handler=True)
        self.gatherData = True

    def __dataStream__(self):
        while self.threadRun:
            if self.gatherData:
                try:
                    measurement = self.FT18690.measurement()  # Get a single sample of all data Fx, Fy, Fz, Tx, Ty, Tz returned as list[6]
                    # Write Data to class variables:
                    lock.acquire()
                    self.FxNewtons = measurement[0]/1000000
                    self.FyNewtons = -1*(measurement[1]/1000000)
                    self.FzNewtons = -1*(measurement[2]/1000000)
                    lock.release()
                except:
                    print('issue with datastream, closing...')
                    self.stop()     
            
    def read(self):
        lock.acquire()
        data = [self.FxNewtons, self.FyNewtons, self.FzNewtons]
        lock.release()
        return data
        
    def stop(self):
        print('Stopping FT stream...')
        self.FT18690.stopStreaming()

        print('Closing datastream...')
        self.threadRun = False
        self.dataThread.join()
        print('Datastream thread joined sucessfully.')

    def close(self):
        self.stop()

hostname = "127.0.0.1"
lock = Lock()

with Pyro4.Daemon(hostname) as daemon:
    ns = Pyro4.locateNS()
    uri = daemon.register(ATIMINI)
    ns.register("ATIMINI", uri)

    print("FT Service Running - press CTRL+C to stop.")
    daemon.requestLoop() 