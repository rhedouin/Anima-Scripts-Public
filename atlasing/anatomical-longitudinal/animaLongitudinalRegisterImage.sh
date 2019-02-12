#!/bin/bash

cd ${1}
ref=${2}
prefixBase=${3}
basePrefBase=`dirname ${3}`
prefix=${4}
numIm=${5}
bchOrder=${6}
ncores=${7}

# Rigid / affine registration

animaPyramidalBMRegistration -r ${ref} -m ${prefixBase}/${prefix}_${numIm}.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_aff.nii.gz -O ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.txt --out-rigid ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr_nearestRigid.txt --ot 2 -p 3 -l 0 -I 2 -T ${ncores} --sym-reg 2

# Non-Rigid registration

# For basic atlases
animaDenseSVFBMRegistration -r ${ref} -m ${basePrefBase}/tempDir/${prefix}_${numIm}_aff.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_bal.nii.gz -O ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz --sr 1 --es 3 --fs 2 -T ${ncores} --sym-reg 2 --metric 1

animaTransformSerieXmlGenerator -i ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.txt -i ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz -o ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.xml

animaLinearTransformArithmetic -i ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr_nearestRigid.txt -M -1 -c ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.txt -o ${basePrefBase}/tempDir/${prefix}_${numIm}_invNRoaff_tr.txt

animaLinearTransformToSVF -i ${basePrefBase}/tempDir/${prefix}_${numIm}_invNRoaff_tr.txt -o ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.nii.gz -g ${ref}

# BCH here:
animaDenseTransformArithmetic -i ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.nii.gz -c ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz -b ${bchOrder} -o ${basePrefBase}/tempDir/${prefix}_${numIm}_compo_tr.nii.gz

ln -s ${PWD}/${basePrefBase}/tempDir/${prefix}_${numIm}_compo_tr.nii.gz ${basePrefBase}/residualDir/${prefix}_${numIm}_compo_tr.nii.gz

if [ -e ${basePrefBase}/tempDir/${prefix}_${numIm}_compo_tr.nii.gz ]; then
    touch ${basePrefBase}/residualDir/${prefix}_${numIm}_flag
fi

rm ${basePrefBase}/tempDir/${prefix}_${numIm}_bal_tr.nii.gz ${basePrefBase}/tempDir/${prefix}_${numIm}_aff_tr.nii.gz