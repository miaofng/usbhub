#!/usr/bin/env python
#coding:utf8
#easy_install pyvisa
#ni visa driver should be installed, to be used as pyvisa backend
#A34410:
#0.06NPLC	1.5PPM	1000rds/s(AUTO ZERO OFF)
#0.2NPLC	0.7PPM	300rds/s(AUTO ZERO OFF)
#DCV 10V RIN=10Mohm/>10Gohm 1.5PPM=>Verr=15uV 1R*10mA = 10mV
#DCI RIN=200R@1mA


import visa
import threading
import time

class DmmIoError(Exception):
	def __init__(self, echo):
		self.echo = echo

class Dmm:
	lock = threading.Lock()
	rm = None
	instr = None

	def release(self):
		if self.instr:
			self.instr.close()
			self.rm.close()
			self.instr = None
			self.rm = None

	def query(self, cmdline):
		timer = time.time()
		self.lock.acquire()

		result = None
		if cmdline.find('?') != -1:
			result = self.instr.query(cmdline)
		else:
			self.instr.write(cmdline)

		self.lock.release()
		timer = time.time() - timer
		#print "DMM: %s ... %.3f S" % (cmdline, timer)
		return result

	def __init__(self, visa_name=None):
		if visa_name is None:
			rm = visa.ResourceManager()
			instr_list = rm.list_resources()
			for instr in instr_list:
				#"USB0::0x0957::0x0607::MY53011514::INSTR"
				if instr.find("USB0::0x0957::0x0607") >= 0:
					visa_name = instr
					break
			rm.close()

		#print "dmm=%s" % visa_name
		self.rm = visa.ResourceManager()
		self.instr = self.rm.open_resource(visa_name)
		#self.reset()
		self.stop()
		self.cls()
		self.idn = self.query("*idn?")
		self.query("FORMAT REAL,64")
		self.query("FORMAT:BORDER SWAP") #little endian

	def __del__(self):
		self.release()

	def reset(self):
		self.query("*rst")
	def cls(self):
		self.query("*cls")
	def error_check(self):
		#dmm has error?
		emsg = self.instr.query("SYST:ERR?")
		if int(emsg[:2]) is not 0:
			raise DmmIoError(emsg)
	def disp(self, message=None):
		if message != None:
			self.query('disp:window:text "%s"'%message)
		else:
			self.query('disp:window:text:clear')

	def measure_res(self):
		return self.query("meas:res?")
	def measure_dcv(self):
		return self.query("meas:volt:dc?")
	def measure_acv(self):
		self.query("CONF:VOLT:AC AUTO")
		self.query("SENS:VOLT:AC:BANDWIDTH 200") #filter bandwidth: 3/20/200Hz
		return self.query("READ?")
	def measure_dci(self):
		return self.query("meas:curr:dc?")
	def measure_diode(self):
		return self.query("meas:diode?")
	def measure_beeper(self):
		#0-10R beep, 10R-1K2 disp value, >1K2 disp OPEN
		#open return +9.90000000E+37
		return self.query("meas:CONTinuity?")

	def trig_ext(self, slope="POS", sdelay="AUTO", count="INF"):
		self.query("OUTP:TRIG:SLOPE %s"%slope)
		self.query("TRIG:SLOPE %s"%slope)
		#note: trig delay is useful except diode&CONTinuity mode
		if type(sdelay) != int:
			self.query("TRIG:DELAY:AUTO ON")
		else:
			self.query("TRIG:DELAY %f"%sdelay)
		if type(count) != count:
			self.query("TRIG:COUNT %s"%count)
		else:
			self.query("TRIG:COUNT %d"%count)
		self.query("TRIG:SOURCE EXT")

	def config(self, bank):
		cmdline = "CONF:%s"%bank
		self.query(cmdline)

	def start(self):
		self.query("TRIG:SOURCE EXT")
		self.query("TRIG:COUNT INF")
		self.query("INIT") #dmm internal buffer will be cleared here

	def stop(self):
		self.query("ABORT")

	def poll(self):
		#return nr of points pending in dmm's internal buffer
		n = self.query("DATA:POINTS?")
		n = int(n)
		return n

	def read(self, npoints=None):
		cmdline = "R?"
		if npoints:
			cmdline = "R? %d"%npoints

		self.lock.acquire()
		results = self.instr.query_binary_values(cmdline, datatype='d', is_big_endian=False)
		self.lock.release()
		return results

if __name__ == '__main__':
	def instr_list():
		rm = visa.ResourceManager()
		list = rm.list_resources()
		for instr in list:
			print(instr)

	from sys import *
	import signal

	def signal_handler(signal, frame):
		sys.exit(0)

	signal.signal(signal.SIGINT, signal_handler)
	argc = len(argv)
	if(argc == 1 or argv[1] == 'help'):
		print 'list		list all instruments'
		print 'cmd		query instr with the specified command'
		quit();

	if argv[1] == 'list':
		instr_list();
	else:
		dmm = Dmm()
		cmdline = argv
		del cmdline[0]
		cmdline = ' '.join(argv)
		print "Q: %s"%cmdline
		print "A: %s"%dmm.query(cmdline)
