#!/bin/bash

#executable statement
echo Working directory is $$PBS_O_WORKDIR
cd $$PBS_O_WORKDIR

cp $$PBS_NODEFILE 1nodefile

mpdboot -f $$PBS_NODEFILE -n 1

mpiexec -machinefile 1nodefile -n $numcpus $$AMBERHOME/bin/sander.MPI -O
-i $infile -o $outfile -p $topology -c $shooter -r $dir_rst -ref $shooter -x $mdcrd
mpdallexit

echo execution finished