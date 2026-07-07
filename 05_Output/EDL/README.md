# 05_Output/EDL — Edit decision lists

Timeline exports and EDL files for the example film. Used to hand off the cut between
DaVinci Resolve and other NLEs, and to reproduce the edit from source clips.

## Files

- [`shotflow_v01.edl`](./shotflow_v01.edl) — v01 EDL for the example film
  *Echo of the Singularity*. References clip names from `05_Output/Rough_Cuts/`.

## Usage

Import into DaVinci Resolve (or any NLE supporting CMX 3600 EDL) to reproduce the cut.
The EDL is regenerated whenever the locked cut changes — see
[`../Rough_Cuts/locked_cut_notes.md`](../Rough_Cuts/locked_cut_notes.md).
