#!/usr/bin/python
# Warning: works only on unix-like systems, not windows where "python animaComputeLongitudinalAtlasWeights.py ..." has to be run

import argparse
import os
import sys
import numpy as np

from read_ITK_transform import readITKtransform # this comes from https://gist.github.com/haehn/5614966

if sys.version_info[0] > 2:
    import configparser as ConfParser
else:
    import ConfigParser as ConfParser

configFilePath = os.path.expanduser("~") + "/.anima/config.txt"
if not os.path.exists(configFilePath):
    print('Please create a configuration file for Anima python scripts. Refer to the README')
    quit()

configParser = ConfParser.RawConfigParser()
configParser.read(configFilePath)

animaDir = configParser.get("anima-scripts", 'anima')
animaScriptsDir = configParser.get("anima-scripts", 'anima-scripts-public-root')

# Argument parsing
parser = argparse.ArgumentParser(description="Extract scaling factors from anisotropic similarity transformations")

parser.add_argument('-i', '--image-file', required=True, type=str, help='list of images (in txt file)')
parser.add_argument('-o', '--out-dir', required=True, type=str, help='output directory')
parser.add_argument('-u', '--scalDir-file', type=str, help='directions of scaling (in itk txt affine transform) (real coordinates)')
parser.add_argument('-c', '--num-cores', type=int, default=8, help='number of cores to run on (default: 8)')

parser.add_argument('-m', '--mask-file', type=str, default="", help='list of masks of ROIs (in txt file) associated to the reference image')
parser.add_argument('-r', '--root-image-file', type=str, default="", help='list of images (in txt file) for renormalization - relative scaling factors will be divided by the average of the scaling factors of those root images')

args = parser.parse_args()

if args.mask_file != "":
    with open(args.mask_file) as f:
        masks = f.read().splitlines()
else:
    masks=" "    

if not os.path.exists(args.out_dir):
    os.makedirs(args.out_dir)

with open(args.scalDir_file) as f:
    us = f.read().splitlines()

for k in [1,2]:
    
    # creating folder tree
    
    if args.root_image_file == "":
        sroot=np.ones((len(masks),3))
        continue
    if k==1:
        outDir=os.path.join(args.out_dir, "root")
        with open(args.root_image_file) as f:
            images = f.read().splitlines()
        sroot=np.zeros((len(masks),3))
    else:
        outDir=args.out_dir
        with open(args.image_file) as f:
            images = f.read().splitlines()
  
    for i in range(1, len(masks)+1):
        fout = open(os.path.join(outDir, "scalingFactors_ROI_"+str(i)+".csv"), 'w')
        fout.write("subject, dir1_rel, dir2_rel, dir3_rel")
        if k==1:
            fout.write("\n")
        else:
            fout.write(", dir1_abs, dir2_abs, dir3_abs\n")                
        if len(us)>1:
            u=readITKtransform(us[i-1])[0:3,0:3]
        else:
            u=readITKtransform(us[0])[0:3,0:3]
        for j in range(0, len(images)):
            image=images[j]
            sub = os.path.splitext(image)[0]
            if os.path.splitext(image)[1] == '.gz' :
                sub = os.path.splitext(sub)[0]
            sub=os.path.basename(sub)
            t=readITKtransform(os.path.join(outDir, "anisotropicSimilarity", "ROI_"+str(i),sub + "_anisotropSim_tr.txt"))[0:3,0:3]
            v, d, wT = np.linalg.svd(t)
            ruT = np.dot(np.linalg.det(v)*v, np.linalg.det(wT)*wT)
            r=np.dot(ruT,u)
            s=np.dot(np.dot(np.transpose(r),t),u)
            fout.write(sub+", "+str(s[0,0])+", "+str(s[1,1])+", "+str(s[2,2]))
            if k==1:
                fout.write("\n")
                sroot[i-1,:]=sroot[i-1,:]+np.diag(s)
            else:
                fout.write(", "+str(s[0,0]/sroot[i-1,0])+", "+str(s[1,1]/sroot[i-1,1])+", "+str(s[2,2]/sroot[i-1,2])+"\n")
        fout.close()
    if k==1:
        sroot=sroot/len(images)
            

