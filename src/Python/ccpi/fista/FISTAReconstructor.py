# -*- coding: utf-8 -*-
###############################################################################
#This work is part of the Core Imaging Library developed by
#Visual Analytics and Imaging System Group of the Science Technology
#Facilities Council, STFC
#
#Copyright 2017 Edoardo Pasca, Srikanth Nagella
#Copyright 2017 Daniil Kazantsev
#
#Licensed under the Apache License, Version 2.0 (the "License");
#you may not use this file except in compliance with the License.
#You may obtain a copy of the License at
#http://www.apache.org/licenses/LICENSE-2.0
#Unless required by applicable law or agreed to in writing, software
#distributed under the License is distributed on an "AS IS" BASIS,
#WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
#See the License for the specific language governing permissions and
#limitations under the License.
###############################################################################



import numpy
#from ccpi.reconstruction.parallelbeam import alg

#from ccpi.imaging.Regularizer import Regularizer
from enum import Enum

import astra

   
    
class FISTAReconstructor():
    '''FISTA-based reconstruction algorithm using ASTRA-toolbox
    
    '''
    # <<<< FISTA-based reconstruction algorithm using ASTRA-toolbox >>>>
    # ___Input___:
    # params.[] file:
    #       - .proj_geom (geometry of the projector) [required]
    #       - .vol_geom (geometry of the reconstructed object) [required]
    #       - .sino (vectorized in 2D or 3D sinogram) [required]
    #       - .iterFISTA (iterations for the main loop, default 40)
    #       - .L_const (Lipschitz constant, default Power method)                                                                                                    )
    #       - .X_ideal (ideal image, if given)
    #       - .weights (statisitcal weights, size of the sinogram)
    #       - .ROI (Region-of-interest, only if X_ideal is given)
    #       - .initialize (a 'warm start' using SIRT method from ASTRA)
    #----------------Regularization choices------------------------
    #       - .Regul_Lambda_FGPTV (FGP-TV regularization parameter)
    #       - .Regul_Lambda_SBTV (SplitBregman-TV regularization parameter)
    #       - .Regul_Lambda_TVLLT (Higher order SB-LLT regularization parameter)
    #       - .Regul_tol (tolerance to terminate regul iterations, default 1.0e-04)
    #       - .Regul_Iterations (iterations for the selected penalty, default 25)
    #       - .Regul_tauLLT (time step parameter for LLT term)
    #       - .Ring_LambdaR_L1 (regularization parameter for L1-ring minimization, if lambdaR_L1 > 0 then switch on ring removal)
    #       - .Ring_Alpha (larger values can accelerate convergence but check stability, default 1)
    #----------------Visualization parameters------------------------
    #       - .show (visualize reconstruction 1/0, (0 default))
    #       - .maxvalplot (maximum value to use for imshow[0 maxvalplot])
    #       - .slice (for 3D volumes - slice number to imshow)
    # ___Output___:
    # 1. X - reconstructed image/volume
    # 2. output - a structure with
    #    - .Resid_error - residual error (if X_ideal is given)
    #    - .objective: value of the objective function
    #    - .L_const: Lipshitz constant to avoid recalculations
    
    # References:
    # 1. "A Fast Iterative Shrinkage-Thresholding Algorithm for Linear Inverse
    # Problems" by A. Beck and M Teboulle
    # 2. "Ring artifacts correction in compressed sensing..." by P. Paleo
    # 3. "A novel tomographic reconstruction method based on the robust
    # Student's t function for suppressing data outliers" D. Kazantsev et.al.
    # D. Kazantsev, 2016-17
    def __init__(self, projector_geometry, output_geometry, input_sinogram, **kwargs):
        # handle parmeters:
        # obligatory parameters
        self.pars = dict()
        self.pars['projector_geometry'] = projector_geometry
        self.pars['output_geometry'] = output_geometry
        self.pars['input_sinogram'] = input_sinogram
        detectors, nangles, sliceZ = numpy.shape(input_sinogram)
        self.pars['detectors'] = detectors
        self.pars['number_og_angles'] = nangles
        self.pars['SlicesZ'] = sliceZ

        print (self.pars)
        # handle optional input parameters (at instantiation)
        
        # Accepted input keywords
        kw = ('number_of_iterations', 
              'Lipschitz_constant' , 
              'ideal_image' ,
              'weights' , 
              'region_of_interest' , 
              'initialize' , 
              'regularizer' , 
              'ring_lambda_R_L1',
              'ring_alpha')
        
        # handle keyworded parameters
        if kwargs is not None:
            for key, value in kwargs.items():
                if key in kw:
                    #print("{0} = {1}".format(key, value))                        
                    self.pars[key] = value
                    
        # set the default values for the parameters if not set
        if 'number_of_iterations' in kwargs.keys():
            self.pars['number_of_iterations'] = kwargs['number_of_iterations']
        else:
            self.pars['number_of_iterations'] = 40
        if 'weights' in kwargs.keys():
            self.pars['weights'] = kwargs['weights']
        else:
            self.pars['weights'] = numpy.ones(numpy.shape(self.pars['input_sinogram']))
        if 'Lipschitz_constant' in kwargs.keys():
            self.pars['Lipschitz_constant'] = kwargs['Lipschitz_constant']
        else:
            self.pars['Lipschitz_constant'] = self.calculateLipschitzConstantWithPowerMethod()
        
        if not 'ideal_image' in kwargs.keys():
            self.pars['ideal_image'] = None
        
        if not 'region_of_interest'in kwargs.keys() :
            if self.pars['ideal_image'] == None:
                pass
            else:
                self.pars['region_of_interest'] = numpy.nonzero(self.pars['ideal_image']>0.0)
            
        if not 'regularizer' in kwargs.keys() :
            self.pars['regularizer'] = None
        else:
            # the regularizer must be a correctly instantiated object
            if not 'ring_lambda_R_L1' in kwargs.keys():
                self.pars['ring_lambda_R_L1'] = 0
            if not 'ring_alpha' in kwargs.keys():
                self.pars['ring_alpha'] = 1
        
            
            
        
    def calculateLipschitzConstantWithPowerMethod(self):
        ''' using Power method (PM) to establish L constant'''
        
        N = self.pars['output_geometry']['GridColCount']
        proj_geom = self.pars['projector_geometry']
        vol_geom = self.pars['output_geometry']
        weights = self.pars['weights']
        SlicesZ = self.pars['SlicesZ']
        
            
                               
        if (proj_geom['type'] == 'parallel') or (proj_geom['type'] == 'parallel3d'):
            #% for parallel geometry we can do just one slice
            #print('Calculating Lipshitz constant for parallel beam geometry...')
            niter = 5;# % number of iteration for the PM
            #N = params.vol_geom.GridColCount;
            #x1 = rand(N,N,1);
            x1 = numpy.random.rand(1,N,N)
            #sqweight = sqrt(weights(:,:,1));
            sqweight = numpy.sqrt(weights[0])
            proj_geomT = proj_geom.copy();
            proj_geomT['DetectorRowCount'] = 1;
            vol_geomT = vol_geom.copy();
            vol_geomT['GridSliceCount'] = 1;
            
            #[sino_id, y] = astra_create_sino3d_cuda(x1, proj_geomT, vol_geomT);
            
            
            for i in range(niter):
            #        [id,x1] = astra_create_backprojection3d_cuda(sqweight.*y, proj_geomT, vol_geomT);
            #            s = norm(x1(:));
            #            x1 = x1/s;
            #            [sino_id, y] = astra_create_sino3d_cuda(x1, proj_geomT, vol_geomT);
            #            y = sqweight.*y;
            #            astra_mex_data3d('delete', sino_id);
            #            astra_mex_data3d('delete', id);
                #print ("iteration {0}".format(i))
                                
                sino_id, y = astra.creators.create_sino3d_gpu(x1,
                                                          proj_geomT,
                                                          vol_geomT)
                
                y = (sqweight * y).copy() # element wise multiplication
                
                #b=fig.add_subplot(2,1,2)
                #imgplot = plt.imshow(x1[0])
                #plt.show()
                
                #astra_mex_data3d('delete', sino_id);
                astra.matlab.data3d('delete', sino_id)
                del x1
                    
                idx,x1 = astra.creators.create_backprojection3d_gpu((sqweight*y).copy(), 
                                                                    proj_geomT,
                                                                    vol_geomT)
                del y
                
                                                                    
                s = numpy.linalg.norm(x1)
                ### this line?
                x1 = (x1/s).copy();
                
            #        ### this line?
            #        sino_id, y = astra.creators.create_sino3d_gpu(x1, 
            #                                                      proj_geomT, 
            #                                                      vol_geomT);
            #        y = sqweight * y;
                astra.matlab.data3d('delete', sino_id);
                astra.matlab.data3d('delete', idx)
                print ("iteration {0} s= {1}".format(i,s))
                
            #end
            del proj_geomT
            del vol_geomT
            #plt.show()
        else:
            #% divergen beam geometry
            print('Calculating Lipshitz constant for divergen beam geometry...')
            niter = 8; #% number of iteration for PM
            x1 = numpy.random.rand(SlicesZ , N , N);
            #sqweight = sqrt(weights);
            sqweight = numpy.sqrt(weights[0])
            
            sino_id, y = astra.creators.create_sino3d_gpu(x1, proj_geom, vol_geom);
            y = sqweight*y;
            #astra_mex_data3d('delete', sino_id);
            astra.matlab.data3d('delete', sino_id);
            
            for i in range(niter):
                #[id,x1] = astra_create_backprojection3d_cuda(sqweight.*y, proj_geom, vol_geom);
                idx,x1 = astra.creators.create_backprojection3d_gpu(sqweight*y, 
                                                                    proj_geom, 
                                                                    vol_geom)
                s = numpy.linalg.norm(x1)
                ### this line?
                x1 = x1/s;
                ### this line?
                #[sino_id, y] = astra_create_sino3d_gpu(x1, proj_geom, vol_geom);
                sino_id, y = astra.creators.create_sino3d_gpu(x1, 
                                                              proj_geom, 
                                                              vol_geom);
                
                y = sqweight*y;
                #astra_mex_data3d('delete', sino_id);
                #astra_mex_data3d('delete', id);
                astra.matlab.data3d('delete', sino_id);
                astra.matlab.data3d('delete', idx);
            #end
            #clear x1
            del x1

        
        return s
    
    
    def setRegularizer(self, regularizer):
        if regularizer is not None:
            self.pars['regularizer'] = regularizer
        
    
    


