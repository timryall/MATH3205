from gurobipy import *

EPS = 0.0001

Resources = ["Lumber", "Finishing", "Carpentry"]
Products = ["Desk", "Table", "Chair"]

R = range(len(Resources))
P = range(len(Products))

Cost = [2,4,5.2]
Input = [
        [8,6,1],
        [4,2,1.5],
        [2,1.5,0.5]]

Prob = [0.3,0.4,0.3]
S = range(len(Prob))

Demand = [
    [50,150,250],
    [20,110,250],
    [200,225,500]]

Sell = [60,40,10]

