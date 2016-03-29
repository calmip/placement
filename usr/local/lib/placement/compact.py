#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from tasksbinding import *
from scatter import *

#
# class CompactGeneMode, dérive de TasksBinding, classe mère pour plusieurs modes compact différents
#       La méthode checkParameters, commune à toutes les classes de type compact, est implantée ici
#
class CompactGenMode(TasksBinding):
    def __init__(self,archi,cpus_per_task=0,tasks=0):
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


#
# class CompactMode, dérive de TaskBinding, implémente les algos utilisés en mode compact
#
class CompactMode(CompactGenMode):
    def __init__(self,archi):
        TasksBinding.__init__(self,archi)
        self.distribTasks()
        
    def distribTasks(self, check=True):
        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        # cpus_per_task plus petit que cores_per_socket
        # ./placement -A   --mode=compact --hyper 4 4
        # S0-------- S1-------- 
        # P AAAABBBBCC .......... 
        # L CCDDDD.... ..........
#        if self.cpus_per_task <= self.archi.cores_per_socket:
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
#                    Utilisé lorsque le swtiche --hyper_as_physical est utilisé, traite les cœurs logiques
#                    comme des sockets supplémentaires
#
class CompactPhysicalMode(CompactGenMode):
    def __init__(self,archi):
        TasksBinding.__init__(self,archi)
        self.distribTasks()
        
    def distribTasks(self, check=True):
        if self.tasks_bound != None:
            return self.tasks_bound

        if check:
            self.checkParameters()

        # cpus_per_task plus petit que cores_per_socket
        # ./placement -A   --mode=compact --hyper 4 4
        # S0-------- S1-------- 
        # P AAAABBBBCC .......... 
        # L CCDDDD.... ..........
#        if self.cpus_per_task <= self.archi.cores_per_socket:
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
