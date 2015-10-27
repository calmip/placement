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

#############################################################################################################
#
#  ARCHITECTURE: L'architecture dépend:
#                     1/ DE LA MACHINE (variable ARCHI, classes dérivant de ARCHITECTURE) ET de son UTILISATION 
#                     2/ DE SON UTILISATION (classe Architecture, Exclusive et Shared)
#
# Constantes liées à nos architectures: 

class ARCHITECTURE(object):
    NAME             = 'unknown'
    SOCKETS_PER_NODE = ''
    CORES_PER_SOCKET = ''
    HYPERTHREADING   = ''
    THREADS_PER_CORE = ''
    IS_SHARED        = ''

# 1/ BULLx DLC (eos), 2 sockets Intel Ivybridge 10 cœurs, hyperthreading activé
class BULLX_DLC(ARCHITECTURE):
    NAME             = 'Bullx_dlc'
    SOCKETS_PER_NODE = 2
    CORES_PER_SOCKET = 10
    HYPERTHREADING   = True
    THREADS_PER_CORE = 2
    IS_SHARED        = False

# 2 / SGI UV, uvprod, 48 sockets, 8 cœurs par socket, pas d'hyperthreading, SHARED
class UVPROD(ARCHITECTURE):
    NAME             = 'uvprod'
    SOCKETS_PER_NODE = 48
    CORES_PER_SOCKET = 8
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = True

# 3/ BULL SMP-mesca, 8 sockets, 15 cœurs par socket, pas d'hyperthreading
class MESCA(ARCHITECTURE):
    NAME             = 'bull mesca1'
    SOCKETS_PER_NODE = 8
    CORES_PER_SOCKET = 15
    HYPERTHREADING   = False
    THREADS_PER_CORE = 1
    IS_SHARED        = False

# Changer cette variable en changeant d'architecture (cf. lignes 70 et suivantes)
ARCHI = ''
#ARCHI = BULLX_DLC()
#ARCHI = UVPROD()
#ARCHI = MESCA()
if ARCHI == '':
    if 'SLURM_NODELIST' in os.environ:
        if os.environ['SLURM_NODELIST'] == 'uvprod':
            ARCHI = UVPROD()
        else:
            ARCHI = BULLX_DLC()
    elif 'PLACEMENT_ARCHI' in os.environ:
        if os.environ['PLACEMENT_ARCHI'] == 'uvprod':
            ARCHI = UVPROD()
        elif os.environ['PLACEMENT_ARCHI'] == 'eos':
            ARCHI = BULLX_DLC()
        else:
            raise PlacementException("OUPS - PLACEMENT_ARCHI="+os.environ['PLACEMENT_ARCHI']+" Architecture inconnue")
    elif 'HOSTNAME' in os.environ and os.environ['HOSTNAME'] == 'uvprod':
            ARCHI = UVPROD()
    
if ARCHI == '':
    ARCHI = BULLX_DLC()

