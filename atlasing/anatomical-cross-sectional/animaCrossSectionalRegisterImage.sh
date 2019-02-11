#!/bin/bash

cd ${1}
ref=${2}
prefixBase=${3}
basePrefBase=`dirname ${3}`
prefix=${4}
numIm=${5}
ncores=${6}

# Rigid / affine registration

animaPyramidalBMRegistration -r ${ref} -m ${prefixBase}/${prefix}_${numIm}.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_aff.nii.gz -O ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.txt --ot 2 -p 4 -l 0 -T ${ncores} --sym-reg 2

# Non-Rigid registration

# For basic atlases
animaDenseSVFBMRegistration -r ${ref} -m ${basePrefBase}/tempDir/${prefix}_${numIm}_aff.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_bal.nii.gz -O ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz --sr 1 --es 3 --fs 2 -T ${ncores} --sym-reg 2 --metric 1

animaTransformSerieXmlGenerator -i ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.txt -i ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.xml

animaApplyTransformSerie -i ${prefixBase}/${prefix}_${numIm}.nii.gz -t ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.xml -o ${basePrefBase}/tempDir/${prefix}_${numIm}_bal.nii.gz -g ${ref} -p ${ncores}

if [ -e ${basePrefBase}/Masks/Mask_${numIm}.nii.gz ]; then
	animaApplyTransformSerie -i ${basePrefBase}/Masks/Mask_${numIm}.nii.gz -t ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.xml -o ${basePrefBase}/tempDir/${prefix}_${numIm}_mask.nii.gz -n nearest -g ${ref} -p ${ncores}
fi

ln -s ${PWD}/${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz ${basePrefBase}/residualDir/${prefix}_${numIm}_bal_tr.nii.gz

if [ -e ${basePrefBase}/residualDir/${prefix}_${numIm}_bal_tr.nii.gz ]; then
    touch ${basePrefBase}/residualDir/${prefix}_${numIm}_flag
fi
