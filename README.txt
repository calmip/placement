INSTALLING placement
====================

1/ Prerequisite: placement needs python 2.X, with X <= 6, the shell wrapper arranges for this, using a module command 
2/ Have a look to the file ./usr/local/etc/placement/placement.conf and modify it to your needs
3/ TO INSTALL ON YOUR MACHINE, Home directory:
   	  ./install.sh LOCAL
4/ TO INSTALL ON YOUR MACHINE, /some/other/directory:
   	  ./install.sh LOCAL /some/other/directory
5/ TO INSTALL ON ANOTHER MACHINE:
   arrange for sshing on the remote host with key authentication
   ./install.sh REMOTE
   OR
   ./install.sh REMOTE DIRECTORY
   OR (other options)
   ./install.sh -h

6/ The following subdirectories will be created by this installation: lib/placement, etc/placement
7/ placement itself is in ~/bin subdirectory (the wrapper placement AND the python program placement.py)
   If not already done, please put this directory in your path !


START USING placement:
======================

   placement --documentation   | less   # read the doc !
   placement --documentation 7 | less   # read only from Section 7
   placement --help                     # shorter but helpful doc
 
QUICK (and somewhat dirty) START:
=================================

   export PLACEMENT_ARCHI=Bullx_dlc
   placement 4 4 --ascii-art


Emmanuel
emmanuel.courcelle@inp-toulouse.fr

https://www.calmip.univ-toulouse.fr
