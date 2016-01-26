#! /usr/bin/env python
# -*- coding: utf-8 -*-

import os
import re
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
        self.processus=[]
        self.tasks_bound   = None
        self.threads_bound = None
        self.archi = None
        self.cpus_per_task = 0
        self.tasks = 0
        self.over_cores = []
        self.__buildTasksBound = buildTasksBound
        self.__processus_reserves = ['srun', 'mpirun', 'ps', 'sshd' ]
        
    # Appelle la commande ps et retourne la liste des pid correspondant à la commande passée en paramètres
    # OU au user passé en paramètre OU sans sélection préalable
    # ne garde ensuite que les processes en état Run, et supprime les processes style ps
    # Initialise self.pid (la liste des processes_id) ET self.processes (TOUT sur les processes)
    def __identProcesses(self):

        ps_res=''

        # --check='+' ==> Recherche le fichier PROCESSES.txt dans le répertoire courant - pour déboguage
        if self.path == '+':
            fh_processes = open('PROCESSES.txt','r')
            #            for l in fh_processes:
            #                ps_res += l
            ps_res = fh_processes.readlines()
            fh_processes.close()
            for i,l in enumerate(ps_res):
                ps_res[i] = l.replace('\n','')
                

        # --check='*' ==> Pas de sélection de tâches !
        elif self.path == '*':
            cmd = "ps --no-headers -o %p -o tid -o %c -o state ax"
            p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            p.wait()
            if p.returncode !=0:
                msg = "OUPS " + cmd + " retourne une erreur: " + str(p.returncode)
                raise PlacementException(msg)
            else:
                ps_res = p.communicate()[0]
        
        # --check='un_nom' Supposons qu'il s'agisse d'un nom d'utilisateur
        else:
            cmd = "ps --no-headers -o %p -o tid -o %c -o state -U "
            cmd += self.path
            p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
            p.wait()

            # code de retour non nul, essayons avec un nom de commande
            if p.returncode !=0:
                cmd = "ps --no-headers -o %p -o tid -o %c -o state -C "
                cmd += self.path
                p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
                p.wait()

                # Si code de retour toujours non nul, on laisse beton
                if p.returncode !=0:
                    msg = "OUPS "
                    msg += "AUCUNE TACHE TROUVEE: peut être n'êtes-vous pas sur la bonne machine ?"
                    raise PlacementException(msg)
                else:
                    ps_res = p.communicate()[0]
            else:
                ps_res = p.communicate()[0]

        
