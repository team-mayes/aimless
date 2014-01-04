Harmonic restraints for umbrella sampli:
coordinate 1: anomeric C to water O
coordinate 2: anomeric C to glycosidic oxygen
&rst
        iat=5802,5392,          ! C1 to attack O(H2O) - if 2, distance restraint; if 3, angle, etc.
        r1=2.0,                 ! value of restraint above which the restraint eney is linear, not parabolic
        r2=2.6,                 ! restraint distance (LHS)
        r3=2.6,                 ! restraint distance (RHS)
        r4=3.6,                 ! value of restraint above which the restraint eney is linear, not parabolic
        rk2=0.0,               ! restraint force constant (LHS)
        rk3=0.0,               ! restraint force constant (RHS)
  /
  &rst
        iat=5392,5428,          ! C1 and anomeric O   - if 2, distance restraint; if 3, ale restraint, etc.
        r1=1.92,                        ! value of restraint above which the restraint eney is linear, not parabolic
        r2=2.69,                        ! restraint distance (LHS)
        r3=2.69,                        ! restraint distance (RHS)
        r4=3.96,                        ! value of restraint above which the restraint eney is linear, not parabolic
        rk2=0.0,               ! restraint force constant (LHS)
        rk3=0.0,               ! restraint force constant (RHS)
   /