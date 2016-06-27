#! /usr/bin/env python
# -*- coding: utf-8 -*-

#
# This file is part of PLACEMENT software
# PLACEMENT helps users to bind their processes to one or more cpu cores
#
# Copyright (C) 2015,2016 Emmanuel Courcelle
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

CALMIP - 2015-2016

WARNING - There is STRONG DEPENDENCY between placement and the SLURM scheduler (http://slurm.schedmd.com)

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
http://www.calmip.univ-toulouse.fr
June 2016
################################################################
"""

import os
import argparse
import subprocess
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

# If we run an a remote machine via ssh, not sure the HOSTNAME environment variable is available !
from socket import gethostname

def main():

    # Si la variable PLACEMENT_DEBUG existe, on simule un environnement shared avec des réservations
    # Exemple: export PLACEMENT_DEBUG='9,10,11,12,13' pour simuler un environnement shared, 5 sockets réservées
    # NB - Ne pas oublier non plus de positionner SLURM_NODELIST ! (PAS PLACEMENT_PARTITION ça n'activera pas Shared)
    #if 'PLACEMENT_DEBUG' in os.environ:
    #    import mock
    #    placement_debug=os.environ['PLACEMENT_DEBUG']
    #    rvl=map(int,placement_debug.split(','))
    #    Shared._Shared__detectSockets = mock.Mock(return_value=rvl)

    # Analysing the command line arguments
    epilog = 'Do not forget to check your environment variables (--environ) and the currently configured hardware (--hard) !'
    ver="1.1.1"
    parser = argparse.ArgumentParser(version=ver,description="placement " + ver,epilog=epilog)

    # WARNING - The arguments of this group are NOT USED by the python program, ONLY by the bash wrapper !
    #           They are reminded here for coherency and for correctly writing help
    group = parser.add_argument_group('checking jobs running on compute nodes (THOSE SWITCHES MUST BE SPECIFIED FIRST)')
    group.add_argument("--checkme",dest='checkme',action="store_true",help="Check my running job")
    group.add_argument("--jobid",dest='jobid',action="store_true",help="Check this running job (must be mine, except for sysadmins)")
    group.add_argument("--host",dest='host',action="store_true",help="Check this host (must execute my jobs, except for sysadmins)")

    group = parser.add_argument_group('Displaying some information')
    group.add_argument("-I","--hardware",dest='show_hard',action="store_true",help="Show the currently selected hardware and leave")
    group.add_argument("-E","--examples",action="store_true",dest="example",help="Print some examples and leave")
    group.add_argument("--environment",action="store_true",dest="show_env",help="Show some useful environment variables and leave")
    
    parser.add_argument('tasks', metavar='tasks',nargs='?',default=-1 ) 
    parser.add_argument('nbthreads', metavar='cpus_per_tasks',nargs='?',default=-1 ) 
    parser.add_argument("-T","--hyper",action="store_true",default=False,dest="hyper",help='Force use of hyperthreading (False)')
    parser.add_argument("-P","--hyper_as_physical",action="store_true",default=False,dest="hyper_phys",help="Used ONLY with mode=compact - Force hyperthreading and consider logical cores as supplementary sockets (False)")
    parser.add_argument("-M","--mode",choices=["compact","scatter","scatter_cyclic","scatter_block"],default="scatter_cyclic",dest="mode",action="store",help="distribution mode: scatter, scatter_cyclic (same as scatter),scatter_block, compact (scatter_cyclic)")
    parser.add_argument("-U","--human",action="store_true",default=False,dest="human",help="Output humanly readable")
    parser.add_argument("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable")
    parser.add_argument("-R","--srun",action="store_const",dest="output_mode",const="srun",help="Output for srun (default)")
    parser.add_argument("-N","--numactl",action="store_const",dest="output_mode",const="numactl",help="Output for numactl")
    parser.add_argument("-Z","--intel_affinity",action="store_const",dest="output_mode",const="kmp",help="Output for intel openmp compiler, try also --verbose")

    parser.add_argument("--mpi_aware",action="store_true",default=False,dest="mpiaware",help="For running hybrid codes, forces --numactl. See examples")
    parser.add_argument("--make_mpi_aware",action="store_true",default=False,dest="makempiaware",help="To be used with --mpi_aware in the sbatch script BEFORE mpirun - See examples")
    parser.add_argument("-C","--check",dest="check",action="store",help="Check the cpus binding of a running process (CHECK=command name or user name or ALL)")
    parser.add_argument("-H","--threads",action="store_true",default=False,help="With --check: show threads affinity to the cpus")
    parser.add_argument("-r","--only_running",action="store_true",default=False,help="With --threads: show ONLY running threads")
    parser.add_argument("-t","--sorted_threads_cores",action="store_true",default=False,help="With --threads: sort the threads in core numbers rather than pid")
    parser.add_argument("-p","--sorted_processes_cores",action="store_true",default=False,help="With --threads: sort the processes in core numbers rather than pid")
    parser.add_argument("-Y","--memory",action="store_true",default=False,help="With --threads: show memory occupation relative to the sockets")
    parser.add_argument("-K","--taskset",action="store_true",default=False,help="Do not use this option, not implemented and not useful")
    parser.add_argument("-V","--verbose",action="store_true",default=False,dest="verbose",help="more verbose output can be used with --check and --intel_kmp")
    parser.set_defaults(output_mode="srun")
    options=parser.parse_args()
    args=(options.tasks,options.nbthreads)

    if options.example==True:
        examples()
        exit(0)

    if options.show_env==True:
        show_env()
        exit(0)

    if options.makempiaware==True:
        make_mpi_aware()
        exit(0)

    # En mode mpi_aware, vérifie que toutes les variables d'environnement sont bien là
    # If called with --mpi_aware, we check all the needed environment variables are set
    if options.mpiaware==True:
        try:
            check_mpi_aware()
        except PlacementException, e:
            print e
            exit(1)

    # Guess the hardware, from the placement.conf file and from environment variables
    hard = '';
    try:
        hard = hardware.Hardware.factory()
            
    except PlacementException, e:
        print e
        exit(1)

    # Main program
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

        # If overlap, print a warning !
        try:
            overlap = tasks_binding.overlap
            if len(overlap)>0:
                print "WARNING - FOLLOWING TASKS ARE OVERLAPPING !"
                print "==========================================="
                print overlap
                print
        except AttributeError:
            pass

        # Second stage - Print data, may be using several formats
        outputs = buildOutputs(options,tasks_binding)
        if len(outputs)==0:
            print "OUPS, No output specified !"
        else:
            if options.check != None:
                print gethostname()
        for o in outputs:
            print o
            
    except PlacementException, e:
        print e
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

    # Print for the KMP_AFFINITY environment variable (intel compilers) are return
    if options.check==None and options.asciiart==False and options.human==False:
        if options.output_mode=="kmp":
            outputs.append(PrintingForIntelAff(tasks_binding,options.verbose))
            return outputs

    # Print for human beings
    if options.human==True:
        outputs.append(PrintingForHuman(tasks_binding))
    
    # Print for artists (!)
    if options.asciiart==True:
        outputs.append(PrintingForAsciiArt(tasks_binding))

    # Only with --check: print a bind matrix
    if options.check!=None and options.threads==True:
        o = PrintingForMatrixThreads(tasks_binding)
        if options.only_running == True:
            o.PrintOnlyRunningThreads()
        if options.memory == True:
            o.PrintNumamem()
        if options.sorted_threads_cores == True:
            o.SortedThreadsCores()
        if options.sorted_processes_cores == True:
            o.SortedProcessesCores()
        outputs.append(o)

    return outputs
        

def examples():
    """ Display a few examples """

    ex = """===================================
USING placement IN AN SBATCH SCRIPT
===================================

1/ Insert the following lines in your script:

placement --ascii
if [[ $? != 0 ]]
then
 echo "ERREUR DANS LE NOMBRE DE PROCESSES OU DE TACHES" 2>&1
 exit $?
fi

2/ Modify your srun call as follows:

srun $(placement) ./my_application

===================================================================
USING placement WITH hybrid codes (mpi/openMP) IN AN SBATCH SCRIPT:
===================================================================

Put the following inside your slurm script:

# Creating environment variables usefull for placement
eval $(~/bin/placement --make_mpi_aware)

# Calling my application with mpirun
mpirun -binding "pin=no" -n ${SLURM_TASKS_PER_NODE} /bin/bash -c 'numactl $(~/bin/placement Tasks Threads --mpi_aware) my_application'
$(placement --mpi_aware) mpirun -np $SLURM_TASKS_PER_NODE ./my_application

=======================================
USING placement TO CHECK A RUNNING JOB:
=======================================
From the frontale execute:

placement --checkme

===========================================================
For a sysadmin: USING placement TO CHECK USER RUNNING JOBS:
===========================================================
From the frontale execute:

placement --host eoscomp666 --check=ALL --threads
"""
    print ex

###########################################################
# Make the environment varialbes useful in mpi_aware mode
# Use with: eval $(~/bin/placement --make_mpi_aware)
#
# Analyze the output of umactl --show
#
###########################################################
def make_mpi_aware():
    """ analyze the output of numactl --show and return some bash strings to create the environment variables useful in mpi_aware mode

    Use with: eval $(~/bin/placement --make_mpi_aware)
    """

    # Analyze the output of umactl --show
    numa_res = subprocess.check_output(["numactl", "--show"]).split("\n")

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

    # Copy the environment SLURM_TASKS, SLURM_CPUS_PER_TASK with a prefix, they will be available in 
    msg  = 'export PLACEMENT_PHYSCPU="'+cores+'"; '
    msg += 'export PLACEMENT_NODE="'+sockets+'"; ';
    msg += 'export PLACEMENT_SLURM_TASKS_PER_NODE="'+os.environ['SLURM_TASKS_PER_NODE']+'"; '
    msg += 'export PLACEMENT_SLURM_CPUS_PER_TASK="'+os.environ['SLURM_CPUS_PER_TASK']+'"; '

    print msg
    
    return

def check_mpi_aware():
    """In mpi_aware mode, check the 4 environment variables are set and raise an exception if they are not """
    if os.environ.has_key('PLACEMENT_PHYSCPU') and os.environ.has_key('PLACEMENT_NODE') and os.environ.has_key('PLACEMENT_SLURM_TASKS_PER_NODE') and os.environ.has_key('PLACEMENT_SLURM_CPUS_PER_TASK'):
        return

    msg =  'OUPS - Je ne suis pas vraiment mpi_aware, il me manque quelques variables d\'environnement\n'
    msg += '       Avez-vous mis la commande $(placement --make_mpi_aware) AVANT l\'appel mpi ?'
    raise PlacementException(msg)

def show_hard(hard):
    """Print some information about the guessed hardware

    Argument:
    hardware
    """

    msg = "Current architecture = " + hard.NAME + " "
    if hard.NAME != 'unknown':
        msg += '(' + str(hard.SOCKETS_PER_NODE) + ' sockets/node, '
        msg += str(hard.CORES_PER_SOCKET) + ' cores/socket, '
        if hard.HYPERTHREADING:
            msg += 'Hyperthreading ON, ' + str(hard.THREADS_PER_CORE) + ' threads/core, '
        if hard.IS_SHARED:
            msg += 'SHARED'
        else:
            msg += 'EXCLUSIVE'
        msg += ')'
        print(msg)

def show_env():
    """ Prints the useful environment variables"""

    cat = hardware.Hardware.catalog()
    msg = "Current important environment variables...\n\n"
    for v in ['PLACEMENT_ARCHI','PLACEMENT_PARTITION','HOSTNAME','SLURM_NNODES','SLURM_NODELIST','SLURM_TASKS_PER_NODE','SLURM_CPUS_PER_TASK',
              'PLACEMENT_NODE','PLACEMENT_PHYSCPU','PLACEMENT_SLURM_TASKS_PER_NODE','PLACEMENT_SLURM_CPUS_PER_TASK']:
        try:
            msg += v
            msg += ' = '
            msg += bold() + os.environ[v] + normal()
        except KeyError:
            msg += '<not specified>'
        if v=='PLACEMENT_ARCHI':
            msg += ' of ' + str(cat[2])
        if v=='PLACEMENT_PARTITION':
            msg += ' of ' + str(cat[1])
        if v=='HOSTNAME':
            msg += ' should match ' + str(cat[0])
        msg += '\n'
    print msg

def compute_data_from_running(options,args,hard):
    """ Compute and return task_distrib observing a running program
    
    Arguments:
    options The command line, used to choose the correct algorithm (ps or taskset)
    args: Not used
    hard: The hardware
    """

    path = options.check

    if options.taskset == True:
        buildTasksBound = BuildTasksBoundFromTaskSet()
    else:
        buildTasksBound = BuildTasksBoundFromPs()

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

    over_cores = None
    [cpus_per_task,tasks] = computeCpusTasksFromEnv(options,args)
    hyper = options.hyper or options.hyper_phys
    if hard.IS_SHARED:
        archi = Shared(hard, cpus_per_task, tasks, hyper)
    else:
        archi = Exclusive(hard, cpus_per_task, tasks, hyper)
            
    task_distrib = ""
    if options.mode == "scatter":
        task_distrib = ScatterMode(archi)
    elif options.mode == "scatter_cyclic":
        task_distrib = ScatterMode(archi)
    elif options.mode == "scatter_block":
        task_distrib = ScatterBlockMode(archi)
    else:
        if options.hyper_phys == True:
            task_distrib = CompactPhysicalMode(archi)
        else:
            task_distrib = CompactMode(archi)
            
    # Sort the threads
    task_distrib.threadsSort()

    # If mpi aware, we keep only the task corresponding the to mpi rank
    if options.mpiaware == True:
        task_distrib.keepOnlyMpiRank()

    return task_distrib

if __name__ == "__main__":
    main()
