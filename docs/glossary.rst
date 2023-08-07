.. currentmodule:: plasmapy

.. _glossary:

********
Glossary
********

.. glossary::
   :sorted:

   drive
      See :term:`probe drive`

   motion list
   motion lists
      A motion list is a 2-D, :math:`M \times N` array containing the list of
      positions a given probe drive is supposed to during a data run.
      :math:`M` represents the number of position the probe must move to and
      :math:`N` must me equal to the number of axes of the probe drive.

   motion space
      The :math:`N`-D space the probe drive moves in.

   probe
      The plasma diagnostic, target, etc. the will be moved by the
      :term:`probe drive`.

   probe drive
      A collection of :math:`N` motor driven axes that are used to
      move a :term:`probe` around the :term:`motion space`.
