import time
import socket
import json

debug = False

class RaspTestError(Exception):pass
class RaspIOError(Exception):pass
class RaspParaError(Exception):pass

class Raspberry:
	timeout = 1

	def __init__(self, saddr, port=10003):
		self.saddr = saddr
		self.port = port

	#auto add eol
	def query(self, cmdline, eol = '\r\n'):
		sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
		sock.settimeout(self.timeout)
		sock.connect((self.saddr, self.port))
		sock.send(cmdline + eol)
		data = sock.recv(4096)
		sock.close()
		if debug:
			print "query: %s"%cmdline
			print " echo: %s"%data

		echo = json.loads(data)
		return echo

	def __status__(self):
		return self.query("status")

	def __isbusy__(self, echo, id):
		if id in echo:
			result = echo[id]
			state = result["state"]
			if state == "ERROR":
				raise RaspTestError

			busy = state == "RUNNING"
			return busy

	#list all identified passmark's id
	def list(self):
		return self.query("list")

	#start passmark speed test
	def benchmark(self, passmark_id = ""):
		cmdline = []
		cmdline.append("benchmark")
		cmdline.append(passmark_id)
		cmdline = ' '.join(cmdline)

		result = self.query(cmdline)
		status = result["status"]
		if status != "OK":
			raise RaspIOError

	#usb benchmark test finished?
	#return None if passmark not exist
	def IsReady(self, id = None):
		echo = self.__status__()
		if id:
			running = self.__isbusy__(echo, id)
		else:
			running = False
			for key in echo:
				busy = self.__isbusy__(echo, key)
				running = running or busy

		if running is not None:
			ready = not running
			return ready

	#usb benchmark test result
	def status(self, id):
		ready = self.IsReady(id)
		if ready and id is not None:
			echo = self.__status__()
			result = echo[id]
			speed = result["speed"]
			speed = speed.split(" ")
			data = {}
			data["w_mbps"] = int(speed[1])
			data["r_mbps"] = int(speed[2])
			data["a_mbps"] = int(speed[3])
			return data

if __name__=='__main__':
	import os, sys, signal
	import settings
	def signal_handler(signal, frame):
		sys.exit(0)

	signal.signal(signal.SIGINT, signal_handler)
	if len(sys.argv) == 1:
		print "rasp list ip			list passmarks identified"
		print "rasp speed ip [id] [id] ...	passmark speed test"
		quit()

	ip = sys.argv[2]
	rasp = Raspberry(ip)
	if sys.argv[1] == "list":
		print rasp.list()

	elif sys.argv[1] == "speed":
		id_list = sys.argv[3:]
		for id in id_list:
			rasp.benchmark(id)

		while True:
			ready = rasp.IsReady()
			time.sleep(0.1)
			echo = rasp.__status__()
			print json.dumps(echo)

			if ready:
				break