###        # On met les pid, les tid dans deux tableaux différents
###        # On ne garde que les processes/threads en 'R' et qui ne sont pas ps ou autres noms "réservés"
###        pid=[]
###       tid=[]qq

        # Création de la structure de données processus
        # Dictionnaire:
        #    k = pid
        #    v = {'pid':pid, 'user':'utilisateur', 'cmd':'commande','threads':{'tid':{'tid':tid, 'psr';psr}}
        # On ne garde que les threads en état 'R' et on supprime les pid dont on a écarté tous les threads
        # On écarte aussi les pid dont le nom de commande est "réservé" (ps, top etc)
        # 
        processus         = {}
        processus_courant = {}
        
        for l in ps_res:

            # Détection des lignes représentant un processus
            mp=re.match(' *(\d+) +- +- +([^ ]+)',l)
            if mp != None:

                # S'il y a un processus_courant avec des threads actifs, on le sauve !
                if processus_courant.has_key('threads')==True:
                    processus[processus_courant['pid']] = processus_courant
                
                # On vide le processus courant, si processus réservé on passe à la ligne suivante
                processus_courant={}
                pid = int(mp.group(1))
                cmd = mp.group(2)
                if cmd in self.__processus_reserves:
                    continue
                else:
                    processus_courant['pid']=pid
                    processus_courant['cmd']=cmd
                    continue

            # Détection des lignes représentant un thread
            mt = re.match(' *- +(\d+) +(\d+) +- +([A-Z])',l)
            if mt != None:
                # Si pas de processus courant (en principe pas possible) ou processus courant non conservé, on passe
                if len(processus_courant)==0:
                    continue
                
                # Si state n'est pas R, on passe
                state = mt.group(3)
                if state != 'R':
                    continue

                # Sinon on garde la trace de ce thread dans processus_courant
                tid   = int(mt.group(1))
                psr   = int(mt.group(2))
                thread_courant        = {}
                thread_courant['tid'] = tid
                thread_courant['psr'] = psr
                if processus_courant.has_key('threads')== False:
                    processus_courant['threads'] = {}
                processus_courant['threads'][tid] = thread_courant

        self.processus = processus
        self.pid = processus.keys()


    # A partir du pid, renvoie le nom de la commande
    # Si possible on utilise self.processus, sinon on appelle la commande ps
    def __pid2cmdu(self,pid):
        if len(self.processus)==0:
            return self.__pid2cmduPs(pid)
        else:
            return self.processus[pid]['cmd']+','+'****'

    def __pid2cmduPs(self,pid):
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
            [c,space,u] = cu.split(' ',2)
            u = u.strip()
            cu = c+','+u
            return cu

    # A partir de tasks_bound, détermine l'architecture
    def __buildArchi(self,tasks_bound):

        # On n'utilise pas cpus_per_task, puisque les cœurs sont déjà distribués !
        self.cpus_per_task = -1
        self.tasks         = len(tasks_bound)
        self.sockets_per_node = self.hardware.SOCKETS_PER_NODE
        self.archi = Exclusive(self.hardware,self.sockets_per_node, self.cpus_per_task, self.tasks, self.hardware.HYPERTHREADING)

    def distribTasks(self,check=False):
        if self.tasks_bound==None:
            self.__initTasksThreadsBound()
        return self.tasks_bound 

    def distribThreads(self,check=False):
        if self.threads_bound==None:

            self.__initTasksThreadsBound()
        return self.threads_bound

    # Appelle __identProcesses pour récolter une liste de pids (self.pid)
    # puis appelle __buildTasksBound pour construire tasks_bound et threads_bound
    def __initTasksThreadsBound(self):
        
        # Récupère la liste des processes à étudier par ps
        self.__identProcesses()

        # Détermine l'affinité des processes et des threads
        self.tasks_bound   = self.__buildTasksBound(self)
        self.threads_bound = self.processus
        
        # Si aucune tâche trouvée, pas la peine d'insister
        if len(self.tasks_bound)==0:
            msg = "OUPS Aucune tâche trouvée !"
            raise PlacementException(msg)

        # Détermine l'architecture à partir des infos de hardware et des infos de processes ou de threads
        self.__buildArchi(self.tasks_bound)

    # Renvoie (pour impression) la correspondance Tâche => pid
    def getTask2Pid(self):
        rvl  = "TACHE ==> PID (CMD) ==> AFFINITE\n"
        rvl += "==========================\n"
        for i in range(len(self.pid)):
            rvl += numTaskToLetter(i)
            rvl += " ==> "
            rvl += str(self.pid[i])
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
    # Renvoie tasks_bound + tableau vide (pas d'infos sur les threads)
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
            msg += str(p.returncode)
            raise PlacementException(msg)
        else:
            # On récupère l'affinité
            out = p.communicate()[0].split('\n')[0]
            return out.rpartition(" ")[2]

# Fonction-objet pour construire la structure de données tasksBinding à partir de ps
# Appelle ps pour chaque process de self.pid
# Renvoie tasks_bound et threads_bound
class BuildTasksBoundFromPs(BuildTasksBound):
    def __call__(self,tasksBinding):
        tasks_bound=[]
        for pid in tasksBinding.processus.keys():
            cores=[]
            threads=tasksBinding.processus[pid]['threads']
            for tid in threads.keys():
                cores.append(threads[tid]['psr'])
            tasks_bound.append(cores)

        return tasks_bound

#    # Passe en threads mode, c-à-d que __call__ renvoie DEUX tableaux: 
#    # le tasks_bound d'une part, le threads_bound d'autre part
#    def setThreadsMode(self):
#        self.thrds_mode = True

#    # Appelle ps pour le process passé en paramètre
#    # Renvoie deux tableaux: l'un contenant la liste des cpus associés aux threads de ce process, l'autre est une 
#    # structure de données du type dictionnairesemboités:   {pid : {tid : psr,...}}
#   def __runPs(self,pid):
#        cmd = "ps -m --no-header -o psr,tid,s -p "
#        cmd += pid
#	p = subprocess.Popen(cmd,shell=True,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
#	p.wait()
#        # Si returncode non nul, on a probablement demandé une tâche qui ne tourne pas
#	if p.returncode !=0:
#            msg = "OUPS "
#            msg += "La commande "
#            msg += cmd
#           msg += " a renvoyé l'erreur "
#            msg += str(p.returncode)
#            raise PlacementException(msg)
#        else:
#            # On récupère l'affinité
#            psout = p.communicate()[0].split('\n')
#            out_psr = []
#            out_tid = {}
#            for l in psout:
#                tmp = l.split(' ');
#                removeBlanks(tmp)
#                if len(tmp)>0 and tmp[2] == 'R':
#                    out_psr.append(int(tmp[0]))
#                    out_tid[tmp[1]] = int(tmp[0])
#            return [out_psr,{pid:out_tid}]
#

