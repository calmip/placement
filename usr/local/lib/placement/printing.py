#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from matrix import *
from utilities import *
from exception import *
from itertools import chain,product

###############################################################################################
#
# PrintingFor = Toutes les classes utilisées en impression dérivent de cette classe abstraite
#
###############################################################################################
class PrintingFor(object):
    def __init__(self,tasks_binding):
        self._tasks_binding = tasks_binding
    def __str__(self):
        return "ERREUR INTERNE - CLASSE ABSTRAITE !!!!!"

###############################################################################################
#
# PrintingForSrun: Imprime des commandes pour srun
#
###############################################################################################
class PrintingForSrun(PrintingFor):
    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)

    #
    # Réécriture de tasks_bound sous forme de paramètres hexadécimaux pour srun
    #
    # Params = archi, tasks_bound
    # Return = La chaine de caractères à afficher
    #    
    def __getCpuBinding(self,archi,tasks_bound):
        mask_cpus=[]
        for t in tasks_bound:
            mask_cpus += [self.__getCpuTaskBinding(archi,t)]

        return "--cpu_bind=mask_cpu:" + ",".join(mask_cpus)


    # Réécrit le placement pour une tâche
    # Réécriture sous forme hexadécimale pour srun
    #
    # Params: archi (l'architecture processeurs)
    #         cores (un tableau d'entiers représentant les cœurs)
    # Return: Le tableau de tableaux réécrit en hexa
    #
    def __getCpuTaskBinding(self,archi,cores):
        i = 1
        rvl = 0
        for j in range(archi.cores_per_node*archi.threads_per_core):
            if (j in cores):
                rvl += i
            i = 2 * i
        rvl = str(hex(rvl))
    
        # Supprime le 'L' final, dans le cas où il y a un grand nombre de threads
        return rvl.rstrip('L')

#########################################################################################
#
# PrintingForHuman: Imprime dans un format humainement compréhensible
#
#########################################################################################
class PrintingForHuman(PrintingFor):
    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)

    def __getCpuBinding(self,archi,tasks_bound):
        rvl = ""
        for t in tasks_bound:
            rvl += self.__getCpuTaskBinding(archi,t)
        return rvl

    #
    # Réécrit le placement pour une tâche
    #
    # Params: archi (l'architecture processeurs), non utilisé
    #         cores (un tableau d'entiers représentant les cœurs d'une tâche)
    # Return: Le tableau de tableaux réécrit en chaine de caractères
    #
    #
    def __getCpuTaskBinding(self,archi,cores):
        rvl="[ "
        sorted_cores = cores
        sorted_cores.sort()
        for c in sorted_cores:
            rvl+=str(c)
            rvl += ' '
        rvl+="]\n"
        return rvl

#########################################################################################
#
# PrintingForAsciiArt: Imprime dans un format hautement artistique
#
#########################################################################################
class PrintingForAsciiArt(PrintingFor):
    def __str__(self):
        if self._tasks_binding.tasks > 66:
            return "OUPS - Représentation AsciiArt impossible pour plus de 66 tâches !"
        else:
            return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound,self._tasks_binding.over_cores)


    def __getCpuBinding(self,archi,tasks_bound,over_cores=None):
        char=ord('A')

        # cores = tableau de cores, prérempli avec '.'
        cores=[]
        for s in range(archi.sockets_per_node):
            if s in archi.l_sockets:
                to_app = '.'
            else:
                to_app = ' '
            for t in range(archi.threads_per_core):
                for c in range(archi.cores_per_socket):
                    cores.append(to_app)

        # remplir le tableau cores avec une lettre correspondant au process
        nt=0
        for t in tasks_bound:
            for c in t:
                if over_cores!=None and c in over_cores:
                    cores[c] = '#'
                else:
                    cores[c] = numTaskToLetter(nt)
            nt += 1

        # Pour une machine SMP plein de sockets type uvprod, on affiche les sockets par groupes de 8
        rvl = ""
        for gs in range(0,archi.sockets_per_node,8):
            rvl += "  "
            # Ecrire l'affectation des cœurs à partir des cores
            for s in range(gs,min(gs+8,archi.sockets_per_node)):
                rvl += 'S'
                rvl += str(s)
                cmin = 2
                if s>=10:
                    cmin=3
                for c in range(archi.cores_per_socket):
                    if c<cmin:
                        continue
                    else:
                        rvl += '-'
                rvl += ' '
            rvl += '\n'

            for l in range(archi.threads_per_core):
                if l==0:
                    rvl += "P "
                else:
                    rvl += "L "

                for s in range(gs,min(gs+8,archi.sockets_per_node)):
                    for c in range(archi.cores_per_socket):
                        rvl += cores[l*archi.cores_per_node+s*archi.cores_per_socket+c]
                    rvl += ' '
                rvl += '\n'
    
        return rvl

