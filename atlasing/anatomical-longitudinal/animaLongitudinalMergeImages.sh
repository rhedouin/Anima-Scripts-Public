#!/bin/bash

cd ${1}

prefixBase=${2}
prefix=${3}
k=${4}
nimages=${5}
ref=${6}
ncores=${7}
weights=${8}

# test if all images are here
nimTest=${nimages}
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

if [ $k -eq 1 ]
then
    animaCreateImage -o tempDir/${prefix}_1_compo_tr.nii.gz -b 0 -g ${prefixBase}/${prefix}_1.nii.gz -v 3
fi

rm -f refIms.txt masksIms.txt sum.txt
for ((a=1;${a}<=${nimages};a++))
do
    echo tempDir/${prefix}_${a}_compo_tr.nii.gz >> sum.txt
done

if [ "${weights}" != "" ]; then
    animaAverageImages -i sum.txt -o tempDir/sum.nii.gz -w ${weights}
else
    animaAverageImages -i sum.txt -o tempDir/sum.nii.gz 
fi
animaImageArithmetic -i tempDir/sum.nii.gz -M -1 -o tempDir/sum.nii.gz 

for ((a=1;${a}<=${nimages};a++))
do
    if [[ $a -eq 1 && $k -eq 1 ]]
    then
        animaTransformSerieXmlGenerator -i tempDir/sum.nii.gz -o tempDir/trsf.xml
    else
        animaTransformSerieXmlGenerator -i tempDir/${prefix}_${a}_aff_tr_nearestRigid.txt -i tempDir/${prefix}_${a}_compo_tr.nii.gz -i tempDir/sum.nii.gz -o tempDir/trsf.xml
    fi
    animaApplyTransformSerie -i ${prefixBase}/${prefix}_${a}.nii.gz -t tempDir/trsf.xml -g ${ref}.nii.gz -o tempDir/${prefix}_${a}_at.nii.gz -p ${ncores} 

    echo tempDir/${prefix}_${a}_at.nii.gz >> refIms.txt
    if [ -e Masks/Mask_${numIm}.nii.gz ]
    then
        echo Masks/Mask_${numIm}.nii.gz >> masksIms.txt
    fi
done

if [ "${weights}" != "" ]; then
    if [ -e Masks/Mask_1.nii.gz ]; then
        animaAverageImages -i refIms.txt -o averageForm${k}.nii.gz -m masksIms.txt -w ${weights}
    else
        animaAverageImages -i refIms.txt -o averageForm${k}.nii.gz -w ${weights}
    fi
    animaAverageImages -i sum.txt -o tempDir/sum.nii.gz -w ${weights}
else
    if [ -e Masks/Mask_1.nii.gz ]; then
        animaAverageImages -i refIms.txt -o averageForm${k}.nii.gz -m masksIms.txt
    else
        animaAverageImages -i refIms.txt -o averageForm${k}.nii.gz
    fi
    animaAverageImages -i sum.txt -o tempDir/sum.nii.gz 
fi

if [ -e averageForm${k}.nii.gz ]; then
    touch it_${k}_done
    let t=${k}+1
    if [ -e tmpRun_${t} ]; then
        \rm -f tmpRun_${k} residualDir/* tempDir/*
    fi
fi
