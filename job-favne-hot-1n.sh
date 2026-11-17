#!/bin/bash
#SBATCH --job-name=fvcal-1n
#SBATCH --account=nnXXXXk
#SBATCH --time=0-03:00:00
#SBATCH --partition=small
#SBATCH --nodes=1
#SBATCH --ntasks-per-node=128
#SBATCH --cpus-per-task=1
#SBATCH --mem-per-cpu=1G
#SBATCH --output=fvcal-1n-%j.out
#SBATCH --export=ALL
set -euo pipefail

SIF="${SIF:-fvcom_mpich5.1.sif}"
export OMP_NUM_THREADS=1
export OPENBLAS_NUM_THREADS=1
export MPICH_CH4_NETMOD=ofi
export FI_PROVIDER=tcp
export MPIR_CVAR_CH4_CMA_ENABLE=0
export MPIR_CVAR_CH4_SHM_POSIX_TOPO_ENABLE=false
export APPTAINER_QUIET=1
export APPTAINER_BIND="${BINDS:-$PROJECT:$PROJECT}"

echo "Nodes: ${SLURM_NODELIST}  Ranks: ${SLURM_NTASKS}"

srun -n $SLURM_NTASKS --mpi=pmi2 apptainer exec "$SIF" bash -c \
  "cd $PROJECT/FavneChild1-hot && exec fvcom --casename=FavneChild1 --dbg=2"
