#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from tasksbinding import *

#
# class ScatterMode, dérive de TaskBinding, implémente les algos utilisés en mode scatter
#

class ScatterMode(TasksBinding):
    def __init__(self,archi,cpus_per_task=0,tasks=0):
        TasksBinding.__init__(self,archi,cpus_per_task,tasks)
        
    def checkParameters(self):
        '''Renvoie None si le check est positif, généère une exception sinon'''
        self._checkParameters()

        if self.cpus_per_task % self.archi.threads_per_core!=0:
            msg = "OUPS - cpus_per_task ("
            msg += str(self.cpus_per_task)
            msg += ") => doit être multiple de threads_per_core ("
            msg += str(self.archi.threads_per_core)
            msg += ")"
            raise PlacementException(msg)

        ### CODE DEBILE ON NE PASSERA JAMAIS PAR LA !!!
        ### Je supprime cette condition pour l'instant
        #if self.tasks>1 and \
        #        self.cpus_per_task<self.archi.cores_per_socket and \
        #        self.cpus_per_task>self.archi.threads_per_core*self.archi.cores_per_socket:

        #    msg =  "OUPS - Votre task déborde du socket, cpus_per_task doit être <= "
        #    msg += str(self.archi.threads_per_core*self.archi.cores_per_socket)
        #    raise PlacementException(msg)
        
        # max_tasks calculé ainsi permet d'être sûr de ne pas avoir une tâche entre deux sockets_per_node, 
        max_tasks = self.archi.sockets_reserved * self.archi.threads_per_core * (self.archi.cores_per_socket/self.cpus_per_task)
        if self.cpus_per_task>1:
            if self.tasks>max_tasks and max_tasks>0:
                msg = "OUPS - Une task est à cheval sur deux sockets ! Diminuez le nombre de tâches par nœuds, le maximum est "
                msg += str(max_tasks)
                raise PlacementException(msg)

    def distribTasks(self,check=True):
        '''Renvoie tasks_bound, ie une liste de listes'''
        if check:
            self.checkParameters()

        # cpus_per_task plus petit que cores_per_socket
        # placement -A   --mode=scatter 4 4
        #   S0-------- S1-------- 
        # P AAAACCCC.. BBBBDDDD.. 
        
        # placement -A   --mode=scatter --hyper 4 4
        #   S0-------- S1-------- 
        # P AAAA...... BBBB...... 
        # L CCCCDDDD.. DDDD...... 
        if self.cpus_per_task <= self.archi.cores_per_socket and self.tasks>1:
            c_step = self.cpus_per_task
            tasks_bound=[]
            t_binding=[]
            t = 0
            th= 0
            #print str(range(0,self.archi.cores_per_socket,c_step))+' ('+str(0)+','+str(self.archi.cores_per_socket)+','+str(c_step)+')'
            # boucle sur les cœurs de calculs
            for c in range(0,self.archi.cores_per_socket,c_step):
                #print "   "+str(range(self.archi.threads_per_core))
                
                # Boucle sur les threads des cœurs (hyperthreading)
                for y in range(self.archi.threads_per_core):
                    #print "      "+str(self.archi.l_sockets)

                    # Boucle sur les sockets
                    for s in self.archi.l_sockets:
                        #print "         "+str(range(self.cpus_per_task))

                        # Boucle sur les threads des processes
                        for th in range(self.cpus_per_task):
                            # Eviter le débordement sauf s'il n'y a qu'une seule task
                            # Ne sert à rien puisqu'on a le c_step
                            #if th==0 and self.archi.cores_per_socket-c < self.cpus_per_task:
                            #    continue
                            t_binding += [y*self.archi.cores_per_node + s*self.archi.cores_per_socket + c + th]
                        tasks_bound += [t_binding]
                        t_binding = []
                        t += 1
                        if (t==self.tasks):
                            return tasks_bound

        # cpu_per_task plus grand que cores_per_socket 
        # on n'a pas plus d'une tâche par socket en moyenne
        # placement -A --mode=scatter 2 16
        #   S0-------- S1-------- 
        # P AAAAAAAA.. AAAAAAAA.. 
        # L BBBBBBBB.. BBBBBBBB.. 
        else:
            # TODO - testé seulement pour au max 2 threads par core !!!
            # On multiplie le nb de tâches et divise le nb de threads, on distribue, on coalesce les tableaux de tâches
            tmp_task_distrib = ScatterMode(self.archi,
                                           self.cpus_per_task/2,
                                           self.tasks*2)
            tmp_tasks_bound= tmp_task_distrib.distribTasks(check=False)
            # On a passé un nombre *2, donc on est sûr que ce nombre est bien pair
            imax = len(tmp_tasks_bound)

            tasks_bound = []
            for i in range(0,imax,2):
                t=[]
                t.extend(tmp_tasks_bound[i])
                t.extend(tmp_tasks_bound[i+1])
                tasks_bound.append(t)
            
            return tasks_bound

        # normalement on ne passe pas par là on a déjà retourné
        return tasks_bound
