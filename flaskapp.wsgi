#!/usr/bin/python
import sys
import logging
logging.basicConfig(stream=sys.stderr)
#sys.path.insert(0,"/var/www/folioreport/")
sys.path.insert(0,"/var/www/changeRecords/")

from app import app as application
