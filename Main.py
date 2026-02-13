# Import packages

from gurobipy import GRB
import pandas as pd
import numpy as np 
from OptimizationClasses import LP_InputData, Expando, LP_OptimizationProblem
from data.data import *

num_variables_G = 12
num_variables_W = 6
num_variables_D = 17

# total constraints: one upper and one lower per unit (gen + wind) and per load
num_constraints_U = num_variables_G + num_variables_W + num_variables_D
num_constraints_L = num_variables_G + num_variables_W + num_variables_D
#num_constraints_D = num_variables_D

# define variable and constraint names consistently
VARIABLES = [f"g{i+1}" for i in range(num_variables_G)] + [f"w{i+1}" for i in range(num_variables_W)] + [f"d{i+1}" for i in range(num_variables_D)]
U_KEYS = [f"u{i+1}" for i in range(num_constraints_U)]
L_KEYS = [f"l{i+1}" for i in range(num_constraints_L)]


# objective coefficients
objective_coeff = {f"g{i+1}": unit_cost_G["C_i"][i] for i in range(num_variables_G)}
objective_coeff |= {f"w{i+1}": 0 for i in range(num_variables_W)}

objective_coeff |= {f"d{i+1}": -demand['Bid_price'][i] for i in range(num_variables_D)}

# helper to build a constraint coeff dict that contains all variables (zero for others)
def one_hot_coeff_for_index(idx, sign=1):
    # idx: 0-based index over VARIABLES (generators then wind)
    coeff = {v: 0 for v in VARIABLES}
    if 0 <= idx < len(VARIABLES):
        coeff[VARIABLES[idx]] = sign
    return coeff

# build constraints coefficients: upper bounds (u1..u18) -> 1 for corresponding variable
constraints_coeff = {}
for i in range(num_constraints_U):
    constraints_coeff[U_KEYS[i]] = one_hot_coeff_for_index(i, sign=1)

# lower bounds represented as -x <= 0  -> coefficient -1 for corresponding variable
for i in range(num_constraints_L):
    constraints_coeff[L_KEYS[i]] = one_hot_coeff_for_index(i, sign=-1)

constraints_coeff["balance"] = {v: 1 for v in VARIABLES[:len(VARIABLES)-num_variables_D]} 
constraints_coeff["balance"].update({v: -1 for v in VARIABLES[len(VARIABLES)-num_variables_D:]}) # only generators and wind in balance constraint

# build RHS: upper bounds from technical data, lower bounds zero, balance set to demand

def rhs_function(num_variables_G, num_variables_W, num_variables_D):
    constraints_rhs = {}

    for i in range(num_variables_G):
        constraints_rhs[U_KEYS[i]] = technical_data_G["P_max"][i]
    for i in range(num_variables_W):
        constraints_rhs[U_KEYS[num_variables_G + i]] = technical_data_W["P_max"][i]
    for i in range(num_variables_D):
        constraints_rhs[U_KEYS[num_variables_G + num_variables_W + i]] = demand['D_max %'][i]*max(load_curve['load_MW'])/100

    constraints_rhs["balance"] = 0

    for i in range(num_constraints_L):
        constraints_rhs[L_KEYS[i]] = 0

    return constraints_rhs

#constraints_rhs = {}
#for i in range(num_variables_G):
#    constraints_rhs[U_KEYS[i]] = technical_data_G["P_max"][i]
#for i in range(num_variables_W):
#    constraints_rhs[U_KEYS[num_variables_G + i]] = technical_data_W["P_max"][i]
#
#for i in range(num_constraints_L):
#    constraints_rhs[L_KEYS[i]] = 0

#constraints_rhs["balance"] = 2650.5

# constraint senses: use LESS_EQUAL for u and l (l uses -x <= 0), equality for balance
constraints_sense = {k: GRB.LESS_EQUAL for k in U_KEYS + L_KEYS}
constraints_sense["balance"] = GRB.EQUAL

input_data = LP_InputData(
    VARIABLES = VARIABLES,
    CONSTRAINTS = U_KEYS + L_KEYS + ["balance"],
    objective_coeff = objective_coeff,
    constraints_coeff = constraints_coeff,
    constraints_rhs = rhs_function(num_variables_G, num_variables_W, num_variables_D),
    constraints_sense = constraints_sense,
    objective_sense = GRB.MINIMIZE,
    model_name = "Economic dispatch problem"
)

problem = LP_OptimizationProblem(input_data)
problem.run()
problem.display_results()

# hola