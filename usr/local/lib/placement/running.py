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
    def __init__(self,path,hardware):
        TasksBinding.__init__(self,None,0,0)
        self.path = path
        self.hardware = hardware
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

    # Appelle ps en lui passant le pid et renvoie le nom de la commande
    def __pid2cmdu(self,pid):
        cmd = "ps --no-headers -o %c%u -p " + str(pid)
	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
	p.wait()
        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
	if p.returncode !=0:
            msg = "OUPS "
            msg += "AUCUNE TACHE TROUVEE: peut-etre le pid vient-il de mourir ?"
            raise PlacementException(msg)
        else:
            cu = p.communicate()[0].split("\n")[0]
            [c,space,u] = cu.split(' ',2)
            u = u.strip()
            cu = c+','+u
            return cu

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
        self.sockets_per_node = self.hardware.SOCKETS_PER_NODE
        self.archi = Exclusive(self.hardware,self.sockets_per_node, self.cpus_per_task, self.tasks, self.hardware.HYPERTHREADING)

    # Appelle __identProcesses pour récolter une liste de pids, la pose dans self.pid
    # puis appelle __buildTasksBound pour construire tasks_bound
    def distribTasks(self,check=False):
        self.pid = self.__identProcesses()
        tasks_bound = self.__buildTasksBound()
        self.__buildArchi(tasks_bound)
        return tasks_bound

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
            rvl += self.aff[i]
            rvl += "\n"
            i += 1
        return rvl
