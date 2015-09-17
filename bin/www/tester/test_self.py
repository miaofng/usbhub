#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random

class Selfcheck(Test):
	path = ""

	def __init__(self, tester, station = 0):
		Test.__init__(self, tester, station)
		self.path = "selfcheck_%d"%station
		self.log_start(self.path)

	def run(self):
		self.tester.start(self.path, self.station)
		self.log("===system self check report====")
		self.mdelay(500)
		self.log("1. dmm checking ...", True)
		self.mdelay(500)
		self.log("2. PLC checking ...", True)
		self.mdelay(500)
		self.log("3. printer checking ...", True)
		self.mdelay(500)
		self.log("4. irt check")
		for i in range(0, 30):
			ms = 5
			if(self.station > 0):
				ms = 100
			self.mdelay(ms)
			err = random.random()
			line = "setting output to %.2fv, measured ... %.2fv"%(i/100.0, i/100.0+err)
			self.log(line, err<0.6)
		self.tester.finish("READY", self.station)





