#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-28
#

import threading
import os
import time
import random
import numpy as np
import pandas as pd
import json
import copy
from pytest import *

class Learn(Test):
	groups = []

	def __init__(self, tester, opts):
		Test.__init__(self, tester, opts)
		#test --test=learn --user=nf xxx.gft
		gft_path = opts["args"][0]
		gft_path = gft_path.replace(".learn.gft", ".gft")
		gft_fname = os.path.split(gft_path)[1]
		[model, ext] = os.path.splitext(gft_fname)
		self.gft = gft_path
		self.model = model
		self.model_settings = self.tester.db.model_get(model)
		self.rules = self.tester.db.rules_get(model)

		self.dmm = tester.instrument_get("dmm")
		self.irt = tester.instrument_get("irt")
		self.gvm = gvm = Gvm()
		gvm.Connect(self.irt, self.dmm)

		def log(info, passed = None, eol = "\n"):
			self.log(info)
		gvm.log = log

		self.ohms = {}
		def Report(measure, result, passed = None):
			if "TRAVEL" not in measure:
				#pass test
				return

			A = measure["A"]
			B = measure["B"]
			if A not in self.ohms:
				self.ohms[A] = {}
			self.ohms[A][B] = result

			Gvm.Report(self.gvm, measure, result, passed)
		gvm.Report = Report

	def Parse(self, group, R):
		A = group["A"]
		B = group["B"]

		def rule_match(ohm):
			for idx, rule in enumerate(self.rules):
				matched = True

				min = rule["min"]
				max = rule["max"]

				if min:
					matched = matched and ohm >= min
				if max:
					matched = matched and ohm <= max
				if matched:
					return idx

			template = {
				"id"	: None,
				"name"	: "short or fuse",
				"type"	: "R",
				"i"		: "3", #100mA
				"range"	: "0", #<
				"value"	: 10.0, # = Rmax
				"min"	: None,
				"max"	: 10.0,
			}

			#oh no ... :(
			rule = copy.copy(template)
			if ohm > 10.0:
				rule["name"]	= "undefined"
				rule["i"] 		= "0" #10mA
				rule["range"]	= "5" #+/-10%
				rule["value"]	= ohm
				rule["min"]		= ohm * 0.9
				rule["max"]		= ohm * 1.1

			idx = len(self.rules)
			self.rules.append(rule)
			return idx

		for idx, line in enumerate(B):
			ohm = R[idx]
			rule_idx = rule_match(ohm)
			if not hasattr(self, "df"):
				self.df = {"A": [], "B": [], "ohm":[], "Rtyp": [], "rule": []}

			self.df["ohm"].append(ohm)
			self.df["rule"].append(rule_idx)
			rule = self.rules[rule_idx]

			self.df["A"].append(A)
			self.df["B"].append(line)
			self.df["Rtyp"].append(rule["value"])

	def Generate(self, df, path):
		gft = open(path, 'w')
		now = time.strftime("%Y/%m/%d %H:%M:%S")
		gft.write("//%s"%now + "\n")
		self.log("//%s"%now)
		gft.write("O2,6,10,11 <Continuity & Leakage>" + "\n")
		self.log("O2,6,10,11 <Continuity & Leakage>")
		gft.write("L0130010" + "\n")
		self.log("L0130010")

		A = None
		B = None
		M = None
		for i in range(len(df)):
			record = df.iloc[i]
			a = record["A"] + 1
			b = record["B"] + 1

			rule_idx = int(record["rule"])
			rule = self.rules[rule_idx]
			#R0(range)1(mS)2(mA)0(exp)020(value)
			ms_def = "0" #16mS
			m = "\nR%s%s%s0%03d"%(rule["range"], ms_def, rule["i"], int(rule["value"]))

			a = "A%d"%a
			b = "	B%d		<%.1fohm, %s(%.0fohm)>"%(b, record["ohm"], rule["name"], rule["value"])

			if m != M:
				M = m
				gft.write(M + "\n")
				self.log(M)

			if a != A:
				A = a
				gft.write(A + "\n")
				self.log(A)

			if b != B:
				B = b
				gft.write(B + "\n")
				if rule["name"] == "undefined":
					self.log(B, False)
				else:
					self.log(B)

		#isolate points
		for line in self.isolate:
			a = "A%d"%(line + 1)
			gft.write(a + "\n")
			self.log(a)

		gft.write("\n<END OF PROGRAM>")
		gft.close()

	def Run(self):
		ofs = self.model_settings["nofs"]
		pts = self.model_settings["npts"]
		lines = range(ofs, ofs + pts)

		defined_A = []
		self.gvm.load(self.gft)
		for instr in self.gvm.pmem:
			opcode = instr.group('i0')
			if opcode == "A":
				try:
					p0 = instr.group("p0")
					pin = int(p0) - 1
					assert pin >= 0
					lines.remove(pin)
					defined_A.append(pin)
				except:
					continue

		a = np.array(defined_A) + 1
		self.log("Forced A: %s"%repr(a.tolist()))
		lines = defined_A + lines
		#print lines

		ngrp = 0
		npts = 0
		groups = self.gvm.Learn(lines)
		self.log("")
		for idx, group in enumerate(groups):
			A = group["A"]
			B = group["B"]
			self.log("{A: %3d, B: %s}"%(A+1, str(np.array(B) + 1)))

			N = len(B)
			if N == 0:
				npts += 1
				if not hasattr(self, "isolate"):
					self.isolate = []
				self.isolate.append(A)
			else:
				npts += N + 1
				ngrp += 1
				R = []
				for line in B:
					R.append(self.ohms[A][line])

				#parse resistor into components
				self.Parse(group, R)

		self.log("Found %d Groups(%d points) In Total"%(ngrp, npts))
		self.log("")

		if hasattr(self, "df"):
			self.log("")
			df = pd.DataFrame(self.df)
			#self.log(repr(df))
			df = df.sort_values(["Rtyp", "A"])
			#self.log(repr(df))

			gft = self.gft.replace(".gft", ".learn.gft")
			self.Generate(df, gft)
			self.log("")
			self.log("Writing to ... %s"%gft)

		self.log("Learn Finished")
		return True

