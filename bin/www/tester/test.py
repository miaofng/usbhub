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
			self.Test()
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
		line = "%s#  %-48s"%(time.strftime('%X'), info)
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
		return emsg

	def setBarcode(self, barcode):
		self.set("barcode", barcode)

	def getBarcode(self):
		return self.get("barcode")

	def Start(self, dfpath=None):
		self.set("ecode", 0)
		self.set("status", "TESTING")
		self.set("dfpath", os.path.abspath(dfpath))
		if dfpath:
			self.log_start(dfpath)

	def Pass(self):
		if not swdebug:
			self.tester.fixture.get("Signal")(self.station, "PASS")
		self.set("status", "PASS")
		self.Record()
		#:( who can notice me when uut is removed
		self.mdelay(2000)
		#now, uut is removed
		self.set("barcode", '')
		self.set("dfpath", '')

	def Fail(self, ecode = -1):
		assert ecode != 0
		self.set("ecode", ecode)
		self.set("status", "FAIL")
		self.Record()
		#self.tester.RequestWaste(self)
		self.tester.fixture.get("Signal")(self.station, "FAIL")
		self.mdelay(10000)
		self.set("barcode", '')
		self.set("dfpath", '')


	def Prompt(self, status):
		self.set("status", status)

###########method could be called by main thread ########
	def stop(self):
		self.set("flag_stop", True)



