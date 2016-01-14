#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import threading
import os
import time
import random
import functools
import fnmatch
from pytest import *

class GFTst(Test):
	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		#test --test=gft --mode=AUTO --mask=0 --user=nf xxx.gft
		gft_path = opts["args"][0]
		self.gft = gft_path
		gft_path = gft_path.replace(".learn.gft", ".gft")
		gft_fname = os.path.split(gft_path)[1]
		[model, ext] = os.path.splitext(gft_fname)
		self.model = model
		model = self.tester.db.model_get(model)
		if model:
			self.barcode_template = model["barcode"]

		mask = None
		if "mask" in opts:
			mask = int(opts["mask"])

		self.mask = mask

		self.scanner = tester.instrument_get("scanner")
		self.fixture = tester.instrument_get("fixture")

		self.gvm = gvm = Gvm(tester.db, mask)
		self.dmm = tester.instrument_get("dmm")
		self.irt = tester.instrument_get("irt")
		gvm.Connect(self.irt, self.dmm)

		def log(info, passed = None, eol = "\n"):
			self.log(info, passed, eol)
		gvm.log = log

	def info(self):
		ScanStart = self.fixture.IsReadyForScan()
		TestStart = self.fixture.IsReadyForTest()

		#to be called by main thread
		self.getDuration()
		self.lock.acquire()
		info = {
			"ecode"		: self.ecode,
			"status"	: self.status,
			"barcode"	: self.barcode,
			"datafile"	: self.dfpath,
			"duration"	: self.duration,
			"ScanStart"	: ScanStart,
			"TestStart"	: TestStart,
		}
		self.lock.release()
		return info

	def wait(self, signal = None, level = True):
		print "wait for signal '%s' = %d" % (signal, level + 0)
		signal_func = getattr(self.fixture, signal)
		while True:
			self.mdelay(0)
			signal = signal_func()
			if signal ^ level: pass
			else: break

	def onStart(self):
		ready = self.fixture.IsReadyForTest()
		if ready:
			self.tester.alert("Please Remove UUT!")

		self.wait("IsReadyForScan")
		barcode = self.scanner.read(1)
		if barcode == "":
			barcode = "mei you tiao ma"

		template = self.barcode_template

		print "barcode=%s"%barcode
		print "template=%s"%template

		#show the barcode
		self.set("barcode", barcode)

		#compare the barcode with template ????
		#in case not matched, abort the test to avoid tester destroy
		if not fnmatch.fnmatchcase(barcode, template):
			barcode = None

			#:( .. show box
			emsg = []
			emsg.append("Barcode Error")
			emsg.append("expect: %s"%template)
			emsg.append("scaned: %s"%barcode)
			emsg = '\n\r'.join(emsg)

		if barcode is not None:
			self.fixture.scan_pass()
			self.wait("IsReadyForScan", False)
			self.fixture.scan_reset()
			self.wait("IsReadyForTest")
			return barcode
		else:
			self.fixture.scan_fail()
			self.wait("IsReadyForScan", False)
			self.fixture.scan_reset()
			return None

	def onPass(self):
		self.fixture.test_pass()
		self.wait("IsReadyForTest", False)
		self.fixture.test_reset()
		self.wait("IsReadyForScan")

	def onFail(self):
		self.fixture.test_fail()
		self.wait("IsReadyForTest", False)
		self.fixture.test_reset()
		self.wait("IsReadyForScan")

	def Run(self):
		model = None
		user = self.opts["user"]
		if len(user.strip()) > 0:
			model = self.model

		self.gvm.load(self.gft, model)
		return self.gvm.Run()
