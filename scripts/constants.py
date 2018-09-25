import os
import re
import sys
import pathlib



me = pathlib.Path(__file__)
SCRIPTSDIR = me.parent
base = SCRIPTSDIR.parent
RAWDIR = base.joinpath('raw')
DATADIR = base.joinpath('data')

SCREENSHOT_START=15
SCREENSHOT_FREQUENCY=15


