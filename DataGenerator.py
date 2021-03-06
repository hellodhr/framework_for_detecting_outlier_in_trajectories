'''
Created on Nov 30, 2016

@author: zahran
'''
import pandas as pd
import numpy as np
import random
from TestSample import *

class DataGenerator(object):    
    def __init__(self, MODEL_PATH, DATA_GEN, perUserSequences):
        self.MODEL_PATH = MODEL_PATH
        self.DATA_GEN = DATA_GEN
        self.perUserSequences = perUserSequences        
        store = pd.HDFStore(MODEL_PATH)         
                        
        self.Theta_zh = store['Theta_zh'].values
        self.Psi_oz = store['Psi_sz'].values    
        self.true_mem_size = store['Dts'].values.shape[1]    
        self.hyper2id = dict(store['hyper2id'].values)
        self.obj2id = dict(store['source2id'].values)
        print len(self.hyper2id), len(self.obj2id)
        
        self.id2obj = dict((v, k) for k, v in self.obj2id.items())
        
        self.nz, self.nh = self.Theta_zh.shape
        self.no, self.nz = self.Psi_oz.shape  
              
        #normalizing 
        #axis 0 is summing the cols. i.e. normalizing by the col sum. (i.e for each env)
        self.Psi_oz = self.Psi_oz / self.Psi_oz.sum(axis=0)
        self.Theta_zh = self.Theta_zh / self.Theta_zh.sum(axis=0)
        
        #for optimization, save the transitions for each environment
        self.envTransitions = {}
                    
        
        store.close()
    
    def getTransitionMatrixForEnv(self, z):                                    
        #Compute transitions for a given env  
        if(z in self.envTransitions):
            return self.envTransitions[z]            
        T = np.outer(self.Psi_oz[:, z], self.Psi_oz[:, z]) #the P[ dest | source, z ] matrix
        np.fill_diagonal(T, 0)
        T = T / T.sum(axis=0) #Re-normalize
        self.envTransitions[z] = T
        return T #(o x o)
    
    def sample(self, srcs, probs):
        #numpy.random.choice(a, size=None, replace=True, p=None)
        #replace =True. i.e. put back the sampled item to the space
        #replace =False. i.e. once picked, it's removed and thus affecting the probability of the remainging items
        mySample = np.random.choice(srcs, 1, replace =True, p=probs)
        return mySample
    
    def generateOneSequence(self, T, starto):
        seq = [starto]
        currento = starto
        for i in range(self.true_mem_size):
            currento_o = T[:,currento]
            sampledo = self.sample(list(range(0,self.no)), currento_o)[0]
            seq.append(sampledo)
            currento = sampledo
        return seq
    
    def generateOneSequence_optimized(self, z, starto, actionCount):
        seq = [starto]
        currento = starto
        for i in range(actionCount-1):
            currento_o = np.array(self.Psi_oz[:, z])
            currento_o *= currento_o[currento]
            currento_o = currento_o / currento_o.sum() #Re-normalize
            #currento_o = T[:,currento]
            sampledo = self.sample(list(range(0,self.no)), currento_o)[0]
            seq.append(sampledo)
            currento = sampledo
        return seq
                            
    
    def generateSequenceByUser_optimized(self, h, actionCount):                        
        h_z = self.Theta_zh[:,h]
        sampledZ = self.sample(list(range(0,self.nz)), h_z)[0]
        
        z_o = self.Psi_oz[:,sampledZ]

        firsto = self.sample(list(range(0,self.no)), z_o)[0]
        
        #T = self.getTransitionMatrixForEnv(sampledZ)  
        
        seqIds = self.generateOneSequence_optimized(sampledZ, firsto, actionCount)
        seq = []
        for s in seqIds:
            seq.append(self.id2obj[s])
            
        return seq
    
    def generateSequenceByUser(self, h):                        
        h_z = self.Theta_zh[:,h]
        sampledZ = self.sample(list(range(0,self.nz)), h_z)[0]
        
        z_o = self.Psi_oz[:,sampledZ]

        firsto = self.sample(list(range(0,self.no)), z_o)[0]
        
        T = self.getTransitionMatrixForEnv(sampledZ)  
        
        seqIds = self.generateOneSequence(T, firsto)
        seq = []
        for s in seqIds:
            seq.append(self.id2obj[s])
            
        return seq
            
        
               
        
    def generate(self, userTrajLen):                    
        w = open(self.DATA_GEN, 'w')
        cnt = 0
        for userName in self.hyper2id:
            if(cnt % 10 == 0):
                print(str(cnt)+' users are finished ...')
            cnt+=1
            h = self.hyper2id[userName]
            
            for i in range(self.perUserSequences):
                w.write(str(userName)+'\t')
                seq = self.generateSequenceByUser(h)                
                for s in seq:
                    w.write(s + '\t')
                for g in range(self.true_mem_size+1):
                    w.write('false\t')
                w.write('\n')               
                w.flush()
        w.close()
        
    
    def generate_optimized(self, userTrajLen):
        w = open(self.DATA_GEN, 'w')
        cnt = 0
        print '#users', len(self.hyper2id)
        for userName in self.hyper2id:
            if(cnt % 1000 == 0):
                print(str(cnt)+' users are finished ...')
            cnt+=1
            h = self.hyper2id[userName]
            seqLen = userTrajLen[userName]
            bursts = seqLen // (self.true_mem_size+1)
            leftovers = seqLen % (self.true_mem_size+1)
            
            #print('user:',userName, seqLen)
            w.write(str(userName)+'\t')
            for i in range(bursts):
                #print userName, i
                seq = self.generateSequenceByUser_optimized(h, self.true_mem_size+1)                
                for s in seq:
                    w.write(s + '\t')
             
            
            
            if(leftovers > 0):
                seq = self.generateSequenceByUser_optimized(h, leftovers)                
                for s in seq:
                    w.write(s + '\t')

           
            #for g in range(seqLen):
            #    w.write('false\t')
            
            w.write('\n')               
            w.flush()
        w.close()
                
            
        
    
    def formOriginalSeq(self, tests):
        origSeq = list(tests[0].actions)  
        if(len(tests) <= 1):
            return origSeq
        for i in range(1,len(tests)):
            a = tests[i].actions[-1]
            origSeq.append(a)           
        return origSeq

    def getUserTrajectoryLengths(self, trainPath):
        userTrajLen = {}
        testDic = {}
        print(">> Reading training set ...")
        testSetCount = 0
        r = open(trainPath, 'r')    
        for line in r:
            line = line.strip() 
            tmp = line.split()  
            actionStartIndex = 10
            
            user = tmp[9]   
            
            seq = tmp[actionStartIndex :]
    
            t = TestSample()  
            t.user = user
            t.actions = list(seq)  
            
            testSetCount += 1
            if(user in testDic):
                testDic[user].append(t)                                                    
            else:
                testDic[user]=[t]
        r.close()
    
        testSetCount = len(testDic)
        for u in testDic:
            tests = testDic[u]
            originalSeq = self.formOriginalSeq(tests)
            userTrajLen[u] = len(originalSeq)
        
        return userTrajLen  





