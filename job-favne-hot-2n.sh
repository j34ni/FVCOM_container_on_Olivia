#!/bin/bash
#SBATCH --job-name=fvcal-2n
#SBATCH --account=nnXXXXk
#SBATCH --time=0-03:00:00
#SBATCH --partition=large
#SBATCH --nodes=2
#SBATCH --ntasks-per-node=64
#SBATCH --cpus-per-task=1
#SBATCH --output=fvcal-2n-%j.out
#SBATCH --export=ALL
set -euo pipefail

SIF="${SIF:-fvcom_mpich5.1.sif}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MPICH_CH4_NETMOD=ofi
export FI_PROVIDER=cxi
export MPIR_CVAR_CH4_CMA_ENABLE=0
export MPIR_CVAR_CH4_OFI_ENABLE_RMA=1
export FI_CXI_RX_MATCH_MODE=hybrid
export MPIR_CVAR_CH4_SHM_POSIX_TOPO_ENABLE=false
export APPTAINER_QUIET=1
export APPTAINER_BIND="${BINDS:-$PROJECT:$PROJECT}"

echo "Nodes: ${SLURM_NODELIST}  Ranks: ${SLURM_NTASKS}"

RUNDIR="$PROJECT/favne-2n-alpine"
rm -rf "$RUNDIR"
mkdir -p "$RUNDIR/output"
for f in "$PROJECT"/FavneChild1-hot/*; do
  case "$f" in
    *_run.nml*|*output*) ;;
    *) ln -s "$f" "$RUNDIR/" ;;
  esac
done
sed "s|OUTPUT_DIR *=.*|OUTPUT_DIR = '$RUNDIR/output'|" \
  "$PROJECT/FavneChild1-hot/FavneChild1_run.nml" > "$RUNDIR/FavneChild1_run.nml"

srun -n $SLURM_NTASKS --mpi=pmi2 apptainer exec "$SIF" bash -c \
  "cd $RUNDIR && exec fvcom --casename=FavneChild1 --dbg=2"
