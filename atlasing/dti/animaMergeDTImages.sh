#!/bin/bash

cd ${1}
prefixDTIBase=${2}
prefixDTI=${3}
k=${4}
nimages=${5}
refDTI=${6}

ncores=${7}

# test if all images are here

nimTest=$nimages
if [ $k -eq 1 ]; then
	let nimTest=nimTest-1
fi

numData=`ls -l residualDir/${prefixDTI}_*_flag | wc -l`
while (($numData < $nimTest))
do
	echo Missing data $numData $nimTest
	sleep 600
	numData=`ls -l residualDir/${prefixDTI}_*_flag | wc -l`
done

# if ok proceed
if [ $k -eq 1 ]; then
	cp ${prefixDTIBase}/${prefixDTI}_1.nii.gz tempDir/${prefixDTI}_1_bal.nii.gz 
	
	animaComputeDTIScalarMaps -i tempDir/${prefixDTI}_1_bal.nii.gz -a tempDir/${prefixDTI}_1_bal_ADC.nii.gz -p ${ncores}
	animaThrImage -i tempDir/${prefixDTI}_1_bal_ADC.nii.gz -t 0 -o tempDir/${prefixDTI}_1_tensMask.nii.gz
	\rm -f tempDir/${prefixDTI}_1_bal_ADC.nii.gz
	
	animaCreateImage -o residualDir/${prefixDTI}_1_bal_tr.nii.gz -b 0 -g ${prefixDTIBase}/${prefixDTI}_1.nii.gz -v 3
fi

rm -f refDTIs.txt masksTens.txt sum.txt
for ((a=1;a<=$nimages;a++))
do
	echo tempDir/${prefixDTI}_${a}_bal.nii.gz >> refDTIs.txt
	echo tempDir/${prefixDTI}_${a}_tensMask.nii.gz >> masksTens.txt
	echo residualDir/${prefixDTI}_${a}_bal_tr.nii.gz >> sum.txt
done

animaAverageImages -i refDTIs.txt -o tempDir/DTIAverageDiv.nii.gz -m masksTens.txt
animaAverageImages -i masksTens.txt -o tempDir/meanMasks_${k}.nii.gz
animaThrImage -i tempDir/meanMasks_${k}.nii.gz -o tempDir/thrMasks_${k}.nii.gz -t 0.25
animaMaskImage -i tempDir/DTIAverageDiv.nii.gz -m tempDir/thrMasks_${k}.nii.gz -o tempDir/DTIAverageDiv.nii.gz

animaAverageImages -i sum.txt -o tempDir/sum.nii.gz

animaTransformSerieXmlGenerator -i tempDir/sum.nii.gz -I 1 -o tempDir/trsf.xml

for ((a=1;${a}<=$nimages;a++))
do
	\rm -f residualDir/${prefixDTI}_${a}_bal_tr.nii.gz
done

# the averaged transform is used in the intensity averaged image

animaTensorApplyTransformSerie -i tempDir/DTIAverageDiv.nii.gz -o averageDTI${k}.nii.gz -t tempDir/trsf.xml -g ${refDTI}.nii.gz -p ${ncores}
animaComputeDTIScalarMaps -i averageDTI${k}.nii.gz -a averageDTI${k}_ADC.nii.gz -p ${ncores}

if [ -e averageDTI${k}.nii.gz ]; then
	touch it_${k}_done
	let t=k+1
	if [ -e tmpRun_${t} ]; then
		\rm -f tmpRun_${k} reg-DTI-${k}-* residualDir/* tempDir/*
	fi
fi
