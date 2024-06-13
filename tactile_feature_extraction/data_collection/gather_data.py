import cv2
import pickle 
import Pyro4
import os
import time

from threading import Thread, Lock

class DataGather(object):
    def __init__(self, resume, dataPath, time_series, display_image):
        # FT Sensor inits:
        self.ft = Pyro4.Proxy ('PYRONAME:ATIMINI')

        self.dataPath = dataPath
        self.time_series = time_series 
        self.display_image = display_image

        if resume == False:
            frame_folder = os.path.join(self.dataPath, f'raw_frames')
            os.makedirs(frame_folder, exist_ok=True)

            video_folder = os.path.join(self.dataPath, f'videos')
            os.makedirs(video_folder, exist_ok=True)

            timeseries_folder = os.path.join(self.dataPath, f'time_series')
            os.makedirs(timeseries_folder, exist_ok=True)

        self.framePath = f'{self.dataPath}/raw_frames'
        self.videoPath = f'{self.dataPath}/videos'
        self.timeseriesPath = f'{self.dataPath}/time_series'

        self.Fx = None
        self.Fy = None
        self.Fz = None

        self.Fx_list = []
        self.Fy_list = []
        self.Fz_list = []

        # TacTip inits:
        # Port
        self.cam = cv2.VideoCapture(1)
        if not self.cam.isOpened():
            raise SystemExit("Error: Could not open camera.")
        else:
            print("Camera captured successfully.")

        # Resolution
        self.cam.set(3, 640)
        self.cam.set(4, 480)
        # Exposure
        #self.cam.set(cv2.CAP_PROP_AUTO_EXPOSURE, 1)
        self.cam.set(cv2.CAP_PROP_EXPOSURE, -8)
        # Brightness
        #self.cam.set(cv2.CAP_PROP_BRIGHTNESS, 64)

        self.frame = None
        self.cam_ready = False
        self.i = None

        # Sampling inits:
        self.sample = 0 # Sample number
        self.sample_list = []
        
        self.start_time = time.time()
        self.out = None

        self.t = []

        self.threadRun = False
        self.log = False

    def __enter__(self):
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        print('exiting...')
        self.close()

    def start(self):
        # Start FT stream background thread
        self.ft.start()

        # Start main data logging threads
        self.imageThread = Thread(None, self.image_worker)
        self.ftThread = Thread(None, self.FT_worker)
        self.threadRun = True
        print(f'self.threadRun {self.threadRun}')
        self.imageThread.start()
        self.ftThread.start()
        print('Main thread started')
        
        time.sleep(1)

    def begin_sample(self, i):
        self.i = i

        video_folder = os.path.join(self.videoPath, f'sample_{self.i}')
        os.makedirs(video_folder, exist_ok=True)
        self.videoframesPath = video_folder
        self.log = True
    
    def stop_and_write(self):
        self.log = False
        data_keys = ["t", "Fx", "Fy", "Fz","n"]
        data_lists = [self.t, self.Fx_list, self.Fy_list, self.Fz_list, self.sample_list]
        dictionary = dict(zip(data_keys,data_lists))
        
        try:
            with open(os.path.join(self.timeseriesPath, f'sample_{self.i}.pkl'), 'wb') as handle:
                pickle.dump(dictionary, handle, protocol=pickle.HIGHEST_PROTOCOL)
            
            #FOR SINGLE FRAME CAP:
            if self.time_series == False:
                time.sleep(0.1)
                filenames = os.listdir(self.videoframesPath)
                max_value = max(int(filename.strip('frame_.png')) for filename in filenames)
                i = 0
                while i < max_value:
                    os.remove(f'{self.videoframesPath}/frame_{i}.png')
                    i=i+1
                i=0
        except:
            pass
        
        # Reset variables:
        self.t = []
        self.Fx_list = []
        self.Fy_list = []
        self.Fz_list = []
        self.sample_list = []
        self.sample = 0
        
    def FT_worker(self):
        # Worker thread which captures FT data while self.log = True
        while self.threadRun:
            if self.cam_ready and self.log:
                try:
                    data = self.ft.read()
                    self.Fx_list.append(data[0])
                    self.Fy_list.append(data[1])
                    self.Fz_list.append(data[2])
                    self.sample_list.append(self.sample)
                except:
                    pass

    def image_worker(self):
        # Worker thread which captures image data while self.log = True
        while self.threadRun:
            if self.log:
                try:
                    self.cam_ready = True
                    self.t.append(time.time())
                    success, self.frame = self.cam.read()
                    self.frame = cv2.cvtColor(self.frame, cv2.COLOR_BGR2GRAY)
                    #self.frame = cv2.resize(self.frame, (320, 180))
                    cv2.imwrite(os.path.join(self.videoframesPath, f'frame_{self.sample}.png'), self.frame)
                    if self.display_image:
                        cv2.imshow("capture", self.frame) # Display video stream
                    cv2.waitKey(1)

                    if success == False:
                        print('No image data')
                        break
                    self.sample = self.sample +1

                except:
                    self.sample = self.sample + 1
                    pass
    
    def tare_ft(self):
        self.log = False
        self.ft.tare()
        self.log = True

    def returnData(self):
        return [self.t, self.Fx_list, self.Fy_list, self.Fz_list]
            
    def stop(self):
        if self.threadRun:
            self.threadRun = False

            self.imageThread.join()
            self.ftThread.join()
            print("Main threads joined successfully")

            self.cam.release()
            print("Camera resources released")

            self.ft.stop()
            print('FT Stream closed')


    def close(self):
        self.stop()

lock = Lock()
