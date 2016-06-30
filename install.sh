#! /bin/bash

#PORT=""
#USER=""
HOST=""
DST=""

function Usage {
	echo "Usage: ./install.sh [-p port] [-u user] machine [repertoire]" && echo "       repertoire par defaut = le home du user sur machine" && exit 1
}

# Note that we use `"$@"' to let each command-line parameter expand to a 
# separate word. The quotes around `$@' are essential!
# We need TEMP as the `eval set --' would nuke the return value of getopt.
TEMP=`getopt -o u:p: -- "$@"`
if [ $? != 0 ] ; then echo "plop..." >&2 ; Usage ; fi

# cf. /usr/share/doc/util-linux/examples/getopt-parse.bash
# Note the quotes around `$TEMP': they are essential!
eval set -- "$TEMP"

while true ; do
	case "$1" in
		-p) PORT=$2; shift 2;;
		-u) USER=$2; shift 2;;
		--) shift ; break ;;
		*)  echo "Internal error!" ; exit 1 ;;
	esac
done

USER=${USER-$(whoami)}
PORT=${PORT-22}
HOST=$1

# Install top directory defaults to home directory
if [ "$HOST" = 'LOCAL' ]
then
	DST=${2-$(cd; pwd -P)}
else
	DST=${2-$(ssh -p $PORT $USER@$HOST pwd -P)}
fi

echo USER=$USER
echo PORT=$PORT
echo HOST=$HOST
echo DST=$DST

[ "$USER" = "" -o "$PORT" = "" -o "$HOST" = "" -o "$DST" = "" ] && Usage

BIN="$DST/bin"
LIB="$DST/lib/placement"
ETC="$DST/etc/placement"

SRC=usr/local

if [ "$HOST" = 'LOCAL' ]
then

echo "OK pour une installation en local..."
[ ! -d $BIN ] && (mkdir -p $BIN || exit 1)
[ ! -d $LIB ] && (mkdir -p $LIB || exit 1)
[ ! -d $ETC ] && (mkdir -p $ETC || exit 1)

for f in hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py utilities.py matrix.py printing.py documentation.txt
do
  cp $SRC/lib/placement/$f $LIB
done

for f in placement.conf 
do
  cp $SRC/etc/placement/$f $ETC
done

cp $SRC/bin/placement.py $SRC/bin/placement $BIN
chmod a=r,u+w $LIB/*
chmod a=rx,u+w $BIN/placement.py $BIN/placement

else

echo "OK for installing on $HOST, user $USER ..."

ssh -p $PORT $USER@$HOST "[ ! -d $BIN ] && (mkdir -p $BIN || exit 1)"
ssh -p $PORT $USER@$HOST "[ ! -d $LIB ] && (mkdir -p $LIB || exit 1)"
ssh -p $PORT $USER@$HOST "[ ! -d $ETC ] && (mkdir -p $ETC || exit 1)"

for f in hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py printing.py utilities.py matrix.py documentation.txt
do
  scp -P $PORT $SRC/lib/placement/$f "$USER@$HOST:$LIB"
done

for f in placement.conf
do
  scp -P $PORT $SRC/etc/placement/$f "$USER@$HOST:$ETC"
done

scp -P $PORT $SRC/bin/placement.py $SRC/bin/placement "$USER@$HOST:$BIN"
ssh -p $PORT $USER@$HOST "chmod a=r,u+w $LIB/* $ETC/*"
ssh -p $PORT $USER@$HOST "chmod a=rx,u+w $BIN/placement.py $BIN/placement"

fi

echo "That's all, folks !"

