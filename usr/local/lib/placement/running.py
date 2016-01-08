#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
from exception import *
from tasksbinding import *
from utilities import *
from architecture import *
import subprocess

#
# class RunningMode, dérive de TaskBuilding, implémente les algos utilisés en mode running, ie observe ce qui se passe
#                    lorsque l'application est exécutée
#                    En déduit archi, cpus_per_task,tasks !
#
class RunningMode(TasksBinding):
    def __init__(self,path,hardware,buildTasksBound):
        TasksBinding.__init__(self,None,0,0)
        self.path = path
        self.hardware = hardware
        self.pid=[]
        self.tasks_bound=[]
        self.archi = None
        self.cpus_per_task = 0
        self.tasks = 0
        self.over_cores = []
        self.__buildTasksBound = buildTasksBound
        #self.__buildTasksBound = BuildTasksBoundFromPs()
        #self.__buildTasksBound = BuildTasksBoundFromTaskSet()
        
    # Appelle la commande ps et retourne la liste des pid correspondant à la commande passée en paramètres
    # Afin d'éviter tout doublon (une hiérarchie de processes qui se partage le même cœur, on filtre les pid
    # en rejetant les processes si le ppid figure lui aussi dans la liste des pid
    # Afin d'éviter les ps accessoires (ssh) on ne garde que les processes dont le sid est celui d'un process slurmdstepd
    def __identProcesses(self):
        slurmstepd_sid = self.__identSlurmStepd()
        if len(slurmstepd_sid)==0:
            msg = "OUPS - PAS DE PROCESS slurmstepd TROUVE, CE NOEUD NE FAIT RIEN !"
            raise PlacementException(msg)

        cmd = "ps --no-headers -o %P,%p, -o sid -C "
        cmd += self.path
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas: on essaie avec le user !
        if p.returncode !=0:
            cmd = "ps --no-headers -o %P,%p, -o sid -U "
            cmd += self.path
            p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            p.wait()

            # Si returncode toujours non nul, on laisse bertom
            if p.returncode !=0:
                msg = "OUPS "
                msg += "AUCUNE TACHE TROUVEE: peut être n'êtes-vous pas sur la bonne machine ?"
                raise PlacementException(msg)

        # On met les ppid, les pid et les sid dans trois tableaux différents
        tmp_ppid=[]
        tmp_pid=[]
        tmp_sid=[]
        pid=[]
        out = p.communicate()[0].split('\n')

        for p in out:
            if p != '':
                tmp = p.split(',')
                tmp_ppid.append(tmp[0].strip())
                tmp_pid.append(tmp[1].strip())
                tmp_sid.append(tmp[2].strip())

        #print str(tmp_ppid)
        #print str(tmp_pid)
        #print str(tmp_sid)
        #print str(slurmstepd_sid)

        # On ne garde dans pid que les processes tels que pid est absent de tmp_ppid, afin de ne pas
        # sélectionner un process ET son père
        # De plus on ne garde que les processes tels que sid est present dans slurmstepd_sid, afin de ne sélectionner QUE
        # les processus réellement lancés par slurm
        for i in range(len(tmp_ppid)):
            if tmp_pid[i] in tmp_ppid:
                pass
            else:
                if tmp_sid[i] in slurmstepd_sid:
                    pid.append(tmp_pid[i])
                else:
                    pass
        #print ('pid => ' + str(pid))
        return pid

    # Renvoie la liste des sid des processes slurmstepd
    def __identSlurmStepd (self):
        cmd = "ps --no-header -C slurmstepd  -o sid"
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()

        def f(s):
            return s.strip()

        # Si returncode non nul, aucun de job ne troune sur cette machine
        if p.returncode !=0:
            return []
        else:
            return map(f,p.communicate()[0].split("\n"))
            

    # Appelle ps en lui passant le pid et renvoie le nom de la commande
    def __pid2cmdu(self,pid):
        cmd = "ps --no-headers -o %c,%u -p " + str(pid)
        p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
        if p.returncode !=0:
            msg = "OUPS "
            msg += "AUCUNE TACHE TROUVEE: peut-etre le pid vient-il de mourir ?"
            raise PlacementException(msg)
        else:
            cu = p.communicate()[0].split("\n")[0]
            #print 'hoho'+cu
            #[c,space,u] = cu.split(' ',2)
            #u = u.strip()
            #cu = c+','+u
            return cu

    # A partir de tasks_bound, détermine l'architecture
    def __buildArchi(self,tasks_bound):

        # On fait l'hypothèse que tous les tableaux de tasks_bound ont la même longueur
        self.cpus_per_task = len(tasks_bound[0])
        self.tasks         = len(tasks_bound)
        self.sockets_per_node = self.hardware.SOCKETS_PER_NODE
        self.archi = Exclusive(self.hardware,self.sockets_per_node, self.cpus_per_task, self.tasks, self.hardware.HYPERTHREADING)

    # Appelle __identProcesses pour récolter une liste de pids, la pose dans self.pid
    # puis appelle __buildTasksBound pour construire tasks_bound
    def distribTasks(self,check=False):
        # Récupère la liste des processes à étudier par ps
        self.pid = self.__identProcesses()

        # Détermine l'affinité des processes en utilisant taskset
        self.tasks_bound = self.__buildTasksBound(self)

        # Détermine l'architecture à partir des infos de hardware et des infos de processes ou de threads
        self.__buildArchi(self.tasks_bound)

        return self.tasks_bound

    # Renvoie (pour impression) la correspondance Tâche => pid
    def getTask2Pid(self):
        rvl  = "TACHE ==> PID (CMD) ==> AFFINITE\n"
        rvl += "==========================\n"
        for i in range(len(self.pid)):
            rvl += numTaskToLetter(i)
            rvl += " ==> "
            rvl += self.pid[i]
            rvl += ' ('
            rvl += self.__pid2cmdu(self.pid[i])
            rvl += ") ==> "
            rvl += list2CompactString(self.tasks_bound[i])
            rvl += "\n"
            i += 1
        return rvl


# Classe abstraite de base
class BuildTasksBound:
    def __call__(self):
        raise("ERREUR INTERNE - FONCTION VIRTUELLE PURE !")

# Fonction-objet pour construire la structure de données tasksBinding à partir de taskset
class BuildTasksBoundFromTaskSet(BuildTasksBound):
    # Appelle __taskset sur le tableau tasksBinding.pid
    # Transforme les affinités retournées: 0-3 ==> [0,1,2,3]
    # Renvoie tasks_bound
    def __call__(self,tasksBinding):
        tasks_bound=[]
        for p in tasksBinding.pid:
            aff = self.__runTaskSet(p)
            tasks_bound.append(compactString2List(aff))
        return tasks_bound

    # Appelle taskset pour le ps passé en paramètre
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

# Appelle ps pour chaque process de self.pid
# Renvoie tasks_bound
class BuildTasksBoundFromPs(BuildTasksBound):
    def __call__(self,tasksBinding):
        tasks_bound=[]
        for p in tasksBinding.pid:
            aff = self.__runPs(p)
            tasks_bound.append(aff)
        return tasks_bound

    # Appelle ps pour le process passé en paramètre
    # Renvoie un tableau contenant la liste des cpus associés aux threads de ce process
    def __runPs(self,p):
        cmd = "ps -m --no-header -o psr,s -p "
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
            psout = p.communicate()[0].split('\n')
            out   = []
            for l in psout:
                if l.endswith('R'):
                    out.append(int(l.strip(' R')))
            return out


