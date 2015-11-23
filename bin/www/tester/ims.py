#!/usr/bin/env python
#coding:utf8

import socket
import select
import Queue
from time import sleep
import sys
import settings

class Ims:
	imsg = {}
	omsg = {}

	def __init__(self, port):
		#ipaddr = self.get_my_ip()
		ipaddr = settings.ims_addr
		self.saddr = (ipaddr, port)
		print 'IMS server init .. %s:%d '%self.saddr
		self._server = socket.socket(socket.AF_INET,socket.SOCK_STREAM)
		self._server.setblocking(False)
		self._server.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
		self._server.bind(self.saddr)
		self._server.listen(port)
		self._inputs = [self._server]
		self._outputs = []

	def __del__(self):
		for s in self._inputs:
			s.close()

	def _update(self):
		rs,ws,es = select.select(self._inputs, self._outputs, self._inputs, 0)
		if not (rs or ws or es):
			return

		for s in rs:
			if s is self._server:
				conn,addr = s.accept()
				#print 'connect by',addr
				conn.setblocking(False)
				self._inputs.append(conn)
				self.imsg[conn] = Queue.Queue()
				self.omsg[conn] = Queue.Queue()
			else:
				#print 'recv ok...'
				try:
					data = s.recv(1024)
				except socket.error:
					data = None

				if data:
					#print data
					self.imsg[s].put(data)
				else:
					#socket close
					if s in self._outputs:
						self._outputs.remove(s)
					#print 'remove rs: %d'%s.fileno()
					self._inputs.remove(s)

					s.close()
					del self.imsg[s]
					del self.omsg[s]
					if s in ws:
						ws.remove(s)

		for s in ws:
			try:
				msg = self.omsg[s].get_nowait()
			except Queue.Empty:
				self._outputs.remove(s)
			else:
				s.send(msg)

		for s in es:
			#print 'except ',s.getpeername()
			if s in self._inputs:
				#print 'remove es: %d'%s.fileno()
				self._inputs.remove(s)
			if s in self._outputs:
				self._outputs.remove(s)
			s.close()
			del self.imsg[s]
			del self.omsg[s]

	def recv(self):
		self._update()
		for s in self.imsg.keys():
			try:
				msg = self.imsg[s].get_nowait()
			except Queue.Empty:
				continue
			else:
				result = None
				req = {}
				req["sock"] = s
				req["data"] = msg
				temp = list(msg)
				if len(msg) != 10:
					return
				for i in range(len(msg)):
					temp[i] = ord(msg[i])
					#print msg[i],
				#print type(msg)
				temp[1] = 0X0B
				#READY REQUEST
				if temp[9] == 1:
					temp[9] = 0x02
				#STOP COMMAND
				elif temp[9] == 3:
					temp[9] = 0x04
					#print "IMS_STOP"
					result = "StopOrder"
					#stop_test(IMS_STOP)
				#START COMMAND
				elif temp[9] == 5:
					temp[9] = 0x06
					#print "IMS_RECOVERY"
					result = "StartOrder"
					#stop_test(RECOVERY)
				else:
					return None

				temp.append(0x06)
				import array
				req["data"] = array.array('B', temp).tostring()#''.join([chr(x) for x in temp])
				self.send(req)
				return result

	def send(self, req):
		s = req["sock"]
		self.omsg[s].put(req["data"])
		if s not in self._outputs:
			self._outputs.append(s)

	def get_my_ip(self):
		"""
		Returns the actual ip of the local machine.
		This code figures out what source address would be used if some traffic
		were to be sent out to some well known address on the Internet. In this
		case, a Google DNS server is used, but the specific address does not
		matter much.  No traffic is actually sent.
		"""
		try:
			csock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
			csock.connect(('8.8.8.8', 80))
			(addr, port) = csock.getsockname()
			csock.close()
			return addr
		except socket.error:
			return "192.168.110.181"

import time
if __name__ == '__main__':
	#pi_addr = get_my_ip()
	#saddr = (pi_addr, 10003)
	ims = Ims(5000)
	while True:
		time.sleep(0.01)
		cmd = ims.recv()
		if cmd is not None:
			print cmd


