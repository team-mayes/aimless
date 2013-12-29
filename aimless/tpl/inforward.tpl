forward portion of the trajectory
  &cntrl
	imin =0,                ! minimization: 0=no, 1=yes
	irest=1,                ! restart: 0=no, 1=yesn
	ntx=5,                  ! level of info to read from restart (coords, vels, box dims, formatted file)n
	nstlim=$fwsteps,        ! number of MD timestepsn
	dt=0.001,               ! timestep in psn
	ntt=2,                  ! T-control; 0=NVE, 1=Berendsen (NO!), 2=Andersen, 3=Langevinn
	tempi=300.0,            ! initial Tn
	temp0=300.0,            ! final Tn
	vrand=1000,             ! Andersen: vels randomized every vrand steps.  Langevin: gamma_ln is collision frequency in ps^-1n
	ntp=1,                  ! P-control; 0=no P-control, 1=isotropic, 2=anisotropic, 3=semiisotropicn
	taup=2.0,               ! P-relaxation time in psn
	ntb=2,                  ! PBCs: 0=none, 1=constant V, 2=constant Pn
	ntc=2,                  ! SHAKE; 1=no SHAKE, 2=bonds w/ H are constrained, 3=all bonds constrainedn
	ntf=2,                  ! Force eval; 1=calc complete interaction, 2=bonds w/ H are omitted, 3=all bonds omitted (generally ntf=ntc, w/ TIP3P, ntf=ntc=2)n
	ntwe=0,                 ! frequency to write T and E to mden filen
	ntwx=100,               ! frequency to write coords to mdcrd file; =0 means don't writen
	ntpr=1,                 ! frequency to print to log filen
	ntwr=$fwsteps,          ! frequency to write restart filen
	cut=8.0,                ! nonbonded cutoffn
	iwrap=0,                ! wrap coordinates for visualizationn
	ifqnt=1,                ! QM/MM: 0=no, 1=yesn
	igb=0,                  ! Generalized Born: 0=no, 1=yesn
	nmropt=1,               ! enable complex restraints (umbrella sampling)n
  /
  &ewald
	dsum_tol=0.000001,      ! Increased PME accuracyn
	vdwmeth=1,              ! correction beyond cutoff; 0=none, 1=continuum model for E and Pn
  /
  &qmmm
        qmmask="@1332-1337,1403-1407,2037-2043,4700-4701,5392-5433,5449,5802-5804,5787-5789", !QM region - ASP175 (cut CB-CG), SER181, ASP221, ASP401 (only C and O), GLC 2, GLC 3, GLC O4, waters
	qmcharge=-1,            ! charge of QM regionn
	qm_theory=DFTB,         ! QM Hamiltonian: "DFTB" = SCC-DFTBn
	qm_ewald=1,             ! long range e-statics for QM region; 1=use PMEn
	qmshake=0,              ! Shake in QM region: 0=no, 1=yesn
	qmcut=8.0,              ! nonbonded cutoffn
	writepdb=0,             ! write pdb of QM region: 0=no, 1=yesn
  /
  &wt
	type='DUMPFREQ',
	istep1=$fwout,
  /
  &wt
	type='END',
  /
  DISANG=cons.rst
  DUMPAVE=cons.dat