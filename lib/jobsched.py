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

#import os
from utilities import runCmd
#from exception import *

class JobSched(object):
    """This class is an abstract class, all classes related to the job schedulers extend this class"""

    def findJobFromId(self,jobid):
        """Return a tuple representing the job of the jobid passed by parameter.
           Return (user,nodeset,jobid,partition)
           user      = The user who launched the job
           nodeset   = A list of nodes used by the job
           jobid     = The jobid
           If jobid does not exist or is not running, return ("","","")
           WARNING - Jobs in any other state than RUNNING are ignored"""

        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"

    def findJobsFromUser(self,user):
        """Return a list of tuples representing the jobs launched by the user passed by parameter.
           Return a list of (user,nodeset,jobid,partition)
           user      = The user who launched the job
           nodeset   = A list of nodes, used by the job
           jobid     = The jobid
           partition = A set of nodes, not used by placement - You can forget it
           If user does not exist or does not have any job running, return []
           WARNING - Jobs in any other state than RUNNING are ignored"""

        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"

    def findJobFromPid(self,pid):
        """Return the jobid, from the process id"""
		
        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"

    def findJobFromCore(self,pid):
        """Return the jobid, from the core number"""
		
        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"

    def findTagFromJob(self,jobid):
        """Return a 'jobtag' from the job number, or 0 if the job number is not found
           the map: self._job2tag is built by the derived classes"""
        
        if jobid in self._job2tag:
            return int(self._job2tag[jobid])
        else:
            return 0
        
    def findMyJob(self):
        """Call FindJobsFromUser, passing the output of whoami, and keeping only the FIRST job returned
           Return  a tuple (jobid,partition,user,nodeset), or ("","","")
           WARNING - Jobs in any other state than RUNNING are ignored"""
           
        user = runCmd('whoami').rstrip()
        return self.findJobsFromUser(user)[0]
    
    def nodesetToHosts(self,nodeset):
        """From a nodeset, ie a string representing a set of nodes, return the list of corresponding nodes
           May return []
        """

        return "INTERNAL ERROR - ABSTRACT CLASS !!!!!"

    def nodesetToHost(self,nodeset):
        """Call nodesetToHosts and return the first one, or "" """
        
        l = self.nodesetToHosts(nodeset)
        if len(l)>0:
            return l[0]
        else:
            return ""

