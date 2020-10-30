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

    def __init__(self,options,hardware,buildTasksBound,jobsched=None):
        """ Constructor

        Arguments:
        path           : The running binary considered
        hardware       : The hardware we run on 
        buildTasksbound: How to build the tasks_bound data structure ? An object-function implementating the algorithm
        withMemory     : If True, try to know memory occupation / socket using a numastat command
        jobsched       : If not None, an object extending JobSched (ex = slurm)
                         Used to map processes and jobs
        """

        TasksBinding.__init__(self,None,0,0)
        self.path       = options.check
        self.withMemory = options.memory

        self.hardware   = hardware
        
        self.__jobid    = options.jobid
        self.__jobsched = jobsched

        self.pid=[]
        self.processus=[]
        self.tasks_bound   = None
        self.threads_bound = None
        self.gpus_info     = None
        self.gpus_processes= set()
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
            Store status in a DATA STRUCTURE called self.gpus_info
            gpus_bound = A list of lists.
                         1st level of list = The socket numbers of the node
                         2nd level of lists= The gpus (objects) attached to each socket
            gpu        = A dictionary describing the gpu utilization (built from nvidia-smi -q -x output)"""

        gpus = self.hardware.GPUS
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
    
        # Collect the processes detected by the gpus, if any
        # They should be known by the cpu, but may be not in state 'R'
        for socket in self.gpus_info:
            #print("----> " + str(socket))
            for gpus in socket:
                a = gpus['PS']
                for p in a:
                    self.gpus_processes.add(p[0])
        
        #print('self.gpus_processes='+str(self.gpus_processes))
         

                
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
            #print ('\n'.join(tmp))
            #print(tmp)

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
               v = {'pid':pid, 'user':'user', 'cmd':'command line', 'job':'jobid', 'threads':{'tid':{'tid':tid, 'psr':psr}}
   
           self.pid is the sorted list of pids

        """

        # the result of the 'ps' command
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
            cmd = 'ps --no-headers -m -o ruser:15 -o sid -o pid -o tid -o psr -o %c -o state -o %cpu -o %mem '
            
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
                    
                    # Still no result... 
                    except PlacementException as e:
                        pass
        
        # Creating data structures processus and pid from the output of the ps command
        # This output is a mixture of lines representing a processus OR a thread
        # BUT For each process, the first line represents the process itself AND the 1st thread, 
        # following lines represent the other threads

        # The processus - key = pid, val = A dict (see processus_courant under)
        processus         = {}
        
        # The current process - key = processus properties, val = The property (ex: pid, sid, etc)
        processus_courant = {}
        
        # The session id - key = session id, val = A list of pid (the processes belonging to the group)
        sids             = {}
        
        for l in ps_res:
               
            # Detecting the processes
            mp=re.match('([a-z0-9]+) +(\d+) +(\d+) +- +- +([^ ]+) +- +[0-9.]+ +([0-9.]+)$',l)
            if mp != None:

                # If there is at least 1 active thread in the current process, it is tagged and saved
                #print ( "mp = " + str(mp))
                if 'pid' in processus_courant:
                    pid=processus_courant['pid']
                else:
                    pid="-1"
                    
                if 'R' in processus_courant or pid in self.gpus_processes:
                    sid = processus_courant['sid']
                    processus[pid] = processus_courant
                    if not sid in sids.keys():
                        sids[sid] = []
                    sids[sid].append(pid)
                    
                # Reinit the current processes dictionary, as we start a new process
                processus_courant={}
                user= mp.group(1)
                sid= int(mp.group(2))
                pid = int(mp.group(3))
                cmd = mp.group(4)
                mem = float(mp.group(5))
                if cmd in self.__processus_reserves:
                    continue
                if user in self.__users_reserves:
                    continue

                processus_courant['user']=user
                processus_courant['sid']=sid
                processus_courant['pid']=pid
                processus_courant['cmd']=cmd
                processus_courant['mem']=mem
                continue

            # Detecting threads
            mt = re.match('[a-z0-9]+ +- +- +(\d+) +(\d+) +- +([A-Z]) +([0-9.]+)',l)
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
                thread_courant['sid'] = processus_courant['sid']               # The sid

                if ('threads' in processus_courant)== False:
                    processus_courant['threads'] = {}

                processus_courant['threads'][tid] = thread_courant

        # If there is at least 1 active thread in the current process when exiting from the loop, it is tagged and saved
        if 'R' in processus_courant:
            pid  = processus_courant['pid']
            sid = int(processus_courant['sid'])
            processus[pid] = processus_courant
            if not sid in sids.keys():
                sids[sid] = []
            sids[sid].append(pid)
                
        # Sort the processes to tag them: The sort order is:
        #   1/ sid asc
        #   2/ pid asc
        #
        
        p_cnt = 0
        for sid in sorted(sids):
            sess = sids[sid]
            for pid in sorted(sess):
                processus[pid]['tag'] = numTaskToLetter(p_cnt)
                p_cnt += 1
        
        # Detect the job number corresponding to those processes
        # The detection is done by the jobscheduler
        # Keep track of the jobid AND give a tag to the jobig (will be used to choose the color)
        js = self.__jobsched
        if js != None:
            joblt   = 1
            jobtags = {}
            for pid in list(processus):
                jobid = js.findJobFromPid(pid)
                processus[pid]['job']= jobid
                if not jobid in jobtags:
                    jobtags[jobid]   = joblt
                    joblt            += 1
                processus[pid]['jobtag'] = jobtags[jobid]
                
                # TODO - This is not optimized, we worked hard on this process before removing it....
                if self.__jobid != None and jobid != str(self.__jobid):
                    del(processus[pid])
            
        # Add default values por job and jobtag !
        else:
            for pid in processus:
                processus[pid]['job']   = "0"
                processus[pid]['jobtag']= 1

		# Return
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
        
       # Call the gpu information
        self.__identGpus()

        # Retrieve the list of processes
        self.__identProcesses()

        # Determine their affinity
        self.tasks_bound   = self.__buildTasksBound(self)
        self.threads_bound = self.processus

        # Detect overlaps, if any
        [self.overlap,self.over_cores] = _detectOverlap(self.tasks_bound)

        # Guess the architecture
        self.__buildArchi(self.tasks_bound)

        # Call numastat to get information about the memory
        if self.withMemory:
            self.__identNumaMem()
            
        # Measure duration
        self.duration = time.time() - begin

    def PrintingForVerbose(self):
        """Return some verbose information"""

        #import pprint
        #print('tasks_bound')
        #pprint.pprint(self.tasks_bound)

        #print('threads_bound')
        #pprint.pprint(self.threads_bound)

        #print('gpus_infos')
        #pprint.pprint(self.gpus_info)
                
        format_str = '{:>7} {}{:>4}{} {:>6} {:>10} {:>20} {:>30} {}{:>6}{}\n'
        rvl = format_str.format('SESSION','','TASK','','PID','USER','CMD','AFFINITY','','jobid','')
        rvl +=format_str.format('=======','','====','','===','====','===','========','','=====','')
        
        last_sid      = 0
        threads_bound = self.threads_bound
        nrm           = AnsiCodes.normal()
        for (pid,proc) in sorted(iter(threads_bound.items()),key=lambda k_v:(k_v[1]['tag'],k_v[0])):
            if last_sid==0:
                last_sid = proc['sid']
                sid      = proc['sid']
            elif last_sid != proc['sid']:
                last_sid = proc['sid']
                sid      = proc['sid']
            else:
                sid      = " "
            
            tag   = proc['tag']
            col = AnsiCodes.map(proc['jobtag'])
            jobid = proc['job']
            
            # @todo - pas jolijoli ce copier-coller depuis BuildTasksBoundFromPs, même pas sûr que ça marche avec taskset !
            cores=[]
            threads=proc['threads']
            for tid in list(threads.keys()):
                if threads[tid]['state']=='R':
                    cores.append(threads[tid]['psr'])
            if len(cores)==0:
                affinity = "not running on cpu"
            else:
                affinity = list2CompactString(cores)
            
            rvl += format_str.format(sid,col,tag,nrm,pid,proc['user'],proc['cmd'],affinity,col,jobid,nrm)
        
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
