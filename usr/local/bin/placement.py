#! /usr/bin/env python
# -*- coding: utf-8 -*-

################################################################
# Ce script peut vous aider à placer vos tâches sur les coeurs
#
# CALMIP - 2015
#
# Commencez par: placement --help 
#
# Calcule et renvoie le switch cpu_bin qui doit être inséré dans l'appel srun
#
# Exemple: 4 processus, 8 threads par processus, hyperthreading activé
#
# Switch -H: Renvoie l'affectation des cores aux processes de manière lisible par les humains:
#
# placement -H 4 8 2
# [ 0 1 2 3 20 21 22 23 ]
# [ 10 11 12 13 30 31 32 33 ]
# [ 4 5 6 7 24 25 26 27 ]
# [ 14 15 16 17 34 35 36 37 ]
#
# --cpu_bind=mask_cpu:0xf0000f,0x3c0003c00,0xf0000f0,0x3c0003c000
#
# Switch -A: Renvoie l'affectation des cores aux processes de manière cartographique:
#
# placement.py -A 4 8 2
# /XXXX...... .......... 
# \XXXX...... .......... 
# /.......... XXXX...... 
# \.......... XXXX...... 
# /....XXXX.. .......... 
# \....XXXX.. .......... 
# /.......... ....XXXX.. 
# \.......... ....XXXX.. 
#
# --cpu_bind=mask_cpu:0xf0000f,0x3c0003c00,0xf0000f0,0x3c0003c000
#
# DANS UN SCRIPT SBATCH:
# ======================
#
# Pas la peine de spécifier les paramètres, les variables d'environnement SLURM seront utilisées
# Commandes recommandées:
# 
# placement -A
# if [[ $? != 0 ]]
# then
#  echo "ERREUR DANS LE NOMBRE DE PROCESES OU DE TACHES" 2>&1
#  exit $?
# fi
# ...
# srun $(placement) ./mon_application
#        
# emmanuel.courcelle@inp-toulouse.fr
# http://www.calmip.univ-toulouse.fr
# Mars 2015
################################################################

import os
from optparse import OptionParser
import subprocess
from itertools import chain,product

class PlacementException(Exception):
    pass

# Changer cette cons en changeant d'architecture (cf. lignes 70 et suivantes)
ARCHI = 'BULLX-DLC'
#ARCHI = 'MESCA'

# Constantes liées à nos architectures: 
SOCKETS_PER_NODE = ''
CORES_PER_SOCKET = ''
HYPERTHREADING   = ''

# 1/ BULLx DLC (eos), 612 nœuds, chacun 2 procs Intel Ivybridge 10 cœurs, hyperthreading activé
if ARCHI == 'BULLX-DLC':
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2

# 2/ BULL SMP-mesca, 8 sockets, 15 cœurs par socket, pas d'HYPERTHREADING
if ARCHI == 'MESCA':
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 15
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1

