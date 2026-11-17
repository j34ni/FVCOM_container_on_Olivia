# End-to-end run on Olivia, from the provided case data

Target: take the provided case files, run FVCOM in this
container, get valid NetCDF output. No step is optional; run them in order.

## 0. Layout

Everything lives under `$PROJECT` (set this first; the project work area
under `/cluster/work/projects/` has no quota):

    export PROJECT=/cluster/work/projects/nn9997k/jeani
    mkdir -p $PROJECT
    cd $PROJECT

    $PROJECT/
      FVCOM_container_on_Olivia/   this repo (git clone; step 1 puts the .sif here)
        fvcom_mpich5.1.sif         the image from ghcr (step 1)
      FavneChild1/
        input/                     the provided case files, copied as-is (step 2)
        FavneChild1_run.nml        the provided namelist, dated Oct 12 (step 2)
      FavneChild1-hot/             created by prep-favne-hot.sh (step 3)
      favne-2n-alpine/             created by the 2-node job (step 5b)

## 1. Image

    cd $PROJECT
    git clone https://github.com/j34ni/FVCOM_container_on_Olivia.git
    cd FVCOM_container_on_Olivia
    apptainer pull --force docker://ghcr.io/j34ni/fvcom-container-on-olivia/fvcom:mpich5.1

`apptainer pull` names the file after image:tag, so this produces
`fvcom_mpich5.1.sif` in the repo directory.

The image must link PETSc against hypre (the semi-implicit solver uses
PCHYPRE/BoomerAMG; without hypre FVCOM dies at `PETSc SETUP`). Check it
before anything else:

    apptainer exec fvcom_mpich5.1.sif sh -c 'ls /usr/lib/libpetsc.so.* && ldd /usr/lib/$(ls /usr/lib | grep "^libpetsc\.so\." | head -1) | grep -i hypre'

The `ldd` output must contain a `libHYPRE` line. If it prints nothing,
stop: the image has no hypre. Record the `libpetsc.so.*` version and the
hypre line; they identify the stack the results were produced with.

## 2. User data

The case directory on Olivia is
`/cluster/projects/nn9238k/qin/FavneChild1` (checked complete 2026-11-17:
the 11 files below, all nonzero, plus `nestnode_0723.nc`). Copy it into
`$PROJECT`:

    cp -r /cluster/projects/nn9238k/qin/FavneChild1 $PROJECT/

The mandatory set inside `$PROJECT/FavneChild1/input/`:

    FavneChild1_grd.dat              grid connectivity
    FavneChild1_dep.dat              depth
    FavneChild1_sigma.dat            sigma layers
    FavneChild1_cor.dat              Coriolis coefficient
    FavneChild1_spg.dat              smoothing parameters
    FavneChild1_obc.dat              open boundaries
    FavneChild1_wnd_0723.nc          wind forcing
    FavneChild1_heat_0723.nc         heat flux forcing
    FavneChild1_prate_0723.nc        precipitation
    FavneChild1_restart_0723.nc      restart fields (hot start)
    FavneChild1NH_restart_0723.nc

Check it after the copy (a missing `nestnode_0723.nc` is fine: the namelist
sets `NESTING_ON = F`):

    cd $PROJECT/FavneChild1/input
    for f in FavneChild1_grd.dat FavneChild1_dep.dat FavneChild1_sigma.dat \
             FavneChild1_cor.dat FavneChild1_spg.dat FavneChild1_obc.dat \
             FavneChild1_wnd_0723.nc FavneChild1_heat_0723.nc \
             FavneChild1_prate_0723.nc FavneChild1_restart_0723.nc; do
      [ -s "$f" ] && echo "OK  $f  $(stat -c %s "$f")" || echo "MISSING  $f"
    done

Every line must be `OK` with a nonzero size. A zero-byte file is a failed
transfer: copy it again.

The case namelist is `$PROJECT/FavneChild1/FavneChild1_run.nml` (the
provided Oct-12 version: `WIND_ON = F`, `HEATING_CALCULATE_ON = F`,
`PLUME_CALCULATE_ON = F`, `END_DATE = '2025-07-30 00:00:00'`, cold start).
The prep script below turns the forcing on and applies the hot-start edits;
the result is byte-identical (verified) to the namelist that produced
the reference runs in `README.md`. `run_fvcom.sh` is the SLURM script
shipped with the case, for the modules-based build; not used here.

