#! /usr/bin/env jython 
#
# Largely based on https://gist.github.com/shapr/507bcbf3e8cfdc5d3549
#

import argparse
import errno
import os
from getpass import getpass

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
from java.awt import BorderLayout
from javax.swing import JFileChooser, JFrame, JPanel 
from javax.swing.filechooser import FileNameExtensionFilter


def main():
    # parser = argparse.ArgumentParser(description='Export all tables from database to CSVs')
    # parser.add_argument('dbfilename', help='Path of the access file to be exported')
    # parser.add_argument('exportdirname', help='Path or name of directory to export files to')
    # args = parser.parse_args()
    # dbfilename = args.dbfilename
    # exportdirname = args.exportdirname
    #exportdirname = os.path.expanduser("~/Desktop/access-csvs")
    dbfilename = FileChooser().get_file_name()
    exportdirname = DirChooser().get_file_name()

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
    mkdirp(exportdirname)
    # use 'em to throw down all the data!
    ExportUtil.exportAll(db,exportdir,'csv',True)

    print "All done!"


def mkdirp(path):
    try:
        os.makedirs(path)
    except OSError as exc:  # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
            raise


class FileChooser(JFrame):

    def __init__(self):
        super(FileChooser, self).__init__()
        self.initUI()

    def initUI(self):

        self.panel = JPanel()
        self.panel.setLayout(BorderLayout())

        chooseFile = JFileChooser()

        chooseFile.setDialogTitle('Select Access Database')
        fnfilter = FileNameExtensionFilter("Access Databases", ["mdb", "accdb"]);
        chooseFile.setFileFilter(fnfilter);

        ret = chooseFile.showSaveDialog(self.panel)

        if ret == JFileChooser.APPROVE_OPTION:
            self.file_name = str(chooseFile.getSelectedFile())

    def get_file_name(self):
        return self.file_name


class DirChooser(JFrame):

    def __init__(self):
        super(DirChooser, self).__init__()

        self.initUI()

    def initUI(self):


        self.panel = JPanel()
        self.panel.setLayout(BorderLayout())

        chooseFile = JFileChooser()

        chooseFile.setDialogTitle('Select Export Location')
        chooseFile.setFileSelectionMode(JFileChooser.DIRECTORIES_ONLY)

        ret = chooseFile.showSaveDialog(self.panel)

        if ret == JFileChooser.APPROVE_OPTION:
            self.file_name = str(chooseFile.getSelectedFile())
            if not chooseFile.getSelectedFile().isDirectory():
                mkdirp(self.file_name)


    def get_file_name(self):
        return self.file_name

if __name__ == "__main__":
    main()