# class Architecture: 
#       Description de l'architecture dans une classe
#       Paramètres du constructeur:
#           sockets_per_node: Nombre de sockets par node, doit être < SOCKETS_PER_NODE 
#           tasks           : Nombre de tâches (processes) souhaité
#           cpus_per_task   : Nombre de cpus par process
#           hyper           : Si False, hyperthreading interdit
#
#           - tasks, threads_per_task, et la constante HYPERTHREADING permet de calculer le nombre
#           de threads par cœur
#           - cores_per_socket est fixe (cf. CORES_PER_SOCKET)
#           - Le nombre de cores par nœud dérive de sockets_per_node et cores_per_socket
#       Il est interdit (et impossible) de changer les attributs par la suite
class Architecture(object):
    def __init__(self, sockets_per_node, cpus_per_task, tasks, hyper):
        if sockets_per_node > SOCKETS_PER_NODE:
            msg = "ERREUR INTERNE "
            msg += str(sockets_per_node)
            msg += " > " 
            msg += str(SOCKETS_PER_NODE)
            print msg
            raise PlacementException(msg)

        self.sockets_per_node = sockets_per_node+0
        self.cores_per_socket = CORES_PER_SOCKET
        self.cores_per_node   = self.sockets_per_node * self.cores_per_socket
        self.threads_per_core = self.activateHyper(hyper,cpus_per_task,tasks)

        #print self.sockets_per_node,self.cores_per_socket,self.cores_per_node,self.threads_per_core

    # Accepte d'initialiser un attribut seulement s'il n'existe pas
    def __setattr__(self,name,value):
        try:
            getattr(self,name)
            raise PlacementException("ERREUR INTERNE - Pas le droit de changer les attributs")
        except Exception:
            object.__setattr__(self,name,value)

    #
    # Active l'HYPERTHREADING si nécessaire:
    #         si hyper == True on active
    #         sinon on active seulement si nécessaire
    #         Si la variable globale HYPERTHREADING est à False et que l'HYPERTHREADING doit être
    #         activé, on lève une exception
    #
    #         Retourne threads_per_core (1 ou 2)
    #
    def activateHyper(self,hyper,cpus_per_task,tasks):
        threads_per_core=1
        if hyper==True or (cpus_per_task*tasks>self.cores_per_node and cpus_per_task*tasks<=THREADS_PER_CORE*self.cores_per_node):
            if HYPERTHREADING:
                threads_per_core = THREADS_PER_CORE
            else:
                msg = "OUPS - l'HYPERTHREADING n'est pas actif sur cette machine"
                raise PlacementException(msg)
        return threads_per_core

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

        for j in range(archi.sockets_per_node):
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
    for i in range(archi.cores_per_node*archi.threads_per_core):
        cores.append('.')

    # remplir le tableau cores avec une lettre correspondant au process
    nt=0
    for t in tasks_binding:
        for c in t:
            if over_cores!=None and c in over_cores:
                cores[c] = '#'
            else:
                cores[c] = numTaskToLetter(nt)
        nt += 1

    # Ecrire l'affectation des cœurs à partir de cores
    rvl = "  "
    for s in range(archi.sockets_per_node):
        rvl += 'S'
        rvl += str(s)
        for c in range(archi.cores_per_socket):
            if c<2:
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

        for s in range(archi.sockets_per_node):
            for c in range(archi.cores_per_socket):
                rvl += cores[l*archi.cores_per_node+s*archi.cores_per_socket+c]
            rvl += ' '
        rvl += "\n"

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
    
#
# TaskBuilding permet d'implémenter les différents algorithmes de répartition
#              Suivant le mode demandé (scatter ou compact) 
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
# distribProcesses()
#      Construit le tableau de tableaux tasks_binding à partir des paramètres
# 
#      Return: tasks_bounded, un tableau de tableaux:
#              Le tableau des processes, chaque process est représenté par un tableau de cœurs.
#
    
class TasksBinding(object):
    def __init__(self,archi,cpus_per_task,tasks):
        self.archi = archi
        self.cpus_per_task = cpus_per_task
        self.tasks = tasks

    def checkParameters():
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")
    def distribProcesses():
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")

    # Code commun à toutes les classes dérivées
    # _checkParameters doit être appelé par toutes les fonctions checkParameters()
    def _checkParameters(self):
        if (self.cpus_per_task<0 or self.tasks<0 ):
            raise PlacementException("OUPS - Tous les paramètres doivent être entiers positifs")
        if self.cpus_per_task*self.tasks<=10:
            raise PlacementException("OUPS - moins de 10 cœurs utilisés: partition shared, placement non supporté")
        if self.cpus_per_task*self.tasks>self.archi.threads_per_core*self.archi.cores_per_node:
            msg = "OUPS - Pas assez de cores ! Diminuez cpus_per_task (";
            msg += str(self.cpus_per_task)
            msg += ") ou tasks ("
            msg += str(self.tasks)
            msg += ")"
            raise PlacementException(msg)

    # Tri INPLACE des threads dans chaque process
    def threadsSort(self,tasks_bound):
        for p in tasks_bound:
            p.sort()