###############################################################################################
#
# PrintingForNumactl: Imprime des commandes pour numactl
#
###############################################################################################
class PrintingForNumactl(PrintingFor):
    def __str__(self):
        return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.tasks_bound)

#
# Réécriture de tasks_bound sous frome de switch numactl
#
    #
    # Réécriture de tasks_binding sous forme de switch numctl
    #
    # Params = archi, tasks_binding
    # Return = La chaine de caractères à afficher
    #    
    def __getCpuBinding(self,archi,tasks_bound):
        cpus=[]

        # compactifie dans une chaine de caractères
        sorted_tasks_bound=list(tasks_bound)
        sorted_tasks_bound.sort()

        for t in sorted_tasks_bound:
            cpus += [self.__getCpuTaskBinding(archi,t)]

        return "--physcpubind=" + ",".join(cpus)

    
    def __getCpuTaskBinding(self,archi,cores):
        return list2CompactString(cores)
  
#########################################################################################
#
# PrintingForMatrixThreads: Imprime les threads dans un format matriciel
#
#########################################################################################
class PrintingForMatrixThreads(PrintingFor):
    def __str__(self):
        if self._tasks_binding.tasks > 66:
            return "OUPS - Représentation des threads impossible pour plus de 66 tâches !"
        else:
            return self.__getCpuBinding(self._tasks_binding.archi,self._tasks_binding.threads_bound)

    #
    # Réécrit le placement pour des ensembles de threads et de tâches
    # Réécriture matricielle, une colonne par cœur et une ligne par thread
    #
    # Params: archi (l'architecture processeurs)
    #         threads_bound (le tableau self.processus de la classe RunningMode, cf running.py)
    # Return: la chaine de caracteres pour affichage
    #

    def __getCpuBinding(self,archi,threads_bound):
        #print str(threads_bound)
        psr_min = 9999
        psr_max = 0
        for pid in threads_bound.keys():
            threads = threads_bound[pid]['threads']
            for tid in threads:
                psr = threads[tid]['psr']
                if psr_min>psr:
                    psr_min=psr
                if psr_max<psr:
                    psr_max=psr

        m = Matrix(archi,psr_min,psr_max)
        #m = Matrix(archi)
        rvl = ''
        rvl += m.getHeader()

        nt=0
        for pid in sorted(threads_bound.keys()):
            l = numTaskToLetter(nt)
            threads = threads_bound[pid]['threads']
            for tid in sorted(threads):
                if threads[tid]['state'] == 'R':
                    S = l
                elif threads[tid]['state'] == 'S':
                    S = '.'
                else:
                    S = '?'
                if threads[tid].has_key('mem'):
                    rvl += m.getLine(pid,tid,threads[tid]['psr'],S,l,threads[tid]['cpu'],threads[tid]['mem'])
                else:
                    rvl += m.getLine(pid,tid,threads[tid]['psr'],S,l,threads[tid]['cpu'])
            nt += 1
        return rvl