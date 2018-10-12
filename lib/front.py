#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your options) any later version.
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
from utilities import runCmd,runCmdNoOut,getHostname
from slurm import *
from exception import *

class FrontNode(object):
    """This class is useful when we are logged on the front node, and we want to execute placement
       on some other node.
       Typical use case: we are on the front node and we want to check a running job on a compute node
    """

    def __init__(self,externals):
        """ externals = An array of external commands, used to decide which JobSched objet to instantiate
        """
        self.options  = None
        self.argv     = None
        if 'squeue' in externals:
            self.__sched_name = 'slurm'
            self.__sched      = Slurm()
        else:
            self.__sched_name = ""
            self.__sched      = None
        
    def __pyPath(self,exe=None):
        """From an exe, compute the path to a python program """
        if exe==None:
            exe = 'placement.py'
        exe =  os.environ['PLACEMENT_ROOT'] + '/lib/' + exe
        return exe
            
    def __runPlacement(self,host):
        """Run placement on another host, using self.argv"""

        cmd = self.argv.copy()        
        cmd.append('--from-frontal')
        
        if host!=getHostname():
            os.environ['PLACEMENT_REMOTE'] = host

        cmd.insert(0,os.environ['PLACEMENT_PYTHON'])
        runCmdNoOut(cmd)
            
        os.environ.pop('PLACEMENT_REMOTE',None)
        
    def setOptions(self,options,argv):
        """ Initialize together options and argv """
        self.options = options
        self.argv    = argv.copy()
        
    def getJobSchedName(self): 
        return self.__sched_name

    def runPlacement(self):
        """ For some options, we run placement or another exe, maybe on another host
            Return True if we launched another exe
            Return False if we just return without doing anything
        """

        # If the switch --from-front is specified, we were already launched by placement.py: return False, avoiding an infinite loop
        if self.options.ff:
            return False

        # Supervision experimental options            
        if self.options.continuous:
            self.argv[0] = self.__pyPath('placement-cont.py')
            self.argv.append("--from-frontal")
            try:
                runCmdNoOut(self.argv)
            except:
                pass
            return True
            
        # Another supervision options:
        if self.options.pathological:
            self.argv[0] = self.__pyPath('placement-patho.py')
            try:
                runCmdNoOut(self.argv)
            except:
                pass
            return True
        
        # The jobid switch and the checkme switch:
        #     Detect the jobid corresponding the --checkme
        #     Then, detect the nodeset we are using for this job and call placement on the first node only
        if self.__sched_name != "":
            if self.options.jobid or self.options.checkme:
                if self.options.checkme:
                    jobid = self.__sched.findMyJob()[2]
                    if jobid=="":
                        raise PlacementException("ERROR - --checkme is a nonsense if you do not have any running job !")
                    self.argv.remove('--checkme')
                    self.argv.append('--jobid')
                    self.argv.append(jobid)
                else:
                    jobid = self.options.jobid
                    
                (nodeset,user,j) = self.__sched.findJobFromId(jobid)
                if nodeset=="":
                    raise PlacementException("ERROR - Bad jobid ! (" + str(jobid) + ")")
    
                host = self.__sched.nodesetToHost(nodeset)
                
                # We check only the user who launched the job
                self.argv.append('--check')
                self.argv.append(user)
                self.__runPlacement(host)
                return True

        # The host switch:
        #     Translate to a list of hosts and call placement on each host
        if self.options.host:
            hosts = self.__sched.nodesetToHosts(self.options.host)
            
            # We check everything on each host
            self.argv.append('--check')
            self.argv.append('ALL')
            for h in hosts:
                try:
                    self.__runPlacement(h)
                except PlacementException as e:
                    print ("host " + h)
                    print (e)
                    print ()
                    
            return True
                     
        return False