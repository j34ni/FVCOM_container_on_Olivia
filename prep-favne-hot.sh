#!/bin/bash
# Build the hot-start case directory from the provided case data.
# Requires $PROJECT (e.g. /cluster/work/projects/nn9997k/jeani) containing:
#   $PROJECT/FavneChild1/input/    the provided case files
#   $PROJECT/FavneChild1/FavneChild1_run.nml   the provided namelist
# Produces $PROJECT/FavneChild1-hot/ with the adjusted namelist and an
# input/ symlink. The provided Oct-12 namelist ships with the forcing
# flags off; the script turns wind/heat-calculate/plume-calculate on and
# applies the hot-start edits (idempotent for a namelist that has them on).
set -euo pipefail

PROD_NML="${PROD_NML:-$PROJECT/FavneChild1/FavneChild1_run.nml}"
RAW_INPUT="${RAW_INPUT:-$PROJECT/FavneChild1/input}"

rm -rf "$PROJECT/FavneChild1-hot"
mkdir -p "$PROJECT/FavneChild1-hot/output"
cp "$PROD_NML" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
ln -s "$RAW_INPUT" "$PROJECT/FavneChild1-hot/input"

# 0) the user's Oct-12 namelist ships with forcing OFF; the production run
#    (and the reference results) use wind COARE + calculated heat flux +
#    plume calculate ON. Idempotent: no-op if already T.
sed -i "s|WIND_ON = F,|WIND_ON = T,|; s|HEATING_CALCULATE_ON = F,|HEATING_CALCULATE_ON = T,|; s|PLUME_CALCULATE_ON         =  F,|PLUME_CALCULATE_ON         =  T,|" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"

# 1) first &NML_STARTUP block -> hot start from the user's restart file
awk '
  { t=$0; gsub(/^[ \t]+|[ \t]+$/,"",t)
    if (!done && t=="&NML_STARTUP") {
      print " &NML_STARTUP"
      print "  STARTUP_TYPE    = \x27hotstart\x27,"
      print "  STARTUP_FILE    = \x27FavneChild1_restart_0723.nc\x27,"
      print "  STARTUP_UV_TYPE = \x27set values\x27,"
      print "  STARTUP_TURB_TYPE = \x27set values\x27,"
      print "  STARTUP_TS_TYPE = \x27set values\x27,"
      print "  STARTUP_T_VALS  = 0.0,"
      print "  STARTUP_S_VALS  = 34.5,"
      print "  STARTUP_U_VALS  = 0.00000,"
      print "  STARTUP_V_VALS  = 0.00000,"
      print "  STARTUP_DMAX    = 0.00000"
      inblk=1; done=1; next }
    if (inblk) { if (t=="/") { inblk=0; print "  /" }; next }
    print }' "$PROJECT/FavneChild1-hot/FavneChild1_run.nml" > /tmp/nml.$$$$ && mv /tmp/nml.$$$$ "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"

# 2) 2 simulated hours (restart at 2025-07-23 01:50 -> END_DATE 02:00)
sed -i "s|END_DATE        = '2025-07-30 00:00:00'|END_DATE        = '2025-07-23 02:00:00'|" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"

# 3) outputs inside the case directory
sed -i "s|OUTPUT_DIR = .*|OUTPUT_DIR = '$PROJECT/FavneChild1-hot/output'|" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"

# verification
grep -q "STARTUP_TYPE    = 'hotstart'" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
grep -q "END_DATE        = '2025-07-23 02:00:00'" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
grep -q "OUTPUT_DIR = '$PROJECT/FavneChild1-hot/output'" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
grep -q "WIND_ON = T" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
grep -q "HEATING_CALCULATE_ON = T" "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
grep -q "PLUME_CALCULATE_ON         =  T," "$PROJECT/FavneChild1-hot/FavneChild1_run.nml"
echo "READY: $PROJECT/FavneChild1-hot (hot start, 2 h simulated, wind + heat flux on)"
