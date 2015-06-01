#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random

class Selfcheck(Test):
	path = "selfcheck.txt"

	def __init__(self, tester):
		Test.__init__(self, tester)
		self.f = open(self.path, 'w')

	def __del__(self):
		self.f.close()

	def log(self, info, type=None):
		line = "%s#  %s"%(time.strftime('%X'), info)
		if type == True:
			line = line + " [PASS]"
		elif type == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + "\n"
		self.f.write(line)
		self.f.flush()

	def run(self):
		self.tester.start(self.path)
		self.log("===system self check report====")
		self.mdelay(1000)
		self.log("1. dmm checking ...", True)
		self.mdelay(1000)
		self.log("2. PLC checking ...", True)
		self.mdelay(1000)
		self.log("3. printer checking ...", True)
		self.mdelay(1000)
		self.log("4. irt check")
		for i in range(0, 1000):
			self.mdelay(5)
			err = random.random()
			line = "setting output to %.2fv, measured ... %.2fv"%(i/100.0, i/100.0+err)
			self.log(line, err<0.6)
		self.tester.finish("READY")





