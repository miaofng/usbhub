import time
import serial

class UctrlIoError(Exception): pass

class Uctrl:
	timeout = 5 #unit: S
	uart = None

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port, baud = 115200):
		self.uart = serial.Serial(port, baud, timeout = self.timeout)
		self.uart.write("shell -a\r")

	def __del__(self):
		self.release()

	def query(self, cmdline):
		self.uart.flushInput()
		self.uart.write(cmdline+"\n\r")
		echo = self.uart.readline()
		if echo[0:2] != "OK":
			raise UctrlIoError

	def mode(self, mode, enable):
		cmdline = "uht %s %s"%(mode, enable)
		self.query(cmdline)

	def reset(self):
		cmdline = "uht init"
		self.uart.write(cmdline+"\n\r")

	def vbat(self, onoff):
		cmdline = "uht sw%s"%onoff
		self.uart.write(cmdline+"\n\r")

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
		self.uart.write(cmdline + "\n\r")
