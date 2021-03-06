import numpy as np

from scipy.stats import truncnorm
from collections import Counter
    
def sample(data_by1Nid, numSamples):
    return [ { 'x': data_by1Nid[0]['x'][:numSamples], 'y': data_by1Nid[0]['y'][:numSamples] } ]

def to_nids_byGid(z):
    gids = np.unique([gid for gid in z if isinstance(gid, int)]) # 숫자만 필터링(None 제외) 후 Unique 적용
    for gid in range(len(gids)):
        if not(gid in gids): raise Exception(str(gids)) # 모든 Group 이 사용되고 있는 지 검사
    nids_byGid = [ sorted([ nid for nid, gid in enumerate(z) if gid == gid_ ]) for gid_ in gids ]
    return nids_byGid

def to_z(numNodes, nids_byGid):
    # nids_byGid 에 없는 nid 가 있을 수도 있으므로 numNodes 를 입력받고, 모두 None 으로 초기화
    z = [ None for _ in range(numNodes) ]
    for gid, nids in enumerate(nids_byGid):
        for nid in nids:
            z[nid] = gid
    return z

def groupRandomly(numNodes, numGroups):
    numNodesPerGroup = partitionSumRandomly(numNodes, numGroups)
    z_rand = [ i for (i, numNodes) in enumerate(numNodesPerGroup) for _ in range(numNodes) ]
    np.random.shuffle(z_rand)
    return z_rand

def groupByClass(data_by1Nid):
    data_byClass = []
    for c in np.unique(data_by1Nid[0]['y']):
        idxExamplesForC = [ i for i, label in enumerate(data_by1Nid[0]['y']) if label == c ]
        data_byClass.append({ 'x': data_by1Nid[0]['x'][idxExamplesForC], 'y': data_by1Nid[0]['y'][idxExamplesForC] })
    return data_byClass

def partitionSumRandomly(targetSum, numPartitions):
    assert( targetSum >= numPartitions )
    if numPartitions == 1: return [ targetSum ]
    
    mu, sigma = 0, 1 # 표준 정규분포로 Sample 개수 가중치 생성
    weights = np.random.normal(mu, sigma, numPartitions)
#     weights = np.random.exponential(scale=1000, size=numPartitions)
    weights = 0.8 * (weights - np.min(weights)) / (np.max(weights) - np.min(weights)) + 0.1 # 모두 0보다 크게 하기 위해 0.1 ~ 0.9 범위로 정규화
    weightSum = sum(weights)
    ps = [ max(int(targetSum*weights[i]/weightSum), 1) for i in range(numPartitions) ] # 최소 한개 보장하기 위한 max(,1)
    if sum(ps) <= targetSum:
        # 부족할 경우 부족한 부분 채우기
        ps[-1] += targetSum - sum(ps)
    else:
        # 넘칠 경우 랜덤으로 넘치는 부분 줄이기
        cntIdx = 0
        while sum(ps) > targetSum:
            curIdx = cntIdx % numPartitions
            ps[curIdx] = ps[curIdx]-1 if ps[curIdx]>1 else ps[curIdx]
            cntIdx += 1
    assert( sum(ps) == targetSum )
    return ps

