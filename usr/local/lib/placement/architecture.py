#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
import subprocess

# class Architecture: 
#       Description de l'architecture dans une classe
#       CLASSE ABSTRAITE - NE PAS UTILISER DIRECTEMENT
#
#       Paramètres du constructeur:
#           hardware        : Un objet de classe Hardware (les limites hardware du système)
#           sockets_per_node: Nombre de sockets par node, doit être < hardware.SOCKETS_PER_NODE 
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
    def __init__(self, hardware, sockets_per_node, cpus_per_task, tasks, hyper):
        if sockets_per_node > hardware.SOCKETS_PER_NODE:
            msg = "ERREUR INTERNE "
            msg += str(sockets_per_node)
            msg += " > " 
            msg += str(hardware.SOCKETS_PER_NODE)
            print msg
            raise PlacementException(msg)

        self.hardware         = hardware
        self.sockets_per_node = sockets_per_node+0
        self.sockets_reserved = self.sockets_per_node
        self.l_sockets        = None
        self.cores_per_socket = self.hardware.CORES_PER_SOCKET
        self.cores_per_node   = self.sockets_per_node * self.cores_per_socket
        self.cores_reserved   = self.cores_per_node
        self.m_cores          = None
        #print self.sockets_per_node,self.cores_per_socket,self.cores_per_node,self.threads_per_core

    # Accepte d'initialiser un attribut seulement s'il n'existe pas
    def __setattr__(self,name,value):
        try:
            getattr(self,name)
            raise PlacementException("ERREUR INTERNE - Pas le droit de changer les attributs")
        except Exception:
            object.__setattr__(self,name,value)

    #
    # Active l'hyperthreading si nécessaire:
    #         si hyper == True on active
    #         sinon on active seulement si nécessaire
    #         Si la variable globale hardware.HYPERTHREADING est à False et que l'hyperthreading doit être
    #         activé, on lève une exception
    #
    #         Retourne threads_per_core (1 ou 2)
    #
    def activateHyper(self,hyper,cpus_per_task,tasks):
        threads_per_core=1
        if hyper==True or (cpus_per_task*tasks>self.cores_reserved and cpus_per_task*tasks<=self.hardware.THREADS_PER_CORE*self.cores_reserved):
            if self.hardware.HYPERTHREADING:
                threads_per_core = self.hardware.THREADS_PER_CORE
            else:
                msg = "OUPS - l'hyperthreading n'est pas actif sur cette machine"
                raise PlacementException(msg)
        return threads_per_core

    # Renvoie le numéro de socket à prtir du numéro de cœur
    # Utilisé par certains affichages
    # TODO - Pour le moment IGNORE L'HYPERTHREADING OULALA
    def getCore2Socket(self,core):
        return core / self.cores_per_socket

    # Renvoie le numéro de cœur sur le socket courant
    # Utilisé par certains affichages
    # TODO - Pour le moment IGNORE L'HYPERTHREADING OULALA
    def getCore2Core(self,core):
        return core % self.cores_per_socket

    def getSocket2CoreMax(self,s):
        return (s+1) * self.cores_per_socket - 1

    def getSocket2CoreMin(self,s):
        return s * self.cores_per_socket

#
# class Exclusive:
#       Description de l'architecture dans le cas où le nœud est dédié (partition exclusive)
#
#       Paramètres du constructeur:
#           hardware        : Un objet de classe Hardware (les limites hardware du système)
#           sockets_per_node: Nombre de sockets par node, doit être < hardware.SOCKETS_PER_NODE 
#           tasks           : Nombre de tâches (processes) souhaité
#           cpus_per_task   : Nombre de cpus par process
#           hyper           : Si False, hyperthreading interdit
#
#       Construit le tableau l_sockets, qui sera utilisé pour les différents itérations