# class Architecture: 
#       Description de l'architecture dans une classe
#       CLASSE ABSTRAITE - NE PAS UTILISER DIRECTEMENT
#
#       Paramètres du constructeur:
#           sockets_per_node: Nombre de sockets par node, doit être < ARCHI.SOCKETS_PER_NODE 
#           tasks           : Nombre de tâches (processes) souhaité
#           cpus_per_task   : Nombre de cpus par process
#           hyper           : Si False, hyperthreading interdit
#
#           - tasks, threads_per_task, et la constante ARCHI.HYPERTHREADING permet de calculer le nombre
#           de threads par cœur
#           - cores_per_socket est fixe (cf. ARCHI.CORES_PER_SOCKET)
#           - Le nombre de cores par nœud dérive de sockets_per_node et cores_per_socket
#       Il est interdit (et impossible) de changer les attributs par la suite
class Architecture(object):
    def __init__(self, sockets_per_node, cpus_per_task, tasks, hyper):
        if sockets_per_node > ARCHI.SOCKETS_PER_NODE:
            msg = "ERREUR INTERNE "
            msg += str(sockets_per_node)
            msg += " > " 
            msg += str(ARCHI.SOCKETS_PER_NODE)
            print msg
            raise PlacementException(msg)

        self.sockets_per_node = sockets_per_node+0
        self.sockets_reserved = self.sockets_per_node
        self.l_sockets  = None
        self.cores_per_socket = ARCHI.CORES_PER_SOCKET
        self.cores_per_node   = self.sockets_per_node * self.cores_per_socket
        self.cores_reserved   = self.cores_per_node

        #print self.sockets_per_node,self.cores_per_socket,self.cores_per_node,self.threads_per_core

    # Accepte d'initialiser un attribut seulement s'il n'existe pas
    def __setattr__(self,name,value):
        try:
            getattr(self,name)
            raise PlacementException("ERREUR INTERNE - Pas le droit de changer les attributs")
        except Exception:
            object.__setattr__(self,name,value)

    #
    # Active l'ARCHI.HYPERTHREADING si nécessaire:
    #         si hyper == True on active
    #         sinon on active seulement si nécessaire
    #         Si la variable globale ARCHI.HYPERTHREADING est à False et que l'ARCHI.HYPERTHREADING doit être
    #         activé, on lève une exception
    #
    #         Retourne threads_per_core (1 ou 2)
    #
    def activateHyper(self,hyper,cpus_per_task,tasks):
        threads_per_core=1
        if hyper==True or (cpus_per_task*tasks>self.cores_reserved and cpus_per_task*tasks<=ARCHI.THREADS_PER_CORE*self.cores_reserved):
            if ARCHI.HYPERTHREADING:
                threads_per_core = ARCHI.THREADS_PER_CORE
            else:
                msg = "OUPS - l'ARCHI.HYPERTHREADING n'est pas actif sur cette machine"
                raise PlacementException(msg)
        return threads_per_core

#
# class Exclusive:
#       Description de l'architecture dans le cas où le nœud est dédié (partition exclusive)
#
#       Paramètres du constructeur:
#           sockets_per_node: Nombre de sockets par node, doit être < ARCHI.SOCKETS_PER_NODE 
#           tasks           : Nombre de tâches (processes) souhaité
#           cpus_per_task   : Nombre de cpus par process
#           hyper           : Si False, hyperthreading interdit
#
#       Construit le tableau l_sockets, qui sera utilisé pour les différents itérations

class Exclusive(Architecture):
    def __init__(self, sockets_per_node, cpus_per_task, tasks, hyper):
        Architecture.__init__(self, sockets_per_node, cpus_per_task, tasks, hyper)
        self.l_sockets = range(sockets_per_node)
        self.threads_per_core = self.activateHyper(hyper,cpus_per_task,tasks)

#
# class Shared:
#       Description de l'architecture dans le cas où le nœud est partagé (partition shared, uvprod)
#
#       Paramètres du constructeur:
#           sockets_per_node: Nombre de sockets par node, doit être < ARCHI.SOCKETS_PER_NODE 
#           tasks           : Nombre de tâches (processes) souhaité
#           cpus_per_task   : Nombre de cpus par process
#           hyper           : Si False, hyperthreading interdit
#
#       Construit le tableau l_sockets, qui sera utilisé pour les différentes itérations:
#           1/ Si la variable SLURM_NODELIST est définie, DONC si on tourne dans l'environnement SLURM, le tableau 
#              est construit à partir de l'appel numactl --show
#              Dans ce cas, on vérifie que sockets_per_node <= len(l_sockets)
#           2/ Sinon il est construit comme pour la classe Exclusive, à partir de sockets_per_node
#       

class Shared(Architecture):
    def __init__(self, sockets_per_node, cpus_per_task, tasks, hyper):
        Architecture.__init__(self, sockets_per_node, cpus_per_task, tasks, hyper)
        if 'SLURM_NODELIST' in os.environ:
            self.l_sockets = self.__detectSockets()
            #if len(self.l_sockets)<self.sockets_per_node:
            #   self.sockets_per_node = len(self.l_sockets)
               # msg  = "OUPS - Vous avez demandé "
               # msg += str(self.sockets_per_node) 
               # msg += " sockets, vous en avez "
               # msg += str(len(self.l_sockets))
               # raise PlacementException(msg)
        else:
            self.l_sockets = range(sockets_per_node)
        
        self.sockets_reserved = len(self.l_sockets)
        self.cores_reserved   = self.cores_per_socket * self.sockets_reserved
        self.threads_per_core = self.activateHyper(hyper,cpus_per_task,tasks)

    def __detectSockets(self):
        cmd = "numactl --show|fgrep nodebind"
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
	if p.returncode !=0:
            msg = "OUPS "
            msg += "Erreur numactl - peut-être n'êtes-vous pas sur la bonne machine ?"
            raise PlacementException(msg)
        else:
            out = p.communicate()[0].split('\n')[0]
            # nodebind: 4 5 6 => [4,5,6]
            l_sockets = map(int,out.rpartition(':')[2].strip().split(' '))
            if max(l_sockets)>self.sockets_per_node:
                msg  = "OUPS - sockets_per_node=" + str(self.sockets_per_node)
                msg += " devrait avoir au moins la valeur " +  str(max(l_sockets))
                msg += " Vérifiez le switch -S"
                raise PlacementException(msg)
            return l_sockets

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
# distribTasks()
#      Construit le tableau de tableaux tasks_binding à partir des paramètres
# 
#      Params: check, si True (defaut), check les valeurs de tasks etc avant d'accepter
#
#      Return: tasks_bound, un tableau de tableaux:
#              Le tableau des processes, chaque process est représenté par un tableau de cœurs.
#
    
