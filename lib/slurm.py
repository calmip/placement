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
import os

class Slurm(JobSched):
    """This class extends JobSched, it should be used with the Slurm job scheduler
       See the documentation in jobsched.py
    """

    def __init__(self):
        self.__pid2jobid = None
        self.__core2jobid= None
        self._job2tag    = None
        
    def __initDataStructures(self):
        '''Init self.__pid2jobid and self.__core2jobid 
           Explore the /sys/fs/cgroup/cpuset pseudo filesystem'''
        
        # If the data do not exist, build them, else return
        if self.__pid2jobid == None or self.__core2jobid == None:
            
            pid2jobid = {}
            core2jobid= {}
            
            # Looking for /sys/fs/cgroup/cpuset/slurm/uid_xxx/job_yyyyyy/step_batch
            top_dir = "/sys/fs/cgroup/cpuset/slurm/"
            for root, dirs, files in os.walk(top_dir,False):
                leaf = os.path.basename(root)
                if leaf.startswith('step_'):
                    job_path = os.path.split(root)[0];    # => .../slurm/uid_xxx/job_yyyyyy
                    job_dir  = os.path.split(job_path)[1] # => job_yyyyyy
                    jobid    = job_dir.replace('job_','') # => yyyyyy
                    
                    # The pids are in the file cgroup.procs
                    pids = []
                    cgroup_procs = root + '/cgroup.procs'
                    with open(cgroup_procs, 'r') as infile:
                        for line in infile:
                            line = line.strip()
                            if line != '':
                                pid2jobid[line] = jobid
                                
                    # The cores are in the file cpuset.cpus
                    cpuset_cpus = root + '/cpuset.cpus'
                    with open(cpuset_cpus, 'r') as infile:
                        for line in infile:
                            line = line.strip()
                            if line != '':
                                # Nearly same format for the cpusets as for the nodesets !
                                cores = self.nodesetToHosts('['+line+']')
                                for core in cores:
                                    core2jobid[core] = jobid
        
            # build the map self._job2tag
            jobids = set(core2jobid.values())
            t = 0;
            m = {}
            for j in jobids:
                t += 1;
                m[j] = t
                
            
            self.__pid2jobid = pid2jobid
            self.__core2jobid= core2jobid
            self._job2tag    = m
            
            #import pprint
            #pprint.pprint(pid2jobid)
            #pprint.pprint(core2jobid)

    def findJobFromId(self,jobid):
        """Call squeue and return a tuple with user/nodeset/jobid """
        
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
        """Call squeue and return a list of tuples corresponding to the jobs running for this user"""
        
        cmd = 'squeue -t RUNNING -u ' + user + ' --noheader -o %.16R@%.15u@%.7A'
        try:
            rvl = runCmd(cmd)
        except:
            return [("","","")]
        
        if rvl == "":
            return [("","","")]

        tuples = []

        # host[0-4]@   user@jobid  @partition ==> (host[0-4],user,jobid,partition)
        for j in rvl.split('\n'):
            tuples.append(tuple(map(str.strip,j.split('@'))))
            
        return tuples

    def nodesetToHosts(self,nodeset):
        """Expand the nodeset to a list of hosts"""

        try:
            nodes = runCmd('nodeset -e ' + nodeset).rstrip().split(' ')
        except:
            return []

        return nodes

    def findJobFromPid(self,pid):
        """Return the jobid from the pid, or "" if not found"""
        
        self.__initDataStructures()
        pid = str(pid)
        if pid in self.__pid2jobid:
            return self.__pid2jobid[pid]
        
        else:
            return ""

    def findJobFromCore(self,core):
        """Return the jobid from the core, or "" if not found"""
        
        self.__initDataStructures()
        core = str(core)
        if core in self.__core2jobid:
            return self.__core2jobid[core]
        
        else:
            return ""
