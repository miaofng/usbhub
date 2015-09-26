#!/usr/bin/env python
#coding:utf8
#1, shell command should be registered in main thread
#2, tester's method is thread safe
#3, instrument's lock must be acquired before calling instrument's method
#4, UUT Status:
#	IDLE			(BARCODE GOT)> 			YELLOW
#	LOADING			(FIXTURE READY)>		YELLOW FLASH + GIF ANIMATION
#	TESTING			(TEST OVER)>			YELLOW
#	PASS/FAIL		(BARCODE GOT)>LOADING	GREEN/RED
#5, show gui waring dialog when:
#	a) press start button, but uut not exist
#	b) scan barcode but no test request received

import io
import time
import os
import sys, signal
from shell import Shell
from db import Db
from test_self import Selfcheck
from test_gft import GFTest
from scanner import Scanner
from fixture import Fixture
from model import Model
import settings
import random
import functools #https://docs.python.org/2/library/functools.html
import shlex #https://docs.python.org/2/library/shlex.html
import getopt #https://docs.python.org/2/library/getopt.html
import threading

swdebug = True
if hasattr(settings, "swdebug"):
	swdebug = settings.swdebug

swdebug_estop = False
if hasattr(settings, "swdebug"):
	swdebug_estop = settings.swdebug_estop

class TesterException(Exception): pass
class ThreadException(Exception):
	def __init__(self, thread):
		name = thread.getName()
		e = thread.exception
		msg = '%s Exception: %s\n\r'%(name, e.args[0])
		print >> sys.stderr, msg
		print >> sys.stderr, thread.stack
		sys.stderr.flush()

class Tester:
	lock = threading.Lock()
	db_lock = threading.Lock()
	fixture_lock = threading.Lock()
	test_lock = threading.Lock()
	waste_lock = threading.Lock()

	time_start = time.time()
	fixture_id = "Invalid"
	fixture_pressed = "Invalid"
	wastes = 0 #nr of uut inside wastebox
	stop = False
	estop = False
	threads = {0: None, 1: None}

	def __init__(self, saddr):
		self.db = Db()
		self.mode = self.db.cfg_get("Mode")

		if swdebug:
			self.RequestTest = self.vRequestTest
			self.RequestWaste = self.vRequestWaste
			self.cmd_plc = self.cmd_vplc
			self.plc_regs_ctrl = [0, 0, 0, 0]
			self.fixture_id = id = 1
		else:
			self.scanner = Scanner(settings.scanner_port)
			self.fixture = Fixture(settings.plc_port)
			id = self.fixture.GetID(0)
			id1 = self.fixture.GetID(1)
			assert id1 == id
			self.fixture_id = id

		self.fixture_pressed = self.db.fixture_get(id, "pressed")

		if True:
			station0 = Selfcheck(self, 0)
			station1 = Selfcheck(self, 1)
			station0.start()
			station1.start()
			self.threads[0] = station0
			self.threads[1] = station1

		self.shell = Shell(saddr)
		self.shell.register("status", self.cmd_status, "display tester status")
		#self.shell.register("reset", self.cmd_reset, "reset tester status to READY")
		self.shell.register("test", self.cmd_test, "test start")
		self.shell.register("stop", self.cmd_stop, "test stop")
		self.shell.register("plc", self.cmd_plc, "plc status&query")

	def __del__(self):
		self.shell.unregister("status")
		self.shell.unregister("reset")
		self.shell.unregister("test")
		self.shell.unregister("stop")

	def update(self):
		time.sleep(0.001) #to avoid cpu usage too high
		self.shell.update()

		#thread exit?
		for key in self.threads:
			thread = self.threads[key]
			if thread:
				thread.lock_exception.acquire()
				if thread.exception:
					raise ThreadException(thread)
				thread.lock_exception.release()

		#estop
		if not swdebug:
			self.estop = self.getFixture().IsEstop()
			self.wastes = self.getFixture().ReadWasteCount()
		elif swdebug_estop:
			ms = self.__runtime__()*1000
			if int(ms) % 3000 == 0:
				self.estop = random.randint(0,1)
		if self.estop:
			self.__stop__()

	def run(self):
		while True:
			self.update()

	def __runtime__(self):
		seconds = time.time() - self.time_start
		return seconds;

	def cmd_status(self, argc, argv):
		result = {}
		self.lock.acquire()
		result["fixture_id"] = self.fixture_id
		result["pressed"] = self.fixture_pressed
		result["wastes"] = self.wastes
		result["runtime"] = int(self.__runtime__())
		result["estop"] = self.estop
		self.lock.release()

		ecode = [0, 0]
		barcode = ['', '']
		status = ['READY', 'READY']
		datafile = ['', '']
		result["testing"] = self.IsTesting()

		for key in self.threads:
			test = self.threads[key]
			if test:
				test.lock.acquire()
				ecode[key] = test.ecode
				status[key] = test.status
				barcode[key] = test.barcode
				datafile[key] = test.dfpath
				test.lock.release()

		result["ecode"] = ecode
		result["status"] = status
		result["barcode"] = barcode
		result["datafile"] = datafile
		return result