def groupByNode_old(data_by1Nid, nodeType, numNodes):
    numClasses = len(np.unique(data_by1Nid[0]['y']))
    if not(numNodes % numClasses == 0): raise Exception(str(numNodes) + ' ' + str(numClasses))
    data_byClass = groupByClass(data_by1Nid)
    data_byNid = []
    if nodeType == 't':
        numNodesPerClass = int(numNodes / numClasses)
        for c in range(numClasses):
            curNumSamples = len(data_byClass[c]['y'])
            ps = partitionSumRandomly(curNumSamples, numNodesPerClass)
            idxStart = 0 ; idxEnd = 0
            for p in ps:
                idxEnd += p
                data_byNid.append( { 'x': np.array(data_byClass[c]['x'][idxStart:idxEnd], dtype=np.float32),
                                     'y': np.array(data_byClass[c]['y'][idxStart:idxEnd], dtype=np.int32) } )
                idxStart += p
    elif nodeType == 'f':
        numClassSet = 5
        numNodesPerClassSet = int(numNodes / numClassSet)
        numClassesPerClassSet = int(numClasses / numClassSet)
        for cs in range(numClassSet):
            curData_byNid = []
            for c_ in range(numClassesPerClassSet):
                c = cs * numClassesPerClassSet + c_
                curNumSamples = len(data_byClass[c]['y'])
                ps = partitionSumRandomly(curNumSamples, numNodesPerClassSet)
                idxStart = 0 ; idxEnd = 0
                for i_ in range(numNodesPerClassSet):
                    idxEnd += ps[i_]
                    if len(curData_byNid) < numNodesPerClassSet:
                        curData_byNid.append( { 'x': np.array(data_byClass[c]['x'][idxStart:idxEnd], dtype=np.float32),
                                                'y': np.array(data_byClass[c]['y'][idxStart:idxEnd], dtype=np.int32) } )
                    else:
                        curData_byNid[i_]['x'] = np.append(curData_byNid[i_]['x'], data_byClass[c]['x'][idxStart:idxEnd], axis=0)
                        curData_byNid[i_]['y'] = np.append(curData_byNid[i_]['y'], data_byClass[c]['y'][idxStart:idxEnd])
                    idxStart += ps[i_]
            data_byNid += curData_byNid
    elif nodeType == 'h':
        numClassSet = 2
        numNodesPerClassSet = int(numNodes / numClassSet)
        numClassesPerClassSet = int(numClasses / numClassSet)
        for cs in range(numClassSet):
            curData_byNid = []
            for c_ in range(numClassesPerClassSet):
                c = cs * numClassesPerClassSet + c_
                curNumSamples = len(data_byClass[c]['y'])
                ps = partitionSumRandomly(curNumSamples, numNodesPerClassSet)
                idxStart = 0 ; idxEnd = 0
                for i_ in range(numNodesPerClassSet):
                    idxEnd += ps[i_]
                    if len(curData_byNid) < numNodesPerClassSet:
                        curData_byNid.append( { 'x': np.array(data_byClass[c]['x'][idxStart:idxEnd], dtype=np.float32),
                                                'y': np.array(data_byClass[c]['y'][idxStart:idxEnd], dtype=np.int32) } )
                    else:
                        curData_byNid[i_]['x'] = np.append(curData_byNid[i_]['x'], data_byClass[c]['x'][idxStart:idxEnd], axis=0)
                        curData_byNid[i_]['y'] = np.append(curData_byNid[i_]['y'], data_byClass[c]['y'][idxStart:idxEnd])
                    idxStart += ps[i_]
            data_byNid += curData_byNid
    elif nodeType == 'a':
        for c in range(numClasses):
            curNumSamples = len(data_byClass[c]['y'])
            ps = partitionSumRandomly(curNumSamples, numNodes)
            idxStart = 0 ; idxEnd = 0
            for i_ in range(numNodes):
                idxEnd += ps[i_]
                if len(data_byNid) < numNodes:
                    data_byNid.append( { 'x': np.array(data_byClass[c]['x'][idxStart:idxEnd], dtype=np.float32),
                                         'y': np.array(data_byClass[c]['y'][idxStart:idxEnd], dtype=np.int32) } )
                else:
                    data_byNid[i_]['x'] = np.append(data_byNid[i_]['x'], data_byClass[c]['x'][idxStart:idxEnd], axis=0)
                    data_byNid[i_]['y'] = np.append(data_byNid[i_]['y'], data_byClass[c]['y'][idxStart:idxEnd])
                idxStart += ps[i_]
    else:
        raise Exception(nodeType)
    return np.array(data_byNid)

