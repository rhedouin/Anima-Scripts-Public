#!/bin/bash

cd ${1}

prefixBase=${2}
prefix=${3}
k=${4}
nimages=${5}
ref=${6}
ncores=${7}

# test if all images are here
nimTest=$nimages
if [ $k -eq 1 ]; then
	let nimTest=nimTest-1
fi

numData=`ls -l residualDir/${prefix}_*_flag | wc -l`
while (($numData < $nimTest))
do
	echo Missing data $numData $nimTest
	sleep 600
	numData=`ls -l residualDir/${prefix}_*_flag | wc -l`
done

# if ok proceed

if [ $k -eq 1 ]; then
	cp ${prefixBase}/${prefix}_1.nii.gz tempDir/${prefix}_1_bal.nii.gz 

	if [ -e Masks/Mask_1.nii.gz ]; then
		cp Masks/Mask_1.nii.gz tempDir/${prefix}_1_mask.nii.gz
	fi

	animaCreateImage -o residualDir/${prefix}_1_bal_tr.nii.gz -b 0 -g ${prefixBase}/${prefix}_1.nii.gz -v 3
fi

rm -f refIms.txt masksIms.txt sum.txt
for ((a=1;${a}<=${nimages};a++))
do
	echo tempDir/${prefix}_${a}_bal.nii.gz >> refIms.txt

	if [ -e Masks/Mask_1.nii.gz ]; then
		echo tempDir/${prefix}_${a}_mask.nii.gz >> masksIms.txt
	fi

	echo residualDir/${prefix}_${a}_bal_tr.nii.gz >> sum.txt
done

if [ -e Masks/Mask_1.nii.gz ]; then
	animaAverageImages -i refIms.txt -o tempDir/IntensityAverageDiv.nii.gz -m masksIms.txt
else
	animaAverageImages -i refIms.txt -o tempDir/IntensityAverageDiv.nii.gz
fi

animaAverageImages -i sum.txt -o tempDir/sum.nii.gz

animaTransformSerieXmlGenerator -i tempDir/sum.nii.gz -I 1 -o tempDir/trsf.xml

for ((a=1;${a}<=$nimages;a++))
do
	\rm -f residualDir/${prefix}_${a}_bal_tr.nii.gz
done

# the averaged transform is used in the intensity averaged image
animaApplyTransformSerie -i tempDir/IntensityAverageDiv.nii.gz -o averageForm${k}.nii.gz -t tempDir/trsf.xml -g ${ref}.nii.gz -p ${ncores}

if [ -e averageForm${k}.nii.gz ]; then
	touch it_${k}_done
	let t=${k}+1
	if [ -e tmpRun_${t} ]; then
		\rm -f tmpRun_${k} residualDir/* tempDir/*
	fi
fi

