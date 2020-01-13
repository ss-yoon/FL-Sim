import numpy as np
import csv
import random
from time import gmtime, strftime #strftime("%m%d_%H%M%S", gmtime()) + ' ' + 

from algorithm.abc import AbstractAlgorithm
import fl_util

GROUPING_INTERVAL = 10000
GROUPING_MAX_STEADY_STEPS = 3
GROUPING_NUM_SAMPLE_NODE = 100

WEIGHTING_MAX_STEADY_STEPS = 100
WEIGHTING_WEIGHT_DIFF = 10

class Algorithm(AbstractAlgorithm):
    
    def getFileName(self):
        d_budget = self.args.opaque1
        return self.args.modelName + '_' + self.args.dataName + '_' + self.args.algName + '_' \
                + str(self.args.numNodeClasses) + str(self.args.numEdgeClasses) + '_' + str(d_budget)
    
    def __init__(self, args):
#         args.edgeType = 'a' # 무조건 처음 edgeType 을 all 로 고정
        super().__init__(args, randomEnabled=True)
        
        fileName = self.getFileName()
        self.fileDelta = open('logs/' + fileName + '_Delta.csv', 'w', newline='', buffering=1)
        self.fwDelta = csv.writer(self.fileDelta, delimiter=',', quotechar='|', quoting=csv.QUOTE_MINIMAL)
        
    def __del__(self):
        self.fileDelta.close()
        super().__del__()
        
    def run(self):
        self.fwDelta.writerow(['time', 'cntSteady', 'Delta_star', 'Delta_cur'])
        self.fwEpoch.writerow(['epoch', 'loss', 'accuracy', 'time', 'aggrType', 'numGroups', 'tau1', 'tau2'])
        (trainData_by1Nid, testData_by1Nid, c) = self.getInitVars()
        
        lr = self.args.lrInitial
        input_w_ks = [ self.model.getParams() for _ in c.groups ]
        d_global = c.get_d_global(True) ; d_group = c.get_d_group(True) ; d_sum = 0
        d_budget = self.args.opaque1
        
    #     for t3 in range(int(self.args.maxEpoch/(tau1*tau2))):
        t = 0 ; t_prev = 0 ; tau1 = 5 ; tau2 = 2 ; t3 = 0
        while True:
            for t2 in range(tau2):
                w_is = []
                w_k_byTime_byGid = []
                output_w_ks = []
                for k, g in enumerate(c.groups): # Group Aggregation
                    w_k = input_w_ks[k]
                    (w_k_byTime, w_k_is) = self.model.federated_train(w_k, g.get_D_k_is(), lr, tau1, g.get_p_k_is())
                    w_is += w_k_is
                    w_k_byTime_byGid.append(w_k_byTime)
                    output_w_ks.append(w_k_byTime[-1])
                input_w_ks = output_w_ks
                w_byTime = self.model.federated_aggregate(w_k_byTime_byGid, c.get_p_ks()) # Global Aggregation
                for t1 in range(tau1):
                    t += 1
                    if (t-t_prev) % tau1 == 0 and not((t-t_prev) % (tau1*tau2)) == 0:
                        d_sum += d_group
                        aggrType = 'Group'
                    elif (t-t_prev) % (tau1*tau2) == 0:
                        d_sum += d_global
                        aggrType = 'Global'
                    else:
                        aggrType = ''
                    (loss, _, _, acc) = self.model.evaluate(w_byTime[t1], trainData_by1Nid, testData_by1Nid)
                    print('Epoch\t%d\tloss=%.3f\taccuracy=%.3f\ttime=%.4f\taggrType=%s\tnumGroups=%d\ttau1=%d\ttau2=%d'
                          % (t, loss, acc, d_sum, aggrType, len(c.groups), tau1, tau2))
                    self.fwEpoch.writerow([t, loss, acc, d_sum, aggrType, len(c.groups), tau1, tau2])
                    
                    lr *= self.args.lrDecayRate
    #                 if t >= self.args.maxEpoch: break
    #             if t >= self.args.maxEpoch: break
    #         if t >= self.args.maxEpoch: break
                    if d_sum >= self.args.maxTime: break;
                if d_sum >= self.args.maxTime: break;
            if d_sum >= self.args.maxTime: break;
                
            w = w_byTime[-1] # 출력을 위해 매 시간마다 수행했던 Global Aggregation 의 마지막 시간 값만 추출
            input_w_ks = [ w for _ in c.groups ]
            
            if t3 % GROUPING_INTERVAL == 0:
                # Gradient Estimation
                (g_is__w, nid2_g_i__w) = self.model.federated_collect_gradients(w, c.get_nid2_D_i())
    #             (g_is__w2, nid2_g_i__w2) = self.model.federated_collect_gradients2(w, c.get_nid2_D_i())
    #             for nid in nid2_g_i__w:
    #                 print(self.model.np_modelEquals(g_is__w[nid], g_is__w2[nid]), self.model.np_modelEquals(nid2_g_i__w[nid], nid2_g_i__w2[nid]))
                g__w = np.average(g_is__w, axis=0, weights=c.get_p_is())
        
