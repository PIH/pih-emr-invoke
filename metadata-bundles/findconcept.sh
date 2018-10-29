#!/bin/bash

grep "<conceptId>$@</conceptId>" *
ack -A50 "<conceptId>$@</conceptId>" | grep -m 1 -A8 "<conceptNameId>" | grep "<name>"
