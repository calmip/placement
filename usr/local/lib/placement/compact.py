#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from tasksbinding import *
from scatter import *

#
# class CompactMode, dérive de TaskBinding, implémente les algos utilisés en mode compact
#
class CompactMode(TasksBinding):
    def __init__(self,archi,cpus_per_task,tasks):
        TasksBinding.__init__(self,archi,cpus_per_task,tasks)
        
    def checkParameters(self):
        self._checkParameters()

        if self.cpus_per_task % self.archi.threads_per_core!=0:
            msg = "OUPS - cpus_per_task ("
            msg += str(self.cpus_per_task)
            msg += ") => doit être multiple de threads_per_core ("
            msg += str(self.archi.threads_per_core)
            msg += ")"
            raise PlacementException(msg)

    def distribTasks(self, check=True):
        if check:
            self.checkParameters()

        if False:
            pass

        # cpus_per_task plus petit que cores_per_socket
        # ./placement -A   --mode=compact --hyper 4 4
        # S0-------- S1-------- 
        # P AAAABBBBCC .......... 
        # L CCDDDD.... ..........
#        if self.cpus_per_task <= self.archi.cores_per_socket:
        if True:
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
                                return tasks_bound

        # cpu_per_task plus grand que cores_per_socket 
        # on n'a pas plus d'une tâche par socket en moyenne
        # placement -A --mode=scatter 2 16
        #   S0-------- S1-------- 
        # P AAAAAAAA.. BBBBBBBB.. 
        # L AAAAAAAA.. BBBBBBBB.. 
        else:
            # TODO - testé seulement pour au max 2 threads par core !!!
            # On multiplie le nb de tâches et divise le nb de threads, on distribue, on coalesce les tableaux de tâches
            tmp_task_distrib = ScatterMode(self.archi,
                                           self.cpus_per_task/2,
                                           self.tasks*2)
            tmp_tasks_bound= tmp_task_distrib.distribTasks(check=False)
            # On a passé un nombre *2, donc on est sûr que ce nombre est bien pair
            imax = len(tmp_tasks_bound)/2

            tasks_bound = []
            for i in range(imax):
                t=[]
                t.extend(tmp_tasks_bound[i])
                t.extend(tmp_tasks_bound[i+imax])
                tasks_bound.append(t)
            
            return tasks_bound

        # normalement on ne passe pas par là on a déjà retourné
        return tasks_bound
