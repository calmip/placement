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

class ScatterGenMode(TasksBinding):
    """ Distributing processes on cores in "scatter" modes, this generic class is a base class

    Two scatter modes are currently implemented:
        1/ scatter (default mode)
           # placement 8 4 --ascii --mode=scatter
           S0-------- S1-------- 
           P AABBCCDD.. EEFFGGHH.. 
           L AABBCCDD.. EEFFGGHH.. 

        2/ scatter_block
           # placement 8 4 --ascii --mode=scatter_block --hyper
           S0-------- S1-------- 
           P AAAAEEEE.. BBBBFFFF.. 
           L CCCCGGGG.. DDDDHHHH.. 

    """

    def __init__(self,archi,cpus_per_task=0,tasks=0):
        TasksBinding.__init__(self,archi,cpus_per_task,tasks)

    def checkParameters(self):
        """ Avoiding tasks straddling different sockets and other ugly things"""

        self._checkParameters()

        # Allow 1 thread, or a multiple of threads_per_core
        if self.cpus_per_task>1 and self.cpus_per_task % self.archi.threads_per_core!=0:
            msg = "ERROR - cpus_per_task ("
            msg += str(self.cpus_per_task)
            msg += ") => should be a multiple of threads_per_core ("
            msg += str(self.archi.threads_per_core)
            msg += ")"
            raise PlacementException(msg)

        # max_cpus = It more than 1 task, each must have less threads than logical cores/socket
        if self.tasks > 1:
            if self.cpus_per_task > self.archi.threads_per_core*self.archi.cores_per_socket:
                msg  = "ERROR - Please reduce the threads number (max threads number = " + str(self.archi.threads_per_core*self.archi.cores_per_socket) +")\n"
                msg += "        Or use only ONE task/node and go to mode scatter !"
                raise PlacementException(msg)
                
        # Avoiding tasks straddling on several sockets ! 
        # If 1 task, the number of threads should be even (because we straddle between sockets !)
        # If not, ajust number of threads
        # TODO - This is great for a bisocket node, but how to manage machines with more than 2 sockets ?
        if self.tasks == 1 and self.cpus_per_task % 2 == 1:
            self.cpus_per_task += 1

        max_tasks = self.archi.sockets_reserved * self.archi.threads_per_core * (self.archi.cores_per_socket//self.cpus_per_task)
        if self.cpus_per_task>1:
            if self.tasks>max_tasks and max_tasks>0:
                msg = "ERROR - One task is straddling two sockets ! Please lower the number of tasks/node, max is "
                msg += str(max_tasks)
                raise PlacementException(msg)


class ScatterMode(ScatterGenMode):
    """Scatter cyclic distribution mode"""

    def __init__(self,archi,check=True,cpus_per_task=0,tasks=0):
        ScatterGenMode.__init__(self,archi,cpus_per_task,tasks)
        self.distribTasks(check)
        
    def distribTasks(self,check=True):
        """Return self.tasks_bound"""

        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        # If only ONE task, it is exploded between available sockets
        if self.tasks==1:
            self.tasks_bound = self.__distribManyThreadsSingleTask(self.cpus_per_task)

        else:
            # If monothreaded tasks
            if self.cpus_per_task==1:
                self.tasks_bound = self.__distribSingleThreadManyTasks(self.tasks)
            
            # If multithreaded tasks: do not straddle between sockets !
            else:
                self.tasks_bound = self.__distribManyThreadsManyTasks(self.cpus_per_task,self.tasks)

        return self.tasks_bound

    def __distribSingleThreadManyTasks(self,tasks):
        """Implementing the distribTasks algo when there are many monothreaded tasks"""


        # The number of physical cores we have
        nb_of_cores = self.archi.hardware.CORES_PER_SOCKET * self.archi.sockets_reserved
        
        # Less tasks than cores - __distribManyThreadsManyTasks works well
        if tasks <= nb_of_cores:
            return self.__distribManyThreadsManyTasks(1,tasks)
            
        # More tasks than cores = Use hyperthreading !
        else:
            # The first nb_of_cores tasks
            tasks_bound     = self.__distribManyThreadsManyTasks(1,nb_of_cores)

            # Compute tasks_bound for the remaining tasks
            tasks_rem       = tasks - nb_of_cores
            tasks_bound_rem = self.__distribManyThreadsManyTasks(1,tasks_rem)

            # Correct the result and append to tasks_bound
            for t in tasks_bound_rem:
                tasks_bound.append([t[0]+self.archi.cores_per_node])
            
            return tasks_bound
        
        
    def __distribManyThreadsSingleTask(self,cpus_per_task):
        """Implementing the distribTasks algo when only one task / many threads"""

        tasks_bound = []
        
        # tmpl is a "template" describing the distribution of the cores for 1 task
        tmpl = self.__compute_task_template(cpus_per_task,True)

        t_bound = []
        for s in self.archi.l_sockets:
            c_start = s * self.archi.cores_per_socket
            for c in tmpl:
                t_bound.append(c_start+c)

        tasks_bound.append(t_bound)
        return tasks_bound

    def __distribManyThreadsManyTasks(self,cpus_per_task,tasks):
        """Implementing the distribTasks algo when many tasks / many threads"""
    
        tasks_bound = []
        
        # tmpl is a "template" describing the distribution of the cores for 1 task
        tmpl = self.__compute_task_template(cpus_per_task)

        # q = number of tasks / socket
        # r = supplementary tasks on first sockets
        q = tasks // self.archi.sockets_reserved
        r = tasks % self.archi.sockets_reserved

        # hp = number of physical cores used by each task (at least 1)
        hp = cpus_per_task // self.archi.threads_per_core
        if hp==0:
            hp=1

        # si = the index in the l_sockets list
        # s  = The socket
        si = 0
        s = self.archi.l_sockets[si]

        # c  = the core, relative to the socket
        # ca = the core, absolute address
        c = 0
        ca = 0

        # cpt_t = Tasks counter on the current socket
        cpt_t = 1

        # Each task uses the same template
        for t in range(tasks):
            ca = s * self.archi.cores_per_socket + c
            t_bound = []
            for h in range(cpus_per_task):
                t_bound.append(ca + tmpl[h])
            tasks_bound.append(t_bound)

            # Compute the next task position
            if cpt_t<q:
                cpt_t += 1
                c     += hp
            elif si<r and cpt_t==q:
                cpt_t += 1
                c     += hp
            else:
                si    += 1
                if si==len(self.archi.l_sockets):
                    break

                s     =  self.archi.l_sockets[si]
                c     =  0
                cpt_t = 1
                
        return tasks_bound

    def __compute_task_template(self,cpus_per_task,explode=False):
        """ Return the cores used by the FIRST task, the pattern will be reproduced by every task.

        If explode == true, the task is exploded between the sockets
        """

        tmpl = []
        c = 0
        y = 0
        if explode:
            nb_cores = cpus_per_task // self.archi.sockets_reserved
        else:
            nb_cores = cpus_per_task

        nb_phys_core = nb_cores // self.archi.threads_per_core
            
        for t in range(0,nb_cores):
            tmpl.append(c)
            c += 1
            if (c == nb_phys_core):
                y += 1
                c = y*self.archi.cores_per_node
        return tmpl

    def test__compute_task_template(self,explode=False):
        '''DO NOT USE - Useful only for unit tests'''

        return self.__compute_task_template(self.cpus_per_task,explode)

#
# class ScatterMode, dérive de TaskBinding, implémente les algos utilisés en mode scatter
#

class ScatterBlockMode(ScatterGenMode):
    """Scatter block distribution mode"""

    def __init__(self,archi,check=True,cpus_per_task=0,tasks=0):
        ScatterGenMode.__init__(self,archi,cpus_per_task,tasks)
        self.distribTasks(check)
        
    def distribTasks(self,check=True):
        """Return self.tasks_bound"""

        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        # cpus_per_task lower than cores_per_socket
        #
        # placement -A   --mode=scatter_block 4 4
        #   S0-------- S1-------- 
        # P AAAACCCC.. BBBBDDDD.. 
        
        # placement -A   --mode=scatter_block --hyper 4 4
        #   S0-------- S1-------- 
        # P AAAA...... BBBB...... 
        # L CCCC...... DDDD...... 
        if self.cpus_per_task <= self.archi.cores_per_socket and self.tasks>1:

            c_step = self.cpus_per_task
            tasks_bound=[]
            t_binding=[]
            t = 0
            th= 0
            #print str(range(0,self.archi.cores_per_socket,c_step))+' ('+str(0)+','+str(self.archi.cores_per_socket)+','+str(c_step)+')'

            # Looping on the cores
            for c in range(0,self.archi.cores_per_socket,c_step):
                #print "   "+str(range(self.archi.threads_per_core))
                
                # Looping on the threads of each core (hyperthreading)
                for y in range(self.archi.threads_per_core):
                    #print "      "+str(self.archi.l_sockets)

                    # Looping on the sockets
                    for s in self.archi.l_sockets:
                        #print "         "+str(range(self.cpus_per_task))

                        # Looping on the process threads
                        for th in range(self.cpus_per_task):
                            t_binding += [y*self.archi.cores_per_node + s*self.archi.cores_per_socket + c + th]

                        tasks_bound += [t_binding]
                        t_binding = []
                        t += 1
                        if (t==self.tasks):
                            self.tasks_bound = tasks_bound
                            return self.tasks_bound

        # cpus_per_task HIGHER than cores_per_socket
        #
        # placement --ascii --mode=scatter_block 2 16
        #   S0-------- S1-------- 
        # P AAAAAAAA.. AAAAAAAA.. 
        # L BBBBBBBB.. BBBBBBBB.. 
        else:
            # TODO - ONLY TESTED WITH 2 THREADS/CORE ! (Xeon OK, KNL not tested)
            # nb of tasks x2, nb of threads /2 then recursive call
            tmp_task_distrib = ScatterBlockMode(self.archi,
                                                check,
                                                self.cpus_per_task//2,
                                                self.tasks*2)
            tmp_tasks_bound= tmp_task_distrib.distribTasks(check=False)

            # Parameter was self.tasks*2, so imax IS an even number
            imax = len(tmp_tasks_bound)

            tasks_bound = []
            for i in range(0,imax,2):
                t=[]
                t.extend(tmp_tasks_bound[i])
                t.extend(tmp_tasks_bound[i+1])
                tasks_bound.append(t)
            
            self.tasks_bound = tasks_bound
            return self.tasks_bound

        # Should be useless, we already returned
        self.tasks_bound = tasks_bound
        return self.tasks_bound
