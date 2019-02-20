#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
This demo scripts support the following publication: 
"CCPi-Regularisation Toolkit for computed tomographic image reconstruction with 
proximal splitting algorithms" by Daniil Kazantsev, Edoardo Pasca, Mark Basham, 
Martin J. Turner, Philip J. Withers and Alun Ashton; Software X, 2019
____________________________________________________________________________
* Reads data which is previously generated by TomoPhantom software (Zenodo link)
* Reconstruct using optimised regularisation parameters (see Demo_SimulData_ParOptimis_SX.py)
____________________________________________________________________________
>>>>> Dependencies: <<<<<
1. ASTRA toolbox: conda install -c astra-toolbox astra-toolbox
2. TomoRec: conda install -c dkazanc tomorec
or install from https://github.com/dkazanc/TomoRec

@author: Daniil Kazantsev, e:mail daniil.kazantsev@diamond.ac.uk
GPLv3 license (ASTRA toolbox)
"""
import timeit
import matplotlib.pyplot as plt
import numpy as np
import h5py
from tomophantom.supp.qualitymetrics import QualityTools

# loading data 
h5f = h5py.File('data/TomoSim_data1550671417.h5','r')
phantom = h5f['phantom'][:]
projdata_norm = h5f['projdata_norm'][:]
proj_angles = h5f['proj_angles'][:]
h5f.close()


sliceSel = 128
#plt.gray()
plt.figure() 
plt.subplot(131)
plt.imshow(phantom[sliceSel,:,:],vmin=0, vmax=1)
plt.title('3D Phantom, axial view')

plt.subplot(132)
plt.imshow(phantom[:,sliceSel,:],vmin=0, vmax=1)
plt.title('3D Phantom, coronal view')

plt.subplot(133)
plt.imshow(phantom[:,:,sliceSel],vmin=0, vmax=1)
plt.title('3D Phantom, sagittal view')
plt.show()

intens_max = 240
plt.figure() 
plt.subplot(131)
plt.imshow(projdata_norm[:,sliceSel,:],vmin=0, vmax=intens_max)
plt.title('2D Projection (erroneous)')
plt.subplot(132)
plt.imshow(projdata_norm[sliceSel,:,:],vmin=0, vmax=intens_max)
plt.title('Sinogram view')
plt.subplot(133)
plt.imshow(projdata_norm[:,:,sliceSel],vmin=0, vmax=intens_max)
plt.title('Tangentogram view')
plt.show()
#%%
# initialise TomoRec DIRECT reconstruction class ONCE
from tomorec.methodsDIR import RecToolsDIR
RectoolsDIR = RecToolsDIR(DetectorsDimH = Horiz_det,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = Vert_det,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    device = 'gpu')
#%%
print ("Reconstruction using FBP from TomoRec")
recNumerical= RectoolsDIR.FBP(projData3D_norm) # FBP reconstruction

sliceSel = int(0.5*N_size)
max_val = 1
#plt.gray()
plt.figure() 
plt.subplot(131)
plt.imshow(recNumerical[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, axial view')

plt.subplot(132)
plt.imshow(recNumerical[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, coronal view')

plt.subplot(133)
plt.imshow(recNumerical[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D Reconstruction, sagittal view')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_tm, recNumerical)
RMSE_fbp = Qtools.rmse()
print("Root Mean Square Error for FBP is {}".format(RMSE_fbp))
#%%
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
print ("Reconstructing with ADMM method using TomoRec software")
print ("%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%%")
# initialise TomoRec ITERATIVE reconstruction class ONCE
from tomorec.methodsIR import RecToolsIR
RectoolsIR = RecToolsIR(DetectorsDimH = Horiz_det,  # DetectorsDimH # detector dimension (horizontal)
                    DetectorsDimV = Vert_det,  # DetectorsDimV # detector dimension (vertical) for 3D case only
                    AnglesVec = angles_rad, # array of angles in radians
                    ObjSize = N_size, # a scalar to define reconstructed object dimensions
                    datafidelity='LS',# data fidelity, choose LS, PWLS (wip), GH (wip), Student (wip)
                    nonnegativity='ENABLE', # enable nonnegativity constraint (set to 'ENABLE')
                    OS_number = None, # the number of subsets, NONE/(or > 1) ~ classical / ordered subsets
                    tolerance = 1e-08, # tolerance to stop outer iterations earlier
                    device='gpu')
#%%
# Run ADMM reconstrucion algorithm with 3D regularisation
RecADMM_reg_fgptv = RectoolsIR.ADMM(projData3D_norm,
                              rho_const = 2000.0, \
                              iterationsADMM = 30, \
                              regularisation = 'FGP_TV', \
                              regularisation_parameter = 0.003,\
                              regularisation_iterations = 250)

sliceSel = int(0.5*N_size)
max_val = 1
plt.figure() 
plt.subplot(131)
plt.imshow(RecADMM_reg_fgptv[sliceSel,:,:],vmin=0, vmax=max_val)
plt.title('3D ADMM-FGP-TV Reconstruction, axial view')

plt.subplot(132)
plt.imshow(RecADMM_reg_fgptv[:,sliceSel,:],vmin=0, vmax=max_val)
plt.title('3D ADMM-FGP-TV Reconstruction, coronal view')

plt.subplot(133)
plt.imshow(RecADMM_reg_fgptv[:,:,sliceSel],vmin=0, vmax=max_val)
plt.title('3D ADMM-FGP-TV Reconstruction, sagittal view')
plt.show()

# calculate errors 
Qtools = QualityTools(phantom_tm, RecADMM_reg_fgptv)
RMSE_admm_fgp = Qtools.rmse()
print("Root Mean Square Error for ADMM-FGP-TV is {}".format(RMSE_admm_fgp))

#%%