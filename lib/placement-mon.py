#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  Copyright (C) 2015-2018 Emmanuel Courcelle
#  PLACEMENT is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PLACEMENT.  If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Emmanuel Courcelle - C.N.R.S. - UMS 3667 - CALMIP
#        Nicolas Renon - Université Paul Sabatier - University of Toulouse)
#

import os
import argparse
import sys
import subprocess
import time
from utilities import *
import hardware
from socket import gethostname
import datetime

SLEEPTIMEMIN=3                                                          # Minimum sleep time you can specify (in s)
SQUEUECMD   =['squeue','-t','R','-p','exclusive','-o','%i','-h']        # The command to send for finding the jobs 
#
# placement-mon is automatically launched by the bash call script when the switch --monitor is detected
#
# It uses squeue to get the list of running jobs, then for each job it runs placement --summary.
# It detects the pathologicalal jobs 
# This is done 5 times, sleeping a while between launches
# Then the jobs which were EACH TIME detected as pathologicalal are printed with the summary message
#
# It may be a good idea then to have a look to theses jobs, with placement --threads, or placement --continuous to understand
# what happens with theses jobs
#

# The PLACEMENT_ROOT env variable (should be correctly set by the install script)
placement_root = os.environ['PLACEMENT_ROOT']

# Path to the placement shell script
PLACEMENT=placement_root + '/bin/placement'

def main():
	
	# Analysing the command line arguments
	#epilog = ""
	ver="1.5.0-dev"
	parser = argparse.ArgumentParser(version=ver,description="placement-mon " + ver)
	group = parser.add_argument_group('continuously checking jobs running on compute nodes')
	group.add_argument("--monitoring",dest='mon',action="store_true",help="required")
	group.add_argument("--time",dest='time',action='store',type=int,default=SLEEPTIMEMIN,help="Sleeping time between two measures")
	
	options=parser.parse_args()

	if options.mon==False:
		sys.stderr.write ("INTERNAL ERROR - --monitoring missing !\n")
		exit(1)
		
	if options.time==None:
		options.time=SLEEPTIMEMIN
	else:
		if options.time<SLEEPTIMEMIN:
			sys.stderr.write ("ERROR - --time should NOT be lower than " + str(SLEEPTIMEMIN) + "\n")
			exit(1)

	# Get the list of running jobs
	running_jobs = detectRunningJobs()

	#
	# Do 5 times:
	#	- Call placement --jobid --summary for each running job
	#	- Wait options.time
	#
	# NOTE - We are looking for jobs remaining pathological for the 5 iterations
	#        So we do not consider jobs starting after the first iteration, 
	#        as well as jobs finishing after the last iteration
	N = 5
	results = []
	sys.stderr.write("Now checking " + str(len(running_jobs)) + " running jobs. Please be patient\n")
	for i in range(N):
		res = callPlacementSummary(running_jobs)
		results.append(res)
		if i < N-1:
			sys.stderr.write("Found " + str(len(res)) + " pathological jobs, now waiting a while\n")
			time.sleep(options.time)
		else:
			sys.stderr.write("Found " + str(len(res)) + " pathological jobs, continuing\n\n")
		
	#
	# Compute the intersection of the keys
	#
	reskeys = []
	for r in results:
		rk = frozenset(r.keys())
		reskeys.append(rk)
		
	inter = reskeys[0]
	for r in reskeys[1:]:
		inter = inter & r
	
	#
	# Print the remaining pathological jobs
	#
	if len(inter) > 0:
		print str(len(inter)) + " PATHOLOGICAL JOBS FOUND ON " + gethostname() + " at " + str(datetime.datetime.today())
		for j in inter:
			print j + ' |',
			for r in results:
				print r[j] + ' | ',
			print

#
# callPlacementSummary
#
# input = The list of running jobs
# return= A dict:
#	      key = jobid of a pathological running job
#         val = The output of placement --summary for each PATHOLOGIC running job
#               A pathological running job is a job whose summary ends with the letter W
#				The nonpathological running jobs are filtered out
#
def callPlacementSummary(jobids):
	output = {}
#	for j in jobids[0:10]:
	for j in jobids:
		
		# Ignore errors in placement --summary, they are probably due to a finished job
		try:
			cmd = [PLACEMENT,'--jobid',j,'--summary','--no_ansi']
			out=subprocess.check_output(cmd).rstrip('\n')
		except subprocess.CalledProcessError:
			pass
		if out.endswith('W'):
			output[j] = out

#		if not out.endswith('W'):
#			print ("j=" + j + "  " + out + " ==> FILTERED OUT")
#		else:
#			output[j] = out
#			print ("j=" + j + "  " + out + " ==> KEPT")
		
	return output
		
#
# detect running jobs from an squeue call
#
# return the list of jobids
#
def detectRunningJobs():
	cmd = SQUEUECMD
	out=subprocess.check_output(cmd).split('\n')
	return out

if __name__ == "__main__":
    main()
