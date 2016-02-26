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
import re
import json

class GFTst(Test):
	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		#self.tester.shell.register("scan", self.cmd_scan, "query dgscan status")

		#test --test=gft --mode=AUTO --mask=0 --user=nf xxx.gft
		gft_path = opts["args"][0]
		self.gft = gft_path
		gft_path = gft_path.replace(".learn.gft", ".gft")
		gft_fname = os.path.split(gft_path)[1]
		[model, ext] = os.path.splitext(gft_fname)
		self.model = model

		#may be fail here in case of manual_measure
		self.dbmodel = self.tester.db.model_get(model)

		mask = None
		if "mask" in opts:
			mask = int(opts["mask"])

		self.mask = mask

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

	def barcode_scan(self):
		barcode = self.scanner.read(0)
		#if barcode == "":
		#	barcode = "mei you tiao ma"

		#show the barcode
		#print "barcode=%s"%barcode
		self.set("barcode", barcode)

		if barcode is not None:
			#compare the barcode with template ????
			#in case not matched, abort the test to avoid tester destroy
			template = self.dbmodel["barcode"]
			#print "template=%s"%template
			if not fnmatch.fnmatchcase(barcode, template):
				self.tester.alert("Barcode Error, Rescan ...")
				barcode = None

	def barcode_generate(self, zpl, sn = 0):
		#{tag:exp} or {exp}
		#tag = "0d" or "1d" or "2d"
		#exp = time.strftime() format string, like "%H:%I:%S" or "%j%y%%04d"
		pattern = re.compile(r"""
			{
				(
					(\s*(?P<tag>\S+)\s*:)
					|
				)
				\s*(?P<exp>\S+)\s*
			}
		""", re.X)

		#fetch the patterns from zpl line
		barcode = "%d" % sn
		zpl = json.loads(zpl)
		quotes = re.compile("{\S+}").findall(zpl)
		for quote in quotes:
			matched = pattern.match(quote)
			if matched:
				tag = matched.group("tag")
				exp = matched.group("exp")
				str = time.strftime(exp)

				if tag == "0d":
					barcode = str = str % sn
				if tag == "1d":
					barcode = str = str % sn
				if tag == "2d":
					barcode = str = str % sn

				#replace all
				zpl = re.compile(quote).subn(str, zpl)[0]

		self.label = zpl
		self.set("barcode", barcode)
		return barcode

	def onStart(self):
		self.fixture.mode("auto")
		ready = self.fixture.IsReadyForTest()
		if ready:
			self.tester.alert("Please Remove UUT!")

		self.wait("IsReadyForScan")
		#self.tester.alert()
		if self.dbmodel["printlabel"] == "1":
			sn = self.tester.db.sn_get(self.model)
			zpl = self.dbmodel["zpl"]
			barcode = self.barcode_generate(zpl, sn)
		else:
			while True:
				self.mdelay(0)
				barcode = self.barcode_scan()
				if barcode:
					break

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

		return barcode

	def onPass(self):
		self.fixture.test_pass()
		self.wait("IsReadyForTest", False)
		self.fixture.test_reset()
		if self.dbmodel["printlabel"] == "1" and self.printer:
			self.printer.print_label(self.label)
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
