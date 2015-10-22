#!/usr/bin/env python
#coding:utf8

import io
import time
import sys, signal
import sqlite3
import threading

class Db:
	lock = threading.Lock()
	conn = None

	def release(self):
		if self.conn:
			self.conn.close()
			self.conn = None

	def __init__(self):
		self.conn = sqlite3.connect('irt.db', check_same_thread = False)
		def dict_factory(cursor, row):
			d = {}
			for idx, col in enumerate(cursor.description):
				d[col[0]] = row[idx]
			return d
		self.conn.row_factory = dict_factory

	def __del__(self):
		self.release()

	def get(self, attr_name, val_def = None):
		if hasattr(self, attr_name):
			self.lock.acquire()
			obj = getattr(self, attr_name, val_def)
			self.lock.release()
			if hasattr(obj, "__call__"):
				def deco(*args, **kwargs):
					self.lock.acquire()
					retval = obj(*args, **kwargs)
					self.lock.release()
					return retval
				return deco
		return obj

	def set(self, attr_name, value):
		self.lock.acquire()
		setattr(self, attr_name, value)
		self.lock.release()

	def cfg_get(self, name):
		cursor = self.conn.cursor()
		cursor.execute('SELECT * FROM cfg WHERE name=?', (name,))
		record = cursor.fetchone()
		return record["value"]

	def cfg_set(self, name, value):
		cursor = self.conn.cursor()
		cursor.execute('UPDATE cfg SET value=? WHERE name=?', (str(value), name, ))
		self.conn.commit()

	def fixture_get(self, id, col):
		cursor = self.conn.cursor()
		cursor.execute('SELECT * FROM fixture WHERE id=?', (id,))
		fixture = cursor.fetchone()
		return fixture[col]

	def fixture_set(self, id, col, val):
		cursor = self.conn.cursor()
		sql = 'UPDATE fixture SET %s=%d WHERE id=%d'%(col, val, id)
		cursor.execute(sql)
		self.conn.commit()

	def model_get(self, name):
		cursor = self.conn.cursor()
		cursor.execute('SELECT * FROM model WHERE name=?', (name,))
		record = cursor.fetchone()
		return record

	def test_add(self, result):
		cursor = self.conn.cursor()
		cols = vals = ""
		for key in result:
			cols += key + ","
			if isinstance(result[key], int):
				vals += str(result[key]) + ","
			else:
				vals += '"%s",'%str(result[key])

		cols = cols + "time"
		vals = vals + 'datetime("now", "localtime")'
		sql = "INSERT INTO test(%s) VALUES(%s)"%(cols, vals)
		cursor.execute(sql)
		self.conn.commit()
		return sql

	def result_add(self, result):
		cursor = self.conn.cursor()
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
		cursor.execute(sql)
		self.conn.commit()
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
