#!/usr/bin/env python
#coding:utf8

import threading
import traceback
import time
import os, sys

class eTestStop(Exception):pass
class Test(threading.Thread):
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
			"ecode"		: self.ecode,
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

	def log(self, info, passed=None):
		#line = "%s#  %-48s"%(time.strftime('%X'), info)
		#line = "%s#  %-48s"%(self.getDuration(), info)
		line = "%-64s"%info
		if passed == True:
			line = line + " [PASS]"
		elif passed == False:
			line = line + " [FAIL]"
		else:
			pass
		line = line + "\n"

		if self.log_file:
			self.log_file.write(line)
			self.log_file.flush()
		else:
			print line ,

	def Init(self):
		self.set("status", "READY")
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
			fname = time.strftime("%H-%M-%S_")+barcode+".dat"
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
		self.set("status", status)

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
					dfpath = "../../step.log"

				self.Start(barcode, dfpath)
				passed = self.Run()

				if passed is not None:
					if passed:
						self.Pass()
						if mode == "AUTO":
							self.Record()
							self.onPass()
					else:
						self.Fail()
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

