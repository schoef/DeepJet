#!/bin/sh -x

#select training name
prefix='TTs_Muon_biLSTM_splitDense_elu_'

#select training data and 
trainingDataTxtFile='/local/tbrueckler/DeepLepton/DeepJet_GPU/TrainingData/v6/step3/2016/muo/pt_5_-1/TTs/train_muo.txt'    #txt file should contain all training files, files should be stored in the same directroy as the txt file
trainingOutputDirectory='/local/tbrueckler/DeepLepton/DeepJet_GPU/DeepJetResults/muon_2016_morepf'                              #training output directory must exist
trainingDataStructure='TrainData_deepLeptons_Muons_sorted_2016'                                             #select from DeepJet/modules/datastructures/TrainData_deepLeptons.py
trainingModelReference='Train/deepLepton_Muons_biLSTM_splitDense_elu_reference.py'                                         #select from DeepJet/Train/deepLeptonXYreference.py, where the training model can be defined, define architecture in DeepJet/modules/models/convolutional_deepLepton.py and layers in DeepJet/modules/models/buildingBlocks_deepLepton.py

#select evaluation data
EvaluationTestDataTxtFile='/local/tbrueckler/DeepLepton/DeepJet_GPU/TrainingData/v6/step3/2016/muo/pt_5_-1/TTs/test_muo.txt' 
EvaluationTrainDataTxtFile='/local/tbrueckler/DeepLepton/DeepJet_GPU/TrainingData/v6/step3/2016/muo/pt_5_-1/TTs/50train_muo.txt'  


#0) Source Environment:
source ./gpu_env.sh
ulimit -m unlimited; ulimit -v unlimited

#1) Preperation:
# Conversion to Data Structure
convertFromRoot.py -i ${trainingDataTxtFile} -o ${trainingOutputDirectory}/${prefix}TrainData -c ${trainingDataStructure}
# ensure, that all files have been converted
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TrainData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TrainData/snapshot.dc

#2) Training:
python ${trainingModelReference} ${trainingOutputDirectory}/${prefix}TrainData/dataCollection.dc ${trainingOutputDirectory}/${prefix}Training

#3) Evaluation:
#a) for test data
convertFromRoot.py --testdatafor ${trainingOutputDirectory}/${prefix}Training/trainsamples.dc -i ${EvaluationTestDataTxtFile} -o ${trainingOutputDirectory}/${prefix}TestData
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestData/snapshot.dc
predict.py ${trainingOutputDirectory}/${prefix}Training/KERAS_model.h5 ${trainingOutputDirectory}/${prefix}TestData/dataCollection.dc ${trainingOutputDirectory}/${prefix}EvaluationTestData
#b) for train data
convertFromRoot.py --testdatafor ${trainingOutputDirectory}/${prefix}Training/trainsamples.dc -i ${EvaluationTrainDataTxtFile} -o ${trainingOutputDirectory}/${prefix}TestDataIsTrainData
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/snapshot.dc
convertFromRoot.py -r ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/snapshot.dc
predict.py ${trainingOutputDirectory}/${prefix}Training/KERAS_model.h5 ${trainingOutputDirectory}/${prefix}TestDataIsTrainData/dataCollection.dc ${trainingOutputDirectory}/${prefix}EvaluationTestDataIsTrainData

