#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu cores
#
# Copyright (C) 2015-2018 Emmanuel Courcelle
# PLACEMENT is free software: you can redistribute it and/or modify
# it under the terms of the GNU General Public License as published by
# the Free Software Foundation, either version 3 of the License, or
# (at your option) any later version.
#
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

"""
This software can help you to bind your processes to one or more cpu cores

CALMIP - 2015-2018

Start with  placement --help 

Without any switch, placement computes and returns the switch cpu_bind which should be inserted inside the srun command line:
For example with 4 processes, 8 threads per processus, hyperthreading on, on the Eos supercomputer:

# placement 4 8
--cpu_bind=mask_cpu:0xf0000f,0xf0000f0,0x3c0003c00,0x3c0003c000

Using the switch --human: returns the same information, but humanly more lisible:

# placement 4 8 --human
[ 0 1 2 3 20 21 22 23 ]
[ 4 5 6 7 24 25 26 27 ]
[ 10 11 12 13 30 31 32 33 ]
[ 14 15 16 17 34 35 36 37 ]

Using the switch --ascii-art: returns the same information, as an ascii-art representing the cores in the sockets.
It is easy to see that hyperthreading is activated (see Physical vs Logical lines)

# placement 4 8 --ascii
  S0-------- S1-------- 
P AAAABBBB.. CCCCDDDD.. 
L AAAABBBB.. CCCCDDDD.. 

CALLING PLACEMENT FROM A SLURM ENVIRONNEMENT, WITH srun:
========================================================

When calling placement from a script_slurm ou do not have to specify any parameter, 
because placement uses the environment variables TASKS_PER_NODE and CPUS_PER_TASK to guess
the number of tasks and the number of threads of your job.

However, it may be clever to call placement with the --ascii-art switch to exactly know how
the processes will be bound, and also to validate the configuration on your hardware.
Thus a minimal script could be written as follows:


placement --ascii-art
if [[ $? != 0 ]]
then
 echo "ERROR - PLEASE CHANGE THE NUMBER OF TASKS OR THREADS !" 2>&1
 exit 1
fi
...
srun $(placement) ./my_program
       
Hardware configuration:

placement guesses the hardware it runs on using some environment variables, 
together with the file placement.conf
Please have a look to this file and adapt it to YOUR configuration !

###############################################################
emmanuel.courcelle@inp-toulouse.fr
https://www.calmip.univ-toulouse.fr
2016-2018
################################################################
"""

import os
import sys
#import argparse
from itertools import chain,product
import hardware
from architecture import *
from exception import *
from tasksbinding import *
from scatter import *
from compact import *
from running import *
from utilities import *
from printing import *
from front import *
from params import *

def main():

    # options = The options parsed from the command line
    # fn      = The object FrontNode, encapsulating the job scheduler, if any
    # args    = The positional arguments
    (options, fn) = params()
    args=(options.tasks,options.nbthreads)

    
    if options.noansi:
        AnsiCodes.noAnsi()
        
    if options.documentation!=0:
        documentation(options.documentation)
        exit(0)

    if options.show_env==True:
        show_env()
        exit(0)

    if options.makempiaware==True:
        options.output_mode="numactl"
        make_mpi_aware()
        exit(0)

    # If necessary run another exe may be on another host
    try:
        if fn.runPlacement() != 0:
            exit(0)
    except PlacementException as e:
        print("PLACEMENT " + str(e), file = sys.stderr)
        exit(1)
            
    # Guess the hardware, from the placement.conf file and from environment variables
    hard = '';
    try:
        hard = hardware.Hardware.factory()
            
    except PlacementException as e:
        print("PLACEMENT_ERROR_FOUND")
        print("PLACEMENT " + str(e), file = sys.stderr)
        exit(1)

# ----------------------------------------------------------------------
#                                Main program
# ----------------------------------------------------------------------

    try:
        if options.show_hard==True:
            show_hard(hard)
            exit(0)

        # First stage: Compute data and store them inside tasks_binding
        
        # If --check specified, data are computed from the running job(s)
        if options.check != None:
            #[tasks,tasks_bound,threads_bound,over_cores,archi] = compute_data_from_running(options,args,hard)
            tasks_binding = compute_data_from_running(options,args,hard)

        # Else, data are computed from the command line parameters
        else:
            #[tasks,tasks_bound,threads_bound,over_cores,archi] = compute_data_from_parameters(options,args,hard)
            tasks_binding = compute_data_from_parameters(options,args,hard)

        # Second stage - Print data, may be using several formats
        # outputs is an array of objects extending PrintingFor
        outputs = buildOutputs(options,tasks_binding)
        if len(outputs)==0:
            print ("OUPS, No output specified !", file = sys.stderr)

        if 'jobid' in options and options.jobid != None:
            print("jobid " + str(options.jobid))
        for o in outputs:
            print (o)
            
    except PlacementException as e:
        if options.summary == False:
            ManageException(e)
        else:
            print ("0.0:0")
        exit(1)


