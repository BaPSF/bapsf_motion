.. currentmodule:: plasmapy

.. _glossary:

********
Glossary
********

.. glossary::
   :sorted:

   drive
      See :term:`probe drive`

   exclusion layer
   exclusion layers
      See :term:`motion exclusion`

   motion exclusion
   motion exclusions
      An exclusion "layer" defined within the `~xarray.Dataset` of the
      |MotionList|.  These layers are constructed by subclasses
      of `~bapsf_motion.motion_list.exclusions.base.BaseExclusion` and
      define regions in the :term:`motion space` where a probe is not
      allowed to be moved to.

   motion layer
   motion layers
      A "point" layer defined within the `~xarray.Dataset` of the
      |MotionList|.  These layers are constructed by subclasses
      of `~bapsf_motion.motion_list.layers.base.BaseLayer` and defined
      the desired points a probe should move to.

   motion list
   motion lists
      A motion list is a 2-D, :math:`M \times N` array containing the list of
      positions a given probe drive is supposed to during a data run.
      :math:`M` represents the number of position the probe must move to and
      :math:`N` must me equal to the number of axes of the probe drive.

   motion list item
      Terminology referring to the `xarray.DataArray` or the class/
      instance object that manages that `~xarray.DataArray` in the
      :term:`motion list` `xarray.Dataset`.  Also see |MotionList| and
      `~bapsf_motion.motion_list.item.MLItem`.

   motion space
      The :math:`N`-D space the probe drive moves in.

   point layer
   point layers
      See :term:`motion layer`

   probe
      The plasma diagnostic, target, etc. the will be moved by the
      :term:`probe drive`.

   probe drive
      A collection of :math:`N` motor driven axes that are used to
      move a :term:`probe` around the :term:`motion space`.