#                 D_is = c.get_D_is()
#                 p_is = [ len(np.unique(D_i['y'])) for D_i in D_is ]
#                 print(p_is)
#                 p_is = [ 1 for _ in range(len(c.get_N())) ]
#                 c.set_p_is(p_is)
#                 c.digest(c.z)
        
                # IID Grouping
#                 c = self.run_IID_Weighting(c, nid2_g_i__w, g__w)
                (c, tau1, tau2, d_group, d_global) = self.run_IID_Grouping(c, nid2_g_i__w, g__w, d_budget)
            t_prev = t # Mark Time
            t3 += 1
            
    def run_IID_Weighting(self, c, nid2_g_i__w, g__w, mode=1):
        print('IID Weighting Started')
        random.seed(1234)
        
        c_star = c.clone()
        if mode == 1:
            delta_star = c.get_Delta(nid2_g_i__w, g__w)
        elif mode == 2:
            delta_star = c.get_delta(nid2_g_i__w)
        elif mode == 3:
            delta_star = c.get_DELTA(nid2_g_i__w, g__w)
        else:
            delta_star = c.get_emd()
        print('Initial delta_star=%.4f' % (delta_star))
        
        cntIdx = 0
        cntSteady = 0
        cntPrint = 0
        while cntSteady < WEIGHTING_MAX_STEADY_STEPS:
            curIdx = cntIdx % len(c.get_N())
            cntIdx += 1
            (c_star, delta_star, cntSteady, cntPrint) = self.improveWeightOnIdx(c, c_star, delta_star, nid2_g_i__w, g__w, curIdx, cntSteady, cntPrint, mode)
#             randIdx = random.randint(0, len(c.get_N())-1)
#             (c_star, delta_star, cntSteady, cntPrint) = self.improveWeightOnIdx(c, c_star, delta_star, nid2_g_i__w, g__w, randIdx, cntSteady, cntPrint, mode)

#         # Tweak weights
#         p_is = c.get_p_is()
#         for i in range(len(p_is)):
#             if random.choice([True, False]) == True:
#                 p_is[i] += WEIGHTING_WEIGHT_DIFF
#             else:
#                 if p_is[i] > WEIGHTING_WEIGHT_DIFF:
#                     p_is[i] -= WEIGHTING_WEIGHT_DIFF
#                 else:
#                     p_is[i] = 0
#         c.set_p_is(p_is)
#         c.digest(c.z)
        
#         if mode == 1:
#             delta_cur = c.get_Delta(nid2_g_i__w, g__w)
#         elif mode == 2:
#             delta_cur = c.get_delta(nid2_g_i__w)
#         elif mode == 3:
#             delta_cur = c.get_DELTA(nid2_g_i__w, g__w)
#         else:
#             delta_cur = c.get_emd()
#         print('Tweaked delta_star=%.4f, delta_cur=%.4f' % (delta_star, delta_cur))
            
        print('IID Weighting Finished')
        return c_star
    
    def improveWeightOnIdx(self, c, c_star, delta_star, nid2_g_i__w, g__w, curIdx, cntSteady, cntPrint, mode):
        p_is = c.get_p_is()
        
        # 높은 Weight 로 변경 시도
        p_is[curIdx] += WEIGHTING_WEIGHT_DIFF
        c.set_p_is(p_is)
        c.digest(c.z)
        
        if mode == 1:
            delta_up = c.get_Delta(nid2_g_i__w, g__w)
        elif mode == 2:
            delta_up = c.get_delta(nid2_g_i__w)
        elif mode == 3:
            delta_up = c.get_DELTA(nid2_g_i__w, g__w)
        else:
            delta_up = c.get_emd()
        if delta_star > delta_up:
            # 유리할 경우 변경
            (c_star, delta_star) = (c.clone(), delta_up)
            cntSteady = 0 # 한 번이라도 바뀌면 Steady 카운터 초기화
            cntPrint += 1
            if cntPrint % 100 == 0:
                print('delta_star=%.4f, delta_cur=%.4f' % (delta_star, delta_up))
                self.fwDelta.writerow([strftime("%m-%d_%H:%M:%S", gmtime()), cntSteady, delta_star, delta_up])
        else:
            # 유리하지 않을 경우,
            # 낮은 Weight 로 변경 시도 (2배: 원래대로 돌리는 것 포함)
            if p_is[curIdx] > 2 * WEIGHTING_WEIGHT_DIFF:
                p_is[curIdx] -= 2 * WEIGHTING_WEIGHT_DIFF
            else:
                p_is[curIdx] = 0
            c.set_p_is(p_is)
            c.digest(c.z)
            
            if mode == 1:
                delta_down = c.get_Delta(nid2_g_i__w, g__w)
            elif mode == 2:
                delta_down = c.get_delta(nid2_g_i__w)
            elif mode == 3:
                delta_down = c.get_DELTA(nid2_g_i__w, g__w)
            else:
                delta_down = c.get_emd()
            if delta_star > delta_down:
                # 유리할 경우 변경
                (c_star, delta_star) = (c.clone(), delta_down)
                cntSteady = 0 # 한 번이라도 바뀌면 Steady 카운터 초기화
                cntPrint += 1
                if cntPrint % 100 == 0:
                    print('delta_star=%.4f, delta_cur=%.4f' % (delta_star, delta_down))
                    self.fwDelta.writerow([strftime("%m-%d_%H:%M:%S", gmtime()), cntSteady, delta_star, delta_down])
            else:
                # 유리하지 않을 경우, 다시 원래대로 초기화
                p_is[curIdx] += WEIGHTING_WEIGHT_DIFF
                c.set_p_is(p_is)
                c.digest(c.z)
                cntSteady += 1
        return (c_star, delta_star, cntSteady, cntPrint)
        
    def run_IID_Grouping(self, c, nid2_g_i__w, g__w, d_budget):
        print('IID Grouping Started')
        
        # 최적 초기화
        c_star = c.clone()
        DELTA_star = c_star.get_DELTA(nid2_g_i__w, g__w)
        print('Initial DELTA_star=%.4f' % (DELTA_star))
        self.fwDelta.writerow([strftime("%m-%d_%H:%M:%S", gmtime()), 0, DELTA_star, DELTA_star])
        
        cntSteady = 0
        while cntSteady < GROUPING_MAX_STEADY_STEPS:
            DELTA_cur = self.iterate_IID_Grouping(c, nid2_g_i__w, g__w)
            if DELTA_star > DELTA_cur:
                (c_star, DELTA_star) = (c.clone(), DELTA_cur)
                cntSteady = 0 # 한 번이라도 바뀌면 Steady 카운터 초기화
            else:
                cntSteady += 1
            print('cntSteady=%d, DELTA_star=%.4f, DELTA_cur=%.4f' % (cntSteady, DELTA_star, DELTA_cur))
            self.fwDelta.writerow([strftime("%m-%d_%H:%M:%S", gmtime()), cntSteady, DELTA_star, DELTA_cur])
            
        d_global = c.get_d_global(True)
        d_group = c.get_d_group(True)
        tau1 = 5
        tau2 = 2