def groupByEdge_old(data_by1Nid, nodeType, edgeType, numNodes, numEdges):
    numNodesPerEdge = int(numNodes / numEdges)
    numClasses = len(np.unique(data_by1Nid[0]['y']))
    if not(numEdges % numClasses == 0): raise Exception(str(numEdges) + ' ' + str(numClasses))
    if not(numNodesPerEdge % numClasses == 0): raise Exception(str(numNodesPerEdge) + ' ' + str(numClasses))
    numNodesPerClass = int(numNodes / numClasses)
    nids_byEid = []
    if (nodeType == 't' and edgeType == 't') \
        or (nodeType == 'f' and edgeType == 'f') \
        or (nodeType == 'h' and edgeType == 'h') \
        or (nodeType == 'a' and edgeType == 'a'):
        nids_byEid = [ [ k * numNodesPerEdge + i_ for i_ in range(numNodesPerEdge) ] for k in range(numEdges) ]
    elif nodeType == 't' and edgeType == 'f':
        numClassSet = 5
        for k in range(numClassSet):
            for j in range(numNodesPerClass):
                nids_byEid.append([ k * int(numNodes / numClassSet) + j + i * numNodesPerClass for i in range(int(numClasses / numClassSet)) ])
        nids_byEid = np.array(nids_byEid).reshape((numEdges, numNodesPerEdge)).tolist()
    elif nodeType == 't' and edgeType == 'h':
        numClassSet = 2
        for k in range(numClassSet):
            for j in range(numNodesPerClass):
                nids_byEid.append([ k * int(numNodes / numClassSet) + j + i * numNodesPerClass for i in range(int(numClasses / numClassSet)) ])
        nids_byEid = np.array(nids_byEid).reshape((numEdges, numNodesPerEdge)).tolist()
    elif nodeType == 'f' and edgeType == 'h':
        numClassSet = 2
        for k in range(numClassSet):
            for j in range(numNodesPerClass):
                nids_byEid.append([ k * int(numNodes / numClassSet) + j + i * numNodesPerClass for i in range(int(numClasses / numClassSet)) ])
        nids_byEid = np.array(nids_byEid).reshape((numEdges, numNodesPerEdge)).tolist()
    elif (nodeType == 't' and edgeType == 'a') \
        or (nodeType == 'f' and edgeType == 'a') \
        or (nodeType == 'h' and edgeType == 'a'):
        nids_byEid = [ [ j + i * numEdges for i in range(numNodesPerEdge) ] for j in range(numEdges) ]
    else:
        raise Exception(nodeType, edgeType)
    data_byNid = groupByNode_old(data_by1Nid, nodeType, numNodes)
    data_byNid = np.array([ data_byNid[nid] for nids in nids_byEid for nid in nids ]) # Node 오름차순으로 데이터 정렬
    z_edge = [ eid for eid in range(numEdges) for _ in range(numNodesPerEdge) ]
    return (data_byNid, z_edge)

def sample_truncated_normal(mean=1, sd=1, low=1, upp=10, size=1):
    if (low == upp): # NUM_CLASS_NODE = NUM_CLASS_EDGE인 경우-->한 EDGE내 모든 NODE는 같은 CLASS를 가짐. 
        sampled = [int(np.rint(low))]*size
    elif (mean >= upp) : # NUM_CLASS_NODE = NUM_CLASS_EDGE인 경우-->한 EDGE내 모든 NODE는 같은 CLASS를 가짐. 
        sampled = [int(np.rint(upp))]*size
    elif (mean <= low):
        sampled = [int(np.rint(low))]*size
    else:
        if (upp-low)/2 < mean:
            upp = upp + 0.5
        elif (upp-low)/2 == mean:
            pass
        else:
            low = low - 0.5
        sampled = truncnorm((low - mean) / sd, (upp - mean) / sd, loc=mean, scale=sd).rvs(size)
        sampled = [int(a) for a in np.rint(sampled)]
    return sampled

def groupByNode(data_by1Nid, nodeType, numNodes):
    data_byNid, z = groupByEdge(data_by1Nid, nodeType, 'a', numNodes, 1)
    return data_byNid

