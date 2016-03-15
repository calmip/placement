#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from tasksbinding import *

#
# class ScatterGeneMode, dérive de TasksBinding, classe mère pour plusieurs modes scatter différents
#       La méthode checkParameters, commune à toutes les classes de type Scatter, est implantée ici
#
class ScatterGenMode(TasksBinding):
    def __init__(self,archi,cpus_per_task=0,tasks=0):
        TasksBinding.__init__(self,archi,cpus_per_task,tasks)

    def checkParameters(self):
        '''Renvoie None si le check est positif, génère une exception sinon'''
        self._checkParameters()

        if self.cpus_per_task % self.archi.threads_per_core!=0:
            msg = "OUPS - cpus_per_task ("
            msg += str(self.cpus_per_task)
            msg += ") => doit être multiple de threads_per_core ("
            msg += str(self.archi.threads_per_core)
            msg += ")"
            raise PlacementException(msg)

        # max_tasks calculé ainsi permet d'être sûr de ne pas avoir une tâche entre deux sockets_per_node, 
        max_tasks = self.archi.sockets_reserved * self.archi.threads_per_core * (self.archi.cores_per_socket/self.cpus_per_task)
        if self.cpus_per_task>1:
            if self.tasks>max_tasks and max_tasks>0:
                msg = "OUPS - Une task est à cheval sur deux sockets ! Diminuez le nombre de tâches par nœuds, le maximum est "
                msg += str(max_tasks)
                raise PlacementException(msg)


#
# class ScatterMode, dérive de TaskBinding, implémente les algos utilisés en mode scatter
#

class ScatterMode(ScatterGenMode):
    def __init__(self,archi,cpus_per_task=0,tasks=0):
        ScatterGenMode.__init__(self,archi,cpus_per_task,tasks)
        self.distribTasks()
        
    def distribTasks(self,check=True):
        '''Init et renvoie self.tasks_bound, ie une liste de listes'''
        if check:
            self.checkParameters()

        if self.tasks_bound != None:
            return self.tasks_bound

        tasks_bound = []

        # Si plusieurs tâches, on ne sépare pas les threads des tâches entre les sockets
        if self.tasks > 1:
            tmpl = self.__compute_task_template()

            # q donne le nombre de tâches par socket, r le nombre de taches excédentaires sur les premiers sockets
            q = self.tasks / self.archi.sockets_reserved
            r = self.tasks % self.archi.sockets_reserved

            # hp est le nombre de cœurs physiques utilisés par chaque tâche
            hp = self.cpus_per_task / self.archi.threads_per_core

            # Le socket/cœur de départ
            s = 0
            c = 0

            # Le cœur en adressage absolu
            ca = 0

            # Compteur de tâches sur le socket courant
            cpt_t = 1

            # Recopier le template au bon endroit
            for t in range(self.tasks):
                ca = s * self.archi.cores_per_socket + c
                #s = self.__task2socket(t)
                #c = self.__task2core(t)
                #c_start = s * self.archi.cores_per_socket + c
                t_bound = []
                for h in range(self.cpus_per_task):
                    t_bound.append(ca + tmpl[h])
                tasks_bound.append(t_bound)

                # Emplacement de la prochaine tâche
                if cpt_t<q:
                    cpt_t += 1
                    c     += hp
                elif s<r and cpt_t==q:
                    cpt_t += 1
                    c     += hp
                else:
                    s     += 1
                    c     =  0
                    cpt_t = 1

        # Si une seule tâche, on explose la tâche entre les sockets disponibles
        else:
            tmpl = self.__compute_task_template(True)
            t_bound = []
            for s in self.archi.l_sockets:
                c_start = s * self.archi.cores_per_socket
                for c in tmpl:
                    t_bound.append(c_start+c)
            tasks_bound.append(t_bound)


        self.tasks_bound = tasks_bound
        return self.tasks_bound

    # Calcule le numéro de socket sur lequel tourne la tâche t
    # s = t / (nb_de_taches/nb_de_sockets)
    def __task2socket(self,t):
        q = self.tasks / self.archi.sockets_reserved
        if q==0:
            return t
        r = self.tasks % self.archi.sockets_reserved
        s = t / q
        if s<r:
            s -= t
        else:
            s -= r

        # on retourne un numéro de socket physique (dépend des réservations)
        return self.archi.l_sockets[s]

    # Calcule le premier numéro de cœur dédié à la tâche t
    def __task2core(self,t):
        q = self.tasks / self.archi.sockets_reserved
        if q==0:
            return 0
        s = t / q
        # s = numéro de socket logique
        s = t * self.archi.sockets_reserved / self.tasks
        # h = nombre de cœurs PHYSIQUES utilisés par chaque tâche
        h = self.cpus_per_task / self.archi.threads_per_core
        # r = reste de la division nb_de_taches/nb_de_sockets
        r = self.tasks % self.archi.sockets_reserved
        
        return (t - s*self.tasks/self.archi.sockets_reserved - min(s,r)) * h

    def __compute_task_template(self,explode=False):
        '''Calcule les coœurs occupés par la tâche qui commence au cœur 0
           Si explode vaut true, la tâche sera explosée entre tous les sockets disponibles'''
        tmpl = []
        c = 0
        y = 0
        if explode:
            nb_cores = self.cpus_per_task / self.archi.sockets_reserved
        else:
            nb_cores = self.cpus_per_task
        nb_phys_core = self.cpus_per_task / self.archi.threads_per_core
            
        for t in range(0,nb_cores):
            tmpl.append(c)
            c += 1
            if (c == nb_phys_core):
                y += 1
                c = y*self.archi.cores_per_node
        return tmpl

    def test__compute_task_template(self,explode=False):
        '''NE PAS UTILISER - Juste pour les tests unitaires'''
        return self.__compute_task_template(explode)

#
# class ScatterMode, dérive de TaskBinding, implémente les algos utilisés en mode scatter
#

class ScatterAltMode(ScatterGenMode):
    def __init__(self,archi,cpus_per_task=0,tasks=0):
        ScatterGenMode.__init__(self,archi,cpus_per_task,tasks)
        self.distribTasks()
        
    def distribTasks(self,check=True):
        '''Init et renvoie self.tasks_bound, ie une liste de listes'''
        if check:
            self.checkParameters()

        if self.tasks_bound != None:
            return self.tasks_bound

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
                            self.tasks_bound = tasks_bound
                            return self.tasks_bound

        # cpu_per_task plus grand que cores_per_socket 
        # on n'a pas plus d'une tâche par socket en moyenne
        # placement -A --mode=scatter 2 16
        #   S0-------- S1-------- 
        # P AAAAAAAA.. AAAAAAAA.. 
        # L BBBBBBBB.. BBBBBBBB.. 
        else:
            # TODO - testé seulement pour au max 2 threads par core !!!
            # On multiplie le nb de tâches et divise le nb de threads, on distribue, on coalesce les tableaux de tâches
            tmp_task_distrib = ScatterAltMode(self.archi,
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
            
            self.tasks_bound = tasks_bound
            return self.tasks_bound

        # normalement on ne passe pas par là on a déjà retourné
        self.tasks_bound = tasks_bound
        return self.tasks_bound
