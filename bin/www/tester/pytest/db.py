#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
import sqlite3
import threading
from eloger import Eloger

class Db:
	lock = threading.Lock()
	conn = None
	cursor = None

	def release(self):
		if self.conn:
			self.cursor.close()
			self.conn.close()
			self.cursor = self.conn = None

	def __init__(self, db="irt.db"):
		self.conn = sqlite3.connect(db, check_same_thread = False)
		def dict_factory(cursor, row):
			d = {}
			for idx, col in enumerate(cursor.description):
				d[col[0]] = row[idx]
			return d
		self.conn.row_factory = dict_factory
		self.cursor = self.conn.cursor()

	def query(self, sql):
		#Eloger().log(sql)

		select = sql[:6].upper() == "SELECT"
		records = None

		self.lock.acquire()
		self.cursor.execute(sql)
		if select:
			records = self.cursor.fetchall()
		else:
			self.conn.commit()
		self.lock.release()
		return records

	def cfg_get(self, name):
		sql = "SELECT * FROM cfg WHERE name='%s'"%name
		records = self.query(sql)
		if len(records) > 0:
			record = records[0]
			return record["value"]

	def cfg_set(self, name, value):
		sql = "UPDATE cfg SET value='%s' WHERE name='%s'"%(value, name)
		self.query(sql)

	def test_add(self, result):
		cols = vals = ""
		for key in result:
			cols += key + ","
			if isinstance(result[key], int):
				vals += str(result[key]) + ","
			else:
				vals += "'%s',"%str(result[key])

		cols = cols + "time"
		vals = vals + 'datetime("now", "localtime")'
		sql = "INSERT INTO test(%s) VALUES(%s)"%(cols, vals)

		self.query(sql)
		return sql

################################################
	def fixture_get(self, id, col):
		self.lock.acquire()
		self.cursor.execute('SELECT * FROM fixture WHERE id=?', (id,))
		record = self.cursor.fetchone()
		self.lock.release()
		if record:
			return record[col]

	def fixture_set(self, id, col, val):
		sql = 'UPDATE fixture SET %s=%d WHERE id=%d'%(col, val, id)
		self.lock.acquire()
		self.cursor.execute(sql)
		self.conn.commit()
		self.lock.release()

	def model_get(self, name):
		self.lock.acquire()
		self.cursor.execute('SELECT * FROM model WHERE name=?', (name,))
		record = self.cursor.fetchone()
		self.lock.release()
		return record

	def result_add(self, result):
		cols = vals = ""
		for key in result:
			cols += key + ","
			if isinstance(result[key], int):
				vals += str(result[key]) + ","
			elif isinstance(result[key], float):
				vals += str(result[key]) + ","
			else:
				vals += '"%s",'%str(result[key])

		cols = cols + "time"
		vals = vals + 'datetime("now", "localtime")'
		sql = "INSERT INTO result(%s) VALUES(%s)"%(cols, vals)

		self.lock.acquire()
		self.cursor.execute(sql)
		self.conn.commit()
		self.lock.release()
		return sql

	def cal_get(self, model, station, name):
		self.lock.acquire()
		self.cursor.execute('SELECT * FROM cal WHERE model=? AND station=? AND name=? ORDER BY id DESC', (model, station, name))
		record = self.cursor.fetchone()
		self.lock.release()
		if record:
			return record["value"]

	def cal_add(self, record):
		#add new cal record
		cols = vals = ""
		for key in record:
			cols += key + ","
			if isinstance(record[key], int):
				vals += str(record[key]) + ","
			elif isinstance(record[key], float):
				vals += str(record[key]) + ","
			else:
				vals += "'%s',"%str(record[key])

		cols = cols + "time"
		vals = vals + 'datetime("now", "localtime")'

		sql = "INSERT INTO cal(%s) VALUES(%s)"%(cols, vals)
		self.lock.acquire()
		self.cursor.execute(sql)
		self.conn.commit()
		self.lock.release()
		return sql

#module self test
if __name__ == '__main__':
	import json

	db = Db();
	print db.cfg_get('gft_last')
	nr_ok = db.cfg_get('nr_ok')
	nr_ok = int(nr_ok)
	print "nr_ok = %d"%nr_ok
	db.cfg_set("nr_ok", nr_ok + 1)
	print db.test_add({"model": "12345", "barcode": "00002", "failed": 0, "runtime":3455, "duration": 5})

	name = raw_input("pls input the model name to query:")
	model = db.model_get(name)
	print model
	if model != None:
		barcode = json.loads(model["barcode"])
		#barcode["x"] = barcode["x"] + 1
		print barcode
