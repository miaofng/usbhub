#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
from test import Test
import random
from db import Db
import os
import json

class GFTest(Test):
	def __init__(self, tester, gft, para):
		Test.__init__(self, tester)
		self.gft = gft
		self.mask = para["mask"]
		self.mode = para["mode"]

		self.db = Db();
		dat_dir = self.db.cfg_get("dat_dir")
		self.dat_dir = os.path.join(dat_dir, time.strftime("%Y-%m-%d"))
		self.path = os.path.join(self.dat_dir, time.strftime("%H_%M.dat"))
		self.log_start(self.path)

	def update(self):
		Test.update(self)
		#add gft specified update here
		#...

	def precheck(self):
		#file format check
		tail = os.path.split(self.gft)[1]
		[head,ext] = os.path.splitext(self.gft)
		if ext != ".gft":
			self.log("Checking File EXT Name ...", False)
			return False

		if not os.path.isfile(self.gft):
			self.log(self.gft)
			self.log("Checking File Existence ...", False)
			return False

		#query the model config in sqlite
		model = os.path.basename(head)
		self.model = self.db.model_get(model)
		if self.model == None:
			self.log(model)
			self.log("Searching Model Configuration ...", False)
			return False

		#checking the barcode configuration
		self.barcode_config = json.loads(self.model["barcode"])
		return True

	def run(self):
		if self.precheck() == False:
			self.tester.start(self.path)
			self.log("Test Abort!!!")
			self.tester.failed()
			return

		while True:
			#1, wait for barcode ready
			barcode = self.tester.barcode_get()
			self.path = os.path.join(self.dat_dir, time.strftime("%H_%M_")+barcode+".dat")
			self.log_start(self.path)

			#2, wait for fixture ready
			self.tester.wait_fixture()

			#3, test start
			self.tester.start(self.path)
			for i in range(0, 1000):
				self.mdelay(5)
				err = random.random()
				line = "R%04d = %.3fohm"%(i, err*10)
				self.log(line, err<0.6)
				if self.flag_stop:
					self.log("Test Abort!!!")
					self.tester.failed()
					return

			self.tester.failed()


#module self test
if __name__ == '__main__':
	test = GFTest("", {"gft":"*.gft", "mode":"AUTO", "mask":0})