#
# class ScatterMode, dérive de TaskBuilding, implémente les algos utilisés en mode scatter
#
class ScatterMode(TasksBinding):
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

        if self.tasks>1 and \
                self.cpus_per_task<self.archi.cores_per_socket and \
                self.cpus_per_task>self.archi.threads_per_core*self.archi.cores_per_socket:

            msg =  "OUPS - Votre task déborde du socket, cpus_per_task doit être <= "
            msg += str(self.archi.threads_per_core*self.archi.cores_per_socket)
            raise PlacementException(msg)
        
        if self.cpus_per_task*self.tasks>self.archi.threads_per_core*self.archi.cores_per_node:
            msg = "OUPS - Pas assez de cores ! Diminuez cpus_per_task (";
            msg += str(self.cpus_per_task)
            msg += ") ou tasks ("
            msg += str(self.tasks)
            msg += ")"
            raise PlacementException(msg)

        # max_tasks calculé ainsi permet d'être sûr de ne pas avoir une tâche entre deux sockets_per_node, 
        max_tasks = self.archi.sockets_per_node * self.archi.threads_per_core * (self.archi.cores_per_socket/self.cpus_per_task)
        if self.cpus_per_task>1:
            if self.tasks>max_tasks and max_tasks>0:
                msg = "OUPS - Une task est à cheval sur deux sockets ! Diminuez le nombre de tâches par nœuds, le maximum est "
                msg += str(max_tasks)
                raise PlacementException(msg)

    def distribProcesses(self):
        self.checkParameters()

        # cpus_per_task plus petit que cores_per_socket
        # placement -A   --mode=scatter 4 4
        #   S0-------- S1-------- 
        # P AAAACCCC.. BBBBDDDD.. 
        
        # placement -A   --mode=scatter --hyper 4 4
        #   S0-------- S1-------- 
        # P AAAA...... BBBB...... 
        # L CCCCDDDD.. DDDD...... 
        if self.cpus_per_task <= self.archi.cores_per_socket:
            c_step = self.cpus_per_task
            tasks_bounded=[]
            t_binding=[]
            t = 0
            th= 0
            for c in range(0,self.archi.cores_per_socket,c_step):
                for y in range(self.archi.threads_per_core):
                    for s in range(self.archi.sockets_per_node):
                        for th in range(self.cpus_per_task):
                            # Eviter le débordement sauf s'il n'y a qu'une seule task
                            if th==0 and self.archi.cores_per_socket-c<self.cpus_per_task:
                                continue
                            t_binding += [y*self.archi.cores_per_node + s*self.archi.cores_per_socket + c + th]
                        tasks_bounded += [t_binding]
                        t_binding = []
                        t += 1
                        if (t==self.tasks):
                            return tasks_bounded

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
            tmp_tasks_bounded= tmp_task_distrib.distribProcesses()
            # On a passé un nombre *2, donc on est sûr que ce nombre est bien pair
            imax = len(tmp_tasks_bounded)

            tasks_bounded = []
            for i in range(0,imax,2):
                t=[]
                t.extend(tmp_tasks_bounded[i])
                t.extend(tmp_tasks_bounded[i+1])
                tasks_bounded.append(t)
            
            return tasks_bounded

        # normalement on ne passe pas par là on a déjà retourné
        return tasks_bounded

#
# class CompactMode, dérive de TaskBuilding, implémente les algos utilisés en mode scatter
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

    def distribProcesses(self):
        self.checkParameters()

        if False:
            pass

        # cpus_per_task plus petit que cores_per_socket
        # ./placement -A   --mode=compact --hyper 4 4
        # S0-------- S1-------- 
        # P AAAABBBBCC .......... 
        # L CCDDDD.... ..........
        if self.cpus_per_task <= self.archi.cores_per_socket:
            tasks_bounded=[]
            t_binding=[]
            t = 0
            th= 0
            for s in range(self.archi.sockets_per_node):
                for h in range(self.archi.threads_per_core):
                    for c in range(self.archi.cores_per_socket):
                        t_binding += [h*self.archi.cores_per_node + s*self.archi.cores_per_socket + c]
                        th+=1
                        if th==self.cpus_per_task:
                            tasks_bounded += [t_binding]
                            t_binding = []
                            th = 0
                            t += 1
                            if (t==self.tasks):
                                return tasks_bounded

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
            tmp_tasks_bounded= tmp_task_distrib.distribProcesses()
            # On a passé un nombre *2, donc on est sûr que ce nombre est bien pair
            imax = len(tmp_tasks_bounded)/2

            tasks_bounded = []
            for i in range(imax):
                t=[]
                t.extend(tmp_tasks_bounded[i])
                t.extend(tmp_tasks_bounded[i+imax])
                tasks_bounded.append(t)
            
            return tasks_bounded

        # normalement on ne passe pas par là on a déjà retourné
        return tasks_bounded