def main():
    MODEL_PATH = '/u/scratch1/mohame11/pins_repins_fixedcat/pins_repins_win10_noop_NoLeaveOut.h5'
    #MODEL_PATH = '/Users/mohame11/Documents/myFiles/Career/Work/New_Linux/PARSED_pins_repins_win10_noop_NoLeaveOut_pinterest.h5'
    DATA_GEN = '/u/scratch1/mohame11/pins_repins_fixedcat/simulatedData/tr9_simData_matchTraining'
    TRAIN_PATH = '/u/scratch1/mohame11/pins_repins_fixedcat/pins_repins_win10.trace'
    perUserSequences = -1
    
    dg = DataGenerator(MODEL_PATH, DATA_GEN, perUserSequences)
    print('Getting user trajectory lengths from training data ...')
    userTrajLen = dg.getUserTrajectoryLengths(TRAIN_PATH)
    print('userTrajLen', len(userTrajLen))
    #dg.generate(userTrajLen)
    dg.generate_optimized(userTrajLen)
  
    

if __name__ == "__main__":
    
#     d = {'a':0.0, 'b':0.0, 'c':0.0, 'd':0.0}
#     srcs = d.keys()    
#     probs = [0.6, 0.2, 0.15, 0.05]
#     tot = 10000
#     for i in range(tot):
#         mySample = np.random.choice(srcs, 1, replace =True, p=probs)[0]
#         d[mySample] += 1
#     for k in srcs:
#         print(k,d[k]/tot)
        
        
    main()       
    print('DONE!')
