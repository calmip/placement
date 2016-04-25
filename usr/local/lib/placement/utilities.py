#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import copy
#from matrix import *
from exception import *
from itertools import chain,product


#############################################################################################################
# retire tous les blancs de la list passée en paramètres
def removeBlanks(L):
    try:
        while True:
            L.remove('')
    except:
        pass

#
# Conversion de  numéro de tâche (0..66) vers lettre(A-Za-z0-9)
def numTaskToLetter(n):
    if n<0 or n>66:
        raise PlacementException("ERREUR INTERNE - Si plus de 62 tâches, utilisez getCpuTaskAsciiBinding")
    if n<26:
        return chr(65+n)   # A..Z
    if n<52:
        return chr(71+n)   # a..z  (71=97-26)
    return chr(n-4)        # 0..>  (-4=53-48)

# Conversion d'une liste d'entiers vers une chaine compacte:
# [0,1,2,5,6,7,9] ==> 0-2,5-7,9
# 
# params: A, liste d'entiers (éventuellement dans le désordre)
#
# return: Chaine de caractères
def list2CompactString(A):

    # On passe par un set pour supprimer les doublons, puis par une nouvelle liste
    # On la trie
    s0 = set(A)
    s  = list(s0)
    s.sort()

    # réécrire tout ça avec la syntaxe: 1,2,3,5 => 1-3,5
    # cl_cpus = Compact List of A
    tmp=[]
    last_c=-1
    start=-1
    end=-1

    # Ajoute '0-2' ou '0' à tmp
    def __compact(tmp,start,end):
        if start==end:
            tmp += [str(start)]
        else:
            tmp += [str(start)+'-'+str(end)]

    for c in s:
        if start==-1:
            start=c
        if last_c==-1:
            last_c=c
        else:
            if c-last_c==1:
                last_c=c
            else:
                __compact(tmp,start,last_c)
                start=c
                last_c=c
                
    if last_c>-1:
        __compact(tmp,start,last_c)
    return ','.join(tmp)

# Conversion d'une chaine compacte vers une listre triée:
#            "0-3,5" ==> [0,1,2,3,5]
# 
# params: S, chaine compacte
# return: Liste d'entiers
# 
def compactString2List(S):
    rvl = []
    if S != "":
        a   = S.split(',')
        for s in a:
            c = s.split('-')
            if len(c) == 1:
                rvl.append([int(c[0])])
            else:
                # [0-3] ==> 0,1,2 + 3
                if c[0] < c[1]:
                    rvl.append(range(int(c[0]),int(c[1])))
                    rvl.append([int(c[1])])
                else:
                    rvl.append(range(int(c[1]),int(c[0])))
                    rvl.append([int(c[0])])

        rvl = list(chain(*rvl))
    return rvl

            
# Calcule à partir de l'environnement ou des options les valeurs de tasks et cpus_per_task
# Les renvoie dans une liste de deux entiers
def computeCpusTasksFromEnv(options,args):

    # Valeurs par défaut: en l'absence d'autres indications
    cpus_per_task = 4
    tasks         = 4

    # Si on est en mpi_aware, regarder PLACEMENT_SLURM_TASKS_PER_NODE, sinon regarder SLURM_TASKS_PER_NODE
    slurm_tasks_per_node = '0'
    if options.mpiaware:
        slurm_tasks_per_node = os.environ['PLACEMENT_SLURM_TASKS_PER_NODE']
    else:
        if 'SLURM_TASKS_PER_NODE' in os.environ:
            slurm_tasks_per_node = os.environ['SLURM_TASKS_PER_NODE']

    # Valeurs par défaut: on prend les variables d'environnement de SLURM, si posible
    if slurm_tasks_per_node != '0':
        tmp = slurm_tasks_per_node.partition('(')[0]         # 20(x2)   ==> 2
        tmp = map(int,tmp.split(','))                        # '11,10'  ==> [11,10]
        if len(tmp)==1:
            tasks = tmp[0]
        elif len(tmp)==2:
            tasks = min(tmp)
            if options.asciiart or options.human:
                msg = "ATTENTION - SLURM_TASKS_PER_NODE = " + slurm_tasks_per_node + "\n"
                msg+= "            Le paradigme utilisé est probablement client-serveur, le placement prend en compte " + str(tasks) + " tâches"
                print msg
                print 
        else:
            msg =  "OUPS - Placement non supporté dans cette configuration:\n"
            msg += "       SLURM_TASKS_PER_NODE = " + slurm_tasks_per_node
            raise PlacementException(msg)

    # Si on est en mpi_aware, regarder PLACEMENT_SLURM_CPUS_PER_TASK, sinon regarder SLURM_CPUS_PER_TASK
    slurm_cpus_per_task = '0'
    if options.mpiaware:
        slurm_cpus_per_task = os.environ['PLACEMENT_SLURM_CPUS_PER_TASK']
    else:
        if 'SLURM_CPUS_PER_TASK' in os.environ:
            slurm_cpus_per_task = os.environ['SLURM_CPUS_PER_TASK']

    if slurm_cpus_per_task != '0':
        cpus_per_task = int(slurm_cpus_per_task)
    
    # Les valeurs spécifiées dans la ligne de commande ont la priorité !
    if args[1] > 0:
        cpus_per_task = int(args[1])
    if args[0] > 0:
        tasks         = int(args[0])

    # retourne les valeurs calculées
    return [cpus_per_task,tasks]

# Passe en bold
def bold():
    return '\033[1m'

def underline():
    return '\033[41m'

def boldunderline():
    return '\033[1;4m'

def white_background():
    return '\033[47m'

def red_foreground():
    return '\033[1;31m'

def mag_foreground():
    return '\033[1;35m'

# Redevient normal
def normal():
    return '\033[0m'