def getEntry(location, nx):
    for item in nx[location].keys():
        print (item)


print ("Loading Data")

##fname = "D:\\Documents\\Dataset\\IMAT\\20170419_crabtomo\\crabtomo\\Sample\\IMAT00005153_crabstomo_Sample_000.tif"
####ind = [i * 1049 for i in range(360)]
#### use only 360 images
##images = 200
##ind = [int(i * 1049 / images) for i in range(images)]
##stack_image = dxchange.reader.read_tiff_stack(fname, ind, digit=None, slc=None)

#fname = "D:\\Documents\\Dataset\\CGLS\\24737_fd.nxs"
#fname = "C:\\Users\\ofn77899\\Documents\\CCPi\\CGLS\\24737_fd_2.nxs"
##fname = "/home/ofn77899/Reconstruction/CCPi-FISTA_Reconstruction/data/dendr.h5"
##nx = h5py.File(fname, "r")
##
### the data are stored in a particular location in the hdf5
##for item in nx['entry1/tomo_entry/data'].keys():
##    print (item)
##
##data = nx.get('entry1/tomo_entry/data/rotation_angle')
##angles = numpy.zeros(data.shape)
##data.read_direct(angles)
##print (angles)
### angles should be in degrees
##
##data = nx.get('entry1/tomo_entry/data/data')
##stack = numpy.zeros(data.shape)
##data.read_direct(stack)
##print (data.shape)
##
##print ("Data Loaded")
##
##
### Normalize
##data = nx.get('entry1/tomo_entry/instrument/detector/image_key')
##itype = numpy.zeros(data.shape)
##data.read_direct(itype)
### 2 is dark field
##darks = [stack[i] for i in range(len(itype)) if itype[i] == 2 ]
##dark = darks[0]
##for i in range(1, len(darks)):
##    dark += darks[i]
##dark = dark / len(darks)
###dark[0][0] = dark[0][1]
##
### 1 is flat field
##flats = [stack[i] for i in range(len(itype)) if itype[i] == 1 ]
##flat = flats[0]
##for i in range(1, len(flats)):
##    flat += flats[i]
##flat = flat / len(flats)
###flat[0][0] = dark[0][1]
##
##
### 0 is projection data
##proj = [stack[i] for i in range(len(itype)) if itype[i] == 0 ]
##angle_proj = [angles[i] for i in range(len(itype)) if itype[i] == 0 ]
##angle_proj = numpy.asarray (angle_proj)
##angle_proj = angle_proj.astype(numpy.float32)
##
### normalized data are
### norm = (projection - dark)/(flat-dark)
##
##def normalize(projection, dark, flat, def_val=0.1):
##    a = (projection - dark)
##    b = (flat-dark)
##    with numpy.errstate(divide='ignore', invalid='ignore'):
##        c = numpy.true_divide( a, b )
##        c[ ~ numpy.isfinite( c )] = def_val  # set to not zero if 0/0 
##    return c
##    
##
##norm = [normalize(projection, dark, flat) for projection in proj]
##norm = numpy.asarray (norm)
##norm = norm.astype(numpy.float32)


