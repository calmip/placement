#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from itertools import chain,product

#############################################################################################################
#
# Réécrit le placement pour une tâche (appelé par getCpuBindingSrun)
# Réécriture sous forme hexadécimale pour srun
#
# Params: archi (l'architecture processeurs)
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Le tableau de tableaux réécrit en hexa
#
def getCpuTaskSrunBinding(archi,cores):
    i = 1
    rvl = 0
    for j in range(archi.cores_per_node*archi.threads_per_core):
        if (j in cores):
            rvl += i
        i = 2 * i
    rvl = str(hex(rvl))
    
    # Supprime le 'L' final, dans le cas où il y a un grand nombre de threads
    return rvl.rstrip('L')

#
# Réécrit le placement pour une tâche (appelé par getCpuBinding)
# Réécriture de manière "humainement lisible"
#
# Params: archi (l'architecture processeurs), non utilisé
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Le tableau de tableaux réécrit en chaine de caractères
#
#
def getCpuTaskHumanBinding(archi,cores):
    rvl="[ "
    sorted_cores = cores
    sorted_cores.sort()
    for c in sorted_cores:
        rvl+=str(c)
        rvl += ' '
    rvl+="]\n"
    return rvl

#
# Réécrit le placement pour une tâche (appelé par getCpuBinding)
# Réécriture en "art ascii" représentant l'architecture processeur
#
# Params: archi (l'architecture processeurs)
#         cores (un tableau d'entiers représentant les cœurs)
# Return: Une ou deux lignes, deux fois 10 colonnes séparées par un espace (pour 2 sockets_per_node de 10 cœurs)
#
# NOTE - PAS UTILISE ACTUELLEMENT, on utilise getCpuBindingAscii à la place
#        On le garde pour cat getCpuBindingAscii est limité à 62 tâches
#

def getCpuTaskAsciiBinding(archi,cores):
    rvl = ""
    for l in range(archi.threads_per_core):
        if (archi.threads_per_core>1):
            if l==0:
                rvl += '/'
            else:
                rvl += '\\'

        for j in archi.l_sockets:
            for k in range(archi.cores_per_socket):
                if (l*archi.cores_per_node+j*archi.cores_per_socket+k in cores):
                    rvl += 'X'
                else:
                    rvl += '.'
            rvl += " "
        rvl += "\n"
    return rvl


def getCpuTaskNumactlBinding(archi,cores):
    return list2CompactString(cores)

#
# Conversion de  numéro de tâche (0..61) vers lettre(A-Za-z0-9)
def numTaskToLetter(n):
    if n<0 or n>61:
        raise PlacementException("ERREUR INTERNE - Si plus de 62 tâches, utilisez getCpuTaskAsciiBinding")
    if n<26:
        return chr(65+n)   # A..Z
    if n<52:
        return chr(71+n)   # a..z  (71=97-26)
    return chr(n-4)        # 0..9  (-4=53-48)

# Conversion d'une liste d'entiers triée vers une chaine compacte:
# ATTENTION - On fait un tri Inplace de A, qui est donc a priori modifié
#             [0,1,2,5,6,7,9] ==> 0-2,5-7,9
# 
# params: A, liste d'entiers (peut être modifiée)
#
# return: Chaine de caractères
def list2CompactString(A):

    A.sort()

    # réécrire tout ça avec la syntaxe: 1,2,3,5 => 1-3,5
    # cl_cpus = Compact List of A
    tmp=[]
    last_c=-1
    start=-1
    end=-1

    # Ajoute '0-2' ou '0' à tmp
    def compact(tmp,start,end):
        if start==end:
            tmp += [str(start)]
        else:
            tmp += [str(start)+'-'+str(end)]

    for c in A:
        if start==-1:
            start=c
        if last_c==-1:
            last_c=c
        else:
            if c-last_c==1:
                last_c=c
            else:
                compact(tmp,start,last_c)
                start=c
                last_c=c
                
    if last_c>-1:
        compact(tmp,start,last_c)
    return ','.join(tmp)

# Conversion d'une chaine compacte vers une listre triée:
#            [0-3,5] ==> [0,1,2,3,5]
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
                rvl.append(range(int(c[0]),int(c[1])))
                rvl.append([int(c[1])])
        rvl = list(chain(*rvl))
    return rvl

