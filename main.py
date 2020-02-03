from picamera.array import PiRGBArray
from picamera import PiCamera
import argparse
import warnings
import datetime
import imutils
import json
import time
import cv2
import copy
import RPi.GPIO as GPIO
GPIO.setmode(GPIO.BOARD)
GPIO.setup(12,GPIO.OUT) #servo
GPIO.setup(8,GPIO.OUT) #8 = direction
GPIO.setup(10,GPIO.OUT) #10 = step

# Start the pump
pwm=GPIO.PWM(12,100)
pwm.start(17)
ap = argparse.ArgumentParser()
ap.add_argument("-c", "--conf", required=True,
help="path to the JSON configuration file")
args = vars(ap.parse_args())
warnings.filterwarnings("ignore")
conf = json.load(open(args["conf"]))
camera = PiCamera()
camera.resolution = tuple(conf["resolution"])
camera.framerate = conf["fps"]
rawCapture = PiRGBArray(camera, size=tuple(conf["resolution"]))
print "[INFO] warming up..."
time.sleep(conf["camera_warmup_time"])
avg = None
pos = 20

# camera starting
for f in camera.capture_continuous(rawCapture, format="bgr", use_video_port=True):
frame = f.array
frame = imutils.resize(frame)
gray = cv2.cvtColor(frame, cv2.COLOR_BGR2GRAY)
gray = cv2.GaussianBlur(gray, (21, 21), 0)
if avg is None:
print "[INFO] starting background model..."
avg = gray.copy().astype("float")
rawCapture.truncate(0)
continue
frameDelta = cv2.absdiff(gray, cv2.convertScaleAbs(avg))
thresh = cv2.threshold(frameDelta, conf["delta_thresh"], 255,
cv2.THRESH_BINARY)[1]
thresh = cv2.dilate(thresh, None, iterations=2)
_,contours,_=cv2.findContours(thresh.copy(),cv2.RETR_EXTERNAL,cv2.CHAIN_APPRO
X_SIMPLE)
(height, width)= thresh.shape[:2]
min_x, min_y = width, height
max_x = max_y = 0
for c in contours:
if cv2.contourArea(c) < 1000:
continue
(x,y,w,h) = cv2.boundingRect(c)
cv2.rectangle(frame, (x, y), (x+w, y+h), (255, 0, 0), 2)
c_y = 16 + ((height-(y + h/2)) / (height/3))
c_x = int((x + w/2) / (width / 40))

# servo & step motor move
pwm.ChangeDutyCycle(c_y)
if pos > c_x:
num_steps = pos - c_x
GPIO.output(8, GPIO.LOW)
while num_steps > 0:
GPIO.output(10, GPIO.HIGH)
GPIO.output(10, GPIO.LOW)
num_steps -= 1
time.sleep(0.0001)
pos = copy.copy(c_x)
elif pos < c_x:
num_steps = c_x - pos
GPIO.output(8, GPIO.HIGH)
while num_steps > 0:
GPIO.output(10, GPIO.HIGH)
GPIO.output(10, GPIO.LOW)
num_steps -= 1
time.sleep(0.0001)
pos = copy.copy(c_x)
else:
pass

# show capture
if conf["show_video"]:
cv2.imshow("Security Feed", frame)
cv2.imshow("Security Feed1", thresh)
key = cv2.waitKey(1) & 0xFF
if key == ord("q"):
break
rawCapture.truncate(0)
pwm.stop()
GPIO.cleanup()
