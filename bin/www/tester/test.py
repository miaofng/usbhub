#!/usr/bin/env python
#coding:utf8

import io
import os
import time
import sys, signal

class Test:
	log_file = None

	def __init__(self, tester):
		self.flag_stop = False
		self.tester = tester

	def __del__(self):
		if self.log_file != None:
			self.log_file.close()

	def update(self):
		self.tester.update()

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

	def stop(self):
		self.flag_stop = True



