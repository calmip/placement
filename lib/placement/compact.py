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
from exception import *
from tasksbinding import *
from scatter import *

class CompactGenMode(TasksBinding):
    """ Distributing processes on core in "scatter" modes, this generic class is a base class """


    def __init__(self,archi,check=True,cpus_per_task=0,tasks=0):
        TasksBinding.__init__(self,archi,cpus_per_task,tasks)

    def checkParameters(self):
        self._checkParameters()

        if self.cpus_per_task % self.archi.threads_per_core!=0:
            msg = "OUPS - cpus_per_task ("
            msg += str(self.cpus_per_task)
            msg += ") => should be a multiple of ("
            msg += str(self.archi.threads_per_core)
            msg += ")"
            raise PlacementException(msg)


class CompactMode(CompactGenMode):
    """Compact distribution mode

    # placement 4 4 --ascii --mode=compact 
      S0-------- S1-------- 
    P AAAABBBBCC CCDDDD.... 

    # placement 4 4 --ascii --mode=compact --hyper
      S0-------- S1-------- 
    P AABBCCDD.. .......... 
    L AABBCCDD.. .......... 

    """

    def __init__(self,archi,check=True):
        TasksBinding.__init__(self,archi)
        self.distribTasks(check)
        
    def distribTasks(self, check=True):
        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        tasks_bound=[]
        t_binding=[]
        t = 0
        th= 0
        for s in self.archi.l_sockets:
            for c in range(self.archi.cores_per_socket):
                for h in range(self.archi.threads_per_core):
                    c1 = s*self.archi.cores_per_socket + c
                    if self.archi.m_cores != None and self.archi.m_cores[s][c1] == False:
                        continue
                    t_binding += [h*self.archi.cores_per_node + s*self.archi.cores_per_socket + c]
                    th+=1
                    if th==self.cpus_per_task:
                        tasks_bound += [t_binding]
                        t_binding = []
                        th = 0
                        t += 1
                        if (t==self.tasks):
                            self.tasks_bound = tasks_bound
                            return self.tasks_bound

        # normalement on ne passe pas par là on a déjà retourné
        self.tasks_bound = tasks_bound
        return tasks_bound

#
# class CompactMode, dérive de TaskBinding, implémente les algos utilisés en mode compact
#                    Utilisé lorsque le switch --hyper_as_physical est utilisé, traite les cœurs logiques
#                    comme des sockets supplémentaires
#
class CompactPhysicalMode(CompactGenMode):
    """ Compact special mode, used when --hyper_physical is activated

    # ./placement -A 4 4 --mode=compact --hyper_as_physical
    S0-------- S1-------- 
    P AAAABBBBCC .......... 
    L CCDDDD.... ..........
    
    """

    def __init__(self,archi,check=True):
        TasksBinding.__init__(self,archi)
        self.distribTasks(check)
        
    def distribTasks(self, check=True):
        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        tasks_bound=[]
        t_binding=[]
        t = 0
        th= 0
        for s in self.archi.l_sockets:
            for h in range(self.archi.threads_per_core):
                for c in range(self.archi.cores_per_socket):
                    c1 = s*self.archi.cores_per_socket + c
                    if self.archi.m_cores != None and self.archi.m_cores[s][c1] == False:
                        continue
                    t_binding += [h*self.archi.cores_per_node + s*self.archi.cores_per_socket + c]
                    th+=1
                    if th==self.cpus_per_task:
                        tasks_bound += [t_binding]
                        t_binding = []
                        th = 0
                        t += 1
                        if (t==self.tasks):
                            self.tasks_bound = tasks_bound
                            return self.tasks_bound

        # normalement on ne passe pas par là on a déjà retourné
        self.tasks_bound = tasks_bound
        return tasks_bound
