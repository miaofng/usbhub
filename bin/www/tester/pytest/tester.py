#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import time
import threading
import getopt #https://docs.python.org/2/library/getopt.html

from shell import Shell

class Tester:
	instruments = {}
	tests = {}

	flag_estop = False
	threads = {} #key is the station nr
	elock = threading.Lock()
	emsg = ''
	ecode = 0

	def instrument_add(self, name, instrument):
		assert name not in self.instruments
		self.instruments[name] = instrument
		instrument.on_event_add(self, name)

	def instrument_get(self, name):
		if name in self.instruments:
			return self.instruments[name]

	def test_add(self, name, test):
		assert name not in self.tests
		self.tests[name] = test

	def test_get(self, name):
		return self.tests[name]

	def alert(self, emsg = '', ecode = 0):
		self.elock.acquire()
		self.emsg = emsg
		self.ecode = ecode
		self.elock.release()
		return emsg

	def __init__(self, db):
		self.time_start = time.time()
		self.db = db
		n = self.db.cfg_get("nr_of_station")
		self.nr_of_station = int(n)

		saddr = db.cfg_get("server")
		saddr = saddr.split(":")
		saddr[1] = int(saddr[1])
		shell = Shell(tuple(saddr))
		self.shell = shell
		shell.register("status", self.cmd_status, "display tester status")
		shell.register("test", self.cmd_test, "run a test")
		shell.register("stop", self.cmd_stop, "stop a test")
		shell.register("exit", self.cmd_exit, "tester exit")

		ims_en = self.db.cfg_get("IMS")
		if ims_en is "1":
			pass

	def update(self):
		self.shell.update()
		for name in self.instruments:
			instrument = self.instruments[name]
			ecodes = instrument.update(self, name)
			if ecodes:
				self.alert(name, ecodes)
		for station in self.threads:
			test = self.threads[station]
			if test:
				test.update()

	def release(self):
		pass

	def run(self):
		while True:
			time.sleep(0.001)
			self.update()

	def estop(self, estop = True):
		self.flag_estop = estop

	def IsTesting(self):
		testing = False
		for key in self.threads:
			thread = self.threads[key]
			if thread:
				if thread.isAlive():
					testing = True
					break
		return testing

	def cmd_status(self, argc, argv):
		test_info = {
			0: {"status": "READY" },
			1: {"status": "READY" },
		}
		for station in self.threads:
			test = self.threads[station]
			test_info[station] = test.info()

		status = {}
		status["runtime"] = time.time() - self.time_start
		status["time"] = time.strftime("%H:%M:%S", time.localtime())
		status["date"] = time.strftime("%Y-%m-%d", time.localtime())
		status["estop"] = self.flag_estop
		status["testing"] = self.IsTesting()
		status["test"] = test_info
		status["ims_saddr"] = "off"
		status["emsg"] = self.emsg
		status["ecode"] = self.ecode
		self.alert()
		return status

	def cmd_test(self, argc, argv):
		if self.IsTesting():
			return self.alert("test is busy now")

		try:
			opt_short = "t:m:x:u:"
			opt_long = ["test=", "mode=", "mask=", "user="]
			opts, args = getopt.getopt(argv[1:], opt_short, opt_long)
		except getopt.GetoptError as e:
			cmdline = ' '.join(argv)
			return self.alert("cmd: %s .. para error"%cmdline)

		if (len(args) > 0) and (args[0] == "help"):
			return 'test --test=gft --mode=AUTO --mask=0 --user=nf xxx.gft'

		#try to execute the specified test
		#print opts, args
		name = ""
		para = {"mode":"STEP", "mask":0, "station": 0, "user": "", "args": args}
		for opt in opts:
			if(opt[0] == "-m" or opt[0] == "--mode"):
				para["mode"] = opt[1]
			elif (opt[0] == "-x" or opt[0] == "--mask"):
				para["mask"] = int(opt[1])
			elif (opt[0] == "-u" or opt[0] == "--user"):
				para["user"] = opt[1]
			elif (opt[0] == "-t" or opt[0] == "--test"):
				name = opt[1]

		if name not in self.tests:
			cmdline = ' '.join(argv)
			return self.alert("cmd: %s .. --test=???"%cmdline)

		if 0 in self.threads:
			oldtest = self.threads[0]
			oldtest.release()
			del oldtest

		Test = self.tests[name]
		test = Test(self, para)
		test.setDaemon(True)
		test.start()

		self.threads[0] = test
		return ""

	def cmd_stop(self, argc, argv):
		for station in self.threads:
			test = self.threads[station]
			test.stop()

	def cmd_exit(self, argc, argv):
		pass
