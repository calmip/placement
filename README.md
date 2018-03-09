placement 
=========
placement is a python application to help you place your processes and threads on the cpu cores, and to let you check if the placement is correct
This is very useful when running heavy computations on a linux HPC server of cluster

PREREQUISITES:
--------------

1. You need python, release 2.7.x
2. Required if using on a shared server (or on a shared node of an HPC cluster): the numactl package
3. placement is designed to run with the SLURM workload manager (see https://slurm.schedmd.com/) on a Linux server or cluster
4. To use placement to check the placement of a running job, you should be able to access the compute node using ssh. Not all clusters are configured to let you ssh on their nodes. However, ssh is not needed if you only want to control the placement of a starting job.


INSTALLING placement:
---------------------

No need to be root to install placement, this is very simple and explained in file INSTALL.txt
All files live in a root directory $PLACEMENT_ROOT

USING placement:
----------------

`placement --documentation   | less`