def groupByEdge(data_by1Nid, nodeType, edgeType, numNodes, numEdges):
    trainData_by1Nid = data_by1Nid
    NUM_CLASS = len(np.unique(trainData_by1Nid[0]['y']))
    
    # average # of class in each node
    if nodeType == 't':
        NUM_CLASS_NODE = max(NUM_CLASS/10, 1)
    elif nodeType == 'q':
        NUM_CLASS_NODE = max(NUM_CLASS/4, 1)
    elif nodeType == 'h':
        NUM_CLASS_NODE = max(NUM_CLASS/2, 1)
    elif nodeType == 'a':
        NUM_CLASS_NODE = NUM_CLASS
    else:
        raise Exception(nodeType)
    
    # average # of class in each edge
    if edgeType == 't':
        NUM_CLASS_EDGE = max(NUM_CLASS/10, 1)
    elif edgeType == 'q':
        NUM_CLASS_EDGE = max(NUM_CLASS/4, 1)
    elif edgeType == 'h':
        NUM_CLASS_EDGE = max(NUM_CLASS/2, 1)
    elif edgeType == 'a':
        NUM_CLASS_EDGE = NUM_CLASS
    else:
        raise Exception(edgeType)
    assert(NUM_CLASS_NODE <= NUM_CLASS_EDGE)

    NUM_NODES = numNodes
    NUM_EDGES = numEdges
    NUM_NODES_PER_EDGE = int(NUM_NODES / NUM_EDGES)
    assert(NUM_NODES % NUM_EDGES == 0)
    
    NUM_DATA_CLASS = [ len(x['x']) for x in groupByClass(data_by1Nid) ]
    choice_prob = np.array(NUM_DATA_CLASS)/np.sum(NUM_DATA_CLASS)
    
    EDGE_CLASS_LIST_UNIQUE = np.zeros(NUM_CLASS-1).tolist()
    while(len(EDGE_CLASS_LIST_UNIQUE)!=NUM_CLASS): # check whether all class are sampled at least once in all nodes
        EDGE_CLASS_LIST = []
        EDGE_NODE_CLASS_LIST = []
        
        
        ########### New CODE 20200117 #################
        NUM_CLASS_EDGE_SAMPLED_MEAN = -100
        
        while(np.abs(NUM_CLASS_EDGE_SAMPLED_MEAN - NUM_CLASS_EDGE)>0.1): # mean error should be lower than 0.1
            NUM_CLASS_EDGE_SAMPLED = sample_truncated_normal(mean=NUM_CLASS_EDGE, sd=1, low=1, upp=NUM_CLASS, size=NUM_EDGES)
            NUM_CLASS_EDGE_SAMPLED_MEAN = np.mean(NUM_CLASS_EDGE_SAMPLED)
        
        
        class_left = set(list(range(NUM_CLASS)))
        num_allocated_edges = 0
        
        while(len(class_left) != 0): # check whether all class are sampled at least once in all edges
            if NUM_CLASS_EDGE_SAMPLED[num_allocated_edges] > len(class_left):
                class_list = list(class_left)
                class_left_complement_list = list(set(range(NUM_CLASS)).difference(class_left))
                p = choice_prob[class_left_complement_list]/np.sum(choice_prob[class_left_complement_list])
                class_list_rest = np.random.choice(class_left_complement_list, NUM_CLASS_EDGE_SAMPLED[num_allocated_edges]-len(class_list), replace=False, p=p).tolist()
                class_list += class_list_rest
            else:
                p = choice_prob[list(class_left)]/np.sum(choice_prob[list(class_left)])
                class_list = np.random.choice(list(class_left), NUM_CLASS_EDGE_SAMPLED[num_allocated_edges], replace=False, p=p).tolist()
            EDGE_CLASS_LIST.append(class_list)
            EDGE_NODE_CLASS_LIST.append([])
            class_left.difference_update(set(class_list))
            num_allocated_edges += 1

        for i in range(NUM_EDGES-num_allocated_edges):
            i += num_allocated_edges
            class_list = np.random.choice(list(range(NUM_CLASS)), NUM_CLASS_EDGE_SAMPLED[i], replace=False, p=choice_prob).tolist()
            EDGE_CLASS_LIST.append(class_list)
            EDGE_NODE_CLASS_LIST.append([])
        EDGE_CLASS_LIST_UNIQUE = np.unique([item for sublist in EDGE_CLASS_LIST for item in sublist])
        ########### New CODE 20200117 #################
        
