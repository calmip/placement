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
DST=${2-"/users/sysadmin/$USER"}

echo USER=$USER
echo PORT=$PORT
echo HOST=$HOST
echo DST=$DST

[ "$USER" = "" -o "$PORT" = "" -o "$HOST" = "" -o "$DST" = "" ] && Usage

BIN="$DST/bin"
LIB="$DST/lib/placement"

ssh -p $PORT $USER@$HOST "[ ! -d $BIN ] && echo Pas de répertoire $BIN sur $HOST" && exit 1
ssh -p $PORT $USER@$HOST "[ ! -d $LIB ] && echo Pas de répertoire $LIB sur $HOST" && exit 1

SRC=usr/local

for f in hardware.py architecture.py exception.py tasksbinding.py scatter.py compact.py running.py utilities.py matrix.py
do
  scp -P $PORT $SRC/lib/placement/$f "$USER@$HOST:$LIB"
done

scp -P $PORT $SRC/bin/placement.py $SRC/bin/placement "$USER@$HOST:$BIN"
ssh -p $PORT $USER@$HOST "chmod a=r,u+w $LIB/*"
ssh -p $PORT $USER@$HOST "chmod a=rx,u+w $BIN/placement.py $BIN/placement"

echo "C'est fait, man !"
