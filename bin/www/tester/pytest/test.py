#!/usr/bin/env python
#coding:utf8

import threading
import traceback
import time
import os, sys
import fnmatch

class eTestStop(Exception):pass
class Test(threading.Thread):
	max_line_char = 58

	lock = threading.Lock()
	ecode = 0 #useful when sub board exist
	status = 'READY'
	barcode = ''
	dfpath = None
	start_time = None
	duration = "&nbsp;"
	log_file = None
	flag_stop = False

	#test except handling
	elock = threading.Lock()
	exception = None
	estack = None

	def get(self, attr_name, val_def = None):
		self.lock.acquire()
		value = getattr(self, attr_name, val_def)
		self.lock.release()
		return value

	def set(self, attr_name, value):
		self.lock.acquire()
		setattr(self, attr_name, value)
		self.lock.release()

	def getDuration(self):
		self.lock.acquire()
		duration = self.duration
		if self.start_time:
			duration = time.time() - self.start_time
			duration = "%4.01fs"%duration
		self.duration = duration
		self.lock.release()
		return duration

	def info(self):
		#to be called by main thread
		self.getDuration()
		self.lock.acquire()
		info = {
			"ecode"		: self.ecode, #0: pass, -1: fail, others: bitN @(ecode + 1) = 1 => sub N fail
			"status"	: self.status,
			"barcode"	: self.barcode,
			"datafile"	: self.dfpath,
			"duration"	: self.duration,
		}
		self.lock.release()
		return info

	def __init__(self, tester, opts = None):
		threading.Thread.__init__(self)
		self.tester = tester
		self.dat_dir = tester.db.cfg_get("dat_dir")
		self.opts = opts
		self.mode = opts["mode"]
		self.station = opts["station"]
		self.printer = tester.instrument_get("printer")
		self.scanner = tester.instrument_get("scanner")
		self.fixture = tester.instrument_get("fixture")

	def update(self):
		#to be called by main thread
		self.elock.acquire()
		e = self.exception
		stack = self.estack
		self.elock.release()
		if e:
			name = self.getName()
			print >> sys.stderr, '%s Exception:\n\r'%(name)
			print >> sys.stderr, self.estack
			sys.stderr.flush()
			self.tester.release()
			sys.exit(0)

	def mdelay(self, ms = 0):
		now = time.time();
		now = now + ms / 1000.0
		while True:
			time.sleep(0.001) #to avoid cpu usage too high
			stop = self.get("flag_stop")
			if stop:
				raise eTestStop

			if time.time() >= now:
				break

	def getPath(self, subdir="", fname=""):
		path = os.path.join(self.dat_dir, subdir, fname)
		return path

	def log_start(self, path):
		if self.log_file:
			self.log_file.close()
		#print path
		dir = os.path.dirname(path)
		if dir and not os.path.isdir(dir):
			os.makedirs(dir)
		self.log_file = open(path, 'w')

	def log(self, info="", passed=None, eol = "\n"):
		if self.printer:
			self.printer.print_line(info, passed)

		#line = "%s#  %-48s"%(time.strftime('%X'), info)
		#line = "%s#  %-48s"%(self.getDuration(), info)

		foldback = False
		if foldback:
			while True:
				suffix = ""
				line = info[:self.max_line_char]
				info = info[self.max_line_char:]
				if len(info) == 0:
					suffix = {None: '', True: "    [PASS]", False: "    [FAIL]"}
					suffix = suffix[passed]

					if len(suffix) > 0:
						#line = "%-64s"%info
						format = "%%-%ds"%self.max_line_char
						line = format % line

				line = line + suffix + eol
				if self.log_file:
					self.log_file.write(line)
				else:
					print line,

				if len(info) == 0:
					break
		else:
			suffix = {None: '', True: "    [PASS]", False: "    [FAIL]"}
			suffix = suffix[passed]
			format = "%%-%ds"%self.max_line_char
			line = format % info
			line = line + suffix + eol
			if self.log_file:
				self.log_file.write(line)
			else:
				print line,

		if self.log_file:
			self.log_file.flush()

	def Init(self):
		self.set("status", "Waiting ...")
		self.set("barcode", '')
		self.set("dfpath", None)

	#barcode = y, dfpath = n => default log file path is used based on barcode
	#barcode = n, dfpath = y => specified log file
	#barcode = n, dfpath = n => no log file
	def Start(self, barcode = None, dfpath = None):
		self.set("barcode", barcode)
		self.set("start_time", time.time())
		self.set("duration", "&nbsp;")
		self.set("status", "TESTING")

		path = dfpath
		if path is None:
			subdir = self.model + "/" + time.strftime("%Y-%m-%d")
			fname = time.strftime("%H-%M-%S_")+barcode.replace(":", "-")+".dat"
			path = self.getPath(subdir, fname)

		self.set("dfpath", os.path.abspath(path))
		if barcode or dfpath:
			self.log_start(path)

	def Pass(self):
		self.set("status", "PASS")
		self.set("ecode", 0)
		self.set("duration", self.getDuration())
		self.set("start_time", 0)

	def Fail(self, ecode = -1):
		assert ecode != 0
		self.set("status", "FAIL")
		self.set("ecode", ecode)
		self.set("duration", self.getDuration())
		self.set("start_time", 0)

	def Prompt(self, status):
		old = self.get("status")
		self.set("status", status)
		return old

	def Record(self):
		dat_dir = self.getPath()
		dat_dir = os.path.abspath(dat_dir)
		datafile = None
		if self.dfpath:
			datafile = os.path.relpath(self.dfpath, dat_dir)

		self.lock.acquire()
		record = {}
		record["model"] = self.model
		record["barcode"] = self.barcode
		record["failed"] = self.ecode
		record["datafile"] = datafile
		record["station"] = self.opts["station"]
		record["operator"] = self.opts["user"]
		self.lock.release()
		self.tester.db.test_add(record)

	def onStart(self): pass
	def onPass(self): pass
	def onFail(self): pass
	def onStop(self): pass

	def run(self):
		mode = self.opts["mode"]
		try:
			while True:
				self.Init()
				barcode = None
				dfpath = None
				if mode == "AUTO":
					dfpath = None
					barcode = self.onStart()
					if barcode is None: continue
				else:
					barcode = None
					dfpath = "../../step%d.log"%self.station

				self.Start(barcode, dfpath)
				passed = self.Run()
				#0 passed
				#-1 failed
				#-1 - (1<<Esubs) sub board N fail

				if passed is not None:
					if isinstance(passed, bool):
						ecode = passed - 1 #True - 1 = 0
					else:
						ecode = passed

					if ecode >= 0:
						self.Pass()
						if mode == "AUTO":
							self.Record()
							self.onPass()
					else:
						self.Fail(ecode)
						if mode == "AUTO":
							self.Record()
							self.onFail()

				if mode == "STEP":
					break

		except eTestStop as e:
			pass
		except Exception as e:
			self.elock.acquire()
			self.exception = e
			self.estack = ''.join(traceback.format_exception(*sys.exc_info()))
			self.elock.release()

		finally:
			self.onStop()

	def stop(self):
		self.set("flag_stop", True)

	def release(self):
		#called before next test takes effect
		pass

