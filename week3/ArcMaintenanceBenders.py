import gurobipy as gp

# Initialise empty data
Nodes = []
Arcs = []
BackArc = None
FromNode = -1

EPS = 1e-4

# Read in the data
with open('Outmax_flow2.dat') as f:
    while True:
        l = f.readline().strip()
        if l[0]=='n':
            FromNode = len(Nodes)
            Nodes.append(l)
        elif l[0]=='a':
            t = l.split(' ')
            flow = int(t[4])
            ToNode = int(t[3])
            if flow==10000:
                BackArc = len(Arcs)
            Arcs.append((FromNode,ToNode,flow))
        else:
            break
N = range(len(Nodes))
A = range(len(Arcs))

print('Nodes and Arcs', len(Nodes), len(Arcs))

# Empty array of jobs
Jobs = []
with open('max_flow2.dat_Job0') as f:
    while True:
        l = f.readline().strip()
        if len(l) <= 1:
            break
        nArc = int(l.split(' ')[1])
        t = f.readline().strip().split(' ')
        Jobs.append((nArc,int(t[1])-1,int(t[2])-1,int(t[3])))
        
T = range(1000)
J = range(len(Jobs))
# The jobs for an arc
JobsA = [[j for j in J if Jobs[j][0]==a] for a in A]
# The starting time periods for job A
JP = [range(Jobs[j][1], Jobs[j][2]) for j in J]

print('Jobs', len(Jobs))
# The jobs and their indices that impact on arc a in time t
JobsTA = [[[(j,p) for j in JobsA[a] for p in JP[j] if p<=t and p+Jobs[j][3]>t]
           for a in A] for t in T]
print('Calculated JobsTA')

BSP = gp.Model('Benders Subproblem')
BSP.Params.OutputFlag = 0

X = {a: BSP.addVar() for a in A}

ConserveFlow = {n:
    BSP.addConstr(gp.quicksum(X[a] for a in A if Arcs[a][0]==n)==
                gp.quicksum(X[a] for a in A if Arcs[a][1]==n))
    for n in N}
    
ArcBound = {a:
    BSP.addConstr(X[a]<=Arcs[a][2])
                # (1-gp.quicksum(Y[j,tt] for (j,tt) in JobsTA[t][a])))
    for a in A}

BSP.setObjective(X[BackArc], gp.GRB.MAXIMIZE)
BSP.optimize()

BMP = gp.Model('Network Maintenance')

Y = {(j,t): BMP.addVar(vtype=gp.GRB.BINARY) for j in J for t in JP[j]}
Theta = {t: BMP.addVar(ub=BSP.ObjVal) for t in T}
EachJobOnce = {j: 
    BMP.addConstr(gp.quicksum(Y[j,t] for t in JP[j])==1) 
    for j in J}
    
BMP.setObjective(gp.quicksum(Theta[t] for t in T), gp.GRB.MAXIMIZE)
    

BMP.Params.MIPGap = 0 
BMP.Params.Threads = 8
BMP.Params.LazyConstraints = 1
BMP.Params.BranchDir = 1

_SolutionCache = {}

def SolveSub(ArcsOff):
    if ArcsOff not in _SolutionCache:
        for a in ArcsOff:
            ArcBound[a].RHS = 0
        BSP.optimize()
        _SolutionCache[ArcsOff] = (BSP.ObjVal,{a: ArcBound[a].pi for a in A})
        for a in ArcsOff:
            ArcBound[a].RHS = Arcs[a][2]
    return _SolutionCache[ArcsOff]

BMP._BestSolution = 0
    
def Callback(model,where):
    if where==gp.GRB.Callback.MIPSOL:
        YV = model.cbGetSolution(Y)
        ThetaV = model.cbGetSolution(Theta)
        CutsAdded = 0
        for t in T:
            ArcsOff = tuple(a for a in A 
                if round(sum(YV[j,tt] for (j,tt) in JobsTA[t][a]))==1)
            ObjVal, DualDict = SolveSub(ArcsOff)
            if ObjVal < ThetaV[t]-EPS:
                ThetaV[t] = ObjVal
                CutsAdded+=1
                model.cbLazy(Theta[t]<=
                     gp.quicksum(DualDict[a]*Arcs[a][2]*
                        (1-gp.quicksum(Y[j,tt] for (j,tt) in JobsTA[t][a]))
                        for a in A))
        if CutsAdded==0 and sum(ThetaV.values())>BMP._BestSolution + EPS:
            BMP._BestSolution = sum(ThetaV.values())
            if BMP._BestSolution > model.cbGet(gp.GRB.Callback.MIPSOL_OBJBST)+EPS:
                print('Posting', BMP._BestSolution)
                model.cbSetSolution(Y,YV)
                model.cbSetSolution(Theta,ThetaV)
            
# Warm start
for v in Y.values():
    v.vType = gp.GRB.CONTINUOUS
    
for k in range(10):
    BMP.optimize()
    CutsAdded = 0
    for t in T:
        for a in A:
            ArcBound[a].RHS = Arcs[a][2]*(1-sum(Y[j,tt].x for (j,tt) in JobsTA[t][a]))
        BSP.optimize()
        if BSP.ObjVal < Theta[t].x - EPS:
            CutsAdded += 1
            BMP.addConstr(Theta[t]<=
                gp.quicksum(ArcBound[a].pi*Arcs[a][2]*
                   (1-gp.quicksum(Y[j,tt] for (j,tt) in JobsTA[t][a]))
                   for a in A))
    if CutsAdded==0:
        break
    print('*****************************************')
    print(CutsAdded, BMP.ObjVal)
    print('*****************************************')
        
for v in Y.values():
    v.vType = gp.GRB.BINARY
    

BMP.optimize(Callback)



