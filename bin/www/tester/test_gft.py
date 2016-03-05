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
		if self.mode == "AUTO":
			width_mm = self.dbmodel["track"]
			if len(width_mm.strip()) > 0:
				width_mm = float(width_mm)
				self.fixture.track(width_mm)

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
		barcode = self.scanner.read(1)
		if barcode == "":
			barcode = "No Barcode"

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
		quotes = re.compile("\{[^{}]+}").findall(zpl)
		for quote in quotes:
			if quote not in ["{sub}"]:
				matched = pattern.match(quote)
				if matched:
					tag = matched.group("tag")
					exp = matched.group("exp")
					s = time.strftime(exp)

					if tag == "0d":
						barcode = s = s % sn
					if tag == "1d":
						barcode = s = s % sn
					if tag == "2d":
						barcode = s = s % sn

					if exp == "mdl":
						s = self.model
					if exp == "wsn": #work station number
						s = "090"

					#replace all
					zpl = re.compile(quote).subn(s, zpl)[0]

		self.label = zpl
		self.set("barcode", barcode)
		return barcode

	def onStart(self):
		ready = self.fixture.IsReadyForTest()
		if ready:
			self.tester.alert("Please Remove UUT!")

		self.wait("IsReadyForScan")
		#self.tester.alert()
		label_setting = int(self.dbmodel["printlabel"])
		if label_setting & 0x01 == 0x01:
			barcode = self.barcode_scan()

		if label_setting & 0x02 == 0x02:
			sn = self.tester.db.sn_get(self.model)
			zpl = self.dbmodel["zpl"]
			barcode = self.barcode_generate(zpl, sn)

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
		label_setting = int(self.dbmodel["printlabel"])
		if (label_setting & 0x02 == 0x02) and self.printer:
			nrow = self.dbmodel["nrow"]
			ncol = self.dbmodel["ncol"]
			nsub = int(nrow) * int(ncol)
			for i in range(nsub):
				sub_name = chr(ord('A')+i)
				label = re.compile("{sub}").subn(sub_name, self.label)[0]
				self.printer.print_label(label)
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
