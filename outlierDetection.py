#-*- coding: utf8
'''
Created on Aug 9, 2016

@author: zahran
'''

#from __future__ import division, print_function
from scipy.stats import chisquare
from collections import OrderedDict
from multiprocessing import Process, Queue

import time
import pandas as pd
#import plac
import numpy as np
import math
import os.path
from MyEnums import *
from TestSample import *
from DetectionTechnique import *
from Tribeflow import *
#from Tribeflowpp import *
#from MyWord2vec import *
#from NgramLM import *
#from RNNLM import *
from HMM import *
import sys
#from bagOfActions import BagOfActions
#sys.path.append('/homes/mohame11/framework_for_detecting_outlier_in_trajectories/Cython')
sys.path.append('myCython')
#sys.path.insert(0,'/homes/mohame11/framework_for_detecting_outlier_in_trajectories/Cython/')
#import cythonOptimize
import pyximport; pyximport.install()
import cythonOptimize
#from cythonOptimize import *
#from myCython import cythonOptimize

class OutlierDetection:
    def __init__(self):
        
        #COMMON
        self.CORES = 2
        #cythonOptimize.getLogProb([],0)
        
        '''          
        self.PATH = '/u/scratch1/mohame11/lastFm/'
        self.RESULTS_PATH = self.PATH + 'simulatedData/pvalues_tr9_www_simData_perUser20'
        self.SEQ_FILE_PATH = self.PATH + 'simulatedData/tr9_www_simData_perUser20'
        self.MODEL_PATH = self.PATH + 'lastfm_win10_noob.h5'
        self.seq_prob = SEQ_PROB.TRIBEFLOW
        self.useWindow = USE_WINDOW.FALSE
        '''

        
        self.PATH = '/Users/mohame11/Documents/myFiles/Career/Work/Purdue/PhD_courses/projects/outlierDetection/pins_repins_fixedcat/win10/HMM/'
        self.RESULTS_PATH = self.PATH + 'pvalues'
        self.SEQ_FILE_PATH = self.PATH + 'likes.trace'
        self.MODEL_PATH = self.PATH + 'pins_repins_win10.trace_HMM_MODEL.pkl'
        self.seq_prob = SEQ_PROB.HMM
        self.useWindow = USE_WINDOW.FALSE
        
        
####################################
        '''
        self.PATH = '/u/scratch1/mohame11/pins_repins_fixedcat/'
        self.RESULTS_PATH = self.PATH + 'allLikes/pvalues_tribeflowpp'
        self.SEQ_FILE_PATH = self.PATH + 'allLikes/likes.trace'
        self.MODEL_PATH = self.PATH + 'pins_repins_win10.trace_tribeflowpp_model/pins_repins_win10_tribeflowpp.h5.mcmc'

        self.seq_prob = SEQ_PROB.TRIBEFLOWPP
        self.useWindow = USE_WINDOW.FALSE
        '''
        
