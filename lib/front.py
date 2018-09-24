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
from utilities import runCmd,runCmdNoOut,getHostname
from slurm import *
from exception import *

class FrontNode(object):
    """This class is useful when we are logged on the front node, and we want to execute placement
       on some other node.
       Typical use case: we are on the fron node and we want to check a running job on a compute node
    """

    def __init__(self,option,argv):
        self.option  = option
        self.argv    = argv.copy()
        self.__sched = Slurm()
        
    def __pyPath(self,exe=None):
        """From an exe, compute the path to a python program """
        if exe==None:
            exe = 'placement.py'
        exe =  os.environ['PLACEMENT_ROOT'] + '/lib/' + exe
        return exe
            
    def __runPlacement(self,host):
        """Run placement on another host, using self.argv"""

        cmd = self.argv.copy()        
        cmd.append('--from_frontal')
        
        if host==getHostname():
            # Same host = we use placement.py as entry point and we do not use ssh
            #             Call through $PLACEMENT_PYTHON
            cmd.insert(0,os.environ['PLACEMENT_PYTHON'])
            runCmdNoOut(cmd)
            
        else:
            # We run placement on another host
            # The entry point must be the bash script, may be there is some stuff to init
            cmd[0]= os.environ['PLACEMENT_ROOT'] + '/bin/placement'
            runCmdNoOut(cmd,host)
                    
    def runPlacement(self):
        """ For some options, we run placement or another exe, maybe on another host
            Return True if we launched another exe
            Return False if we just return without doing anything
        """

        # If the switch --from-front is specified, we were already launched by placement.py: return False, avoiding an infinite loop
        if self.option.ff:
            return False

        # Supervision experimental option            
        if self.option.continuous:
            self.argv[0] = self.__pyPath('placement-cont.py')
            try:
                runCmdNoOut(self.argv)
            except:
                pass
            return True
            
        # Another supervision option:
        if self.option.pathological:
            self.argv[0] = self.__pyPath('placement-patho.py')
            try:
                runCmdNoOut(self.argv)
            except:
                pass
            return True
        
        # The jobid switch and the checkme switch:
        #     Detect the jobid corresponding the --checkme
        #     Then, detect the nodeset we are using for this job and call placement on the first node only
        if self.option.jobid or self.option.checkme:
            if self.option.checkme:
                jobid = self.__sched.findMyJob()[2]
                if jobid=="":
                    raise PlacementException("ERROR - --checkme is a nonsense if you do not have any running job !")
                self.argv.remove('--checkme')
                self.argv.append('--jobid')
                self.argv.append(jobid)
            else:
                jobid = self.option.jobid
                
            (nodeset,user,j,partition) = self.__sched.findJobFromId(jobid)
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
        if self.option.host:
            hosts = self.__sched.nodesetToHosts(self.option.host)
            
            # We check everything on each host
            self.argv.append('--check')
            self.argv.append('ALL')
            for h in hosts:
                self.__runPlacement(h)
            return True
                     
        return False
