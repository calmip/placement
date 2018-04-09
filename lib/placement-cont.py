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

#
# placement-cont is automatically launched by the bash call script when the switch --continuous is detected
#
# It must be used with the --jobid switch
# The list of compute hosts is detected with squeue, then placement --csv is launched on the hosts (using clush),
# The program sleeps a while, the launches placement --csv again
# The program stops when squeue returns an error (because the job is finished), OR when the user sends SIGINT (ctrl-c)
# 
# You can start this program BEFORE the job is running: it will squeue the jobid until its state goes to R
#

SLEEPTIMEMIN=30               # Minimum sleep time you can specify (in s)

# The PLACEMENT_ROOT env variable (should be correctly set by the install script)
placement_root = os.environ['PLACEMENT_ROOT']

# Path to the placement shell script
PLACEMENT=placement_root + '/bin/placement'

def main():
	# Analysing the command line arguments
	#epilog = ""
	ver="1.5.0-dev"
	parser = argparse.ArgumentParser(version=ver,description="placement-cont " + ver)
	group = parser.add_argument_group('continuously checking jobs running on compute nodes')
	group.add_argument("--continuous",dest='cont',action="store_true",help="required")
	group.add_argument("-j","--jobid",dest='jobid',action="store",help="Continuously check this running job")
	group.add_argument("--time",dest='time',action='store',type=int,default=SLEEPTIMEMIN,help="Sleeping time between two measures")
	
	
	options=parser.parse_args()

	if options.jobid==None:
		sys.stderr.write ("ERROR - --jobid is required\n")
		exit(1)
		
	if options.cont==False:
		sys.stderr.write ("INTERNAL ERROR - --continuous missing !\n")
		exit(1)
		
	if options.time==None:
		options.time=SLEEPTIMEMIN
	else:
		if options.time<SLEEPTIMEMIN:
			sys.stderr.write ("ERROR - --time should NOT be lower than " + str(SLEEPTIMEMIN) + "\n")
			exit(1)

	# Detect the partition, the compute hosts and the user from the jobid
	[partition,hosts,user] = jobid2hosts(options.jobid)

	sys.stderr.write ("jobid    = "+options.jobid+"\n")
	sys.stderr.write ("hosts    = "+str(hosts)+"\n")
	sys.stderr.write ("partition= "+str(partition)+"\n")
	sys.stderr.write ("user     = "+str(user)+"\n")

	sys.stderr.write ("Sleeping " + str(options.time) + "s between measures, press CTRL-C to stop !\n\n")
	
	# The printHeaders will create a new hardware, and will use this env variable
	# callPlacement, too
	os.environ['PLACEMENT_PARTITION'] = partition
	printHeaders()

	try:
		while True:
			if not isRunning(options.jobid):
				exit(0)
			callPlacement(partition, hosts, user)
			time.sleep(SLEEPTIMEMIN)
	except KeyboardInterrupt:
		exit(0)

#
# Is the job still running ?
#
# input = jobid
# output = True/False
#
def isRunning(jobid):
	cmd = ['squeue','-j',str(jobid),'-o','%t','-h']
	try:
		out=subprocess.check_output(cmd).rstrip('\n')
		return (out=='R')
	except subprocess.CalledProcessError:
		return False
	
#
# Guess the hardware using the env var PLACEMENT_PARTITION, and print the headers of the csv
#
def printHeaders():
	hard = '';
	try:
		hard = hardware.Hardware.factory()
			
	except PlacementException, e:
		print (e)
		exit(1)
	
	h='nodename,';
	for c in range(0,hard.CORES_PER_NODE):
		h += 'CPU'
		h += str(c)
		h += ','
	h += 'MEM,'
	
	gpus=hard.GPUS
	if gpus != None:
		gpus=compactString2List(gpus)
		for g in gpus:
			h +='GPU'+str(g)+'_U'+','
			h +='GPU'+str(g)+'_M'+','
			h += 'GPU'+str(g)+'_P'+','
	
	print (h.replace(' ',''))

#
# Call placement on a list of hosts, using clush and print the result
#
def callPlacement(partition, hosts, user):
	cmd=['clush','-w',hosts,PLACEMENT,'--check',user,'--csv']	# 
	out=subprocess.check_output(cmd).rstrip('\n').split(': ')	# totocomp: 100,100,100,99,... -> ['totocomp: ','100','100',...]
	out=','.join(out)                                           # 'totocomp,100,100,100,99,...
	print(out)
	

#
# Detect and return the list of hosts corresponding to a jobid
# If there is a squeue error, exit
# If the job is 'PD' (pending), wait for it to bcome running
#
# input  = jobid
# output = [partition, list of hostnames, user]
#
def jobid2hosts(jobid):

	# Call squeue to know the list of compute nodes for this job
	cmd = ['squeue','-o','"%t@%P@%R@%u','-h','-j',str(jobid)]

	while(True):
		try:
			tmp = subprocess.check_output(cmd)
			tmp = tmp.rstrip('"\n')
			tmp = tmp.strip('"')
			tmp = tmp.split('@')
		except subprocess.CalledProcessError:
			sys.stderr.write ("ERROR - squeue did not work, may be the job is finished ?\n")
			exit(1)
		
		if tmp[0] == 'PD':
			time.sleep(30)		# Pending: sleep 30s before retrying
			continue
			
		if tmp[0] == 'R':	# Running !
			break

		sys.stderr.write ("ERROR - THE job " + str(jobid) + " is NOT running\n")
		exit(1)
	
	partition = tmp[1]
	#hosts     = expandNodeList(tmp[2])
	hosts     = tmp[2]
	user      = tmp[3]
	return [partition,hosts,user]
	 
#else:
#	hosts = utilities.expandNodeList(tmp[1])
		
	return hosts
			
#import utilities

#
# Use: placement-cont 12345 60
#
#      1/ Detect the list of hosts corresponding to the job 12345
#      2/ Open 1 output file / host
#      3/ For each host, call placement --host hostN --csv, append 1 line to the corresponding file
#      4/ If there is an error, exit
#      5/ Sleep 60 s
#      6/ Go to 3/
#      

def Usage():
	sys.stderr.write ("Usage: placement-cont 12345 60")
	sys.stderr.write ("placement-cont calls placement continuously to check a running job")
	sys.stderr.write ("       12345 = Some jobid")
	sys.stderr.write ("          60 = sleeptime before next check")
	
# Main program
#if len(sys.argv) != 3:
#	Usage()
#	exit(1)
#else:
#	jobid     = sys.argv[1]
#	sleeptime = sys.argv[2]

# Call squeue to know the list of compute nodes for this job
#cmd = ['squeue','-o','"%t %B"','-h','-j',str(jobid)]

#try:
#	tmp = subprocess.check_output(cmd)
#	tmp = tmp.rstrip('"\n')
#	tmp = tmp.strip('"')
#	tmp = tmp.split(' ')
#except subprocess.CalledProcessError:
#	print "ERROR - squeue did not work, may be the job is finished ?"
#	exit(1)

#if tmp[0]!="R":
#	print "ERROR - THE job " + str(jobid) + " is NOT running"
#	exit(1)
#else:
#	hosts = utilities.expandNodeList(tmp[1])
	
#print (hosts)

if __name__ == "__main__":
    main()
