#! /usr/bin/env jython 
#
# Largely based on https://gist.github.com/shapr/507bcbf3e8cfdc5d3549
#

import sys
sys.path.append('jackcess-2.1.12.jar') # assume the jackcess is in the same directory
sys.path.append('jackcess-encrypt-2.1.4.jar')
sys.path.append('bcprov-ext-jdk15on-160.jar') # Bouncy Castle encryption library
sys.path.append('commons-lang-2.6.jar')
sys.path.append('/usr/share/java/commons-logging-1.2.jar') # in case logging didn't get picked up
from com.healthmarketscience.jackcess import *
from com.healthmarketscience.jackcess.util import ExportFilter
from com.healthmarketscience.jackcess.util import ExportUtil
from com.healthmarketscience.jackcess.util import SimpleExportFilter
from com.healthmarketscience.jackcess import CryptCodecProvider
import java.io
from java.io import File

import argparse
import os
from getpass import getpass

parser = argparse.ArgumentParser(description='Export all tables from database to CSVs')
parser.add_argument('dbfilename', help='Path of the access file to be exported')
parser.add_argument('exportdirname', help='Path or name of directory to export files to')
args = parser.parse_args()
dbfilename = args.dbfilename
exportdirname = args.exportdirname

print "input filename is",dbfilename
print "tables will be saved into directory",exportdirname
dbfile = File(dbfilename)
exportdir = File(exportdirname)
passwd = getpass("Database password: ")
# make a database object
db = DatabaseBuilder(dbfile).setCodecProvider(CryptCodecProvider(passwd)).open()
# make an export filter object
export_filter = SimpleExportFilter()
# make the output directory
os.mkdir(exportdirname)
# use 'em to throw down all the data!
ExportUtil.exportAll(db,exportdir,'csv',True)

print "All done!"
