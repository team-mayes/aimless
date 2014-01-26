.. _installation:

============
Installation
============

At the command line::

    $ python setup.py install

Make sure that your Python installation location's ``bin`` directory is
in your shell's ``PATH`` (see the `Python install page`_ for details).

There are two commands that are included in
this package: ``aimless`` and ``aimless_init``.  The first is the main
processing command while the second is used for creating the initial
directory structure for running aimless shooting calculations.

External Tools
--------------

These tools are expected to be installed prior to running the tool.

* Amber_: A package of molecular simulation  programs
* Torque_: The batch job management system.  Note that other PBS-equivalent
  job management systems might work (we use ``qsub`` and ``qstat``), but
  they are not tested.

.. _Python install page: http://docs.python.org/2/install/
.. _Amber: http://ambermd.org/
.. _Torque: http://www.adaptivecomputing.com/products/open-source/torque/