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
import argparse
from exception import *
from front import *

PLACEMENT_VERSION = "1.12.1"

def params():
    """Parse the command line and return a tuple:
       - options (the result of the parse)
       - FrontNode (the FrontNode object, depends on the environment variable PLACEMENT_EXTERNALS)
    """

    externals = []
    if 'PLACEMENT_EXTERNALS' in os.environ:
        externals = os.environ['PLACEMENT_EXTERNALS'].strip().split(' ')

    fn = FrontNode(externals)
        
    # Analyzing the command line arguments
    epilog = 'Do not forget to check your environment variables (--environ) and the currently configured hardware (--hard) !'
    parser = argparse.ArgumentParser(description="placement " + PLACEMENT_VERSION,epilog=epilog)
    parser.add_argument('--version', action='version', version='%(prog)s '+PLACEMENT_VERSION)

    # WARNING - The arguments of this group are NOT USED by the python program, ONLY by the bash wrapper !
    #           They are reminded here for coherency and for correctly writing help
    group = parser.add_argument_group('checking jobs running on the compute nodes')
    
    if fn.getJobSchedName() != "":
        group.add_argument("--checkme",dest='checkme',action="store_true",help="Check my running job")
        group.add_argument("--jobid",dest='jobid',action="store",type=int,help="Check this running job")

    group.add_argument("--host",dest='host',action="store",type=str,help="Check those hosts, ex: node[10-15]")

    group = parser.add_argument_group('Displaying some information')
    group.add_argument("-I","--hardware",dest='show_hard',action="store_true",help="Show the currently selected hardware and leave")
    group.add_argument("-E","--documentation", action="store",nargs='?',type=int,default=0,dest="documentation",help="Print the complete documentation and leave")
    group.add_argument("--environment",action="store_true",dest="show_env",help="Show some useful environment variables and leave")
    
    parser.add_argument('tasks', metavar='tasks',nargs='?',default=-1 ) 
    parser.add_argument('nbthreads', metavar='cpus_per_tasks',nargs='?',default=-1 ) 
    parser.add_argument("-T","--hyper",action="store_true",default=False,dest="hyper",help='Force use of hyperthreading (False)')
    parser.add_argument("-P","--hyper_as_physical",action="store_true",default=False,dest="hyper_phys",help="Used ONLY with mode=compact - Force hyperthreading and consider logical cores as supplementary sockets (False)")
    parser.add_argument("-M","--mode",choices=["compact","scatter","scatter_block"],default="scatter",dest="mode",action="store",help="distribution mode: scatter,scatter_block, compact (scatter)")
    parser.add_argument("-U","--human",action="store_true",default=False,dest="human",help="Output humanly readable")
    parser.add_argument("-A","--ascii-art",action="store_true",default=False,dest="asciiart",help="Output geographically readable")
    parser.add_argument("-R","--srun",action="store_const",dest="output_mode",const="srun",help="Output for srun (default)")
    parser.add_argument("-N","--numactl",action="store_const",dest="output_mode",const="numactl",help="Output for numactl")
    parser.add_argument("-z","--intel_pin_domain",action="store_const",dest="output_mode",const="i_mpi_pin_domain",help="Output for intel mpiexec.hydra: eval $(placement -z)")
    parser.add_argument("-Z","--intel_affinity",action="store_const",dest="output_mode",const="kmp",help="Output for intel openmp compiler, try also --verbose: eval $(placement -Z --verb")
    parser.add_argument("-G","--gnu_affinity",action="store_const",dest="output_mode",const="gomp",help="Output for gnu openmp compiler")
    parser.add_argument("--make_mpi_aware",action="store_true",default=False,dest="makempiaware",help="Can be used with --mpi_aware in the sbatch script BEFORE mpirun, if you work on a SHARED node - EXPERIMENTAL")
    parser.add_argument("--mpi_aware",action="store_true",default=False,dest="mpiaware",help="For running hybrid codes, implies --numactl")
    parser.add_argument("-C","--check",const="ALL", nargs='?', dest="check",action="store",help="Check the cpus binding of a running process (CHECK is a command name, or a user name or ALL)")
#    FOR THE DEV: --check=+ ==> look for files called PROCESSES.txt, *.NUMASTAT.txt, gpu.xml
    parser.add_argument("-H","--threads",action="store_true",default=False,help="With --check: show threads affinity to the cpus on a running process (default if check specified)")
    parser.add_argument("--summary","--summary",action="store_true",default=False,help="With --check: show summary of core and gpus utilization in a running process, with a warning for pathological cases")
    parser.add_argument("--show_depop","--show_depop",action="store_true",default=False,help="With --check --summary: show as pathological jobs the depopulated jobs, ie jobs with low cpu use and high memory allocation")
    parser.add_argument("--cpu_threshold",dest="cpu_thr",action="store",type=int,help="With --check --summary: threshold to consider the cpu use as \"low\" ")
    parser.add_argument("--mem_threshold",dest="mem_thr",action="store",type=int,help="With --check --summary: threshold to consider the mem allocated as \"high\" ")
    parser.add_argument("--csv","--csv",action="store_true",default=False,help="With --check: same infos as --summary, but csv formatted and no warning indicators")
    parser.add_argument("-i","--show_idle",action="store_true",default=False,help="With --threads: show idle threads, not only running")
    parser.add_argument("-t","--sorted_threads_cores",action="store_true",default=True,help="With --threads: sort the threads in core numbers rather than pid")
    parser.add_argument("-p","--sorted_processes_cores",action="store_true",default=False,help="With --threads: sort the processes in core numbers rather than pid")
    parser.add_argument("--memory","--memory",action="store_true",default=False,help="With --threads: show memory occupation of each process / socket")
#    parser.add_argument("-K","--taskset",action="store_true",default=False,help="Do not use this option, not implemented and not useful")
    parser.add_argument("-V","--verbose",action="store_true",default=False,dest="verbose",help="more verbose output can be used with --check and --intel_kmp")
    parser.add_argument("--no_ansi",action="store_true",default=False,dest="noansi",help="Do not use ansi sequences")
    parser.add_argument("--from-frontal",action="store_true",default=False,dest="ff",help=argparse.SUPPRESS)
    
    # Still experimental, not documented
    parser.add_argument("--continuous",action="store_true",default=False,dest="continuous",help=argparse.SUPPRESS)
    parser.add_argument("--pathological",action="store_true",default=False,dest="pathological",help=argparse.SUPPRESS)

    # default is srun
    parser.set_defaults(output_mode="srun")
    options=parser.parse_args()
    
    # mpi_aware = force mode to numactl
    if options.mpiaware:
        options.output_mode="numactl"
    
    fn.setOptions(options,sys.argv)

    #print("coucou "+options.check)
    
    return (options, fn)