#	def cmd_reset(self, argc, argv):
#		result = {"error": "E_OK",}
#		self.lock.acquire()
#		if(self.status == "PASS") or (self.status == "FAIL"):
#			self.status = "READY"
#		self.lock.release()
#		return result;

	def IsTesting(self):
		testing = False
		for key in self.threads:
			thread = self.threads[key]
			if thread:
				if thread.isAlive():
					testing = True
		return testing

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

		if self.IsTesting():
			result["error"] = "test is runing"
			return result

		self.stop = False

		#try to execute the specified test
		#print opts, args
		para = {"mode":"AUTO", "mask":0}
		for opt in opts:
			if(opt[0] == "-m" or opt[0] == "--mode"):
				para["mode"] = opt[1]
			elif (opt[0] == "-x" or opt[0] == "--mask"):
				para["mask"] = int(opt[1])

		model = Model()
		model = model.Parse(args[0])
		if model:
			station0 = GFTest(self, model, 0)
			station1 = GFTest(self, model, 1)
			station0.start()
			station1.start()
			self.threads[0] = station0
			self.threads[1] = station1
		return result

	def cmd_stop(self, argc, argv):
		result = {"error": "OK",}
		self.__stop__()
		return result;

	def __stop__(self):
		self.stop = True
		for key in self.threads:
			thread = self.threads[key]
			if thread:
				thread.stop()

	def cmd_plc(self, argc, argv):
		if argc > 1:
			inv = 0
			if argv[1] == "TLDOOR":
				#100.00(open) 100.01(close) 100.05(lamp)
				reg = 300
				msk = (1 << 0) | (1 << 5)
				inv = (1 << 1)
			elif argv[1] == "TRDOOR":
				#100.02(open) 100.03(close) 100.04(lamp)
				reg = 300
				msk = (1 << 2) | (1 << 4)
				inv = (1 << 3)
			elif argv[1] == "TLPSFL":
				#103.02(R) 103.03(G)
				reg = 303
				msk = (1 << 2) | (1 << 3)
			elif argv[1] == "TRPSFL":
				#103.00(R) 103.01(G)
				reg = 303
				msk = (1 << 0) | (1 << 1)
			else:
				val = float(argv[1])
				reg = int(val)
				bit = int(val * 100) % 100
				msk = 1 << bit

			val = self.getFixture().cio_read(reg)
			if val & (msk | inv) == msk:
				val = val ^ (msk | inv)
			else:
				val = val & ~(msk | inv)
				val = val | msk
			self.getFixture().cio_write(reg, val)
			return {"error": "OK",}
		else:
			sensors = self.getFixture().cio_read(  0, 4)
			control = self.getFixture().cio_read(300, 4)
			result = {sensors, control}
		return result

	def cmd_vplc(self, argc, argv):
		if argc > 1:
			inv = 0
			if argv[1] == "TLDOOR":
				#100.00(open) 100.01(close) 100.05(lamp)
				reg = 300
				msk = (1 << 0) | (1 << 5)
				inv = (1 << 1)
			elif argv[1] == "TRDOOR":
				#100.02(open) 100.03(close) 100.04(lamp)
				reg = 300
				msk = (1 << 2) | (1 << 4)
				inv = (1 << 3)
			elif argv[1] == "TLPSFL":
				#103.02(R) 103.03(G)
				reg = 303
				msk = (1 << 2) | (1 << 3)
			elif argv[1] == "TRPSFL":
				#103.00(R) 103.01(G)
				reg = 303
				msk = (1 << 0) | (1 << 1)
			else:
				val = float(argv[1])
				reg = int(val)
				bit = int(val * 100) % 100
				msk = 1 << bit

			reg = reg % 100
			val = self.plc_regs_ctrl[reg]
			if val & (msk | inv) == msk:
				val = val ^ (msk | inv)
			else:
				val = val & ~(msk | inv)
				val = val | msk
			self.plc_regs_ctrl[reg] = val
			return {"error": "OK",}
		else:
			sensors = []
			for i in range(0, 4):
				sensors.append(random.randint(0, 4095))
			result = {}
			result["sensors"] = sensors
			result["control"] = self.plc_regs_ctrl
		return result