#
# class RunningMode, dérive de TaskBuilding, implémente les algos utilisés en mode running, ie observe ce qui se passe
#                    lorsque l'application est exécutée
#                    En déduit archi, cpus_per_task,tasks !
#
class RunningMode(TasksBinding):
    def __init__(self,path):
        TasksBinding.__init__(self,None,0,0)
        self.path = path
        self.pid=[]
        self.aff=[]
        self.archi = None
        self.cpus_per_task = 0
        self.tasks = 0
        self.over_cores = []
        
    # Appelle la commande ps et retourne la liste des pid correspondant à la commande passée en paramètres
    # Afin d'éviter tout doublon (une hiérarchie de processes qui se partage le même cœur, on filtre les pid
    # en rejetant les processes si le ppid figure lui aussi dans la liste des pid
    def __identProcesses(self):
        cmd = "ps --no-headers -o %P,%p -C "
        cmd += self.path
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
	if p.returncode !=0:
            msg = "OUPS "
            msg += "AUCUNE TACHE TROUVEE: peut être n'êtes-vous pas sur la bonne machine ?"
            raise PlacementException(msg)
        else:
            # On met les ppid et les pid dans deux tableaux différents
            tmp_ppid=[]
            tmp_pid=[]
            pid=[]
            out = p.communicate()[0].split('\n')
            for p in out:
                if p != '':
                    tmp = p.split(',')
                    tmp_ppid.append(tmp[0].strip())
                    tmp_pid.append(tmp[1].strip())
            
            # On ne garde dans pid que les processes tels que ppid est absent de tmp_pid, afin de ne pas
            # sélectionner un process ET son père
            for i in range(len(tmp_ppid)):
                if tmp_ppid[i] in tmp_pid:
                    pass
                else:
                    pid.append(tmp_pid[i])
            return pid

    # Appelle taskset sur le pid passé en paramètre et renvoie l'affinité
    # Format retourné: 0-3
    def __runTaskSet(self,p):
        cmd = "taskset -c -p "
        cmd += p
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
	if p.returncode !=0:
            msg = "OUPS "
            msg += "La commande "
            msg += cmd
            msg += " a renvoyé l'erreur "
            msg += p.returncode
            raise PlacementException(msg)
        else:
            # On récupère l'affinité
            out = p.communicate()[0].split('\n')[0]
            return out.rpartition(" ")[2]

    # Appelle __runTaskSet taskset sur le tableau self.pid
    # Transforme les affinités retrounées: 0-3 ==> [0,1,2,3]
    # Renvoie tasks_bounded
    def __buildTasksBounded(self):
        tasks_bounded=[]
        for p in self.pid:
            aff = self.__runTaskSet(p)
            self.aff.append(aff)

            tasks_bounded.append(compactString2List(aff))
        return tasks_bounded

    # A partir de tasks_bounded, détermine l'architecture
    def __buildArchi(self,tasks_bounded):

        # On fait l'hypothèse que tous les tableaux de tasks_bounded ont la même longueur
        self.cpus_per_task = len(tasks_bounded[0])
        self.tasks         = len(tasks_bounded)
        self.sockets_per_node = SOCKETS_PER_NODE
        self.archi = Architecture(self.sockets_per_node, self.cpus_per_task, self.tasks, HYPERTHREADING)

    # Appelle __identProcesses pour récolter une liste de pids, la pose dans self.pid
    # puis appelle __buildTasksBounded pour construire tasks_bounded
    def distribProcesses(self):
        self.pid = self.__identProcesses()
        tasks_bounded = self.__buildTasksBounded()
        self.__buildArchi(tasks_bounded)
        return tasks_bounded

    # Renvoie (pour impression) la correspondance Tâche => pid
    def getTask2Pid(self):
        rvl  = "TACHE ==> PID ==> AFFINITE\n"
        rvl += "==========================\n"
        for i in range(len(self.pid)):
            rvl += numTaskToLetter(i)
            rvl += " ==> "
            rvl += self.pid[i]
            rvl += " ==> "
            rvl += self.aff[i]
            rvl += "\n"
            i += 1
        return rvl

