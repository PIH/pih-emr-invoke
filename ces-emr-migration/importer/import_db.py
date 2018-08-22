#! env/bin/python3
"""
import_db.py

Imports data from CSV files to the OpenMRS MySQL database
"""

import csv

import MySQLdb


def main():

    db = MySQLdb.connect("localhost", "root", "asdf;lkj", "openmrs_chiapas")
    cursor = db.cursor()

    db.close()


def csv_as_list(filename):
    with open(filename, "rt", encoding="utf8") as csvfile:
        reader = csv.reader(csvfile)
        return list(reader)


if __name__ == "__main__":
    main()