## 3. Prepare the case directory

    cd $PROJECT/FVCOM_container_on_Olivia
    PROD_NML=$PROJECT/FavneChild1/FavneChild1_run.nml bash prep-favne-hot.sh

Last line printed (path = your $PROJECT):

    READY: /cluster/work/projects/nn9997k/jeani/FavneChild1-hot (hot start, 2 h simulated, wind + heat flux on)

This writes `$PROJECT/FavneChild1-hot/` with:

- `FavneChild1_run.nml` — the production namelist with exactly three edits:
  `&NML_STARTUP` set to hot start from `FavneChild1_restart_0723.nc`,
  `END_DATE = '2025-07-23 02:00:00'` (2 simulated hours), `OUTPUT_DIR`
  pointing at `$PROJECT/FavneChild1-hot/output`;
- `input` — a symlink to `$PROJECT/FavneChild1/input`;
- an empty `output/` directory.

The prep script fails loudly (`set -euo pipefail` + five `grep -q` checks)
if the production namelist does not have the fields it edits. If it dies,
compare the namelist against the field names above; do not hand-edit the
result.

## 4. Fresh-run hygiene (only when re-running over a previous run)

    rm -f  $PROJECT/FavneChild1-hot/FavneChild1.part   # partition file, regenerated
    mv     $PROJECT/FavneChild1-hot/output $PROJECT/FavneChild1-hot/output-old 2>/dev/null
    mkdir  $PROJECT/FavneChild1-hot/output

The 2-node job recreates its own run directory; nothing to clean there.

## 5. Run

Set your project number in the job scripts (`#SBATCH --account=nnXXXXk` →
your account) and submit from the repo directory, where `fvcom_mpich5.1.sif`
is (step 1). To use a different image file, set `SIF` before `sbatch`:

    export SIF=fvcom_mpich5.1.sif   # default in the job scripts

5a. One node, 128 ranks (partition `small`) — the simple case, MPI all-local:

    cd $PROJECT/FVCOM_container_on_Olivia
    sbatch job-favne-hot-1n.sh

5b. Two nodes, 2x64 ranks (partition `large`) — also exercises Slingshot
ofi/cxi inter-node; it writes into its own `favne-2n-alpine/` directory and
can run in parallel with 5a:

    sbatch job-favne-hot-2n.sh

Expect 28800 steps: ~1:10 on 1 node, ~0:48 on 2 nodes.

## 6. Pass/fail in the job output

Check `fvcal-1n-*.out` / `fvcal-2n-*.out`, in this order:

1. `Nodes: ...  Ranks: 128` and 128 `PETSc PARTITION:` rows, all non-empty
   -> METIS decomposition OK
2. `PETSc SETUP        : COMPLETE!` -> hypre/BoomerAMG solver set up; this
   is the marker that kills runs on an image without hypre
3. `IINT ... SIMTIME ... SECS/IT` rows advancing
4. `PETSc CLEANUP      : COMPLETE!` and `TADA!` -> normal end
5. files:

       ls -l $PROJECT/FavneChild1-hot/output/FavneChild1_0001.nc \
             $PROJECT/FavneChild1-hot/output/FavneChild1_restart_0001.nc

Known signatures:

- `Unable to find requested PC type hypre` at setup -> image lacks hypre, step 1.
- `TOTAL NUMBER OF ELEMENTS SET UP TO RECEIVE DATA NOT EQUAL TO ... HALO ELEMENTS`
  -> stale `FavneChild1.part` for a different rank count, step 4.
- `File ... does not exist` naming a case file -> missing input file, step 2.

`IEEE_UNDERFLOW_FLAG IEEE_DENORMAL` notes at the end are the normal gfortran
summary on this case (values in the FLOW FIELD STATS are ~1e-6); not an error.

## 7. Performance measure

    sh medians.sh   # adapt the two .out filenames at the top of the script

The `median ... s/it` lines are the numbers for the README table; include
the job ids. Reference with this stack: 1n 0.1452 s/it, 2n 0.1012 s/it.
