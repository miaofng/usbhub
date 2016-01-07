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

class Db(Db):
	def model_get(self, name):
		sql = 'SELECT * FROM model WHERE name = "%s"'%name
		records = self.query(sql)
		if len(records) > 0:
			record = records[0]
			return record

class GFTst(Test):
	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		#test --test=gft --mode=AUTO --mask=0 --user=nf xxx.gft
		gft_path = opts["args"][0]
		gft_fname = os.path.split(gft_path)[1]
		[model, ext] = os.path.splitext(gft_fname)
		self.gft = gft_path
		self.model = model

		mask = None
		if "mask" in opts:
			mask = int(opts["mask"])

		self.mask = mask

		self.scanner = tester.instrument_get("scanner")
		#self.fixture = tester.instrument_get("fixture")

		self.gvm = gvm = Gvm(tester.db, mask)
		self.dmm = tester.instrument_get("dmm")
		self.irt = tester.instrument_get("irt")
		gvm.Connect(self.irt, self.dmm)

		def log(info, passed = None):
			self.log(info, passed)
		gvm.log = log

	def onStart(self):
		#wait for scan_ready signal
		while True:
			self.mdelay(0)
			ready = self.fixture.scan_IsReady()
			if ready:
				break

		barcode = self.scanner.read()

		#compare the barcode with template ????
		#in case not matched, abort the test to avoid tester destroy
		if barcode:
			self.set("barcode", barcode)
			barcode = barcode

		if barcode:
			self.fixture.scan_Pass()
		else:
			self.fixture.scan_Fail()
			return

		#wait for tester ready signal
		while True:
			self.mdelay(0)
			ready = self.fixture.IsReady()
			if ready:
				break

	def onPass(self):
		#wait until scan ready signal
		while True:
			self.mdelay(0)
			ready = self.fixture.scan_IsReady()
			if ready:
				break

	def onFail(self):
		#wait until scan ready signal
		while True:
			self.mdelay(0)
			ready = self.fixture.scan_IsReady()
			if ready:
				break

	def Run(self):
		self.gvm.load(self.gft)
		return self.gvm.Run()
