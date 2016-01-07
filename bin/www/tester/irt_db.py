#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-10
#

import json
from pytest import *

class IRDb(Db):
	def model_get(self, name):
		sql = 'SELECT * FROM model WHERE name = "%s"'%name
		records = self.query(sql)
		if len(records) > 0:
			record = records[0]
			return record

	def rule_get(self, id):
		sql = 'SELECT * FROM rule WHERE id = %d'%id
		records = self.query(sql)
		if len(records) > 0:
			record = records[0]
			return record

	#read all effective rules of specified model
	def rules_get(self, model):
		rules = []
		rules_setting = None

		record = self.model_get(model)
		if record:
			rules_setting = record["rules"]

		try:
			rules_setting = json.loads(rules_setting)
			for id in rules_setting:
				rule = self.rule_get(id)
				if rule:
					#i = rule["i"]
					#i = float(dict_mA[i])
					value = float(rule["value"])
					range = rule["range"]
					range = dict_range[range]

					min = max = None
					if range == "<":
						max = value
					elif range == ">":
						min = value
					else:
						range = float(range)
						min = value * (1 - range)
						max = value * (1 + range)


					#rule["mA"] = i
					rule["value"] = value
					rule["min"] = min
					rule["max"] = max
					rules.append(rule)

		except:
			print "except: rules_setting = %s"%rules_setting
			print "except: rule = %s"%str(rule)
			pass

		finally:
			return rules

if __name__ == '__main__':
	from sys import *
	import signal

	db = "irt.db"
	model = "1419513"

	if len(argv) > 1:
		model = argv[1]

	db = IRDb(db)
	rules = db.rules_get(model)
	for rule in rules:
		print rule


