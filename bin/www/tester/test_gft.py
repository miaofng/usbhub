#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random
import os
import json
import imp
import fnmatch

class GFTest(Test):
	model = None

	def __init__(self, tester, model, station = 0):
		Test.__init__(self, tester, station)
		self.model = model
		#self.fpath = config["file"]
		#self.config = imp.load_source("config", self.fpath)
		# subdir = time.strftime("%Y-%m-%d")
		# fname = "%d_%s"%(self.station, time.strftime("%H_%M.dat"))
		# dataFile = self.tester.getPath(subdir, fname)
		# self.log_start(dataFile)

	def update(self):
		Test.update(self)
		#add specified update here
		#...

	# def verifyBarcode(self, barcode):
		# if hasattr(self.model, "barcode"):
			# template = self.model.barcode
			# if not fnmatch.fnmatchcase(barcode, template):
				# emsg = []
				# emsg.append("Barcode Error")
				# emsg.append("expect: %s", template)
				# emsg.append("scaned: %s", barcode)
				# emsg = '\n\r'.join(emsg)
				# return emsg

	def Record(self):
		dat_dir = self.getPath()
		dat_dir = os.path.abspath(dat_dir)
		self.lock.acquire()
		record = {}
		record["model"] = self.model.name
		record["barcode"] = self.barcode
		record["failed"] = self.ecode
		record["datafile"] = os.path.relpath(self.dfpath, dat_dir)
		record["station"] = self.station
		self.lock.release()
		self.tester.db.get('test_add')(record)

	def Test(self):
		self.mdelay(random.randint(0,500))
		for i in range(0, 500):
			self.mdelay(5)
			err = random.random()
			line = "R%04d = %.3fohm"%(i, err*10)
			self.log(line, err<0.6)

		if random.randint(0,1):
			self.Pass()
		else:
			self.Fail()

#module self test
if __name__ == '__main__':
	test = GFTest("", {"gft":"*.gft", "mode":"AUTO", "mask":0})





