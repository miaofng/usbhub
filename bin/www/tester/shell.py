#!/usr/bin/env python
#coding:utf8
import sys
from nbstreamreader import NonBlockingStreamReader
from server import Server
import getopt #https://docs.python.org/2/library/getopt.html
import time
import json
from test import Test
from test_gft import GFTest
import shlex

class Shell:
	def __init__(self, tester, saddr):
		self.tester = tester
		self._nbsr = NonBlockingStreamReader(sys.stdin)
		self._server = Server(saddr)
		print "> ",

	def update(self):
		req = {}
		line = self._nbsr.readline()
		if line:
			req["sock"] = 0
			req["data"] = line
			self.process(req)
		else:
			req = self._server.recv()
			if req:
				self.process(req)

	def process(self, req):
		try:
			cmdline = shlex.split(req["data"]);
		except ValueError as e:
			self.response(req, {"error": str(e), })
		else:
			req['cmdline'] = cmdline
			if len(cmdline) > 0:
				func = "cmd_%s"%cmdline[0]
				if hasattr(self, func):
					func = getattr(self, func)
					data = func(req)
					self.response(req, data)

		if req["sock"] == 0:
			print "\r> ",

	def response(self, req, data):
		if req["sock"]:
			req["data"] = json.dumps(data)
			self._server.send(req)
		else:
			for key in data.keys():
				print "%s	: %s"%(key, data[key])

	def cmd_status(self, req):
		result = {}
		result["testing"] = False
		result["status"] = self.tester.status
		result["runtime"] = int(self.tester.runtime())
		result["nr_ok"] = str(self.tester.nr_ok)
		result["nr_ng"] = str(self.tester.nr_ng)
		result["barcode"] = self.tester.barcode
		result["datafile"] = self.tester.datafile
		if hasattr(self.tester, "test"):
			result["testing"] = True

		seconds = self.tester.testtime()
		if seconds != None:
			result["testtime"] = int(seconds)

		return result

	def cmd_test(self, req):
		result = {"error": "E_OK",}
		argvs = req["cmdline"]
		del argvs[0]
		try:
			opts, args = getopt.getopt(argvs, "m:x:", ["mode=", "mask="])
		except getopt.GetoptError as e:
			result["error"] = str(e)
			return result

		if (len(args) > 0) and (args[0] == "help"):
			result["usage"] = 'test --mode=AUTO --mask=0 xxxyy.gft'
			return result

		if hasattr(self.tester, "test"):
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
		self.tester.test = GFTest(self.tester, gft, para)
		return result

	def cmd_stop(self, req):
		result = {"error": "No Test is Running",}
		if hasattr(self.tester, "test"):
			result["error"] = "E_OK";
			self.tester.test.stop()
		return result;
