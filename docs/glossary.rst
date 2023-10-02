.. currentmodule:: plasmapy

.. _glossary:

********
Glossary
********

.. glossary::
   :sorted:

   BaPSF
   Basic Plasma Science Facility
      The Basic Plasma Science Facility is a US national collaborative
      research facility for fundamental plasma physics, supported by
      the US Department of Energy and the National Science Foundation.
      (\ https://plasma.physics.ucla.edu/\ )

   drive
      See :term:`probe drive`

   exclusion layer
   exclusion layers
      See :term:`motion exclusion`

   LaPD
   LAPD
   Large Plasma Device
      The `Large Plasma Device
      <https://plasma.physics.ucla.edu/large-plasma-device.html>`_ is
      the primary devices deployed at :term:`BaPSF`.

   motion builder
      The motion builder (i.e. |MotionBuilder|) is the entity that
      manages all the functionality around :term:`probe drive` motion
      in the :term:`motion space`.  This functionality includes: (1)
      defining the physical motion space, (2) building and generating
      the :term:`motion list`, and (3) generating motion trajectories
      to avoid obstacles in the motion space.

   motion builder item
      Terminology referring to the `xarray.DataArray` or the class/
      instance object that manages that `~xarray.DataArray` in the
      :term:`motion builder` `xarray.Dataset`.  Also see
      |MotionBuilder| and `~bapsf_motion.motion_builder.item.MBItem`.

   motion exclusion
   motion exclusions
      An exclusion "layer" defined within the `~xarray.Dataset` of the
      |MotionBuilder|.  These layers are constructed by subclasses
      of `~bapsf_motion.motion_builder.exclusions.base.BaseExclusion` and
      define regions in the :term:`motion space` where a probe is not
      allowed to be moved to.

   motion group
      A motion group is the entity that brings together all the
      components that are needed to move a probe drive around the
      :term:`motion space`.  These components include: (1) the full
      motion group configuration, (2) communicate with the
      :term:`probe drive`, (3) an understand of the :term:`motion space`
      as defined by the :term:`motion builder`, and (4) how to covert
      between the motion spacer coordinate system and the probe drive
      coordinate system.

   motion layer
   motion layers
      A "point" layer defined within the `~xarray.Dataset` of the
      |MotionBuilder|.  These layers are constructed by subclasses
      of `~bapsf_motion.motion_builder.layers.base.BaseLayer` and defined
      the desired points a probe should move to.

   motion list
   motion lists
      A motion list is a 2-D, :math:`M \times N` array containing the
      list of positions a given probe drive is supposed to move through
      during a data run.  :math:`M` represents the number of positions
      the probe must move to and :math:`N` must me equal to the number
      of axes of the probe drive.

   motion space
      The :math:`N`-D space the probe drive moves in, e.g. the
      :term:`LaPD` volume.

   point layer
   point layers
      See :term:`motion layer`

   probe
      The plasma diagnostic, target, etc. that will be moved by the
      :term:`probe drive`.

   probe drive
      A collection of :math:`N` motor driven axes that are used to
      move a :term:`probe` around the :term:`motion space`.

   probe drive space
      The probe drive space is the space defined by the motorized axes
      of the :term:`probe drive`.  This space is not necessarily
      identical to the :term:`motion space` coordinate systems. The
      :term:`transformers` are intended to be the functionality
      that converts between these two coordinate systems.

   transformer
   transformers
      A transformer is a member of the
      `~bapsf_motion.transform.base.BaseTransform` subclasses that
      provides, and does, coordinate transforms between the
      :term:`motion space` coordinate system and the :term:`probe drive`
      coordinate system, and vice versa.