#         for i in range(NUM_EDGES):
#             class_list = np.random.choice(list(range(NUM_CLASS)), NUM_CLASS_EDGE_SAMPLED[i], replace=False, p=choice_prob).tolist()
#             EDGE_CLASS_LIST.append(class_list)
#             EDGE_NODE_CLASS_LIST.append([])
#         EDGE_CLASS_LIST_UNIQUE = np.unique([item for sublist in EDGE_CLASS_LIST for item in sublist])
        
        
    NODE_CLASS_LIST_UNIQUE = np.zeros(NUM_CLASS-1).tolist()
    NODE_CLASS_NUM_SAMPLED_MEAN = -100
    SEARCH_LIMIT = 0
    min_error = 100000
    while((len(NODE_CLASS_LIST_UNIQUE) < NUM_CLASS) and (np.abs(NODE_CLASS_NUM_SAMPLED_MEAN-NUM_CLASS_NODE)>0.1)): # check whether all class are sampled at least once
        if SEARCH_LIMIT > 1000:
            break
        SEARCH_LIMIT += 1
        
#         for i in range(NUM_EDGES): # select class in the nodes for an edge
#             edge_class_list = EDGE_CLASS_LIST[i]       
#             EDGE_CLASS_LIST_REAL_FLAT = np.zeros(NUM_CLASS+1)
            
#             while (len(EDGE_CLASS_LIST_REAL_FLAT) != len(EDGE_CLASS_LIST[i])): # check whether all nodes in a edge sample all class assigned to the edge
#                 EDGE_NODE_CLASS_LIST[i] = []
#                 for j in range(NUM_NODES_PER_EDGE):
#                     num_class_in_node = sample_truncated_normal(mean=NUM_CLASS_NODE, sd=1, low=1, upp=len(edge_class_list),size=1)
#                     class_in_node = np.random.choice(edge_class_list, num_class_in_node, replace=False).tolist()
#                     EDGE_NODE_CLASS_LIST[i].append(class_in_node)
#                 EDGE_CLASS_LIST_REAL_FLAT = np.unique([item for sublist in EDGE_NODE_CLASS_LIST[i] for item in sublist])


        for i in range(NUM_EDGES): # select class in the nodes for an edge
            EDGE_NODE_CLASS_LIST[i] = []
            edge_class_list = EDGE_CLASS_LIST[i]  
            
            
            NUM_CLASS_NODE_SAMPLED_MEAN = -100
            while(np.abs(NUM_CLASS_NODE_SAMPLED_MEAN - NUM_CLASS_NODE)>0.1): # mean error should be lower than 0.1 for sampling the number of class in each node for an edge
                NUM_CLASS_NODE_SAMPLED = sample_truncated_normal(mean=NUM_CLASS_NODE, sd=1, low=1, upp=len(edge_class_list), size=NUM_NODES_PER_EDGE)
                NUM_CLASS_NODE_SAMPLED_MEAN = np.mean(NUM_CLASS_NODE_SAMPLED)
                if len(edge_class_list) < NUM_CLASS_NODE:
                    break
            
            class_left = set(edge_class_list)
            num_allocated_nodes = 0
            while(len(class_left) != 0): # check whether all class are sampled at least once in the nodes for an edge
                if NUM_CLASS_NODE_SAMPLED[num_allocated_nodes] > len(class_left):
                    class_list = list(class_left)
                    class_left_complement_list = list(set(edge_class_list).difference(class_left))
                    p = choice_prob[class_left_complement_list]/np.sum(choice_prob[class_left_complement_list])
                    class_list_rest = np.random.choice(class_left_complement_list, NUM_CLASS_NODE_SAMPLED[num_allocated_nodes]-len(class_list), replace=False, p=p).tolist()
                    class_list += class_list_rest
                else:
                    p = choice_prob[list(class_left)]/np.sum(choice_prob[list(class_left)])
                    class_list = np.random.choice(list(class_left), NUM_CLASS_NODE_SAMPLED[num_allocated_nodes], replace=False, p=p).tolist()
                EDGE_NODE_CLASS_LIST[i].append(class_list)
                class_left.difference_update(set(class_list))
                num_allocated_nodes += 1

            for j in range(NUM_NODES_PER_EDGE-num_allocated_nodes): # allocate class to rest of nodes in an edge
                j += num_allocated_nodes
                p = choice_prob[edge_class_list]/np.sum(choice_prob[edge_class_list])
                class_list = np.random.choice(edge_class_list, NUM_CLASS_NODE_SAMPLED[j], replace=False, p=p).tolist()
                EDGE_NODE_CLASS_LIST[i].append(class_list)
            
        EDGE_NODE_CLASS_LIST_FLAT = [iitem for sublist in EDGE_NODE_CLASS_LIST for item in sublist for iitem in item]
        NODE_CLASS_LIST_UNIQUE = np.unique(EDGE_NODE_CLASS_LIST_FLAT)
        NODE_CLASS_NUM_SAMPLED_MEAN = np.mean([len(item) for sublist in EDGE_NODE_CLASS_LIST for item in sublist])
        
        min_error_new = np.abs(NODE_CLASS_NUM_SAMPLED_MEAN-NUM_CLASS_NODE)
        if min_error_new < min_error:
            EDGE_NODE_CLASS_LIST_SAVED = EDGE_NODE_CLASS_LIST
    
