#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *

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

    
class TasksBinding(object):
    """ TasksBinding contains the algorithms used to distribute tasks and threads on cores

    This is an abstract class, the real derived class depends on the chosen algorithm

    DATA STRUCTURES:
    threads_bound = Only built in running mode: see running.py, L 135
    tasks_bound   = A list of lists, describing the list of cores(inner lists) of the tasks (outer list)
    over_cores    = A list of cores bound to 2 or more tasks
    """

    def __init__(self,archi,cpus_per_task=0,tasks=0):
        self.archi = archi
        if archi != None and cpus_per_task == 0:
            self.cpus_per_task = self.archi.cpus_per_task
        else:
            self.cpus_per_task = cpus_per_task
        if archi != None and tasks == 0:
            self.tasks         = self.archi.tasks
        else:
            self.tasks         = tasks
        self.tasks_bound   = None
        self.threads_bound = None
        self.over_cores    = None

    def checkParameters(self):
        """ Check the parameters, raise an exception if anything wrong"""

        raise("ERROR - VIRTUAL PURE FONCTION !")
    def distribTasks(self,check=True):
        """ Return tasks_bound as a list of lists

        tasks_bound is a list of lists, each list is a list of cores used by the process
        psrN means 'Core nb n':
        [[psr1,psr2],[psr3,psr4],...]
        """
        raise("ERROR - VIRTUAL PURE FUNCTION !")

    def PrintingForVerbose(self):
        raise("ERROR - VIRTUAL PURE FUNCTION !")

    def _checkParameters(self):
        """ Should be called by ALL checkParameters methods in the derived classes.

        Raise of exception in case of a problem
        """

        if (self.cpus_per_task<0 or self.tasks<0 ):
            raise PlacementException("OUPS - Every parameter should be integer, >= 0")
        if self.cpus_per_task*self.tasks>self.archi.threads_per_core*self.archi.cores_reserved:
            msg = "OUPS - Not enough cores ! Please lower cpus_per_task (";
            msg += str(self.cpus_per_task)
            msg += ") or tasks ("
            msg += str(self.tasks)
            msg += ")"
            msg += ' NUMBER OF LOGICAL CORES RESERVED FOR THIS PROCESS = ' + str(self.archi.cores_reserved*self.archi.threads_per_core)
            raise PlacementException(msg)

    def threadsSort(self):
        """Sort inplace the threads inside their processes"""

        for p in self.tasks_bound:
            p.sort()

    def keepOnlyMpiRank(self):
        """Used when mpi_aware mode: keep only the task corresponding to the mpi rank"""

        rank = -1;
        try:
            # Le rank si on utilise openmpi, bullx_mpi, etc.
            rank = os.environ['OMPI_COMM_WORLD_RANK']
        except KeyError:
            pass

        if rank == -1:
            try:
                # Le rank si on utilise intelmpi
                rank = os.environ['PMI_RANK']
            except KeyError:
                msg = "NINI ERROR - NOT intelmpi, NOT bullxmpi, NOT openmpi"
                for k in os.environ.keys():
                    print k + ' => ' + os.environ[k]

                raise PlacementException(msg)

        rank = int(rank)
        if rank>=len(self.tasks_bound):
            msg  = "ERREUR de placement mpi_aware - rank vaut " + str(rank)
            msg += " alors qu'il n'y a que " + str(len(self.tasks_bound)) + " tâches !"
            raise PlacementException(msg)

        rank_tasks_bound = []
        rank_tasks_bound.append(self.tasks_bound[rank])
        self.tasks_bound = rank_tasks_bound

