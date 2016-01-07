#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import threading
import os
import time
import random
import functools
from pytest import *

class IRScn(Test):
	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		self.tester.shell.register("scan", self.cmd_scan, "query dgscan status")
		self.dmm = tester.instrument_get("dmm")
		self.irt = tester.instrument_get("irt")
		self.gvm = gvm = Gvm()
		gvm.Connect(self.irt, self.dmm)

		#test --test=scan slot 5
		args = self.opts["args"]
		start = 0
		lines = 0
		mode = args[0]
		if args[0] == "ZIF" or args[0] == "FZF":
			zif = int(args[1]) - 1
			start = zif * 256
			lines = 256
		elif mode == "SLOT":
			slot = int(args[1]) - 1
			start = slot * 32
			lines = 32

		report_func = {
			"PROBE"	: self.report_probe,
			"SLOT"	: self.report_zif,
			"ZIF"	: self.report_zif,
			"FZF"	: self.report_zif,
		}

		func = report_func[mode]
		gvm.report = functools.partial(func, self)

		self.scan_lock = threading.Lock()
		self.scan_over = threading.Lock()
		self.scan_status = self.status_init(mode, lines, start)

	def release(self):
		self.tester.shell.unregister("scan")

	def status_init(self, mode, bits, bpos = 0):
		bitm = None
		if bits > 0:
			words = (bits + 31) / 32
			bitm = []
			for i in range(0, words):
				bitm.append(0)

		status = {
			"mode": mode,
			"bitm": bitm,
			"bpos": bpos,
			"bits": bits,
			"curr": -1,
			"over": False,
		}
		return status

	def status_set_value(self, status, pos, val = None):
		bits = status["bits"]
		if bits > 0:
			if pos >= bits:
				pos = pos % bits

			val = val & 1
			word = pos / 32
			bpos = pos % 32
			bitm = status["bitm"]
			bitm[word] &= ~(1 << bpos)
			bitm[word] |= val << bpos

		status["curr"] = pos
		return status

	def status_set(self, status, pos):
		return self.status_set_value(status, pos, 1)

	def status_clr(self, status, pos):
		return self.status_set_value(status, pos, 0)

	def cmd_scan(self, argc, argv):
		if not hasattr(self, "scan_status"):
			return

		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		now = time.time()
		if status["over"]:
			try:
				self.scan_over.release()
			except:
				#scan is over, no more data to acquire
				del self.scan_status
				return

		return status

	def report(self, measure, result):
		self.mdelay(0)

		#Gvm.report(self.gvm, measure, result)
		A = measure["A"]
		B = measure["B"]
		result = result * 1000 / measure["mA"]
		v, unit = self.gvm.unitconv(result)
		unit += "Ohm"

		max = measure["max"]
		passed = (result <= max)

		line = "R(%4d) = %5.01f %-4s"%(A+1, v, unit)
		self.log(line, passed)

	def report_zif(self, gvm, measure, result):
		self.report(measure, result)

		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		bpos = status["bpos"]
		bits = status["bits"]

		line = measure["A"]
		passed = result < measure["max"]

		if "bus" in measure:
			bus = measure["bus"]
			if bus == 0:
				#default to pass state
				status = self.status_set(status, line - bpos)

			if not passed:
				status = self.status_clr(status, line - bpos)
		else:
			status = self.status_set_value(status, line - bpos, passed + 0)

		self.scan_lock.acquire()
		self.scan_status = status
		self.scan_lock.release()

	def fscn(self):
		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		bits = status["bits"]
		bpos = status["bpos"]
		self.gvm.fscn(bpos, bits)

	def scan(self):
		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		bits = status["bits"]
		bpos = status["bpos"]
		self.gvm.scan(bpos, bits)

	def scan_slot(self):
		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		for count in xrange(0, status["bits"]):
			v = random.randint(0, 1)
			status = self.status_set_value(status, count, v)

			self.scan_lock.acquire()
			self.scan_status = status
			self.scan_lock.release()

			self.mdelay(10)

	def report_probe(self, gvm, measure, result):
		self.report(measure, result)

		self.scan_lock.acquire()
		status = self.scan_status
		self.scan_lock.release()

		line = measure["A"]
		status = self.status_set(status, line)

		self.scan_lock.acquire()
		self.scan_status = status
		self.scan_lock.release()


	def probe(self):
		while True:
			self.gvm.probe()
			self.mdelay(100)

	def Run(self):
		self.Start(None, "../../scan.log")

		try:
			self.scan_lock.acquire()
			status = self.scan_status
			self.scan_lock.release()

			test_func = {
				"PROBE"	: self.probe,
				"SLOT"	: self.fscn,
				"ZIF"	: self.scan,
				"FZF"	: self.fscn,
			}

			mode = status["mode"]
			test = test_func[mode]
			test()

		except eTestStop:
			self.gvm.irt.pipeline(False)
			self.gvm.irt.__reset__()
			pass;

		self.scan_lock.acquire()
		self.scan_status["over"] = True
		self.scan_over.acquire()
		self.scan_lock.release()

		#blocked here!! to ensure scan result fully display
		#cmd_scan, please save me .. thanks all my life:)
		self.scan_over.acquire()
		self.scan_over.release()
