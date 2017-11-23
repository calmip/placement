#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
import re
import subprocess
from exception import *
from itertools import chain,product

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  Copyright (C) 2015,2016 Emmanuel Courcelle
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


def removeBlanks(L):
    """ remove the blanks from list of strings passed by parameters"""

    try:
        while True:
            L.remove('')
    except:
        pass


def numTaskToLetter(n):
    """ Return a single letter (A-Z-a-z0-9) from a (task) number (0..66) """

    if n<0 or n>66:
        raise PlacementException("ERREUR INTERNE - Si plus de 62 tâches, utilisez getCpuTaskAsciiBinding")
    if n<26:
        return chr(65+n)   # A..Z
    if n<52:
        return chr(71+n)   # a..z  (71=97-26)
    return chr(n-4)        # 0..>  (-4=53-48)


def list2CompactString(A):
    """ Return a compact list 0-2,5-7,9 from a list of integers [0,1,2,5,6,7,9] """

    # Convert to a sorted set to avoid doublons
    s0 = set(A)
    s  = list(s0)
    s.sort()

    # Rewrite s
    tmp=[]
    last_c=-1
    start=-1
    end=-1

    def __compact(tmp,start,end):
        """ Return tmp (a list) with '0' or 4-2' appended to it """

        if start==end:
            tmp += [str(start)]
        else:
            tmp += [str(start)+'-'+str(end)]

    for c in s:
        if start==-1:
            start=c
        if last_c==-1:
            last_c=c
        else:
            if c-last_c==1:
                last_c=c
            else:
                __compact(tmp,start,last_c)
                start=c
                last_c=c
                
    if last_c>-1:
        __compact(tmp,start,last_c)
    return ','.join(tmp)

def expandNodeList(nodelist):
    """ Return a list nodes, just like ExpandNodeList
        toto[5-6] -> return ['toto5','toto6'] 
        toto      -> return ['toto'] """
    
    matches = re.match('(.+)\[(.+)\](.*)',nodelist)
    if matches:
        prefix = matches.group(1)
	postfix= matches.group(3)
        #print map(lambda x:prefix+str(x)+postfix,compactString2List(matches.group(2)))
        return map(lambda x:prefix+str(x)+postfix,compactString2List(matches.group(2)))
    else:
        return [ nodelist ]

def getHostname():
    """ Return the environment HOSTNAME if set, else call /bin/hostname -s"""
    if 'HOSTNAME' in os.environ:
        return os.environ['HOSTNAME']
    else:
        cmd = "/bin/hostname -s"
        p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        p.wait()

        # If error, it is a Fatal Error !!!
        if p.returncode !=0:
            msg = "OUPS "
            msg += "/bin/hostname -s returned an error !"
            raise PlacementException(msg)
        else:
            return p.communicate()[0].split('\n')[0]
        
def compactString2List(S):
    """ Return a list of integers [0,1,2,5,6,7,9] from a compact list 0-2,5-7,9 """

    rvl = []
    if S != "":
        a   = S.split(',')
        for s in a:
            c = s.split('-')
            if len(c) == 1:
                rvl.append([int(c[0])])
            else:
                # [0-3] ==> 0,1,2 + 3
                l0 = int(c[0])
                l1 = int(c[1])
                if l0 < l1:
                    rvl.append(range(l0,l1))
                    rvl.append([l1])
                else:
                    rvl.append(range(l1,l0))
                    rvl.append([l0])

        rvl = list(chain(*rvl))
    return rvl

            
def computeCpusTasksFromEnv(options,args):
    """ Return cpu_per_task and tasks from the environment or from the switches"""

    # Default values, if nothing else specified
    cpus_per_task = 4
    tasks         = 4

    # --- COMPUTING TASKS PER NODE ---
    # If mpi_aware, consider PLACEMENT_SLURM_TASKS_PER_NODE, else consider SLURM_TASKS_PER_NODE
    slurm_tasks_per_node = '0'
    if options.mpiaware:
        if 'PLACEMENT_SLURM_TASKS_PER_NODE' in os.environ:
            slurm_tasks_per_node = os.environ['PLACEMENT_SLURM_TASKS_PER_NODE']
    else:
        if 'SLURM_TASKS_PER_NODE' in os.environ:
            slurm_tasks_per_node = os.environ['SLURM_TASKS_PER_NODE']

    # If possible, use the SLURM environment
    if slurm_tasks_per_node != '0':
        tmp = slurm_tasks_per_node.partition('(')[0]         # 20(x2)   ==> 2
        tmp = map(int,tmp.split(','))                        # '11,10'  ==> [11,10]
        if len(tmp)==1:
            tasks = tmp[0]
        elif len(tmp)==2:
            tasks = min(tmp)
            if options.asciiart or options.human:
                msg = "WARNING - SLURM_TASKS_PER_NODE = " + slurm_tasks_per_node + "\n"
                msg+= "          We are probably using a cleint-server paradigm, placement takes into account " + str(tasks) + " tasks"
                print msg
                print 
        else:
            msg =  "OUPS - Placement not supported in this configuration:\n"
            msg += "       SLURM_TASKS_PER_NODE = " + slurm_tasks_per_node
            raise PlacementException(msg)

    # --- COMPUTING CPUS PER TASK ---
    # If mpi_aware, consider PLACEMENT_SLURM_CPUS_PER_TASK, else consider SLURM_CPUS_PER_TASK
    slurm_cpus_per_task = '0'
    if options.mpiaware:
        if 'PLACEMENT_SLURM_CPUS_PER_TASK' in os.environ:
            slurm_cpus_per_task = os.environ['PLACEMENT_SLURM_CPUS_PER_TASK']
    else:
        if 'SLURM_CPUS_PER_TASK' in os.environ:
            slurm_cpus_per_task = os.environ['SLURM_CPUS_PER_TASK']

    if slurm_cpus_per_task != '0':
        cpus_per_task = int(slurm_cpus_per_task)
    
    # In anything specified in the command line, use it preferably
    if args[1] > 0:
        cpus_per_task = int(args[1])
    if args[0] > 0:
        tasks         = int(args[0])

    # Returning computing values
    return [cpus_per_task,tasks]

def bold():
    return '\033[1m'

def underline():
    return '\033[41m'

def boldunderline():
    return '\033[1;4m'

def white_background():
    return '\033[47m'

def red_foreground():
    return '\033[1;31m'

def mag_foreground():
    return '\033[1;35m'

# Back to "normal"
def normal():
    return '\033[0m'

