#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
from shell import Shell
from db import Db
from test_self import Selfcheck
import random

class Tester:
	status = 'INIT'
	time_start = time.time()
	time_test_start = 0
	time_test = 0
	barcode = ''
	nr_ok = 0
	nr_ng = 0
	datafile = ''
	ecode = 0

	def __init__(self, saddr):
		self._shell = Shell(self, saddr)
		self.db = Db();
		self.nr_ok = int(self.db.cfg_get("nr_ok"))
		self.nr_ng = int(self.db.cfg_get("nr_ng"))
		self.test = Selfcheck(self)
		self.test.run()

	def update(self):
		time.sleep(0.001) #to avoid cpu usage too high
		self._shell.update()

	def run(self):
		if hasattr(self, "test"):
			del self.test

		while True:
			self.update()
			if hasattr(self, "test"):
				return self.test

	def runtime(self):
		seconds = time.time() - self.time_start
		return seconds;

	def testtime(self):
		seconds = self.time_test
		if self.time_test_start != 0:
			seconds = time.time() - self.time_test_start
		return seconds

	#to be called by test routine
	def start(self, datafile):
		self.ecode = 0
		self.time_test_start = time.time()
		self.status = "TESTING"
		self.datafile = os.path.abspath(datafile)

	def finish(self, status):
		self.time_test = self.testtime()
		self.time_test_start = 0
		self.status = status
		self.save()

	def save(self):
		if self.status != "PASS" and self.status != "FAIL":
			return

		record = {}
		record["model"] = self.test.model["name"]
		record["mask"] = self.test.mask
		record["barcode"] = self.barcode
		record["runtime"] = self.runtime()
		record["duration"] = self.testtime()
		record["failed"] = self.ecode
		record["datafile"] = self.datafile
		self.db.test_add(record)

	def passed(self):
		self.nr_ok = self.nr_ok + 1
		self.finish("PASS")

	def failed(self, ecode = -1):
		if ecode != 0:
			self.ecode = ecode
		self.nr_ng = self.nr_ng + 1
		self.finish("FAIL")

	def barcode_get(self):
		self.test.mdelay(1000)
		self.barcode = str(random.randint(15200,99000))
		return self.barcode

	def wait_fixture(self):
		self.test.mdelay(500)

def signal_handler(signal, frame):
	print 'user abort'
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

#tester config
saddr = ('localhost', 10003)
tester = Tester(saddr)
while True:
	test = tester.run()
	if test:
		test.run()

