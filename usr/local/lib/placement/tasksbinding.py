#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *

#
# TaskBinding permet d'implémenter les différents algorithmes de répartition
#              Suivant le mode demandé (scatter ou compact, cf. scatter.py et compact.py)
#              on utilisera l'une ou l'autre des classes dérivées
#
# PRINCIPALES METHODES:
#
# checkParameters()
#      Valide les paramètres d'entrée, lève une exception avec un message clair si pas corrects
#
#      On vérifie que les paramètres ne sont pas trop grands ou trop petits
#      En particulier, si le nombre tasks*cpus_per_task est < 10, on n'est pas sur la partition exclusive
#      (TODO -> Partition exclusive ou pas, ça ne concerne qu'eos)
#
#      En scatter seulement, on refuse les tâches à cheval sur deux sockets, sauf s'il n'y a qu'une tâche 
#      (tâche unique avec 20 threads: OK, 5 tâches de 4 threads, HTOFF: NON)
#
# distribTasks()
#      Construit le tableau de tableaux tasks_binding à partir des paramètres
# 
#      Params: check, si True (defaut), check les valeurs de tasks etc avant d'accepter
#              archi, une architecture déjà initialisée (peut etre None)
#              cpus_per_task, par défaut prend la valeur de architecture
#              tasks, par défaut prend la valeur de architecture si possible
#
#      Return: tasks_bound, un tableau de tableaux:
#              Le tableau des processes, chaque process est représenté par un tableau de cœurs.
#              [[psr1,...],[psr3,...],...]
#
    
class TasksBinding(object):
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
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")
    def distribTasks(self,check=True):
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")
    def PrintingForVerbose(self):
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")

    # Code commun à toutes les classes dérivées
    # _checkParameters doit être appelé par toutes les fonctions checkParameters()
    def _checkParameters(self):
        if (self.cpus_per_task<0 or self.tasks<0 ):
            raise PlacementException("OUPS - Tous les paramètres doivent être entiers positifs")
        if self.cpus_per_task*self.tasks>self.archi.threads_per_core*self.archi.cores_reserved:
            msg = "OUPS - Pas assez de cores ! Diminuez cpus_per_task (";
            msg += str(self.cpus_per_task)
            msg += ") ou tasks ("
            msg += str(self.tasks)
            msg += ")"
            msg += ' NUMBER OF CORES RESERVED FOR THIS PROCESS = ' + str(self.archi.cores_reserved)
            raise PlacementException(msg)

    # Tri INPLACE des threads dans chaque process
    def threadsSort(self):
        for p in self.tasks_bound:
            p.sort()

    # Pour le mode mpi_aware: Ne garde QUE la tache correspondant à mon rang mpi
    def keepOnlyMpiRank(self):
        rank = 0;
        try:
            # Le rank si on utilise openmpi, bullx_mpi, etc.
            rank = os.environ['OMPI_COMM_WORLD_RANK']
        except KeyError:
            pass

        if rank==0:
            try:
                # Le rank si on utilise intelmpi
                rank = os.environ['PMI_RANK']
            except KeyError:
                msg = "ERREUR NINI - NI intelmpi, NI bullxmpi, NI openmpi"
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