class Exclusive(Architecture):
    def __init__(self, hardware, sockets_per_node, cpus_per_task, tasks, hyper):
        Architecture.__init__(self, hardware, sockets_per_node, cpus_per_task, tasks, hyper)
        self.l_sockets = range(sockets_per_node)
        self.threads_per_core = self.activateHyper(hyper,cpus_per_task,tasks)
        self.m_cores = None

#
# class Shared:
#       Description de l'architecture dans le cas où le nœud est partagé (partitions shared, mesca)
#
#       Paramètres du constructeur:
#           hardware        : Un objet de classe Hardware (les limites hardware du système)
#           sockets_per_node: Nombre de sockets par node, doit être <= hard.SOCKETS_PER_NODE 
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
    def __init__(self, hardware, sockets_per_node, cpus_per_task, tasks, hyper):
        Architecture.__init__(self, hardware, sockets_per_node, cpus_per_task, tasks, hyper)
        if 'SLURM_NODELIST' in os.environ:
            (self.l_sockets,self.m_cores) = self.__detectSockets()
            #if len(self.l_sockets)<self.sockets_per_node:
            #   self.sockets_per_node = len(self.l_sockets)
               # msg  = "OUPS - Vous avez demandé "
               # msg += str(self.sockets_per_node) 
               # msg += " sockets, vous en avez "
               # msg += str(len(self.l_sockets))
               # raise PlacementException(msg)
        else:
            self.l_sockets = range(sockets_per_node)
            self.m_cores = None
        
        self.sockets_reserved = len(self.l_sockets)
        if self.m_cores != None:
            self.cores_reserved = 0
            for s in self.m_cores:
                for c in self.m_cores[s]:
                    if self.m_cores[s][c]:
                        self.cores_reserved += 1
        else:
            self.cores_reserved   = self.cores_per_socket * self.sockets_reserved
        self.threads_per_core = self.activateHyper(hyper,cpus_per_task,tasks)

    #
    # Detecte les sockets et les cores qui nous sont alloués, en analysant la sortie de la commande numactl --show
    # Retourne les tableaux:
    #                          l_sockets => liste des sockets
    #                          m_cores   => masque des cores alloués ou pas (dictionnaire, k=numéro de core/v=True/False)
    # ATTENTION Cette fonction analyse la sortie de numactl --show, elle est sans doute très dépendante de la version de numactl !
    #
    def __detectSockets(self):
        l_sockets = []
        m_cores   = {}
        cmd = "numactl --show"
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
	if p.returncode !=0:
            msg = "OUPS "
            msg += "Erreur numactl - peut-être n'êtes-vous pas sur la bonne machine ?"
            raise PlacementException(msg)
        else:
            output = p.communicate()[0].split('\n')

            # l_sockets à partir de la Ligne nodebind de numactl:
            # nodebind: 4 5 6 => [4,5,6]
            for l in output:
                if l.startswith('nodebind:'):
                    l_sockets = map(int,l.rpartition(':')[2].strip().split(' '))
                elif l.startswith('physcpubind:'):
                    physcpubind = map(int,l.rpartition(':')[2].strip().split(' '))

            # génération de m_cores à partir de l_sockets et de physcpubind
            for s in l_sockets:
                cores={}
                for c in range(self.cores_per_socket):
                    c1 = c + s*self.cores_per_socket
                    cores[c1] = c1 in physcpubind
                m_cores[s] = cores

            # Vérification qu'il n'y a pas d'incohérence
            if len(l_sockets) > self.sockets_per_node:
                msg  = "OUPS - sockets_per_node=" + str(self.sockets_per_node)
                msg += " devrait avoir au moins la valeur " +  str(len(l_sockets))
                msg += " Vérifiez le switch -S"
                raise PlacementException(msg)

            for s in l_sockets:
                if len(m_cores[s]) != self.cores_per_socket:
                    msg  = "OUPS - cores_per_socket=" + str(self.cores_per_socket)
                    msg += " être égal à " +  str(m_cores[s])
                    msg += " Vérifiez le switch -S"
                    raise PlacementException(msg)

            return [l_sockets,m_cores]


