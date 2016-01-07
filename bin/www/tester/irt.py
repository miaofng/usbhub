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

db = IRDb()
dmm = Dmm()
irt = Matrix()
#fixture = Fixture()
scanner = Fs36()

tester = Tester(db)
tester.instrument_add("dmm", dmm)
tester.instrument_add("irt", irt)
tester.instrument_add("scanner", scanner)
#tester.instrument_add("fixture", fixture)
tester.test_add("gft", GFTst)
tester.test_add("cal", IRCal)
tester.test_add("scn", IRScn)
tester.test_add("learn", Learn)
tester.run()
