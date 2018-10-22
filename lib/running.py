#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu-cores
#
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
#  Copyright (C) 2015-2018 Emmanuel Courcelle
#  PLACEMENT is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU General Public License for more details.
#
#  You should have received a copy of the GNU General Public License
#  along with PLACEMENT.  If not, see <http://www.gnu.org/licenses/>.
#
#  Authors:
#        Emmanuel Courcelle - C.N.R.S. - UMS 3667 - CALMIP
#        Nicolas Renon - Université Paul Sabatier - University of Toulouse)
#

import os
import re
import time
import xml.etree.ElementTree as et
from exception import *
from tasksbinding import *
from utilities import *
from architecture import *

#
# class RunningMode, Extends TasksBinding.
#                    Implements the algorithms used in Running mode: we observe a running job and we deduce 
#                    the number of tasks and the number of threads per task
# 

class RunningMode(TasksBinding):
    """ Observe the running tasks, and guess architecture and threads_bound 
        ==> Hardware is guessed from the node name, as usual
            Architecture is guessed from the running job """

    def __init__(self,path,hardware,buildTasksBound,withMemory):
        """ Constructor

        Arguments:
        path           : The running binary considered
        hardware       : The hardware we run on 
        buildTasksbound: How to build the tasks_bound data structure ? An object-function implementating the algorithm
        withMemory     : If True, try to know memory occupation / socket using a numastat command
        """

        TasksBinding.__init__(self,None,0,0)
        self.path = path
        self.hardware = hardware
        self.withMemory = withMemory
        self.pid=[]
        self.processus=[]
        self.tasks_bound   = None
        self.threads_bound = None
        self.gpus_info     = None
        self.archi = None
        self.cpus_per_task = 0
        self.tasks = 0
        self.overlap    = []
        self.over_cores = None
        self.__buildTasksBound = buildTasksBound
        self.__processus_reserves = ['srun', 'mpirun', 'ps', 'sshd' ]
        self.__users_reserves     = ['root' ]
        self.__initTasksThreadsBound()

    def __identGpus(self):
        """ Call nvidia-smi to get gpus status
            Store status in a DATA STRUCTURE:
            gpus_bound = A list of lists.
                         1st level of list = The socket numbers of the node
                         2nd level of lists= The gpus (objects) attached to each socket
            gpu        = A dictionary describing the gpu utilization (built from nvidia-smi -q -x output)"""

        gpus = self.archi.gpus
        if gpus == '':
            return
            
        # --check='+' ==> Just using the file called gpu.xml in the current directory, used ONLY for debugging 
        if self.path == '+':
            try:
                tree = et.parse('gpu.xml')
            except:
                return
        else:
            xml_header = '<?xml version="1.0" ?>\n<!DOCTYPE nvidia_smi_log'
            cmd = 'nvidia-smi -q -x'
            xml = runCmd(cmd)

            # May be there are some lines before the xml (if the user has some stuff in its .bashrc)
            # So we detect and keep only from the first xml line
            if not xml.startswith(xml_header):
                start_xml = xml.find(xml_header)
                if start_xml == -1:
                    raise PlacementException("ERROR - bad xml header returned by nvidia-smi")
                else:
                    xml = xml[start_xml:]

            tree = et.fromstring(xml)

        # '0-1,2-3' ==> ['0-1','2-3'] ==> [[0,1],[2,3]]
        gpus_bound_tmp = []
        for s in gpus.split(','):
            gpus_bound_tmp.append(compactString2List(s))

        gpus_bound = []
        for s in gpus_bound_tmp:
            sg = []
            for g in s:
                xpath_request = ".//gpu/[minor_number='"+str(g)+"']";
                obj_g = tree.findall(xpath_request)[0]  # TODO - Verifier qu'il n'y en a qu'un seul !
                gpu   = {}
                
                # Memory used
                mem_used = int(obj_g.find(".//fb_memory_usage/used").text.partition(' ')[0])
                mem_total= int(obj_g.find(".//fb_memory_usage/total").text.partition(' ')[0])
                gpu['M'] = int((100.0*mem_used)/mem_total);
                
                # gpu utilization
                gpu['U'] = int(obj_g.find(".//utilization/gpu_util").text.strip('%'))
                
                # power used
                pwr_used = float(obj_g.find(".//power_readings/power_draw").text.partition(' ')[0])
                pwr_limit= float(obj_g.find(".//power_readings/power_limit").text.partition(' ')[0])
                gpu['P'] = int(100 * pwr_used / pwr_limit)
                
                # gpu number
                gpu['id'] = g
                
                # processes
                processes = []
                max_mem = 0
                for obj_proc in obj_g.findall(".//processes/process_info"):
                    pid = int(obj_proc.find(".//pid").text)
                    mem = convertMemory(obj_proc.find(".//used_memory").text)
                    if mem>max_mem:
                        max_mem=mem
                    processes.append([pid,mem])
                    
                # normalize the memory used (0..100)
                if max_mem>0:
                    for ps in processes:
                        ps[1] = int(100.0*ps[1]/max_mem)

                gpu['PS'] = processes
                
                sg.append(gpu)
            gpus_bound.append(sg)

        self.gpus_info = gpus_bound                
        # print ("gpus_info =  " + str(self.gpus_info))
                
    def __identNumaMem(self):
        """ Call numastat for each pid of threads_bound, and keep the returned info inside threads_bound"""
                
        for pid in self.threads_bound:
            # --check='+' ==> Just using the file called PROCESSES.txt in the current directory, used ONLY for debugging 
            if self.path == '+':
                fh_numastat = open(str(pid)+'.NUMASTAT.txt','r')
                tmp = fh_numastat.readlines()
                tmp = [x.replace('\n','') for x in tmp]
            else:
                cmd = 'numastat ' + str(pid)
                tmp = runCmd(cmd).split('\n')
                tmp.pop()
            #print '\n'.join(tmp)

            # Keep only last line (should Total=)
            ttl = tmp[-1].split()

            # If the first word does not start with Total, we have a problem ! (probably a permission problem)
            if ttl[0].lower().startswith('total'):
                # remove first and last columns
                ttl.pop()
                ttl.pop(0)
                ttl = list(map(float,ttl))
    
                # We must have same number of numbers / sockets !
                if self.hardware.SOCKETS_PER_NODE != len(ttl):
                    raise PlacementException("INTERNAL ERROR - numastat returns " + str(len(ttl)) + " columns, but we have " + SOCKETS_PER_NODE + " sockets !")
                self.threads_bound[pid]['numamem']=ttl
                
            # Disable other checks - If we do not have permission for first process, it will be the same for the others
            else:
                self.withMemory = False
                break

    def __identProcesses(self):
        """Identify the interesting processes together with their threads, from a set of commands ps

        We keep only processes selected by the switch --check, ie processes launched by a command, or belonging
        to some user... pr all processes
        Among them, some "reserved" commands ('ps', 'top' etc) are discarded
        And finally we keep only processes having at least ONE running thread
        
        Two data structures are created by this function:
   
           self.processus is a dictionary of dictionaries:
               k = pid
               v = {'pid':pid, 'user':'user', 'cmd':'command line','threads':{'tid':{'tid':tid, 'psr':psr}}
   
           self.pid is the sorted list of pids

        """

        ps_res=''

        # --check='+' ==> Just using the file called PROCESSES.txt in the current directory, used ONLY for debugging 
        if self.path == '+':
            fh_processes = open('PROCESSES.txt','r')
            ps_res = fh_processes.readlines()
            fh_processes.close()
            for i,l in enumerate(ps_res):
                ps_res[i] = l.replace('\n','')
                
        # Build a complicated command ps
        else:
            cmd = 'ps --no-headers -m -o ruser:15 -o %p -o tid -o psr -o %c -o state -o %cpu -o %mem '
            
            # --check=ALL ==> No selection among the processes
            if self.path == 'ALL':
                exe = cmd + 'ax'
                tmp    = runCmd(exe)
                ps_res = tmp.split('\n')
                for i,l in enumerate(ps_res):
                    ps_res[i] = l.replace('\n','')

            # --check='some_name' Let's suppose it is a user name
            else:
                exe = cmd + "-U "
                exe += self.path

                try:
                    tmp    = runCmd(exe)
                    ps_res = tmp.split('\n')
                    for i,l in enumerate(ps_res):
                        ps_res[i] = l.replace('\n','')

                except PlacementException as e:
                    if (e.err != 1):
                        raise e
                    else:
                        ps_res = ""

                # No result: let's suppose it is a command name
                if ps_res == "":
                    exe = cmd + "-C "
                    exe += self.path

                    try:
                        tmp    = runCmd(exe)
                        ps_res = tmp.split('\n')
                        for i,l in enumerate(ps_res):
                            ps_res[i] = l.replace('\n','')

                    except PlacementException as e:
                        msg = "ERROR "
                        if (e.err == 1):
                            msg += "No task found: Are you sure you are working on the correct host ?"
                        else:
                            msg += cmd + " returned an error: " + str(e.returncode)
                        raise PlacementException(msg)
        
        # Creating data structures processus and pid from the output of the ps command
        # This output is a mixture of lines representing a processus OR a thread
        # BUT For each process, the first line represents the process itself AND the 1st thread, 
        # following lines represent the other threads
        processus         = {}
        processus_courant = {}
        process_nb = 0
        for l in ps_res:
               
            # Detecting processus
            mp=re.match('([a-z0-9]+) +(\d+) +- +- +([^ ]+) +- +[0-9.]+ +([0-9.]+)$',l)
            if mp != None:

                # If there is at least 1 active thread in the current process, it is tagged and saved
                if 'R' in processus_courant:
                    processus_courant['tag'] = numTaskToLetter(process_nb)
                    process_nb += 1
                    processus[processus_courant['pid']] = processus_courant
                    
                # Reinit the current processus dictionary, as we start a new process
                processus_courant={}
                user= mp.group(1)
                pid = int(mp.group(2))
                cmd = mp.group(3)
                mem = float(mp.group(4))
                if cmd in self.__processus_reserves:
                    continue
                if user in self.__users_reserves:
                    continue

                processus_courant['user']=user
                processus_courant['pid']=pid
                processus_courant['cmd']=cmd
                processus_courant['mem']=mem
                continue

            # Detecting threads
            mt = re.match('[a-z0-9]+ +- +(\d+) +(\d+) +- +([A-Z]) +([0-9.]+)',l)
            if mt != None:
                # If no current process, skip this line. However this should not happen
                if len(processus_courant)==0:
                    continue
                
                # If at least 1 thread is 'R', remember !
                state = mt.group(3)
                if state == 'R':
                    processus_courant['R']=True

                # Keeping track of this thread
                tid   = int(mt.group(1))
                psr   = int(mt.group(2))
                cpu   = float(mt.group(4))
                thread_courant        = {}
                thread_courant['tid'] = tid                                     # thread id
                thread_courant['psr'] = self.hardware.getAddr2Core(psr)         # core number (internal representation)
                thread_courant['ppsr']= self.hardware.getCore2PhysCore(psr)     # physical code number (in case of hyperthreading) 
                thread_courant['cpu'] = cpu                                     # % cpu use
                thread_courant['state'] = state                                 # State of the thrad (running etc)
                thread_courant['mem'] = processus_courant['mem']                # % mem use

                if ('threads' in processus_courant)== False:
                    processus_courant['threads'] = {}

                processus_courant['threads'][tid] = thread_courant

        # If there is at least 1 active thread in the current process when xiting from the loop, it is tagged and saved
        if 'R' in processus_courant:
            processus_courant['tag'] = numTaskToLetter(process_nb)
            processus[processus_courant['pid']] = processus_courant
                
        self.processus = processus
        self.pid = sorted(processus.keys())


    def __buildArchi(self,tasks_bound):
        """ Guess architecture from observed tasks_bound"""

        # The parameter cpus_per_task is not used here
        self.cpus_per_task = -1
        self.tasks         = len(tasks_bound)
        self.sockets_per_node = self.hardware.SOCKETS_PER_NODE
        
        # The machine, ie the sockets and cores reserved for me, are exclusively reserved for me !
        self.archi = Exclusive(self.hardware, self.cpus_per_task, self.tasks, self.hardware.HYPERTHREADING)

    def distribTasks(self,check=False):
        """ Init and return tasks_bound  """
        if self.tasks_bound==None:
            self.__initTasksThreadsBound()
        return self.tasks_bound 

    def __initTasksThreadsBound(self):
        """ Call __identProcesses then __buildTasksBound and other things """

        # Measure time
        begin = time.time()
        
        # Retrieve the list of processes
        self.__identProcesses()

        # Determine their affinity
        self.tasks_bound   = self.__buildTasksBound(self)
        self.threads_bound = self.processus

        # No task found
        if len(self.tasks_bound)==0:
            msg = "ERROR No task found !"
            raise PlacementException(msg)

        # Detect overlaps, if any
        [self.overlap,self.over_cores] = _detectOverlap(self.tasks_bound)

        # Guess the architecture
        self.__buildArchi(self.tasks_bound)

        # Call numastat to get information about the memory
        if self.withMemory:
            self.__identNumaMem()
            
        # Call the gpu information
        self.__identGpus()

        # Measure duration
        self.duration = time.time() - begin

    def PrintingForVerbose(self):
        """Return some verbose information"""

        rvl  = "TASK  ==> PID (USER,CMD) ==> AFFINITY\n"
        rvl += "=====================================\n"
        threads_bound = self.threads_bound
        for (pid,proc) in sorted(iter(threads_bound.items()),key=lambda k_v:(k_v[1]['tag'],k_v[0])):
            rvl += proc['tag'] + '     '
            rvl += ' ==> '
            rvl += str(pid)
            rvl += ' ('
            rvl += proc['user']
            rvl += ','
            rvl += proc['cmd']
            rvl += ') ==> '

            # @todo - pas jolijoli ce copier-coller depuis BuildTasksBoundFromPs, même pas sûr que ça marche avec taskset !
            cores=[]
            threads=proc['threads']
            for tid in list(threads.keys()):
                if threads[tid]['state']=='R':
                    cores.append(threads[tid]['psr'])

            rvl += list2CompactString(cores)
            rvl += "\n"

        return rvl


