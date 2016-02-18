#!/bin/bash
set -e
DIRNAME=$(dirname "$BASH_SOURCE")
ENVNAME=$1
ACTIVATE="$ENVNAME/bin/activate"
RUNFILE="$DIRNAME/flux_run.py"

trap 'kill -TERM $PID' TERM
trap 'kill -KILL $PID' KILL

if [ ! -d ${ENVNAME} ]; then
  echo "Error: $ENVNAME does not exist"
  exit 1
fi
echo "Sourcing \"$ACTIVATE\""
. "$ACTIVATE"
echo "Running \"$RUNFILE\""
"$RUNFILE" &

PID=$!
wait $PID
