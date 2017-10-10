#!/bin/bash

cd ${1}
dtiRef=${2}
prefixDTIBase=${3}
prefixDTI=${4}
numIm=${5}
ncores=${6}

basePrefBase=`dirname ${prefixDTIBase}`

# Rigid / affine registration
animaComputeDTIScalarMaps -i ${prefixDTIBase}/${prefixDTI}_${numIm}.nii.gz -a ${prefixDTIBase}/${prefixDTI}_ADC_${numIm}.nii.gz -p ${ncores}

animaPyramidalBMRegistration -r ${dtiRef%.nii.gz}_ADC.nii.gz -m ${prefixDTIBase}/${prefixDTI}_ADC_${numIm}.nii.gz -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_rig.nii.gz -O ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_rig_tr.txt --sp 3 -s 0 --opt 1 --fr 0.01 -a 2 --at 0.8 -p 4 -l 0 -T ${ncores} --sym-reg 2

animaPyramidalBMRegistration -r ${dtiRef%.nii.gz}_ADC.nii.gz -m ${prefixDTIBase}/${prefixDTI}_ADC_${numIm}.nii.gz -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff.nii.gz -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_rig_tr.txt -O ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.txt --sp 3 -s 0 --opt 1 --ot 2 --fr 0.01 -a 2 --at 0.8 -p 4 -l 0 -T ${ncores} --sym-reg 2

# Cropping ref since acquisitions may not cover the whole brain
dtiRefCr=${dtiRef%.nii.gz}_${numIm}_c.nii.gz

animaTransformSerieXmlGenerator -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.txt -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.xml

animaCreateImage -b 1 -v 1 -g ${prefixDTIBase}/${prefixDTI}_${numIm}.nii.gz -o ${basePrefBase}/tempDir/tmpFullMask_${numIm}.nii.gz
animaApplyTransformSerie -g ${dtiRef%.nii.gz}_ADC.nii.gz -i ${basePrefBase}/tempDir/tmpFullMask_${numIm}.nii.gz -t ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.xml -o ${basePrefBase}/tempDir/tmpMask_${numIm}.nii.gz -p ${ncores}
animaMaskImage -i ${dtiRef} -m ${basePrefBase}/tempDir/tmpMask_${numIm}.nii.gz -o ${dtiRefCr}

animaTensorApplyTransformSerie -i ${prefixDTIBase}/${prefixDTI}_${numIm}.nii.gz -g ${dtiRef} -t ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.xml -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff.nii.gz -p ${ncores}

# Non-Rigid registration

# For basic atlases
animaDenseTensorSVFBMRegistration -r ${dtiRefCr} -m ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff.nii.gz -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal.nii.gz -O ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_tr.nii.gz --sp 2 -s 0.001 --opt 1 --sr 1 --fr 0.01 -a 0 -p 4 -l 0 --metric 3 -T ${ncores} --sym-reg 2

\rm -f ${dtiRefCr}

animaTransformSerieXmlGenerator -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_aff_tr.txt -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_tr.nii.gz -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_tr.xml

animaTensorApplyTransformSerie -i ${prefixDTIBase}/${prefixDTI}_${numIm}.nii.gz -t ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_tr.xml -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal.nii.gz -g ${dtiRef} -p ${ncores}

animaComputeDTIScalarMaps -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal.nii.gz -a ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_ADC.nii.gz -p ${ncores}
animaThrImage -i ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_ADC.nii.gz -t 0 -o ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_tensMask.nii.gz
\rm -f ${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_ADC.nii.gz

ln -s ${PWD}/${basePrefBase}/tempDir/${prefixDTI}_${numIm}_bal_tr.nii.gz ${basePrefBase}/residualDir/${prefixDTI}_${numIm}_bal_tr.nii.gz

if [ -e ${basePrefBase}/residualDir/${prefixDTI}_${numIm}_bal_tr.nii.gz ]; then
    touch ${basePrefBase}/residualDir/${prefixDTI}_${numIm}_flag
fi
