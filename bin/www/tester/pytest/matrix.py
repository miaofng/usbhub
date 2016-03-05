#!/usr/bin/env python
#coding:utf8
#linktron techology matrix driver
#miaofng@2015-8-31 initial version
#miaofng@2015-11-26 optimization for matrix pipeline mode
#
#note:
#1, RLY1 Operation Sequence:
#	CLOS - SCAN - OPEN ... OK
#	CLOS - OPEN - SCAN ... RLY1 Not Acts
#	CLOS - GRP - OPEN -... OK
#	so in pipeline mode, close+open the same relay operation
#	maybe ignored during the same scan stage
#
#2, to use pipeline mode(zero wait), you must:
#	matrix.pipeline(True) #start thread
#	matrix.switch(...) as normal, but it only adds op to queue
#	matrix.pipeline(False) #stop thread

import sys, os, signal
import serial #http://pythonhosted.org/pyserial/
import re
import functools
import time
import threading
import Queue
import copy
import ctypes
from instrument import Instrument

class MatrixIoTimeout(Exception):pass
class MatrixIoError(Exception):
	def __init__(self, cmdline, echo):
		Exception.__init__(self)
		print >> sys.stderr, "Q: %s"%cmdline
		print >> sys.stderr, "A: %s"%echo

class Matrix(Instrument):
	lock = threading.Lock()

	timeout = 3 #unit: S
	uart = None

	#<+0, No Error
	epat = re.compile(r"[\n\r]*<(?P<ecode>[+-]\d*)(,\s*(?P<emsg>[\S ]+)|)[\n\r]+$")
	last_cmd = None #record last ROUTE_XXX cmd for resend purpose

	cmdline_max_bytes = 192 #do not exceed matrix's uart dma fifo size!!!
	IRT_E_VM_OPQ_FULL = -16
	IRT_E_HV_UP = -7
	IRT_E_HV_DN = -8
	IRT_E_HV = -9

	def get(self, attr_name, val_def = None):
		if hasattr(self, attr_name):
			#self.lock.acquire()
			obj = getattr(self, attr_name, val_def)
			#self.lock.release()
			# if hasattr(obj, "__call__"):
				# def deco(*args, **kwargs):
					# self.lock.acquire()
					# retval = obj(*args, **kwargs)
					# self.lock.release()
					# return retval
				# return deco
		return obj

	def set(self, attr_name, value):
		#self.lock.acquire()
		setattr(self, attr_name, value)
		#self.lock.release()

	def release(self):
		if self.uart:
			self.query("shell -m", echo=False)
			self.uart.close()
			self.uart = None

	def __init__(self, port=None, baud=115200):
		if port is None:
			d2xx = ctypes.WinDLL("ftd2xx.dll")
			handle = ctypes.c_void_p(None)
			d2xx.FT_OpenEx("IRT", 2, ctypes.byref(handle))
			port = ctypes.c_long(-1)
			d2xx.FT_GetComPortNumber(handle, ctypes.byref(port))
			d2xx.FT_Close(handle)
			port = "COM%d"%port.value
			print "IRMATRIX: port = %s" % port

		self.uart = serial.Serial(port, baud, timeout = self.timeout)
		self.query("shell -a", echo=False)
		self.opq = Queue.Queue(500)
		self.pipeline_enable = False
		self.thread = None

	def __del__(self):
		self.pipeline(False)
		self.release()

	def pipeline(self, enable=True):
		while not self.opq.empty():
			ops = self.opq.get(True, 0.1)
			print "opt.type = %s"%ops["opt"]
			print "opt.bus = %s"%ops["bus0"]
			print "opt.line0 = %s"%ops["line0"]
			print "opt.line1 = %s"%ops["line1"]

		self.pipeline_enable = enable
		if enable:
			assert(self.thread is None)
			self.thread = threading.Thread(target=self.execute)
			self.thread.setDaemon(True)
			self.thread.start()
		else:
			if self.thread:
				self.thread.join()
				self.thread = None
	def abort(self):
		pass

	def __reset__(self):
		self.query("*RST", False)
		time.sleep(0.2)
		self.query("shell -a", echo=False)
		self.mode("OFF")

	def reset(self):
		self.open(0, 0, 63)
		self.open(1, 0, 63)
		self.open(2, 0, 63)
		self.open(3, 0, 63)

	def cls(self):
		cmdline = "*CLS"
		ecode = self.query(cmdline)
		if ecode:
			raise MatrixIoError(cmdline, self.echo)

	def err(self):
		return self.query("*ERR?")

	def arm(self, arm):
		cmdline = "ROUTE ARM %d"%arm
		ecode = self.query(cmdline)
		if ecode:
			raise MatrixIoError(cmdline, self.echo)

	def mode(self, md):
		if md != "OFF":
			cmdline = "MODE OFF"
			ecode = self.query(cmdline)
			if ecode:
				raise MatrixIoError(cmdline, self.echo)

		cmdline = "MODE %s"%md
		ecode = self.query(cmdline)
		if ecode:
			raise MatrixIoError(cmdline, self.echo)

	def mdelay(self, ms):
		cmdline = "ROUTE DELAY %d"%ms
		ecode = self.query(cmdline)
		if ecode:
			raise MatrixIoError(cmdline, self.echo)

	# def opc(self):
		# opc = False
		# if self.opq.empty():
			# opc = self.query("*OPC?")
			# print "opc=%d"%opc
			# #if opc: ?????????
			# opc = True
		# return opc

	def trig(self):
		#2047 not exist, so it's a dummy scan(trig only)
		self.scan(0, 2047)
		self.scan(1, 2047)

	def open_all_lines(self, bus = None):
		if bus is None:
			self.open(0, 0, 2047)
			self.open(1, 0, 2047)
			self.open(2, 0, 2047)
			self.open(3, 0, 2047)
		else:
			self.open(bus, 0, 2047)

	def open(self, bus0, line0, line1=None):
		return self.switch("OPEN", bus0, line0, line1)

	def close(self, bus0, line0, line1=None):
		return self.switch("CLOS", bus0, line0, line1)

	def scan(self, bus0, line0, line1=None):
		return self.switch("SCAN", bus0, line0, line1)

	def fscn(self, bus0, line0, line1=None, bus1=None):
		return self.switch("FSCN", bus0, line0, line1, bus1)

	def switch(self, opt, bus0, line0, line1=None, bus1=None):
		if bus1 is None:
			bus1 = bus0
		ops = {"opt": opt, "bus0": bus0, "line0": line0, "bus1": bus1, "line1": line1}

		#raise Queue.Full if opq full more than 0.5s
		self.opq.put(ops, True, 0.5)
		#print "OPQPUT: %d"%ops["line0"]

		#wait until matrix response or timeout exception
		if not self.pipeline_enable:
			self.execute()

	def execute(self):
		hv_ecodes = [
			self.IRT_E_HV_UP,
			self.IRT_E_HV_DN,
			self.IRT_E_HV
		]

		timeout = 0 #do not wait to avoid deadlock
		if self.pipeline_enable:
			timeout = 0.01

		ops = None
		while True:
			#get a group of ops
			last_opt = None
			cmdline = None
			paras = []
			bytes = 16 #ROUTE CLOS (@)
			while True:
				if ops is None:
					if self.opq.empty():
						time.sleep(0.001)
						break
					ops = self.opq.get(True, timeout)

				if last_opt is None:
					last_opt = ops["opt"]

				if ops["opt"] == last_opt:
					cmdline = "%02d%04d"%(ops["bus0"], ops["line0"])
					if ops["line1"] is not None:
						cmdline = cmdline + ":%02d%04d"%(ops["bus1"], ops["line1"])
					ops = None #been used

					paras.append(cmdline)
					bytes = bytes + len(cmdline) + 1 #+','
					if bytes > self.cmdline_max_bytes:
						break
				else:
					break

			ecode = None
			if cmdline:
				cmdline = ",".join(paras)
				cmdline = "ROUTE %s (@%s)"%(last_opt, cmdline)
				while True:
					ecode = self.query(cmdline, True)
					if ecode is 0:
						ecode = None
						break
					elif ecode in hv_ecodes:
						break
					elif ecode is self.IRT_E_VM_OPQ_FULL:
						continue #resend
					else:
						raise MatrixIoError(cmdline, self.echo)

			#non-pipeline mode only run once
			if not self.pipeline_enable:
				break
		#return None or hv_ecodes
		return ecode

	# def retval(self, echo):
		# match = re.search("^<[+-]\d*", echo)
		# if match is not None:
			# match = match.group()
			# if len(match) > 2:
				# ecode = int(match[1:])
				# return ecode

		# raise MatrixIoError(echo)

	def query(self, cmdline, echo=True):
		timer = time.time()
		self.lock.acquire()
		self.uart.flushInput()
		self.uart.write(cmdline + "\n\r")

		retval = None
		if echo:
			#wait until echo back or timeout
			line = self.uart.readline()
			if len(line) == 0:
				raise MatrixIoError(cmdline, "")
			self.echo = line #for debug or exception purpose
			match = re.search("^<[+-]\d*", line)
			if match is not None:
				match = match.group()
				if len(match) > 2:
					retval = int(match[1:])
				else:
					raise MatrixIoError(cmdline, echo)

		self.lock.release()
		timer = time.time() - timer
		#print "IRT: %s ... %.3f S" % (cmdline, timer)
		return retval

