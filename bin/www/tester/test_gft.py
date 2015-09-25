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

	# def precheck(self):
		# # #file format check
		# # tail = os.path.split(self.fpath)[1]
		# # [head, ext] = os.path.splitext(self.fpath)
		# # ok_ext = (ext == ".py")
		# # self.log(self.fpath)
		# # self.log("Checking File EXT Name ...", ok_ext)

		# # self.log("fixture_id = %d"%self.config.fixture)

		# # #query the model config in sqlite
		# # model = os.path.basename(head)
		# # self.log("model: %s"%model)
		# # self.model = model

		# # ok_gft = os.path.isfile(self.fpath)
		# # self.log("Checking File Existence ...", ok_gft)
		# return True

	def Record(self):
		dat_dir = self.getPath()
		dat_dir = os.path.abspath(dat_dir)
		self.lock.acquire()
		record = {}
		record["model"] = self.model["name"]
		record["barcode"] = self.barcode
		record["failed"] = self.ecode
		record["datafile"] = os.path.relpath(self.dfpath, dat_dir)
		record["station"] = self.station
		self.lock.release()
		self.tester.getDB().test_add(record)

	def Test(self):
		# if self.precheck() == False:
			# self.tester.start(self.path, self.station)
			# self.log("Test Abort!!!")
			# self.tester.failed(self.station)
			# return

		while True:
			stop = self.tester.RequestTest(self)
			if stop:
				break

			subdir = time.strftime("%Y-%m-%d")
			fname = time.strftime("%H_%M_")+self.getBarcode()+".dat"
			fpath = self.getPath(subdir, fname)
			self.Start(fpath)

			self.mdelay(random.randint(0,500))
			for i in range(0, 500):
				self.mdelay(5)
				err = random.random()
				line = "R%04d = %.3fohm"%(i, err*10)
				self.log(line, err<0.6)
				if self.flag_stop:
					self.log("Test Abort by usr!!!")
					self.Fail()
					return

			if random.randint(0,1):
				self.Pass()
			else:
				self.Fail()
			self.Record()
			self.mdelay(2000)

#module self test
if __name__ == '__main__':
	test = GFTest("", {"gft":"*.gft", "mode":"AUTO", "mask":0})





