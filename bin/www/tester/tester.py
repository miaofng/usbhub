#!/usr/bin/env python
#coding:utf8

import io
import time
import os
import sys, signal
from shell import Shell
from db import Db
from test_self import Selfcheck
from test_gft import GFTest
import random
import functools #https://docs.python.org/2/library/functools.html
import shlex #https://docs.python.org/2/library/shlex.html
import getopt #https://docs.python.org/2/library/getopt.html

class Tester:
	status = 'INIT' #'TESTING' 'PASS' 'FAIL' 'READY'
	time_start = time.time()
	time_test_start = 0
	time_test = 0
	barcode = ''
	nr_ok = 0
	nr_ng = 0
	datafile = ''
	ecode = 0

	def __init__(self, saddr):
		self.shell = Shell(saddr)
		self.shell.register("status", self.cmd_status, "display tester status")
		self.shell.register("reset", self.cmd_reset, "reset tester status to READY")
		self.shell.register("test", self.cmd_test, "test start")
		self.shell.register("stop", self.cmd_stop, "test stop")
		self.db = Db();
		self.nr_ok = int(self.db.cfg_get("nr_ok"))
		self.nr_ng = int(self.db.cfg_get("nr_ng"))
		self.test = Selfcheck(self)
		self.test.run()
		del(self.test)

	def __del__(self):
		self.shell.unregister("status")
		self.shell.unregister("reset")
		self.shell.unregister("test")
		self.shell.unregister("stop")

	def update(self):
		try:
			time.sleep(0.001) #to avoid cpu usage too high
		except:
			print 'sleep exception'
			sys.exit(0)
		self.shell.update()

	def run(self):
		while True:
			self.update()
			if hasattr(self, "test"):
				self.test.run()
				del(self.test)

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
		#convert abs path to relative path
		dat_dir = self.db.cfg_get("dat_dir")
		dat_dir = os.path.abspath(dat_dir)
		record["datafile"] = os.path.relpath(self.datafile, dat_dir)
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

	def cmd_status(self, argc, argv):
		result = {}
		result["status"] = self.status
		result["ecode"] = self.ecode
		result["runtime"] = int(self.runtime())
		result["nr_ok"] = str(self.nr_ok)
		result["nr_ng"] = str(self.nr_ng)
		result["barcode"] = self.barcode
		result["datafile"] = self.datafile
		result["testtime"] = int(self.testtime())
		result["testing"] = False
		if hasattr(self, "test"):
			result["testing"] = True
		return result

	def cmd_reset(self, argc, argv):
		result = {"error": "E_OK",}
		if(self.status == "PASS") or (self.status == "FAIL"):
			self.status = "READY"
		return result;

	def cmd_test(self, argc, argv):
		result = {"error": "E_OK",}
		del argv[0]
		try:
			opts, args = getopt.getopt(argv, "m:x:", ["mode=", "mask="])
		except getopt.GetoptError as e:
			result["error"] = str(e)
			return result

		if (len(args) > 0) and (args[0] == "help"):
			result["usage"] = 'test --mode=AUTO --mask=0 xxxyy.gft'
			return result

		if hasattr(self, "test"):
			result["error"] = "another test is running"
			return result

		#try to execute the specified test
		#print opts, args
		para = {"mode":"AUTO", "mask":0}
		for opt in opts:
			if(opt[0] == "-m" or opt[0] == "--mode"):
				para["mode"] = opt[1]
			elif (opt[0] == "-x" or opt[0] == "--mask"):
				para["mask"] = int(opt[1])

		gft = args[0]
		self.test = GFTest(self, gft, para)
		return result

	def cmd_stop(self, argc, argv):
		result = {"error": "No Test is Running",}
		if hasattr(self, "test"):
			result["error"] = "E_OK";
			self.test.stop()
		return result;

def signal_handler(signal, frame):
	print 'user abort'
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
saddr = ('localhost', 10003)
tester = Tester(saddr)
tester.run()
