#!/bin/bash

#executable statement
echo Working directory is $$PBS_O_WORKDIR
cd $$PBS_O_WORKDIR

mpdboot -f $$PBS_NODEFILE -n 1

mpiexec -machinefile $$PBS_NODEFILE -n $numcpus $$AMBERHOME/bin/sander.MPI -O
-i $infile -o $outfile -p $topology -c $shooter -r $dir_rst -ref $shooter -x $mdcrd
mpdallexit

echo execution finished