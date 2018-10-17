#! /bin/bash

#PORT=""
#USER=""
HOST=""
PLACEMENT_ROOT=""

function Usage {
    echo "Usage: ./install.sh --help " &&
    echo "       ./install.sh [directory]" &&
    echo "       The default install directory is ~/placement, where ~ is your home directory" && 
    echo "       The install directory is created if necessary" && exit 1
}

# Call Usage
[ "$1" = "--help" ] && Usage

# Install top directory defaults to home directory
PLACEMENT_ROOT=${1-$(cd; pwd -P)}/placement

echo "placement will be installed inside the directory: " $PLACEMENT_ROOT
read -p "Are you OK (Y/N) ?"
if [ "$REPLY" != "Y" ] 
then
    echo "Cancelled"; 
    exit 1; 
fi

BIN="$PLACEMENT_ROOT/bin"
LIB="$PLACEMENT_ROOT/lib"
ETC="$PLACEMENT_ROOT/etc"

SRC=$(pwd)

echo "Now installing placement..."
[ ! -d $BIN ] && (mkdir -p $BIN || exit 1)
[ ! -d $LIB ] && (mkdir -p $LIB || exit 1)
[ ! -d $ETC ] && (mkdir -p $ETC || exit 1)

if [ "$SRC/lib" != "$LIB" ]
then

for f in params.py jobsched.py slurm.py front.py hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py utilities.py matrix.py printing.py placement.py placement-cont.py placement-patho.py
do
  cp $SRC/lib/$f $LIB
done

fi

if [ "$SRC/etc" != "$ETC" ]
then

for f in placement.conf-dist documentation.txt
do
  cp $SRC/etc/$f $ETC
done

fi

if [ "$SRC/bin" != "$BIN" ]
then
    cp $SRC/bin/placement-dist $BIN
fi

chmod -R a=rX,u+w $LIB $BIN $ETC
chmod a+rx $BIN/placement-dist $LIB/placement.py $LIB/placement-cont.py $LIB/placement-patho.py

echo

EXTERNALS=""
# Do we have numactl ?
NUMACTL=$(which numactl)
if [ "$NUMACTL" = "" ]
then
    echo "numactl is NOT installed on this machine. PLACEMENT CANNOT BE INSTALLED "
    exit 1
fi

# Do we have numastat ?
NUMASTAT=$(which numastat)
if [ "$NUMASTAT" = "" ]
then
    echo "numastat is NOT installed on this machine. The switch --memory will NOT be available"
else
    echo "Found numastat = $NUMASTAT"
    EXTERNALS="$EXTERNALS numastat"
fi

# Do we have squeue or nodeset ?
SQUEUE=$(which squeue)
if [ "$SQUEUE" = "" ]
then
    echo "squeue is NOT installed on this machine. The switches --jobid, --checkme will NOT be available"
else
    echo "Found squeue   = $SQUEUE"
    EXTERNALS="$EXTERNALS squeue"
fi

# Do we have squeue or nodeset ?
NODESET=$(which nodeset)
if [ "$NODESET" = "" ]
then
    echo "nodeset is NOT installed on this machine. The switches --host, --jobid, --checkme will NOT be available"
else
    echo "Found nodeset  = $NODESET"
    EXTERNALS="$EXTERNALS nodeset"
fi

# Do we have clush ?
CLUSH=$(which clush)
if [ "$CLUSH" = "" ]
then
    echo "clush is NOT installed on this machine. The switches --continuous, --pathological will NOT be available"
else
    echo "Found clush    = $CLUSH"
    EXTERNALS="$EXTERNALS clush"
fi

# edit placement-dist 
sed -i -e "s!PLACEMENT_ROOT=PROOT!PLACEMENT_ROOT=$PLACEMENT_ROOT!" -e "s!PLACEMENT_EXTERNALS=PEXT!PLACEMENT_EXTERNALS=\"$EXTERNALS\"!" $BIN/placement-dist 


echo
echo "==========================="   
echo "That's all for me, folks ! "
echo "==========================="

echo "Now, you should do: "
echo "     cd $PLACEMENT_ROOT/bin"
echo "     cp placement-dist placement"
echo "     chmod a+rx placement"
echo "     edit placement to be sure all is OK (the python version for example)"
echo ""
echo "     cd $PLACEMENT_ROOT/etc"
echo "     cp placement.conf-dist placement.conf"
echo "     edit $ETC/placement.conf to configure placement"