class TasksBinding(object):
    def __init__(self,archi,cpus_per_task,tasks):
        self.archi = archi
        self.cpus_per_task = cpus_per_task
        self.tasks = tasks

    def checkParameters(self):
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")
    def distribTasks(self,check=True):
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")

    # Code commun à toutes les classes dérivées
    # _checkParameters doit être appelé par toutes les fonctions checkParameters()
    def _checkParameters(self):
        if (self.cpus_per_task<0 or self.tasks<0 ):
            raise PlacementException("OUPS - Tous les paramètres doivent être entiers positifs")
        #if self.cpus_per_task*self.tasks <= 10:
        #    raise PlacementException("OUPS - moins de 10 cœurs utilisés: partition shared, placement non supporté")
        if self.cpus_per_task*self.tasks>self.archi.threads_per_core*self.archi.cores_reserved:
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
        
        # max_tasks calculé ainsi permet d'être sûr de ne pas avoir une tâche entre deux sockets_per_node, 
        max_tasks = self.archi.sockets_reserved * self.archi.threads_per_core * (self.archi.cores_per_socket/self.cpus_per_task)
        if self.cpus_per_task>1:
            if self.tasks>max_tasks and max_tasks>0:
                msg = "OUPS - Une task est à cheval sur deux sockets ! Diminuez le nombre de tâches par nœuds, le maximum est "
                msg += str(max_tasks)
                raise PlacementException(msg)

    def distribTasks(self,check=True):
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
            for c in range(0,self.archi.cores_per_socket,c_step):
                for y in range(self.archi.threads_per_core):
                    for s in self.archi.l_sockets:
                        for th in range(self.cpus_per_task):
                            # Eviter le débordement sauf s'il n'y a qu'une seule task
                            if th==0 and self.archi.cores_per_socket-c<self.cpus_per_task:
                                continue
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
        if self.cpus_per_task <= self.archi.cores_per_socket:
            tasks_bound=[]
            t_binding=[]
            t = 0
            th= 0
            for s in self.archi.l_sockets:
                for h in range(self.archi.threads_per_core):
                    for c in range(self.archi.cores_per_socket):
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
    # Renvoie tasks_bound
    def __buildTasksBound(self):
        tasks_bound=[]
        for p in self.pid:
            aff = self.__runTaskSet(p)
            self.aff.append(aff)

            tasks_bound.append(compactString2List(aff))
        return tasks_bound

    # A partir de tasks_bound, détermine l'architecture
    def __buildArchi(self,tasks_bound):

        # On fait l'hypothèse que tous les tableaux de tasks_bound ont la même longueur
        self.cpus_per_task = len(tasks_bound[0])
        self.tasks         = len(tasks_bound)
        self.sockets_per_node = ARCHI.SOCKETS_PER_NODE
        self.archi = Exclusive(self.sockets_per_node, self.cpus_per_task, self.tasks, ARCHI.HYPERTHREADING)

    # Appelle __identProcesses pour récolter une liste de pids, la pose dans self.pid
    # puis appelle __buildTasksBound pour construire tasks_bound
    def distribTasks(self,check=False):
        self.pid = self.__identProcesses()
        tasks_bound = self.__buildTasksBound()
        self.__buildArchi(tasks_bound)
        return tasks_bound

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

