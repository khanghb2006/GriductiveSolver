"""
    SAT-backed Logic Agent: classifies unsolved cells by logical
        entailment
"""
from .logic import CRIMINAL, INNOCENT, UNKNOWN , Inference

class SatAgent:
    def __init__(self, build_kb , solve):
        self.build_kb = build_kb # public_state -> KB(clauses , n_primary , n_aux)
        self.solve = solve # (clauses , n_vars , assumptions) -> Solve Result
        
    def classify(self , public_state):
        kb = self.build_kb(public_state)
        n_vars = kb.n_primary + kb.n_aux
        
        def satisfiable(*assumptions):
            return self.solve(kb.clauses , n_vars , assumptions).sat
        
        if not satisfiable():
            return Inference({} , 0) # KB itself UNSAT
        
        statuses = {}
        for var , cell in enumerate(public_state['layout'] , start = 1):
            if cell['id'] in public_state['known']:
                continue # skip known cells
            
            can_be_criminal = satisfiable(var) # var = True
            can_be_innocent = satisfiable(-var) # var = False
            
            statuses[cell['id']] = (
                UNKNOWN if can_be_criminal and can_be_innocent
                else CRIMINAL if can_be_criminal
                else INNOCENT
            )
        return Inference(statuses , 1) # model_count = 1 since KB is SAT
    