#         tau2 = int(d_budget)
#         if d_group < d_global:
#             tau2 = max( int((d_budget + d_group - d_global) / d_group), 1 )
#         else:
#             tau2 = 2
        print('Final DELTA_star=%.4f, tau1=%d, tau2=%d' % (DELTA_star, tau1, tau2))
    
        DELTA_star = c_star.get_DELTA(nid2_g_i__w, g__w)
        print('Final DELTA_star=%.4f, tau1=%d, tau2=%d' % (DELTA_star, tau1, tau2))
        
        print('IID Grouping Finished')
        return c_star, tau1, tau2, d_group, d_global
    
    def iterate_IID_Grouping(self, c, nid2_g_i__w, g__w):
        DELTA_cur = c.get_DELTA(nid2_g_i__w, g__w)

        # Iteration 마다 탐색 인덱스 셔플
        idx_Nid1 = np.arange(len(c.get_N()))
        np.random.shuffle(idx_Nid1)
        idx_Nid1 = idx_Nid1[:GROUPING_NUM_SAMPLE_NODE]

        idx_Nid2 = np.arange(len(c.get_N()))
        np.random.shuffle(idx_Nid2)
        idx_Nid2 = idx_Nid2[:GROUPING_NUM_SAMPLE_NODE]

        z = c.z
        for i in idx_Nid1:
            for j in idx_Nid2:
                # 목적지 그룹이 이전 그룹과 같을 경우 무시
                if z[i] == z[j]: continue
                    
                # 그룹 멤버쉽 변경 시도
                temp_k = z[i]
                z[i] = z[j]
                z[j] = temp_k
                
                nids_byGid = fl_util.to_nids_byGid(z)
                numClassesPerGroup = np.mean([ len(np.unique(np.concatenate([c.D_byNid[nid]['y'] for nid in nids]))) for nids in nids_byGid ])
                if numClassesPerGroup != 10:
                    # 데이터 분포가 IID 가 아니게 될 경우, 다시 원래대로 그룹 멤버쉽 초기화
                    temp_k = z[i]
                    z[i] = z[j]
                    z[j] = temp_k
                    continue
                    
                # 한 그룹에 노드가 전부 없어지는 것은 있을 수 없는 경우
                if c.digest(z) == False: raise Exception(str(z))
                    
                # 다음 후보에 대한 DELTA 계산
                DELTA_next = c.get_DELTA(nid2_g_i__w, g__w)
                
                if DELTA_cur > DELTA_next:
                    # 유리할 경우 변경
                    DELTA_cur = DELTA_next
                else:
                    # 유리하지 않을 경우, 다시 원래대로 그룹 멤버쉽 초기화 (다음 Iteration 에서 Digest)
                    temp_k = z[i]
                    z[i] = z[j]
                    z[j] = temp_k
    #         print(i, DELTA_cur)
    
        # 마지막 멤버십 초기화가 발생했을 수도 있으므로, Cloud Digest 시도
        if c.digest(z) == False: raise Exception(str(z))
        return DELTA_cur