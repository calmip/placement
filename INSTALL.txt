INSTALLING placement
====================

1/ Prerequisites: 
    -placement needs python 2.7.x, but NOT (yet) python3 !
    -You should use slurm as resource scheduler (at least for --check use)
    -When you are running a job on a cluster, you should be able to ssh to the working node
     to be able to use placement --checkme or any other --check option

2/ Execute the installation script:
           ./install.sh                      ==> Installing in the directory ~/placement
           or
           ./install.sh /usr/local/placement ==> Installing in the directory /usr/local/placement
3/ OPTIONAL:
   copy the file ...../placement/etc/placement.conf-dist to ...../placement/etc/placement.conf
   Edit placement.conf to configure placement to your needs

4/ REQUIRED:
   copy the file ...../placement/bin/placement-dist to ...../placement/bin/placement
   Edit the new file to check that everything is OK for your, particularly the python version (2.7.x, no more, no less)
   Create a symbolic link from a directory in the path (~/bin, /usr/local/bin, etc) to this file

   OR

   copy the file ...../placement/bin/placement-dist to a directory in the path
   Edit the new file as explained above
     
START USING placement:
======================
   placement --documentation   | less   # read the doc !
   placement --documentation 7 | less   # read only from Section 7
   placement --help                     # shorter but helpful doc
   
QUICK and DIRTY START:
======================
   copy placement.conf as explained in 3/ (no use editing the file), then:

# export PLACEMENT_ARCHI=Bullx_dlc
# placement 4 4 --ascii-art
  S0-------- S1-------- 
P AAAABBBB.. CCCCDDDD.. 




Have fun !

Emmanuel
emmanuel.courcelle@inp-toulouse.fr
https://www.calmip.univ-toulouse.fr