if __name__ == '__main__':
	def cmd_query(matrix, argc, argv):
		command = " ".join(argv)
		echo = "query: "+command + "\n\r"
		echo = echo + matrix.query(command)
		return echo

	def cmd_switch(matrix, argc, argv):
		if argc >= 3:
			op = argv[0]
			bus = int(argv[1])
			line0 = int(argv[2])
			if argc == 4:
				line1 = int(argv[3])
			else:
				line1 = None

			func = {"open": matrix.open, "close": matrix.close, "scan": matrix.scan}[op]
			ecode = func(bus, line0, line1)
			return str(ecode)+"\n\r"
		return "open/close/scan bus line\n\r"

	def cmd_test(matrix, argc, argv):
		sdelay = 0
		loops = 1
		if argc > 1:
			loops = int(argv[1])
		if argc > 2:
			sdelay = float(argv[2])

		now = time.time()
		for i in range(0, loops):
			for line in range(0, 32):
				for bus in range(0, 4):
					matrix.close(bus, line)
					if sdelay != 0:
						time.sleep(sdelay)
			for line in range(0, 32):
				for bus in range(0, 4):
					if sdelay != 0:
						time.sleep(sdelay)
					matrix.open(bus, line)
		now = time.time() - now
		now = now * 1000 / 256.0 / loops
		return "%.1fmS/operation\n\r"%now

	def cmd_pipe(matrix, argc, argv):
		sdelay = 0
		loops = 1
		if argc > 1:
			loops = int(argv[1])
		if argc > 2:
			sdelay = float(argv[2])

		ms = int(sdelay * 1000)
		echo = matrix.query("ROUTE DELAY %d"%ms)
		print "echo = %s" % echo

		now = time.time()
		matrix.pipeline(True)
		for i in range(0, loops):
			for line in range(0, 32):
				for bus in range(0, 4):
					matrix.close(bus, line)

			while not matrix.opc(): continue

			for line in range(0, 32):
				for bus in range(0, 4):
					matrix.open(bus, line)

			while not matrix.opc(): continue

		matrix.pipeline(False)
		now = time.time() - now
		now = now * 1000 / 32 / 4 / 2 / loops
		return "%.1fmS/operation\n\r"%now

	def cmd_pscn(matrix, argc, argv):
		sdelay = 0
		loops = 1
		if argc > 1:
			loops = int(argv[1])
		if argc > 2:
			sdelay = float(argv[2])

		ms = int(sdelay * 1000)
		echo = matrix.query("ROUTE DELAY %d"%ms)
		print "echo = %s" % echo

		now = time.time()
		matrix.pipeline(True)
		for i in range(0, loops):
			for line in range(0, 32):
				for bus in range(0, 4):
					matrix.scan(bus, line)

			while not matrix.opc(): continue

		matrix.pipeline(False)
		now = time.time() - now
		now = now * 1000 / 32 / 4 / loops
		return "%.1fmS/operation\n\r"%now

	def signal_handler(signal, frame):
		sys.exit(0)

	from shell import Shell
	signal.signal(signal.SIGINT, signal_handler)
	matrix = Matrix("COM3", 115200)
	saddr = ('localhost', 10003)
	shell = Shell(saddr)
	shell.register("default", functools.partial(cmd_query, matrix), "query matrix")
	shell.register("open", functools.partial(cmd_switch, matrix), "relay open")
	shell.register("close", functools.partial(cmd_switch, matrix), "relay close")
	shell.register("scan", functools.partial(cmd_switch, matrix), "relay scan")
	shell.register("test", functools.partial(cmd_test, matrix), "test")
	shell.register("pipe", functools.partial(cmd_pipe, matrix), "pipe")
	shell.register("pscn", functools.partial(cmd_pscn, matrix), "pscn")

	while True:
		shell.update()