class BuildTasksBound:
    """ This is a functor, use to build the data structure tasksBinding from taskset or ps
        ABSTRACT CLASS """

    def __call__(self):
        raise("INTERNAL ERROR - VIRTUAL PURE FUNCTION !")

# This functor builds the tasks_bound data structure from ps
# Construit tasks_bound à partir de la structure de données tasksBinding.processus
# tasks_bound est construit dans l'ordre donné par les labels des processes (cf. __identProcesses)
# Ne considère QUE les threads en état 'R' !
# Renvoie tasks_bound
class BuildTasksBoundFromPs(BuildTasksBound):
    """ This is just a rewriting of the data structure processus !"""

    def __call__(self,tasksBinding):
        tasks_bound=[]
        #for pid in sorted(tasksBinding.processus.keys()):
        for (pid,proc) in sorted(iter(tasksBinding.processus.items()),key=lambda k_v1:(k_v1[1]['tag'],k_v1[0])):
            cores=[]
            threads=proc['threads']
            for tid in list(threads.keys()):
                if threads[tid]['state']=='R':
                    cores.append(threads[tid]['psr'])
            tasks_bound.append(cores)

        return tasks_bound


def _detectOverlap(tasks_bound):
    """ Return couples of overlapping as a list of pairs, together with the list of impacted cores"""

    over=[]
    over_cores=[]
    for i in range(len(tasks_bound)):
        for j in range(i+1,len(tasks_bound)):
            overlap = list(set(tasks_bound[i])&set(tasks_bound[j]))
            if len(overlap)!=0:
                over.append((i,j))
                over_cores.extend(overlap)

    # Use 1-char tags instead of numbers, however the number should be < 296 (and we do not check, shame !)
    over_l = []
    for c in over:
        over_l.append( (numTaskToLetter(c[0]),numTaskToLetter(c[1])) )

    # Removing duplications
    over_cores = set(over_cores)
    over_cores = list(over_cores)
    over_cores.sort()
    
    return (over_l,over_cores)