#     print(EDGE_NODE_CLASS_LIST)
    
    EDGE_NODE_CLASS_LIST = EDGE_NODE_CLASS_LIST_SAVED
    EDGE_NODE_CLASS_LIST_FLAT = [iitem for sublist in EDGE_NODE_CLASS_LIST for item in sublist for iitem in item]
    EDGE_NODE_CLASS_LIST_FLAT_2 = [item for sublist in EDGE_NODE_CLASS_LIST for item in sublist]
    Class_Counter = Counter(EDGE_NODE_CLASS_LIST_FLAT) # number of sampled class in all nodes

    DATA_BY_CLASS = groupByClass(trainData_by1Nid)
    for i in range(NUM_CLASS): # ensure data type
        DATA_BY_CLASS[i]['x'] = DATA_BY_CLASS[i]['x'].astype(np.float32)
        DATA_BY_CLASS[i]['y'] = DATA_BY_CLASS[i]['y'].astype(np.int32)
    
    
    NUM_DATA_PER_CLASS = [len(x['x']) for x in DATA_BY_CLASS]

    NUM_DATA_PER_SAMPLED_CLASS = []
    for i in range(NUM_CLASS):
        NUM_DATA_PER_SAMPLED_CLASS.append(DATA_BY_CLASS[i]['x'].shape[0]/Class_Counter[i])
    
    trainData_byNid = []
    z_edge = []
    
    for edge_ind in range(NUM_EDGES):
        for node_class_list in EDGE_NODE_CLASS_LIST[edge_ind]:
            initial_counter = 0
            z_edge.append(edge_ind)
            for i in node_class_list: # i-th node
                if initial_counter == 0: # make initial x,y dictionary for each node
                    num_sampled = sample_truncated_normal(mean=NUM_DATA_PER_SAMPLED_CLASS[i], sd = 1, low=1, upp=2*NUM_DATA_PER_SAMPLED_CLASS[i], size=1)[0] # number of datapoint for a class in a node
                    if num_sampled > 2:
                        num_sampled -= 1
                    if NUM_DATA_PER_CLASS[i] > num_sampled:
                        indice_sampled = np.random.choice(range(NUM_DATA_PER_CLASS[i]), size=num_sampled, replace=False).tolist()
                        trainData_byNid.append({'x':DATA_BY_CLASS[i]['x'][indice_sampled] , 'y':DATA_BY_CLASS[i]['y'][indice_sampled]})
                        DATA_BY_CLASS[i]['x'] = np.delete(DATA_BY_CLASS[i]['x'], indice_sampled,0)
                        DATA_BY_CLASS[i]['y'] = np.delete(DATA_BY_CLASS[i]['y'], indice_sampled,0)
                        NUM_DATA_PER_CLASS[i] = NUM_DATA_PER_CLASS[i] - num_sampled
                        initial_counter += 1
                    else:
                        num_sampled = NUM_DATA_PER_CLASS[i]
                        indice_sampled = np.random.choice(range(NUM_DATA_PER_CLASS[i]), size=num_sampled, replace=False).tolist()
                        trainData_byNid.append({'x':DATA_BY_CLASS[i]['x'][indice_sampled] , 'y':DATA_BY_CLASS[i]['y'][indice_sampled]})
                        DATA_BY_CLASS[i]['x'] = np.delete(DATA_BY_CLASS[i]['x'], indice_sampled,0)
                        DATA_BY_CLASS[i]['y'] = np.delete(DATA_BY_CLASS[i]['y'], indice_sampled,0)
                        NUM_DATA_PER_CLASS[i] = 0
                        initial_counter += 1
                else: # add next datapoint from other class to x,y dictionary for each node
                    num_sampled = sample_truncated_normal(mean=NUM_DATA_PER_SAMPLED_CLASS[i], sd = 1, low=1, upp=2*NUM_DATA_PER_SAMPLED_CLASS[i], size=1)[0] # number of datapoint for a class in a node
                    if NUM_DATA_PER_CLASS[i] > num_sampled:
                        indice_sampled = np.random.choice(range(NUM_DATA_PER_CLASS[i]), size=num_sampled, replace=False).tolist()
                        trainData_byNid[-1]['x'] = np.concatenate([trainData_byNid[-1]['x'],DATA_BY_CLASS[i]['x'][indice_sampled]])
                        trainData_byNid[-1]['y'] = np.concatenate([trainData_byNid[-1]['y'],DATA_BY_CLASS[i]['y'][indice_sampled]])
                        DATA_BY_CLASS[i]['x'] = np.delete(DATA_BY_CLASS[i]['x'], indice_sampled,0)
                        DATA_BY_CLASS[i]['y'] = np.delete(DATA_BY_CLASS[i]['y'], indice_sampled,0)
                        NUM_DATA_PER_CLASS[i] = NUM_DATA_PER_CLASS[i] - num_sampled
                    else:
                        num_sampled = NUM_DATA_PER_CLASS[i]
                        indice_sampled = np.random.choice(range(NUM_DATA_PER_CLASS[i]), size=num_sampled, replace=False).tolist()
                        trainData_byNid[-1]['x'] = np.concatenate([trainData_byNid[-1]['x'],DATA_BY_CLASS[i]['x'][indice_sampled]])
                        trainData_byNid[-1]['y'] = np.concatenate([trainData_byNid[-1]['y'],DATA_BY_CLASS[i]['y'][indice_sampled]])
                        DATA_BY_CLASS[i]['x'] = np.delete(DATA_BY_CLASS[i]['x'], indice_sampled,0)
                        DATA_BY_CLASS[i]['y'] = np.delete(DATA_BY_CLASS[i]['y'], indice_sampled,0)
                        NUM_DATA_PER_CLASS[i] = 0

    nids_byGid = to_nids_byGid(z_edge)
    trainData_byNid_NODE_CLASS_LIST = [np.unique(trainData_byNid[nid]['y']).tolist() for nids in nids_byGid for nid in nids]
    for i in range(NUM_CLASS):
        if NUM_DATA_PER_CLASS[i] != 0:
            node_index = 0
            node_cand = []
            for j in trainData_byNid_NODE_CLASS_LIST:
                if i in j:
                    node_cand.append(node_index)
                node_index += 1
            if NUM_DATA_PER_CLASS[i] > len(node_cand):
                node_samp = np.random.choice(node_cand, size = NUM_DATA_PER_CLASS[i], replace=True).tolist()
            else:
                node_samp = np.random.choice(node_cand, size = NUM_DATA_PER_CLASS[i], replace=False).tolist()
            for k in node_samp:
                trainData_byNid[k]['x'] = np.concatenate([trainData_byNid[k]['x'],DATA_BY_CLASS[i]['x'][[0]]])
                trainData_byNid[k]['y'] = np.concatenate([trainData_byNid[k]['y'],DATA_BY_CLASS[i]['y'][[0]]])
                DATA_BY_CLASS[i]['x'] = np.delete(DATA_BY_CLASS[i]['x'], 0,0)
                DATA_BY_CLASS[i]['y'] = np.delete(DATA_BY_CLASS[i]['y'], 0,0)
                NUM_DATA_PER_CLASS[i] = NUM_DATA_PER_CLASS[i] - 1

    for i in range(NUM_CLASS):
        assert(NUM_DATA_PER_CLASS[i] == 0)
        assert(len(DATA_BY_CLASS[i]['x']) == 0)
        assert(len(DATA_BY_CLASS[i]['y']) == 0)
    
    datanum = 0
    for node in trainData_byNid:
        datanum += len(node['x'])
    assert(datanum == len(data_by1Nid[0]['x']))
    
    return (trainData_byNid, z_edge)