def buildOutputs(options,tasks_binding):
    """  Return an array with different objects deriving from the PrintingFor abstract class, following the commandline

    Arguments:
    options The command line
    tasks_binding The tasks_binding data structure, will be passed to the created printing objects
    """

    outputs = []

    # Print verbose unless using kmp mode
    if options.verbose and options.output_mode != 'kmp':
        outputs.append(PrintingForVerbose(tasks_binding))

    # Print for srun OR for numactl and return
    if options.check==None and options.asciiart==False and options.human==False:
        if options.output_mode=="srun":
            outputs.append(PrintingForSrun(tasks_binding))
            return outputs
        if options.output_mode=="numactl":
            outputs.append(PrintingForNumactl(tasks_binding))
            return outputs

    # Print for the KMP_AFFINITY environment variable (intel compilers) or GOMP_AFFINITY (gnu compilers) and return
    if options.check==None and options.asciiart==False and options.human==False:
        if options.output_mode=="kmp":
            outputs.append(PrintingForIntelAff(tasks_binding,options.verbose))
            return outputs

        if options.output_mode=="gomp":
            outputs.append(PrintingForGnuAff(tasks_binding,options.verbose))
            return outputs

    # If check, the output default is --threads
    if options.check!=None and (options.asciiart==False and options.human==False and options.summary==False and options.csv==False):
        options.threads = True
        
    # Print for human beings
    if options.human==True:
        outputs.append(PrintingForHuman(tasks_binding))
        
    # Print for artists (!)
    if options.asciiart==True:
        outputs.append(PrintingForAsciiArt(tasks_binding))

    # Only with --check: print a bind matrix
    if options.check!=None and options.threads==True:
        o = PrintingForMatrixThreads(tasks_binding)
        if options.show_idle == True:
            o.ShowIdleThreads()
        if options.memory == True:
            o.PrintNumamem()
        if options.sorted_threads_cores == True:
            o.SortedThreadsCores()
        if options.sorted_processes_cores == True:
            o.SortedProcessesCores()
        outputs.append(o)

    # Only with --check: print a summary
    if options.check!=None and options.summary==True:
        o = PrintingForSummary(tasks_binding)
        if options.verbose == True:
            o.setVerbose()
        if options.show_depop == True:
            o.ShowDepopulated()
        if options.cpu_thr != None:
            o.SetCpuThreshold(options.cpu_thr)
        if options.mem_thr != None:
            o.SetMemThreshold(options.mem_thr)
        outputs.append(o)

    # Only with --csv: print a summary in csv format
    if options.check!=None and options.csv==True:
        o = PrintingForCsv(tasks_binding)
        outputs.append(o)
        
    return outputs
        

def documentation(section):
    """ Display documentation, my be from a given section """

    if section==None:
        flag = 2
        sct = ''
    else:
        flag = 0
        sct  = str(section) + '.'
    
    #print "coucou " + str(section)
    f_doc  = os.environ['PLACEMENT_ROOT'] + '/etc/documentation.txt'
    fh_doc = open(f_doc, 'r')
    
    for line in fh_doc:
        if line.startswith(sct):
            flag += 1
        if flag >= 2:
            if line.startswith('<code>'):
                print (AnsiCodes.bold())
                continue
            if line.startswith('</code>'):
                print (AnsiCodes.normal())
                continue

            print(line, end='')

    if flag==False:
        print("OUPS - Nothing in documentation, section " + sct + ' !')
            

###########################################################
# Make the environment variables useful in mpi_aware mode
# Use with: eval $(~/bin/placement --make_mpi_aware)
#
# Analyze the output of numactl --show
#
###########################################################
def make_mpi_aware():
    """ analyze the output of numactl --show and return some bash strings to create the environment variables useful in mpi_aware mode

    Use with: eval $(~/bin/placement --make_mpi_aware)
    """

    # Analyze the output of umactl --show
    numa_res = runCmd(["numactl", "--show"]).split("\n")

    # Look for the line physcpubind: 0 1 ...
    cores=''
    sockets=''
    for l in numa_res:
        (h,s,t) = l.partition(':')
        if h=='physcpubind':
            cores=t
        if h=='nodebind':
            sockets=t
    
    cores=cores.strip().replace(' ',',')
    sockets=sockets.strip().replace(' ',',')

    # Copy the environment SLURM_TASKS, SLURM_CPUS_PER_TASK with a prefix, they will be available if we live in a sbatch script
    msg  = 'export PLACEMENT_PHYSCPU="'+cores+'"; '
    msg += 'export PLACEMENT_NODE="'+sockets+'"; ';
    if 'SLURM_TASKS_PER_NODE' in os.environ:
        msg += 'export PLACEMENT_SLURM_TASKS_PER_NODE="'+os.environ['SLURM_TASKS_PER_NODE']+'"; '
    if 'SLURM_CPUS_PER_TASK' in os.environ:
        msg += 'export PLACEMENT_SLURM_CPUS_PER_TASK="'+os.environ['SLURM_CPUS_PER_TASK']+'"; '

    print(msg)
    
    return

