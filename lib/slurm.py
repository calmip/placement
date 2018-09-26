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

from jobsched import *
from utilities import runCmd
from exception import *

class Slurm(JobSched):
    """This class extends JobSched, it should be used with the Slurm job scheduler
       See the documentation in jobsched.py
    """

    def findJobFromId(self,jobid):
        
        cmd = 'squeue -t RUNNING -j ' + str(jobid) + ' --noheader -o %.16R@%.15u@%.7A'
        try:
            rvl = runCmd(cmd)
        except:
            return ("","","")
        
        if rvl == "":
            return ("","","")

        # host[0-4]@   user@jobid  @partition ==> (host[0-4],user,jobid,partition)
        return tuple(map(str.strip,rvl.split('@'))) 

    def findJobsFromUser(self,user):
        
        cmd = 'squeue -t RUNNING -u ' + user + ' --noheader -o %.16R@%.15u@%.7A'
        try:
            rvl = runCmd(cmd)
        except:
            return ("","","")
        
        if rvl == "":
            return ("","","")

        tuples = []

        # host[0-4]@   user@jobid  @partition ==> (host[0-4],user,jobid,partition)
        for j in rvl.split('\n'):
            tuples.append(tuple(map(str.strip,rvl.split('@'))))
            
        return tuples

    def nodesetToHosts(self,nodeset):

        try:
            nodes = runCmd('nodeset -e ' + nodeset).rstrip().split(' ')
        except:
            return []

        return nodes

