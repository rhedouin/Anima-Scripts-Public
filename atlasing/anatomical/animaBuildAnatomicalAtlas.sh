#! /bin/bash
# Computes an atlas of scalar images using Anima registration tools and Guimond method slightly modified to use the log-Euclidean framework
# Has to be run on an OAR cluster

# Get local variables
. ~/.anima/configParser.sh

prefix=$1
nimages=$2
niter=$3
ncores=$4

mkdir tempDir
mkdir residualDir

ref=${prefix}_1
prefixBase=`dirname ${prefix}`
prefix=`basename ${prefix}`

# In the first iteration we take the first image as reference, then it is used in the dataset
firstImage=2
previousMergeId=0

for((k=1;k<=$niter;k++))
do
  if [ -e it_${k}_done ]; then
      ref=averageForm${k}
      firstImage=1
      continue
  fi

	let mergeReqNum=${k}-1

  	echo " "
  	echo "*************Iteration $k Processing Reference: $ref "

	for ((a=$firstImage;a<=$nimages;a++))
	do
		rm -f residualDir/${prefix}_${a}_{bal_tr.nii.gz,flag}
	done

	let nrun=${nimages}-${firstImage}+1
	let ncoresLowMem=${ncores}+${ncores}

	echo "#!/bin/bash" > tmpRun_${k}

	echo "#OAR -l /nodes=1/core=${ncores},walltime=03:59:00" >> tmpRun_${k}
	echo "#OAR --array ${nrun}" >> tmpRun_${k}
	echo "#OAR -O ${PWD}/reg-${k}.%jobid%.output" >> tmpRun_${k}
	echo "#OAR -E ${PWD}/reg-${k}.%jobid%.error" >> tmpRun_${k}

	echo "export PATH=${PATH}:${ANIMA_DIR}:" >> tmpRun_${k}
	echo "cd ${PWD}" >> tmpRun_${k}

	if [ ${k} -eq 1 ]; then
		echo "let index=\${OAR_ARRAY_INDEX}+1" >> tmpRun_${k}
		echo "${ROOT_DIR}/atlasing/anatomical/animaRegisterImage.sh ${PWD} ${ref}.nii.gz ${prefixBase} ${prefix} \$index ${ncores}" >> tmpRun_${k}
	else
		echo "${ROOT_DIR}/atlasing/anatomical/animaRegisterImage.sh ${PWD} ${ref}.nii.gz ${prefixBase} ${prefix} \$OAR_ARRAY_INDEX ${ncores}" >> tmpRun_${k}
	fi

	chmod u+x tmpRun_${k}

	a=''
	if [ $previousMergeId -eq 0 ]; then
		a=`oarsub -n reg-${k} -S ${PWD}/tmpRun_${k}`
	else
		a=`oarsub -n reg-${k} -a ${previousMergeId} -S ${PWD}/tmpRun_${k}`
	fi

	jobsId=''
	for tmpstr in `echo $a | tr " " "\n"`
	do
		if [ "`echo $tmpstr | grep OAR_JOB_ID`" == "" ]; then
			continue
		fi

		tmpid=`echo $tmpstr | awk -F 'OAR_JOB_ID' '{print $2;exit}' | sed "s/\=//g"`
		jobsId="${jobsId} -a ${tmpid}"
	done

	echo "#!/bin/bash" > mergeRun_${k}
	echo "#OAR -l /nodes=1/core=${ncores},walltime=03:59:00" >> mergeRun_${k}
	echo "#OAR -O ${PWD}/merge-${k}.%jobid%.output" >> mergeRun_${k}
	echo "#OAR -E ${PWD}/merge-${k}.%jobid%.error" >> mergeRun_${k}

	echo "export PATH=${PATH}:${ANIMA_DIR}:" >> mergeRun_${k}
	echo "cd ${PWD}" >> mergeRun_${k}
	echo "${ROOT_DIR}/atlasing/anatomical/animaMergeImages.sh ${PWD} ${prefixBase} ${prefix} ${k} ${nimages} ${ref} ${ncores}" >> mergeRun_${k}

	chmod u+x mergeRun_${k}
	a=`oarsub -n merge-${k} -S ${PWD}/mergeRun_${k} ${jobsId}`
	previousMergeId=`echo $a | awk -F 'OAR_JOB_ID' '{print $2;exit}' | sed "s/\=//g"`

 	ref=averageForm${k}
 	firstImage=1
done
