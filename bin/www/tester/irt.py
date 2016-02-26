#!/usr/bin/env python
#coding:utf8
#miaofng@2015-12-14
#

from pytest import *
from fixture import Fixture
from test_cal import IRCal
from test_scn import IRScn
from test_gft import GFTst
from learn import Learn
from irt_db import IRDb

import sys, signal
import time
import threading
import traceback

def signal_handler(signal, frame):
	sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)

db = IRDb("../../../data/data.db")
tester = Tester(db)

dmm = Dmm()
tester.instrument_add("dmm", dmm)

irt = Matrix()
tester.instrument_add("irt", irt)

port_fixture = db.cfg_get("port_plc")
fixture = Fixture(str(port_fixture))
tester.instrument_add("fixture", fixture)

port_scanner = db.cfg_get("port_scanner")
if port_scanner != "OFF":
	scanner = Scanner(str(port_scanner))
	tester.instrument_add("scanner", scanner)

port_printer = db.cfg_get("port_printer")
if port_printer != "OFF":
	printer = Printer(str(port_printer))
	tester.instrument_add("printer", printer)

tester.test_add("gft", GFTst)
tester.test_add("cal", IRCal)
tester.test_add("scn", IRScn)
tester.test_add("learn", Learn)
tester.run()
