
TOPDIR        = /opt/fvcom-src/src
INSTALLDIR    = $(TOPDIR)/libs/install

DEF_FLAGS     = -P -traditional

LIBDIR        = -L$(INSTALLDIR)/lib
INCDIR        = -I$(INSTALLDIR)/include

DTLIBS        = -ljulian
DTINCS        =

IOLIBS        = $(shell nf-config --flibs)
IOINCS        = $(shell nf-config --fflags)

FLAG_1   = -DDOUBLE_PRECISION
FLAG_2   = -DSPHERICAL
FLAG_4   = -DMULTIPROCESSOR
FLAG_8   = -DLIMITED_NO
FLAG_9   = -DSEMI_IMPLICIT
FLAG_10  = -DGCN
FLAG_15  = -DMPDATA
FLAG_27  = -DHEATING_CALCULATED
FLAG_44  = -DTVD
FLAG_61  = -DPLUME
FLAG_611 = -DPLUME_CALCULATED

FLAG_411 = -DMETIS_5
PARTINCS = -I/usr/include
PARTLIBS = -lmetis -lm

PETSC_DIR ?= /usr
FVCOM_PETSC_REQUIRED_FLAGS := -DDATA_ASSIM -DSEMI_IMPLICIT -DRRKF -DENKF -DNH -DWAVE_OFFLINE
FVCOM_SELECTED_PETSC_FLAGS := $(filter $(FVCOM_PETSC_REQUIRED_FLAGS),$(FLAG_7) $(FLAG_9) $(FLAG_23) $(FLAG_30) $(FLAG_37))
ifneq ($(strip $(FVCOM_SELECTED_PETSC_FLAGS)),)
  ifeq ($(wildcard $(PETSC_DIR)/lib/petsc/conf/variables),)
    $(error FVCOM options $(FVCOM_SELECTED_PETSC_FLAGS) require PETSc, but PETSC_DIR=$(PETSC_DIR) has no lib/petsc/conf/variables)
  endif
  FLAG_41 = -DPETSC_C
  include $(PETSC_DIR)/lib/petsc/conf/variables
endif

COMPILER  = -DGFORTRAN
CC        = mpicc
CXX       = mpicxx
CFLAGS    = -O3 -fstack-clash-protection
FC        = mpif90
DEBFLGS   = -cpp
OPT       = -O3 -g -fallow-argument-mismatch -ffree-line-length-none -ffixed-line-length-none -fstack-clash-protection
CPP       = /usr/bin/cpp

CPPFLAGS  = $(DEF_FLAGS) $(COMPILER)
FFLAGS    = $(DEBFLGS) $(OPT)
MDEPFLAGS = --cpp --fext=f90 --file=-
RANLIB    = ranlib
AR        = ar rc

CPPARGS =  $(CPPFLAGS) $(DEF_FLAGS) $(FLAG_1) $(FLAG_2) \
   $(FLAG_3) $(FLAG_4) $(FLAG_5) $(FLAG_6)  \
   $(FLAG_7) $(FLAG_8) $(FLAG_9) $(FLAG_10) \
   $(FLAG_11) $(FLAG_12) $(FLAG_13) $(FLAG_14) \
   $(FLAG_15) $(FLAG_16) $(FLAG_17) $(FLAG_18) \
   $(FLAG_19) $(FLAG_20) $(FLAG_21) $(FLAG_22) \
   $(FLAG_23) $(FLAG_24) $(FLAG_25) $(FLAG_26) \
   $(FLAG_27) $(FLAG_28) $(FLAG_29) $(FLAG_30) \
   $(FLAG_31) $(FLAG_32) $(FLAG_33) $(FLAG_34) \
   $(FLAG_35) $(FLAG_36) $(FLAG_37) $(FLAG_38) \
   $(FLAG_39) $(FLAG_40) $(FLAG_41) $(FLAG_42) \
   $(FLAG_43) $(FLAG_44) $(FLAG_45) $(FLAG_80) $(FLAG_81) $(FLAG_LAM) $(FLAG_411) \
   $(FLAG_51) $(FLAG_52) $(FLAG_521) $(FLAG_61) $(FLAG_611) \
   $(FLAG_101) $(FLAG_102) $(FLAG_103) $(FLAG_104) $(FLAG_105) $(FLAG_321)\
   $(FLAG_211) $(FLAG_212) $(FLAG_213) $(FLAG_251) $(FLAG_261) $(FLAG_262)\
   $(FLAG_USE_NETCDF4) $(FLAG_USE_COMPRESSION)

LIBS  =	$(LIBDIR) $(CLIB) $(PARLIB) $(PARTLIBS) $(IOLIBS) $(DTLIBS) \
	$(MPILIB) $(GOTMLIB) $(KFLIB) $(BIOLIB) \
	$(OILIB) $(VISITLIB) $(PROJLIBS) $(PETSC_LIB)

INCS  =	$(INCDIR) $(IOINCS) $(GOTMINCS) $(BIOINCS) \
	$(VISITINCPATH) $(PROJINCS) $(DTINCS) $(PARTINCS) \
	$(PETSC_FC_INCLUDES)