def main():

    # Si la variable PLACEMENT_DEBUG existe, on simule un environnement shared avec des réservations
    # Exemple: export PLACEMENT_DEBUG='9,10,11,12,13' pour simuler un environnement shared, 5 sockets réservées
    # NB - Ne pas oublier non plus de positionner SLURM_NODELIST ! (PAS PLACEMENT_ARCHI ça n'activera pas Shared)
    if 'PLACEMENT_DEBUG' in os.environ:
        import mock
        placement_debug=os.environ['PLACEMENT_DEBUG']
        rvl=map(int,placement_debug.split(','))
        Shared._Shared__detectSockets = mock.Mock(return_value=rvl)

    epilog = 'Environment:\n PLACEMENT_ARCHI, SLURM_NODELIST, SLURM_TASKS_PER_NODE, SLURM_CPUS_PER_TASK'
    parser = OptionParser(version="%prog 1.0",usage="%prog [options] tasks cpus_per_task",epilog=epilog)
    parser.add_option("-I","--archi",dest='show_archi',action="store_true",help="Show the currently selected architecture")
    parser.add_option("-E","--examples",action="store_true",dest="example",help="Print some examples")
    parser.add_option("-S","--sockets_per_node",type="choice",choices=map(str,range(1,ARCHI.SOCKETS_PER_NODE+1)),default=ARCHI.SOCKETS_PER_NODE,dest="sockets",action="store",help="Nb of available sockets(1-%default, default %default)")
    parser.add_option("-T","--hyper",action="store_true",default=False,dest="hyper",help="Force use of ARCHI.HYPERTHREADING (%default)")
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
        if options.show_archi==True:
            show_archi()
            exit(0)
        # Option --check
        if options.check != None:
            task_distrib = RunningMode(options.check)
            tasks_bound= task_distrib.distribTasks()
            #print tasks_bound
            #print task_distrib.pid
            archi = task_distrib.archi
            cpus_per_task = task_distrib.cpus_per_task
            tasks         = task_distrib.tasks

            print task_distrib.getTask2Pid()
            print

            (overlap,over_cores) = detectOverlap(tasks_bound)
            if len(overlap)>0:
                print "ATTENTION LES TACHES SUIVANTES ONT DES RECOUVREMENTS:"
                print "====================================================="
                print overlap
                print

        else:
            over_cores = None
            [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
            if ARCHI.IS_SHARED:
                archi = Shared(int(options.sockets), cpus_per_task, tasks, options.hyper)
            else:
                archi = Exclusive(int(options.sockets), cpus_per_task, tasks, options.hyper)
            
            task_distrib = ""
            if options.mode == "scatter":
                task_distrib = ScatterMode(archi,cpus_per_task,tasks)
            else:
                task_distrib = CompactMode(archi,cpus_per_task,tasks)
            
            tasks_bound = task_distrib.distribTasks()

        task_distrib.threadsSort(tasks_bound)


        # Imprime le binding de manière compréhensible pour les humains
        if options.human==True:
            print getCpuBinding(archi,tasks_bound,getCpuTaskHumanBinding)
    
        # Imprime le binding en ascii art
        if options.asciiart==True:
            if tasks<=62:
                print getCpuBindingAscii(archi,tasks_bound,over_cores)
            else:
                # print getCpuBinding(archi,tasks_bound,getCpuTaskAsciiBinding)
                raise PlacementException("OUPS - switch --ascii interdit pour plus de 62 tâches !")
    
        # Imprime le binding de manière compréhensible pour srun ou numactl
        # (PAS si --check)
        if options.check == None:
            if options.output_mode=="srun":
                print getCpuBindingSrun(archi,tasks_bound)
            if options.output_mode=="numactl":
                print getCpuBindingNumactl(archi,tasks_bound)

    except PlacementException, e:
        print e
        exit(1)

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

def show_archi():
    msg = "Current architecture = " + ARCHI.NAME + " "
    if ARCHI.NAME != 'unknown':
        msg += '(' + str(ARCHI.SOCKETS_PER_NODE) + ' sockets/node, '
        msg += str(ARCHI.CORES_PER_SOCKET) + ' cores/socket, '
        if ARCHI.HYPERTHREADING:
            msg += 'Hyperthreading ON, ' + str(ARCHI.THREADS_PER_CORE) + ' threads/core, '
        if ARCHI.IS_SHARED:
            msg += 'SHARED'
        else:
            msg += 'EXCLUSIVE'
        msg += ')'
        print(msg)

if __name__ == "__main__":
    main()