##niterations = 15
##threads = 3
##
##img_cgls = alg.cgls(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads, False)
##img_mlem = alg.mlem(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads, False)
##img_sirt = alg.sirt(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads, False)
##
##iteration_values = numpy.zeros((niterations,))
##img_cgls_conv = alg.cgls_conv(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads,
##                              iteration_values, False)
##print ("iteration values %s" % str(iteration_values))
##
##iteration_values = numpy.zeros((niterations,))
##img_cgls_tikhonov = alg.cgls_tikhonov(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads,
##                                      numpy.double(1e-5), iteration_values , False)
##print ("iteration values %s" % str(iteration_values))
##iteration_values = numpy.zeros((niterations,))
##img_cgls_TVreg = alg.cgls_TVreg(norm, angle_proj, numpy.double(86.2), 1 , niterations, threads,
##                                      numpy.double(1e-5), iteration_values , False)
##print ("iteration values %s" % str(iteration_values))
##
##
####numpy.save("cgls_recon.npy", img_data)
##import matplotlib.pyplot as plt
##fig, ax = plt.subplots(1,6,sharey=True)
##ax[0].imshow(img_cgls[80])
##ax[0].axis('off')  # clear x- and y-axes
##ax[1].imshow(img_sirt[80])
##ax[1].axis('off')  # clear x- and y-axes
##ax[2].imshow(img_mlem[80])
##ax[2].axis('off')  # clear x- and y-axesplt.show()
##ax[3].imshow(img_cgls_conv[80])
##ax[3].axis('off')  # clear x- and y-axesplt.show()
##ax[4].imshow(img_cgls_tikhonov[80])
##ax[4].axis('off')  # clear x- and y-axesplt.show()
##ax[5].imshow(img_cgls_TVreg[80])
##ax[5].axis('off')  # clear x- and y-axesplt.show()
##
##
##plt.show()
##
