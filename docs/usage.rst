========
Usage
========

Once the package has been :ref:`installed <installation>`, you can use the ``aimless_init``
command to create a calculation directory. ::

    $ aimless_init calc_dir
    $ cd calc_dir
    $ aimless

This will create the ``calc_dir`` directory and add the file ``aimless.ini`` and the
directories ``input`` and ``tpl``.  The ``aimless`` command will start the calculation
process.

.. _cfgfile:

The configuration file
----------------------

Here's a sample of the contents of an ``aimless.ini`` file::

    [main]
    numpaths = 20
    totalsteps = 2500
    topology = input/topology.prmtop
    coordinates = input/coordinates.rst
    tpldir = tpl
    tgtdir = .

    [jobs]
    numnodes = 1
    numcpus  = 8
    walltime = 999:00:00
    mail = user@host.net

    [basins]
    RC1loA = 2.75
    RC1hiA = 10.0
    RC2loA = 0.0
    RC2hiA = 1.9
    RC1loB = 0.0
    RC1hiB = 2.0
    RC2loB = 3.0
    RC2hiB = 10.0

The file has three main sections: ``main``, ``jobs``, and ``basins``.

main
::::

These are settings that apply to the script as a whole.

- ``numpaths``: The number of paths to calculate
- ``totalsteps``: The total number of steps to compute
- ``topology``: The topology file for the environment
- ``coordinates``: The coordinates for the molecure
- ``tpldir``: The location of the templates used by the script (the
  ``aimless_init`` script creates this directory along with default
  versions of all of the needed templates
- ``tgtdir``: The location where working files will be written

jobs
::::

These parameters are used when creating PBS job submissions.  These are
optional and/or have default values.

- ``numnodes``: The number of nodes to use when running the job
- ``numcpus``: The number of CPUs to request from each node when running
  the job
- ``walltime``: The requested maximum runtime for the job
- ``mail``: The email address or addresses that should receive job statuses.

basins
::::::

These parameters define the dimensions of the basins used when processing
the results of the Amber_ runs.

- ``RC1loA``: The low value for the **A** well on |RC| 1.
- ``RC1hiA``: The high value for the **A** well on |RC| 1.
- ``RC2loA``: The low value for the **A** well on |RC| 2.
- ``RC2hiA``: The high value for the **A** well on |RC| 2.
- ``RC1loB``: The low value for the **B** well on |RC| 1.
- ``RC1hiB``: The high value for the **B** well on |RC| 1.
- ``RC2loB``: The low value for the **B** well on |RC| 2.
- ``RC2hiB``: The high value for the **B** well on |RC| 2.

The input directory
-------------------

This is conventionally where the topology and coordinates files are placed.
The default :ref:`configuration file <cfgfile>` defines the topology file as
``input/topology.prmtop`` and the coordinates file as
``input/coordinates.rst``.

The template directory
----------------------

The template directory (``tpl`` in the default
:ref:`configuration file <cfgfile>`) contains files formatted to be processed
as Python `template strings`_.  The basic concept is that variables prefixed
with ``$`` are replaced by values provided by the ``aimless`` script.  For
instances where a literal ``$`` is needed, we use ``$$`` to escape the symbol.

- ``amber_job.tpl``: The template used for creating Amber_ jobs.  Note that
  most PBS directives are passed directly to ``qsub`` by the ``aimless``
  script, but it should be possible to provide other directives by modifying
  this template.
- ``cons.tpl``: The force constants file.  This is used to get final bond
  lengths.  The filled result is named ``cons.rst`` in the target directory.
- ``inbackward.tpl``: The input for the backward-trajectory aimless shooting
  calculation.  The filled result is named ``inbackward.in`` in the
  target directory.
- ``indt.tpl``: The input for the aimless shooting calculation that determines
  the change in time for the trajectory.  The filled result is named
  ``indt.in`` in the target directory.
- ``inforward.tpl``: The input for the forward-trajectory aimless shooting
  calculation.  The filled result is named ``inforward.in`` in the
  target directory.
- ``instarter.in``: The input for the calculation that generates the velocities
  for this shooting point calculation.  The filled result is named
  ``instarter.in`` in the target directory.


.. |RC| replace:: reaction coordinate
.. _template strings: http://docs.python.org/2/library/string.html#template-strings
.. _Amber: http://ambermd.org/