###########thread safe method##########
	def getDB(self):
		self.db_lock.acquire()
		db = self.db
		self.db_lock.release()
		return db

	def getFixture(self):
		self.fixture_lock.acquire()
		fixture = self.fixture
		self.fixture_lock.release()
		return fixture

	def RequestTest(self, test):
		#to protect scan-PutUUT-start process integrity
		#blocked if request fail
		station = test.station
		self.test_lock.acquire()
		while not self.stop:
			#yellow flash
			self.getFixture().Signal(station, "OFF")
			time.sleep(0.010)
			self.getFixture().Signal(station, "BUSY")
			time.sleep(0.010)

			#uut present?
			#not self.IsUutPresent(station):

			#fixture motion enable
			barcode = self.scanner.read()
			if barcode:
				test.setBarcode(barcode)
				self.getFixture().Start(station)

			#fixture ready?
			ready = self.getFixture().IsReady(station)
			if ready:
				self.lock.acquire()
				self.fixture_pressed = self.fixture_pressed + 1
				self.lock.release()
				break

		self.test_lock.release()
		return self.stop

	def vRequestTest(self, test):
		station = test.station
		self.test_lock.acquire()
		while not self.stop:
			time.sleep(0.020)
			guess = random.randint(0,99)
			if guess > 90:
				barcode = str(random.randint(1000,9999))
				test.setBarcode(barcode)
			if guess > 98:
				self.lock.acquire()
				pressed = self.fixture_pressed + 1
				self.fixture_pressed = pressed
				self.lock.release()
				self.getDB().fixture_set(self.fixture_id, "pressed", pressed)
				break

		self.test_lock.release()
		return self.stop

	def RequestWaste(self, test):
		#to avoid WasteBox Competion
		#blocked if request fail
		station = test.station
		self.waste_lock.acquire()
		wastes = self.getFixture().ReadWasteCount()
		self.getFixture().Signal(self.station, "FAIL")
		while True:
			time.sleep(0.001)
			n = self.getFixture().ReadWasteCount()
			if n > wastes:
				assert n - wastes == 1
				break
		self.waste_lock.release()

	def vRequestWaste(self, test):
		#to avoid WasteBox Competion
		#blocked if request fail
		station = test.station
		self.waste_lock.acquire()
		time.sleep(3)
		self.lock.acquire()
		self.wastes = self.wastes + 1
		self.lock.release()
		self.waste_lock.release()

def signal_handler(signal, frame):
	print 'user abort'
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
saddr = ('localhost', 10003)
tester = Tester(saddr)
tester.run()
