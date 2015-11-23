#!/usr/bin/env python
#coding:utf8

import io
import os
import time
import sys, signal
import threading
import traceback
from Queue import Queue, Empty
import settings
import fnmatch

swdebug = True
if hasattr(settings, "swdebug"):
	swdebug = settings.swdebug

class Test(threading.Thread):
	station = 0
	file = None

	exception = None
	stack = ''

	lock = threading.Lock()
	lock_exception = threading.Lock()
	ecode = 0
	status = 'READY'
	barcode = ''
	dfpath = ''

	#for test duration calculation
	start_time = 0
	duration = "&nbsp;"

	#..
	flag_stop = False

	def __init__(self, tester, station = 0):
		threading.Thread.__init__(self)
		self.tester = tester
		self.station = station

	def __del__(self):
		if self.file != None:
			self.file.close()

	def get(self, attr_name, val_def = None):
		self.lock.acquire()
		value = getattr(self, attr_name, val_def)
		self.lock.release()
		return value

	def set(self, attr_name, value):
		self.lock.acquire()
		setattr(self, attr_name, value)
		self.lock.release()

	def run(self):
		try:
			test_mode = self.tester.get("test_mode")
			while True:
				if test_mode == "AUTO":
					stop = self.tester.RequestTest(self)
					if stop:
						break

					subdir = self.model.name + "/" + time.strftime("%Y-%m-%d")
					fname = time.strftime("%H-%M-%S_")+self.getBarcode()+".dat"
					fpath = self.getPath(subdir, fname)
					self.Start(fpath)
					self.check_passed = True
					self.Test()

				elif test_mode == "STEP":
					subdir = self.model.name + "/" + time.strftime("%Y-%m-%d")
					fname = time.strftime("%H-%M-%S_STEP")+".dat"
					fpath = self.getPath(subdir, fname)
					self.Start(fpath)
					self.check_passed = True
					self.Test()
					break

				else:
					stop = self.tester.RequestTest(self)
					if stop:
						break

					subdir = self.model.name + "/" + time.strftime("%Y-%m-%d")
					fname = time.strftime("%H-%M-%S_CAL")+".dat"
					fpath = self.getPath(subdir, fname)
					self.Start(fpath)
					self.check_passed = True
					self.Calibrate()
					break

		except Exception as e:
			self.lock_exception.acquire()
			self.exception = e
			self.stack = ''.join(traceback.format_exception(*sys.exc_info()))
			self.lock_exception.release()

	def update(self):
		time.sleep(0.001) #to avoid cpu usage too high

	def mdelay(self, ms):
		now = time.time();
		now = now + ms / 1000.0
		while time.time() < now:
			self.update()

	def getPath(self, subdir=None, fname=None):
		#return full data file path according to specified fname
		path = self.tester.db.get('cfg_get')("dat_dir")
		if subdir:
			path = os.path.join(path, subdir)
		if fname:
			path = os.path.join(path, fname)
		return path

	def log_start(self, path):
		if self.file != None:
			self.file.close()
		#print path
		dir = os.path.dirname(path)
		if dir and not os.path.isdir(dir):
			os.makedirs(dir)
		self.file = open(path, 'w')

	def log(self, info, passed=None):
		#line = "%s#  %-48s"%(time.strftime('%X'), info)
		#line = "%s#  %-48s"%(self.getDuration(), info)
		line = "%-48s"%info
		if passed == True:
			line = line + " [PASS]"
		elif passed == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + "\n"
		self.file.write(line)
		self.file.flush()

	def Record(self, barcode):
		pass

	def verifyBarcode(self, barcode):
		emsg = None
		if not settings.swdebug:
			if len(barcode) < 16:
				emsg = "Plese Scan 2D Barcode"
		else:
			barcode = int(barcode)
			if barcode < 195000:
				emsg = "Plese Scan 2D Barcode"
		return emsg

	def setBarcode(self, barcode):
		self.set("barcode", barcode)

	def getBarcode(self):
		return self.get("barcode")

	def Start(self, dfpath=None):
		self.set("start_time", time.time())
		self.set("duration", "&nbsp;")
		self.set("ecode", 0)
		self.set("status", "TESTING")
		self.set("dfpath", os.path.abspath(dfpath))
		if dfpath:
			self.log_start(dfpath)

	def wait_uut_remove(self, signal = "PASS"):
		if not swdebug:
			self.tester.fixture.get("Signal")(self.station, signal)

		deadline = time.time() + 3
		while True:
			if settings.enable_sensor_ue:
				ue = self.tester.fixture.get("IsUutPresent")(self.station)
				if not ue:
					break
			else:
				if deadline > time.time():
					break

	def Pass(self):
		self.set("duration", self.getDuration())
		self.set("start_time", 0)

		test_mode = self.tester.get("test_mode")
		self.set("status", "PASS")
		if test_mode is not "STEP":
			#wait...until uut been removed
			#:( who can notice me when uut is removed
			self.wait_uut_remove("PASS")

		if test_mode == "AUTO":
			self.Record()

			#now, uut is removed
			self.set("barcode", '')
			self.set("dfpath", '')

	def Fail(self, ecode = -1):
		self.set("duration", self.getDuration())
		self.set("start_time", 0)

		test_mode = self.tester.get("test_mode")
		assert ecode != 0
		self.set("ecode", ecode)
		self.set("status", "FAIL")
		if test_mode == "AUTO":
			self.Record()
			#self.wait_uut_remove("FAIL")
			self.tester.RequestWaste(self)
			self.set("barcode", '')
			self.set("dfpath", '')

	def Prompt(self, status):
		self.set("status", status)

###########method could be called by main thread ########
	def stop(self):
		self.set("flag_stop", True)

	def getDuration(self):
		start_time = self.get("start_time")
		duration = self.get("duration")
		if start_time != 0:
			duration = time.time() - start_time
			duration = "%4.01fs"%duration
		return duration



