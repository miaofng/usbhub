#!/usr/bin/env python
#coding:utf8
#1, shell command should be registered in main thread
#2, tester's method is thread safe
#3, instrument's lock must be acquired before calling instrument's method

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
import threading

class TesterException(Exception): pass

class Tester:
	lock = threading.Lock()
	db_lock = threading.Lock()
	time_start = time.time()
	fixture_id = "Invalid"
	fixture_pressed = "Invalid"
	status = ['INIT', 'INIT'] #'TESTING' 'PASS' 'FAIL' 'READY'
	barcode = ["", ""]
	datafile = ["", ""]
	ecode = [0, 0]
	tests = []

	def __init__(self, saddr):
		self.db = Db()
		self.shell = Shell(saddr)
		self.shell.register("status", self.cmd_status, "display tester status")
		self.shell.register("reset", self.cmd_reset, "reset tester status to READY")
		self.shell.register("test", self.cmd_test, "test start")
		self.shell.register("stop", self.cmd_stop, "test stop")
		if True:
			station0 = Selfcheck(self, {"station": 0})
			station1 = Selfcheck(self, {"station": 1})
			station0.start()
			station1.start()
			self.tests.append(station0)
			self.tests.append(station1)

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
			self.lock.acquire()
			tests = self.tests
			self.lock.release()
			for idx, test in enumerate(tests):
				if not test.isAlive():
					del tests[idx]
			self.lock.acquire()
			self.tests = tests
			self.lock.release()

	def __runtime__(self):
		seconds = time.time() - self.time_start
		return seconds;

	def cmd_status(self, argc, argv):
		result = {}
		self.lock.acquire()
		result["fixture_id"] = self.fixture_id
		result["pressed"] = self.fixture_pressed
		result["runtime"] = int(self.__runtime__())
		result["ecode"] = self.ecode
		result["status"] = self.status
		result["barcode"] = self.barcode
		result["datafile"] = self.datafile
		result["testing"] = False
		if len(self.tests) > 0:
			result["testing"] = True
		self.lock.release()
		return result

	def cmd_reset(self, argc, argv):
		result = {"error": "E_OK",}
		self.lock.acquire()
		if(self.status == "PASS") or (self.status == "FAIL"):
			self.status = "READY"
		self.lock.release()
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

		if len(self.tests) > 0:
			result["error"] = "test is runing"
			return result

		#try to execute the specified test
		#print opts, args
		para = {"mode":"AUTO", "mask":0}
		for opt in opts:
			if(opt[0] == "-m" or opt[0] == "--mode"):
				para["mode"] = opt[1]
			elif (opt[0] == "-x" or opt[0] == "--mask"):
				para["mask"] = int(opt[1])

		para["file"] = args[0]
		para["station"] = 0
		station0 = GFTest(self, para)
		para["station"] = 1
		station1 = GFTest(self, para)
		station0.start()
		station1.start()
		self.tests = [station0, station1]
		return result

	def cmd_stop(self, argc, argv):
		result = {"error": "OK",}
		for test in self.tests:
			result["error"] = "E_OK";
			test.stop()
		return result;

###########thread safe method##########
	def getDB(self):
		self.db_lock.acquire()
		db = self.db
		self.db_lock.release()
		return db

	#to be called by test routine
	def start(self, datafile, station = 0):
		self.lock.acquire()
		self.ecode[station] = 0
		self.status[station] = "TESTING"
		self.datafile[station] = os.path.abspath(datafile)
		self.lock.release()

	def finish(self, status, station = 0):
		self.lock.acquire()
		self.status[station] = status
		self.lock.release()

	def save(self, record, station = 0):
		#convert abs path to relative path
		dat_dir = self.getDB().cfg_get("dat_dir")
		dat_dir = os.path.abspath(dat_dir)

		self.lock.acquire()
		if self.status[station] != "PASS" and self.status[station] != "FAIL":
			#only test pass or fail are recorded in database
			self.lock.release()
			return

		record["barcode"] = self.barcode[station]
		record["runtime"] = self.__runtime__()
		record["failed"] = self.ecode[station]
		record["datafile"] = os.path.relpath(self.datafile[station], dat_dir)
		record["station"] = station;
		self.lock.release()
		self.getDB().test_add(record)

	def passed(self, station=0):
		self.finish("PASS", station)

	def failed(self, station=0, ecode = -1):
		if ecode != 0:
			self.lock.acquire()
			self.ecode[station] = ecode
			self.lock.release()
		self.finish("FAIL", station)

	def barcode_get(self, station=0):
		#self.test.mdelay(1000)
		barcode = str(random.randint(15200,99000))
		self.lock.acquire()
		self.barcode[station] = barcode;
		self.lock.release()
		return barcode

	def wait_fixture(self, station=0):
		#self.test.mdelay(500)
		pass

def signal_handler(signal, frame):
	print 'user abort'
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
saddr = ('localhost', 10003)
tester = Tester(saddr)
tester.run()
