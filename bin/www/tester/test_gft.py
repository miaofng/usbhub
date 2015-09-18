#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random
import os
import json

class GFTest(Test):
	dat_dir = ""
	station = 0
	spec = ""

	def __init__(self, tester, config):
		Test.__init__(self, tester)
		self.spec = config["file"]
		self.station = config["station"]

		dat_dir = self.tester.getDB().cfg_get("dat_dir")
		self.dat_dir = os.path.join(dat_dir, time.strftime("%Y-%m-%d"))
		fname = "%d_%s"%(self.station, time.strftime("%H_%M.dat"))
		self.path = os.path.join(self.dat_dir, fname)
		self.log_start(self.path)

	def update(self):
		Test.update(self)
		#add specified update here
		#...

	def precheck(self):
		#file format check
		tail = os.path.split(self.spec)[1]
		[head, ext] = os.path.splitext(self.spec)
		ok_ext = (ext == ".py")
		self.log(self.spec)
		self.log("Checking File EXT Name ...", ok_ext)

		#query the model config in sqlite
		model = os.path.basename(head)
		self.log("model: %s"%model)
		self.model = model

		ok_gft = os.path.isfile(self.spec)
		self.log("Checking File Existence ...", ok_gft)
		return ok_ext

	def run(self):
		if self.precheck() == False:
			self.tester.start(self.path, self.station)
			self.log("Test Abort!!!")
			self.tester.failed(self.station)
			return

		while True:
			#1, wait for barcode ready
			barcode = self.tester.barcode_get(self.station)
			self.mdelay(500*self.station)
			if self.flag_stop:
				self.log("Test Abort by usr!!!")
				self.tester.failed(self.station)
				return

			self.path = os.path.join(self.dat_dir, time.strftime("%H_%M_")+barcode+".dat")
			self.tester.start(self.path, self.station)
			self.log_start(self.path)

			#2, wait for fixture ready
			self.tester.wait_fixture(self.station)

			#3, test start
			for i in range(0, 1000):
				self.mdelay(5)
				err = random.random()
				line = "R%04d = %.3fohm"%(i, err*10)
				self.log(line, err<0.6)
				if self.flag_stop:
					self.log("Test Abort by usr!!!")
					self.tester.failed(self.station)
					return

			self.tester.failed(self.station)
			self.tester.save({"model":self.model,}, self.station)
			self.mdelay(2000)


#module self test
if __name__ == '__main__':
	test = GFTest("", {"gft":"*.gft", "mode":"AUTO", "mask":0})