#####################################        
        self.groupActionsByUser = False   # True will just append all sequences for a user into a long sequence
        self.DATA_HAS_USER_INFO = True
        self.VARIABLE_SIZED_DATA = False

        
        #TRIBEFLOW
        #self.TRACE_PATH = self.PATH + 'pins_repins_win10.trace'
        self.TRACE_PATH = self.PATH + 'lastfm_win10_trace'
        #self.TRACE_PATH = self.PATH + 'pins_repins_win10.trace_tribeflowpp.tsv.gz'
        self.STAT_FILE = self.PATH +'Stats_win10'
        self.UNBIAS_CATS_WITH_FREQ = False
        self.smoothingParam = 1.0   #smoothing parameter for unbiasing item counts.
        
        #NGRM/RNNLM/WORD2VEC/TRIBEFLOWPP
        self.HISTORY_SIZE = 9
        #self.ALL_ACTIONS_PATH = self.PATH + 'pins_repins_win10.trace_tribeflowpp_actionMappings'
        self.nonExistingUserFile = self.PATH +'likes.trace_nonExistingUsers'


                           
    def getPvalueWithoutRanking(self, currentActionRank, keySortedProbs, probabilities):
        #normConst = 0.0
        #for i in range(len(probabilities)):
        #    normConst += probabilities[i]
            
        cdf = 0.0
        for i in range(currentActionRank+1):
            cdf += probabilities[keySortedProbs[i]]
        
        #prob = cdf/normConst
        return cdf
  
    #testDic, quota, coreId, q, store, true_mem_size, hyper2id, obj2id, Theta_zh, Psi_sz, smoothedProbs             
    def get_norm_from_logScores(self,logScores):
        if(len(logScores) == 1):
            return logScores[0]
 
        pw = (-1)*logScores[0] + self.get_norm_from_logScores(logScores[1:])

        try:
            res = logScores[0] + math.log10(1+(math.pow(10,pw)))
        except:
            res = logScores[0] + pw
 
        return res


    def outlierDetection(self, coreTestDic, quota, coreId, q, myModel):
        myCnt = 0    
        print('writing to: ',myModel.RESULTS_PATH+'/outlier_analysis_pvalues_'+str(coreId))
        writer = open(myModel.RESULTS_PATH+'/outlier_analysis_pvalues_'+str(coreId),'w')
        #print('Inside: coreId',coreId,' len(coreTestDic)', len(coreTestDic))
        #print('10keys', coreTestDic.keys()[0:10])
        for user in coreTestDic:
            #print('user',user)
            for testSample in coreTestDic[user]:
                myCnt += 1
                #print('myCnt=', myCnt)
                seq = testSample.actions
                goldMarkers = testSample.goldMarkers
                actions = myModel.getAllPossibleActions()              
                #print 'len(actions)=', len(actions)
                pValuesWithRanks = {}
                pValuesWithoutRanks = {}
                for i in range(len(seq)): #for all actions in the sequence.
                    #Take the action with index i and replace it with all possible actions             
                    probabilities = {}
                    scores = {}        
                    newSeq = list(seq)
                    #currentActionId = myModel.obj2id[newSeq[i]] #current action id
                    currentActionIndex = actions.index(newSeq[i])# the current action index in the action list.
                    #cal scores (an un-normalized sequence prob in tribeflow)
                    #print 'current action: ',i
                   
                    for j in range(len(actions)): #for all possible actions that can replace the current action
                        #print 'replacement# ',j
                        del newSeq[i]                
                        newSeq.insert(i, actions[j])    
                        userId = myModel.getUserId(user)     
                        seqScore = myModel.getProbability(userId, newSeq)  
                        scores[j] = seqScore
                    
                    #print 'finished all replacements'
                    
                    #print 'calculating normalizing constant'
                    try:
                        #allScores = np.array(scores.values(), dtype = 'd').copy()
                        #logNormalizingConst = cythonOptimize.getLogProb(allScores,len(allScores))
                        logNormalizingConst = self.get_norm_from_logScores(scores.values())
                        for j in range(len(actions)): #for all possible actions that can replace the current action
                            logProb = float(scores[j]) - float(logNormalizingConst)
                            probabilities[j] = math.pow(10, logProb)

                    except:
                        normConst = 0.0
                        for j in range(len(actions)):
                            scores[j] = math.pow(scores[j], 10)
                            normConst += scores[j]
                        for j in range(len(actions)): 
                            prob = float(scores[j]) / float(normConst)
                            probabilities[j] = prob
                            #print 'prob[action j]', prob

                        
                        

                    #print 'normalizing sequence scores'
                    #sorting ascendingy
                    keySortedProbs = sorted(probabilities, key=lambda k: (-probabilities[k], k), reverse=True)
                    currentActionRank = keySortedProbs.index(currentActionIndex)
                    currentActionPvalueWithoutRanks = self.getPvalueWithoutRanking(currentActionRank, keySortedProbs, probabilities)
                    currentActionPvalueWithRanks = float(currentActionRank+1)/float(len(actions))
                    pValuesWithRanks[i] = currentActionPvalueWithRanks
                    pValuesWithoutRanks[i] = currentActionPvalueWithoutRanks
                if(len(seq) == len(pValuesWithoutRanks)):                    
                    writer.write('user##'+str(user)+'||seq##'+str(seq)+'||PvaluesWithRanks##'+str(pValuesWithRanks)+'||PvaluesWithoutRanks##'+str(pValuesWithoutRanks)+'||goldMarkers##'+str(goldMarkers)+'\n')
                    #print 'writing sm'
                else:
                    print('seq len not equal to the number of pvalues !')
                if(myCnt % 5 == 0):
                    writer.flush()
                    print('>>> proc: '+ str(coreId)+' finished '+ str(myCnt)+'/'+str(quota)+' instances ...')                
        writer.close()    
        #ret = [chiSqs, chiSqs_expected]
        #q.put(ret)                                          
                                                                                                                                    
    def distributeOutlierDetection(self):
        myModel = None
  
        if(self.seq_prob == SEQ_PROB.NGRAM):
            myModel = NgramLM()
            myModel.useWindow = self.useWindow
            myModel.model_path = self.MODEL_PATH
            myModel.true_mem_size = self.HISTORY_SIZE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.ALL_ACTIONS_PATH = self.ALL_ACTIONS_PATH
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.loadModel()
        
        elif(self.seq_prob == SEQ_PROB.RNNLM):
            myModel = RNNLM()
            myModel.useWindow = self.useWindow
            myModel.model_path = self.MODEL_PATH
            myModel.true_mem_size = self.HISTORY_SIZE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.RESULTS_PATH = self.RESULTS_PATH
            myModel.ALL_ACTIONS_PATH = self.ALL_ACTIONS_PATH
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.loadModel()
            
        
        elif(self.seq_prob == SEQ_PROB.WORD2VEC):
            #w2v = MyWord2vec()
            #w2v.model_path = '/u/scratch1/mohame11/pins_repins_fixedcat/pins_repins_win10.trace_word2vec_SKIPG'
            #model = gensim.models.Word2Vec.load(w2v.model_path)  # you can continue training with the loaded model!
            #print('Fast word2vec =', gensim.models.word2vec.FAST_VERSION)
            #print('Fast word2vec_inner=', gensim.models.word2vec_inner.FAST_VERSION)
            myModel = MyWord2vec()
            myModel.useWindow = self.useWindow
            myModel.model_path = self.MODEL_PATH
            myModel.true_mem_size = self.HISTORY_SIZE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.RESULTS_PATH = self.RESULTS_PATH
            myModel.ALL_ACTIONS_PATH = self.ALL_ACTIONS_PATH
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.nonExistingUserFile = self.nonExistingUserFile
            myModel.loadModel()
            
        elif(self.seq_prob == SEQ_PROB.HMM):
            
            myModel = HMM()
            myModel.useWindow = self.useWindow
            myModel.model_path = self.MODEL_PATH
            myModel.true_mem_size = self.HISTORY_SIZE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.RESULTS_PATH = self.RESULTS_PATH
            #myModel.ALL_ACTIONS_PATH = self.ALL_ACTIONS_PATH
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.nonExistingUserFile = self.nonExistingUserFile
            myModel.actionMappingsPath = self.PATH + 'pins_repins_win10.trace_HMM_ACTION_MAPPINGS'
            myModel.loadModel()
        
        elif(self.seq_prob == SEQ_PROB.TRIBEFLOWPP):        
            myModel = TribeFlowpp()
            myModel.useWindow = self.useWindow
            myModel.model_path = self.MODEL_PATH
            myModel.true_mem_size = self.HISTORY_SIZE    
            myModel.trace_fpath = self.TRACE_PATH
            myModel.UNBIAS_CATS_WITH_FREQ = self.UNBIAS_CATS_WITH_FREQ
            myModel.STAT_FILE = self.STAT_FILE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.userMappingsPath = self.PATH + 'pins_repins_win10.trace_tribeflowpp_userMappings'
            myModel.actionMappingsPath = self.PATH + 'pins_repins_win10.trace_tribeflowpp_actionMappings'
     
            if(self.UNBIAS_CATS_WITH_FREQ):
                print('>>> calculating statistics for unbiasing categories ...')
                myModel.calculatingItemsFreq(self.smoothingParam)
            myModel.loadModel()
        
        elif(self.seq_prob == SEQ_PROB.TRIBEFLOW):        
            myModel = TribeFlow()
            myModel.useWindow = self.useWindow
            
            myModel.model_path = self.MODEL_PATH
            myModel.store = pd.HDFStore(self.MODEL_PATH)
            myModel.Theta_zh = myModel.store['Theta_zh'].values
            myModel.Psi_sz = myModel.store['Psi_sz'].values    
            myModel.true_mem_size = myModel.store['Dts'].values.shape[1]    
            myModel.hyper2id = dict(myModel.store['hyper2id'].values)
            myModel.obj2id = dict(myModel.store['source2id'].values)    
            #myModel.trace_fpath = myModel.store['trace_fpath'][0][0]
            myModel.trace_fpath = self.TRACE_PATH
            myModel.UNBIAS_CATS_WITH_FREQ = self.UNBIAS_CATS_WITH_FREQ
            myModel.STAT_FILE = self.STAT_FILE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.groupActionsByUser = self.groupActionsByUser
     
            if(self.UNBIAS_CATS_WITH_FREQ):
                print('>>> calculating statistics for unbiasing categories ...')
                myModel.calculatingItemsFreq(self.smoothingParam)
        
        
        elif(self.seq_prob == SEQ_PROB.BAG_OF_ACTIONS):
            myModel = BagOfActions()  
            myModel.trace_fpath = self.TRACE_PATH
            myModel.smoothingParam = self.smoothingParam
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.DATA_HAS_USER_INFO = self.DATA_HAS_USER_INFO
            myModel.VARIABLE_SIZED_DATA = self.VARIABLE_SIZED_DATA
            myModel.true_mem_size = self.HISTORY_SIZE
            myModel.SEQ_FILE_PATH = self.SEQ_FILE_PATH
            myModel.RESULTS_PATH = self.RESULTS_PATH
            myModel.useWindow = self.useWindow
            myModel.groupActionsByUser = self.groupActionsByUser
            myModel.loadModel()
        
        
        myModel.RESULTS_PATH = self.RESULTS_PATH      
        testDic,testSetCount = myModel.prepareTestSet()
        print('Number of test samples: '+str(testSetCount))   

        
        start_time = time.time()
        myProcs = []
        workTot = 0
        idealCoreQuota = testSetCount // self.CORES
        userList = testDic.keys()    
        uid = 0
        q = Queue()
        for i in range(self.CORES):  
            coreTestDic = {}
            coreShare = 0
            while uid < len(userList):
                coreShare += len(testDic[userList[uid]])
                coreTestDic[userList[uid]] = testDic[userList[uid]]
                uid += 1
                if(coreShare >= idealCoreQuota):
                    p = Process(target = self.outlierDetection, args=(coreTestDic, coreShare, i, q, myModel))
                    #self.outlierDetection(coreTestDic, coreShare, i, q, myModel)
                    myProcs.append(p)         
                    testSetCount -= coreShare
                    leftCores = (self.CORES-(i+1))
                    if(leftCores >0):
                        idealCoreQuota = testSetCount // leftCores 
                    print('>>> Starting process: '+str(i)+' on '+str(coreShare)+' samples.')
                    workTot += coreShare
                    p.start()       
                    break
                                       
            #myProcs.append(p)        
        print('Total workload', workTot)
            
            
        for i in range(self.CORES):
            myProcs[i].join()
            print('>>> process: '+str(i)+' finished')
        
        elapsed_time = time.time() - start_time
        print 'Elapsed Time=', elapsed_time
        #results = []
        #for i in range(CORES):
        #    results.append(q.get(True))
                
                                
        print('\n>>> All DONE!')
        #store.close()

                                    
def work():  
    detect = OutlierDetection() 
    detect.distributeOutlierDetection() 
  
    

if __name__ == "__main__":
    work()    
    #cProfile.run('distributeOutlierDetection()')
    #plac.call(main)
    print('DONE!')