# Renvoie les couples de processes qui présentent un recouvrement, ainsi que
# la liste des cœurs en cause
def detectOverlap(tasks_bounded):
    over=[]
    over_cores=[]
    for i in range(len(tasks_bounded)):
        for j in range(i+1,len(tasks_bounded)):
            overlap = list(set(tasks_bounded[i])&set(tasks_bounded[j]))
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


def main():

    # Parser de la ligne de commande
    parser = OptionParser(version="%prog 1.0",usage="%prog [options] tasks cpus_per_task")
    parser.add_option("-E","--examples",action="store_true",dest="example",help="Print some examples")
    parser.add_option("-S","--sockets_per_node",type="choice",choices=map(str,range(1,SOCKETS_PER_NODE+1)),default=SOCKETS_PER_NODE,dest="sockets",action="store",help="Nb of available sockets(1-%default, default %default)")
    parser.add_option("-T","--hyper",action="store_true",default=False,dest="hyper",help="Force use of HYPERTHREADING (%default)")
    parser.add_option("-M","--mode",type="choice",choices=["compact","scatter"],default="scatter",dest="mode",action="store",help="distribution mode: scatter, compact (%default)")
    parser.add_option("-H","--human",action="store_true",default=False,dest="human",help="Output humanly readable (%default)")
    parser.add_option("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable (%default)")

    parser.add_option("-R","--srun",action="store_const",dest="output_mode",const="srun",help="Output for srun (default)")
    parser.add_option("-N","--numactl",action="store_const",dest="output_mode",const="numactl",help="Output for numactl")
    parser.add_option("-C","--check",dest="check",action="store",help="Check the cpus binding of a running process")
    parser.set_defaults(output_mode="srun")
    (options, args) = parser.parse_args()

    try:

        if options.example==True:
            examples()
            exit(0)

        # Option --check
        if options.check != None:
            task_distrib = RunningMode(options.check)
            tasks_bounded= task_distrib.distribProcesses()
            #print tasks_bounded
            #print task_distrib.pid
            archi = task_distrib.archi
            cpus_per_task = task_distrib.cpus_per_task
            tasks         = task_distrib.tasks

            print task_distrib.getTask2Pid()
            print

            (overlap,over_cores) = detectOverlap(tasks_bounded)
            if len(overlap)>0:
                print "ATTENTION LES TACHES SUIVANTES ONT DES RECOUVREMENTS:"
                print "====================================================="
                print overlap
                print

        else:
            over_cores = None
            [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
            archi = Architecture(int(options.sockets), cpus_per_task, tasks, options.hyper)
            task_distrib = ""
            if options.mode == "scatter":
                task_distrib = ScatterMode(archi,cpus_per_task,tasks)
            else:
                task_distrib = CompactMode(archi,cpus_per_task,tasks)
            
            tasks_bounded = task_distrib.distribProcesses()

        task_distrib.threadsSort(tasks_bounded)

    except PlacementException, e:
        print e
        exit(1)

# Imprime le binding de manière compréhensible pour les humains
    if options.human==True:
        print getCpuBinding(archi,tasks_bounded,getCpuTaskHumanBinding)
    
# Imprime le binding en ascii art
    if options.asciiart==True:
        if tasks<=62:
            print getCpuBindingAscii(archi,tasks_bounded,over_cores)
        else:
            print getCpuBinding(archi,tasks_bounded,getCpuTaskAsciiBinding)
    
# Imprime le binding de manière compréhensible pour srun ou numactl
# (PAS si --check)
    if options.check == None:
        if options.output_mode=="srun":
            print getCpuBindingSrun(archi,tasks_bounded)
        if options.output_mode=="numactl":
            print getCpuBindingNumactl(archi,tasks_bounded)

def examples():
    ex = """USING placement IN AN SBATCH SCRIPT
===================================

1/ Insert the following lines in your script:

placement -A
if [[ $? != 0 ]]
then
 echo "ERREUR DANS LE NOMBRE DE PROCESSES OU DE TACHES" 2>&1
 exit $?
fi

2/ Modify your srun call as followes:

srun $(placement) ./my_application
"""
    print ex

if __name__ == "__main__":
    main()
