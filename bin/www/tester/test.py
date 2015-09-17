#!/usr/bin/env python
#coding:utf8

import io
import os
import time
import sys, signal
import threading
from Queue import Queue, Empty

class Test(threading.Thread):
	lock = threading.Lock()
	log_file = None
	flag_stop = False

	def __init__(self, tester, station = 0):
		threading.Thread.__init__(self)
		self.tester = tester
		self.station = station

	def __del__(self):
		if self.log_file != None:
			self.log_file.close()

	def update(self):
		pass

	def log_start(self, path):
		if self.log_file != None:
			self.log_file.close()
		#print path
		dir = os.path.dirname(path)
		if dir and not os.path.isdir(dir):
			os.makedirs(dir)
		self.log_file = open(path, 'w')

	def log(self, info, type=None):
		line = "%s#  %s"%(time.strftime('%X'), info)
		if type == True:
			line = line + " [PASS]"
		elif type == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + "\n"
		self.log_file.write(line)
		self.log_file.flush()

	def mdelay(self, ms):
		now = time.time();
		now = now + ms / 1000.0
		while time.time() < now:
			self.update()

###########method could be called by main thread ########
	def stop(self):
		self.lock.acquire()
		self.flag_stop = True
		self.lock.release()



