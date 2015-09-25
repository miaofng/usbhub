#!/usr/bin/env python
#coding:utf8

import io
import os
import time
import sys, signal
import threading
import traceback
from Queue import Queue, Empty

class Test(threading.Thread):
	station = 0
	file = None

	exception = None
	stack = ''

	lock = threading.Lock()
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

	def run(self):
		try:
			self.Test()
		except Exception as e:
			self.exception = e
			self.stack = ''.join(traceback.format_exception(*sys.exc_info()))

	def update(self):
		time.sleep(0.001) #to avoid cpu usage too high

	def mdelay(self, ms):
		now = time.time();
		now = now + ms / 1000.0
		while time.time() < now:
			self.update()

	def getPath(self, subdir=None, fname=None):
		path = self.tester.getDB().cfg_get("dat_dir")
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
		line = "%s#  %s"%(time.strftime('%X'), info)
		if passed == True:
			line = line + " [PASS]"
		elif passed == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + "\n"
		self.file.write(line)
		self.file.flush()

	def setBarcode(self, barcode):
		self.lock.acquire()
		self.barcode = barcode
		self.lock.release()

	def getBarcode(self):
		self.lock.acquire()
		barcode = self.barcode
		self.lock.release()
		return barcode

	def Start(self, dfpath=None):
		self.lock.acquire()
		self.ecode = 0
		self.status = "TESTING"
		self.dfpath = os.path.abspath(dfpath)
		self.lock.release()
		if dfpath:
			self.log_start(dfpath)

	def Pass(self):
		self.lock.acquire()
		self.status = "PASS"
		self.lock.release()

	def Fail(self, ecode = -1):
		assert ecode != 0
		self.lock.acquire()
		self.ecode = ecode
		self.status = "FAIL"
		self.lock.release()

	def Prompt(self, status):
		self.lock.acquire()
		self.status = status
		self.lock.release()

###########method could be called by main thread ########
	def stop(self):
		self.lock.acquire()
		self.flag_stop = True
		self.lock.release()