#
# Réécriture de tasks_binding sous forme 'ascii art'
#
# Params = archi (passé à getCpuTasksMachineBinding)
#          tasks_binding
#          over_cores (un tableau d'entiers représentant les cores qui doivent exécuter plusieurs tâches, defaut=None)

# Return = La chaine de caractères à afficher
#    
def getCpuBindingAscii(archi,tasks_binding,over_cores=None):
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
    for t in tasks_binding:
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

#
# Appel de fct pour chaque élément de tasks_binding
# concatène et renvoie les retours de fct
#
def getCpuBinding(archi,tasks_binding,fct):
    rvl = ""
    for t in tasks_binding:
        rvl += fct(archi.threads_per_core,t)
    return rvl

#
# Réécriture de tasks_binding sous forme de paramètres hexadécimaux pour srun
#
# Params = archi, tasks_binding
# Return = La chaine de caractères à afficher
#    
def getCpuBindingSrun(archi,tasks_binding):
    mask_cpus=[]
    for t in tasks_binding:
        mask_cpus += [getCpuTaskSrunBinding(archi,t)]

    return "--cpu_bind=mask_cpu:" + ",".join(mask_cpus)

#
# Réécriture de tasks_binding sous frome de switch numactl
#
def getCpuBindingNumactl(archi,tasks_binding):
    cpus=[]

    # remettre à plat tasks_binding
#    for tasks in tasks_binding:
#        for t in tasks:
#            cpus.append(int(t))

    # compactifie dans une chaine de caractères

    sorted_tasks_binding=list(tasks_binding)
    sorted_tasks_binding.sort()

    for t in sorted_tasks_binding:
        cpus += [getCpuTaskNumactlBinding(archi,t)]

    return "--physcpubind=" + ",".join(cpus)
    
    s_cpus = list2CompactString(cpus)
    return "--physcpubind=" + s_cpus
    


# Renvoie les couples de processes qui présentent un recouvrement, ainsi que
# la liste des cœurs en cause
def detectOverlap(tasks_bound):
    over=[]
    over_cores=[]
    for i in range(len(tasks_bound)):
        for j in range(i+1,len(tasks_bound)):
            overlap = list(set(tasks_bound[i])&set(tasks_bound[j]))
            if len(overlap)!=0:
                over.append((i,j))
                over_cores.extend(overlap)

    # Remplace les numéros par des lettres
    # TODO - Si un numéro est plus gros que 62, plantage !
    over_l = []
    for c in over:
        over_l.append( (numTaskToLetter(c[0]),numTaskToLetter(c[1])) )

    # Supprime les doublons dans self.over_core
    over_cores = set(over_cores)
    over_cores = list(over_cores)
    over_cores.sort()
    return (over_l,over_cores)

            
# Calcule à partir de l'environnement ou des options les valeurs de tasks et cpus_per_task
# Les renvoie dans une liste de deux entiers
def computeCpusTasksFromEnv(options,args):

    # Valeurs par défaut: en l'absence d'autres indications
    cpus_per_task = 4
    tasks         = 4

    # Valeurs par défaut: on prend les variables d'environnement de SLURM, si posible
    if 'SLURM_TASKS_PER_NODE' in os.environ:
        tmp = os.environ['SLURM_TASKS_PER_NODE'].partition('(')[0]         # 20(x2)   ==> 2
        tmp = map(int,tmp.split(','))                                      # '11,10'  ==> [11,10]
        if len(tmp)==1:
            tasks = tmp[0]
        elif len(tmp)==2:
            tasks = min(tmp)
            if options.asciiart or options.human:
                msg = "ATTENTION - SLURM_TASKS_PER_NODE = " + os.environ['SLURM_TASKS_PER_NODE'] + "\n"
                msg+= "            Le paradigme utilisé est probablement client-serveur, le placement prend en compte " + str(tasks) + " tâches"
                print msg
                print 
        else:
            msg =  "OUPS - Placement non supporté dans cette configuration:\n"
            msg += "       SLURM_TASKS_PER_NODE = " + os.environ['SLURM_TASKS_PER_NODE']
            raise PlacementException(msg)

    if 'SLURM_CPUS_PER_TASK' in os.environ:
        cpus_per_task = int(os.environ['SLURM_CPUS_PER_TASK'])
    
    # Les valeurs spécifiées dans la ligne de commande ont la priorité !
    if len(args) >= 2:
        cpus_per_task = int(args[1])
    if len(args) >= 1:
        tasks         = int(args[0])

    # retourne les valeurs calculées
    return [cpus_per_task,tasks]
