import time
import serial
import eloger

class UctrlIoError(Exception): pass

class Uctrl:
	timeout = 5 #unit: S
	uart = None

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port, baud = 115200):
		self.port = port
		self.baud = baud
		#self.baud = baud
		#self.uart = serial.Serial(port, baud, timeout = self.timeout)
		#self.uart.write("shell -a\r")
		self.query("shell -a")

	def __del__(self):
		self.release()

	def __query__old(self, cmdline, echo = None):
		self.uart = uart = serial.Serial(self.port, self.baud, timeout = self.timeout)
		uart.flushInput()
		uart.write(cmdline+"\n\r")
		resp = ""
		if echo is not None:
			resp = self.uart.readline()
		uart.close()
		self.uart = None
		if echo is not None:
			if resp[0:2] != echo:
				raise UctrlIoError

	def __query__(self, cmdline, echo = None):
		if self.uart is None:
			self.uart = serial.Serial(self.port, self.baud, timeout = self.timeout)
		self.uart.flushInput()
		self.uart.write(cmdline+"\n\r")
		if echo is not None:
			resp = self.uart.readline()
			if resp[0:2] != echo:
				raise UctrlIoError

	def query(self, cmdline, echo = None):
		count = 0
		while True:
			try:
				self.__query__(cmdline, echo)
				return
			except Exception as e:
				if self.uart is not None:
					self.uart.close()
					self.uart = None
				loger = eloger.Eloger(e)
				loger.log("port = %s"%self.port)
				count = count + 1
				if count > 3:
					raise e

	def mode(self, mode, enable):
		cmdline = "uht %s %s"%(mode, enable)
		self.query(cmdline, "OK")

	def reset(self):
		cmdline = "uht init"
		#self.uart.write(cmdline+"\n\r")
		self.query(cmdline)

	def vbat(self, onoff):
		cmdline = "uht sw%s"%onoff
		self.query(cmdline)
		#self.uart.write(cmdline+"\n\r")

	def switch(self, relay, enable):
		relay = {
			"load1": 12,
			"load2": 14,
			"cdp2": 0,
		}[relay]
		enable = {
			"enable": 1,
			"disable": 0,
		}[enable]

		#cdp2<relay k0> hardware invert
		if relay == 0:
			enable = enable ^ 1

		cmdline = "uht set %d %d"%(relay, enable)
		#self.uart.write(cmdline + "\n\r")
		self.query(cmdline)