def show_hard(hard):
    """Print some information about the guessed hardware

    Argument:
    hardware
    """

    if hard.NAME == 'Slurm':
        # This was removed in placement 1.8
        arch = 'Guessed from slurm.conf'
    else:
        arch = hard.NAME
    msg = "Current architecture = " + arch + " "
    if hard.NAME != 'unknown':
        msg += '(' + str(hard.SOCKETS_PER_NODE) + ' sockets/node, '
        msg += str(hard.CORES_PER_SOCKET) + ' cores/socket, '
        if hard.HYPERTHREADING:
            msg += str(hard.THREADS_PER_CORE) + ' threads/core ' + '(hyperthreading on), '
        msg += str(hard.MEM_PER_SOCKET) + ' Mb/socket, '
        if hard.IS_SHARED:
            msg += 'SHARED NODE'
        else:
            msg += 'EXCLUSIVE'
        msg += ')'
        print(msg)

def show_env():
    """ Prints the useful environment variables"""

    cat = hardware.Hardware.catalog()
    msg = "Current environment...\n"
    msg += "WORKING ON HOST " + getHostname() + ', should match one of ' + str(cat[0]) + '\n'
    
    for v in ['PLACEMENT_PYTHON','PYTHONPATH','PLACEMENT_ROOT','PLACEMENT_ARCHI','SLURM_TASKS_PER_NODE','SLURM_CPUS_PER_TASK',
              'PLACEMENT_NODE','PLACEMENT_PHYSCPU','PLACEMENT_SLURM_TASKS_PER_NODE','PLACEMENT_SLURM_CPUS_PER_TASK','PLACEMENT_DEBUG','PLACEMENT_DEBUG_1']:
        try:
            msg += v
            msg += ' = '
            msg += AnsiCodes.bold() + os.environ[v] + AnsiCodes.normal()
            if v=='PLACEMENT_DEBUG_1':
                msg += AnsiCodes.red_foreground() + AnsiCodes.bold() + ' - SHOULD NOT BE SET IN PRODUCTION !' + AnsiCodes.normal()
        except KeyError:
            msg += '<not specified>'
        if v=='PLACEMENT_ARCHI':
            msg += ' of ' + str(cat[1])
        msg += '\n'
    print(msg)

def compute_data_from_running(options,args,hard):
    """ Compute and return task_distrib observing a running program
    
    Arguments:
    options The command line, used to choose the correct algorithm (ps or taskset)
    args: Not used
    hard: The hardware
    """


    #if options.taskset == True:
        #buildTasksBound = BuildTasksBoundFromTaskSet()
    #else:
        #buildTasksBound = BuildTasksBoundFromPs()

    buildTasksBound = BuildTasksBoundFromPs()
    path = options.check
    task_distrib = RunningMode(path,hard,buildTasksBound,options.memory)

    return task_distrib


##########################################################
# @brief Calcule les structures de données à partir des paramètres de la ligne de commande
#
# @param options Les switches de la ligne de commande
# @param args (non utilisé)
# @param Le hardware
#
# @return Un tableau de tableaux: les taches, les coeurs utilisés, les coeurs en conflit, l'architecture
#
##########################################################
def compute_data_from_parameters(options,args,hard):
    """ Compute and return task_distrib from the command line
    
    Arguments:
    options The command line (options part)
    args: The command line (arguments part)
    hard: The hardware
    """

    #check = not options.relax
    check = True
    over_cores = None
    [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
    hyper = options.hyper or options.hyper_phys
    if hard.IS_SHARED:
        archi = Shared(hard, cpus_per_task, tasks, hyper)
    else:
        archi = Exclusive(hard, cpus_per_task, tasks, hyper)
            
    task_distrib = ""
    if options.mode == "scatter":
        task_distrib = ScatterMode(archi,check)
    elif options.mode == "scatter_block":
        task_distrib = ScatterBlockMode(archi,check)
    else:
        if options.hyper_phys == True:
            task_distrib = CompactPhysicalMode(archi,check)
        else:
            task_distrib = CompactMode(archi,check)
            
    # Sort the threads
    task_distrib.threadsSort()

    # If mpi aware, we keep only the task corresponding to the mpi rank
    if options.mpiaware == True:
        task_distrib.keepOnlyMpiRank()

    return task_distrib

if __name__ == "__main__":
    main()
