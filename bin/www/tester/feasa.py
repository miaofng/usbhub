import time
import serial #http://pythonhosted.org/pyserial/
import re
import eloger

class FeasaTimeout(Exception):pass
class FeasaIOError(Exception):pass

class Feasa:
	timeout = 1
	uart = None

	def release(self):
		if self.uart:
			self.uart.close()
			self.uart = None

	def __init__(self, port, baud = 57600):
		self.uart = serial.Serial(port, baud,
			serial.EIGHTBITS,
			serial.PARITY_NONE,
			serial.STOPBITS_ONE,
			timeout = self.timeout,
			writeTimeout = self.timeout
		)

	def __del__(self):
		self.release()

	#auto add eol
	def query(self, cmdline, eol = '\r\n'):
		time.sleep(0.1)
		self.echo = ""
		self.uart.flushInput()
		self.uart.write(cmdline + eol)
		self.ready = False

	#auto remove eol
	def readline(self, eol = "\r\n\4"):
		linebuf = ""
		deadline = time.time() + self.timeout
		while True:
			if time.time() > deadline:
				raise FeasaTimeout

			nbytes = self.uart.inWaiting()
			if nbytes > 0:
				data = self.uart.read(nbytes)
				linebuf = linebuf + data

				idx = linebuf.find(eol)
				if idx >= 0:
					result = linebuf[:idx]
					return result

	def reset(self):
		self.query("RESET")
		self.readline()
		time.sleep(0.5)

	def getExposureFactor(self):
		self.query("GetFactor")
		echo = self.readline()
		factor = int(echo)
		return factor

	#range: Auto,Low,Medium,High,Super,Ultra
	def capture(self, range="auto"):
		range = {
			"auto": "",
			"low": "1",
			"medium": "2",
			"high": "3",
			"super": "4",
			"ultra": "5"
		}[range.lower()]

		self.query("CAPTURE%s"%range)

	#to poll: capture is finished?
	def IsReady(self):
		if not self.ready:
			nbytes = self.uart.inWaiting()
			if nbytes > 0:
				data = self.uart.read(nbytes)
				self.echo = self.echo + data

			idx = self.echo.find("OK")
			self.ready = idx >= 0
		return self.ready

	def getXYI(self, ch):
		ch = ch + 1
		self.query("GetXY%02d"%ch)
		echo = self.readline()
		[x, y] = echo.split(" ")
		x = float(x)
		y = float(y)

		self.query("GetABSINT%02d"%ch)
		echo = self.readline()

		i = 0.0
		if echo.find("RANGE") >= 0:
			i = 0.0
		else:
			#find a float inside a string, such as "xxx1.2e15dddss" or "+1.0z" ..
			#to fixed feasa's unknown "EOT" char issue
			echo = re.search("[\\d+-][\deE\.\+\-]*", echo).group()

			i = float(echo)
			i = i / 1000 / self.getExposureFactor()

		self.query("GetIntensity%02d"%ch)
		echo = self.readline()
		d = float(echo)

		##add###
		self.query("GetHSI%02d"%ch)
		echo = self.readline()
		hsi = echo.split(' ')
		h = float(hsi[0])

		loger = eloger.Eloger()
		loger.log(echo)

		return [x, y, i, d, h]

if __name__=='__main__':
	import os, sys, signal
	import settings
	def signal_handler(signal, frame):
		sys.exit(0)

	signal.signal(signal.SIGINT, signal_handler)
	if len(sys.argv) == 1:
		print "feasa [ch:0-9]	deadloop capture&display"
		quit()

	ch = sys.argv[1]
	ch = int(ch)
	feasa = Feasa(settings.feasa_ports[1])
	feasa.reset()
	while True:
		feasa.capture("auto")
		while not feasa.IsReady():
			time.sleep(1)
			print("."),
		[x, y, i] = feasa.getXYI(ch)
		print("\rxyi = %.03f %.03f %.03f"%(x,y,i))
