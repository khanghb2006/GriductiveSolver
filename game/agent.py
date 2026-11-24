"""
    SAT-backed Logic Agent: classifies unsolved cells by logical
        entailment
"""
from .logic import CRIMINAL, INNOCENT, UNKNOWN , Inference , proof_support

ACCEPTED , NOT_PROVABLE = 'ACCEPTED' , 'NOT_PROVABLE'
CONTRADICTED , INCONSISTENT =  'CONTRADICTED' , 'INCONSISTENT'
FORCED , STUCK = 'FORCED' , 'STUCK'
UNIQUE , MULTIPLE , NO_SOLUTION = 'UNIQUE' , 'MULTIPLE' , 'NO_SOLUTION'


def _value(model , var):
    # Value of variable var in a model given
    return model[var] if isinstance(model , dict) else model[var - 1]


class SatAgent:
    def __init__(self, build_kb , solve):
        self.build_kb = build_kb # public_state -> KB(clauses , n_primary , n_aux)
        self.solve = solve # (clauses , n_vars , assumptions) -> Solve Result
        self.queries = [] # queries for trace
        
    def classify(self , public_state):
        kb = self.build_kb(public_state)
        n_vars = kb.n_primary + kb.n_aux
        queries = self.queries = []
        
        def satisfiable(*assumptions):
            sat = self.solve(kb.clauses , n_vars , assumptions).sat
            queries.append((assumptions , sat))
            return sat

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
    
    def check_verdict(self , public_state , cell , verdict):
        inference = self.classify(public_state)
        
        if not inference.model_count:
            return INCONSISTENT # KB itself UNSAT
        
        forced = inference.statuses.get(cell , UNKNOWN)
        
        if forced == UNKNOWN:
            return NOT_PROVABLE # verdict is not forced
        
        return ACCEPTED if forced == verdict else CONTRADICTED # verdict is forced
        
    def step(self , public_state):
        inference = self.classify(public_state)
        
        if not inference.model_count:
            return dict(outcome = INCONSISTENT)
        
        queries = self.queries
        
        for cell in public_state['layout']:
            verdict = inference.statuses.get(cell['id'] , UNKNOWN)

            if verdict != UNKNOWN:
                used = proof_support(self , public_state , cell['id'] , verdict)
            
                return dict(outcome = FORCED , cell = cell['id'] , verdict = verdict,
                        clues_ids = [c['id'] for c in used] , queries = queries)
            
        return dict(outcome = STUCK)
    
    def auto_solve(self , engine):
        trace = []
        
        while True:
            state = engine.knowledge()
            if len(state['known']) == len(state['layout']):
                return 'COMPLETE' , trace
            
            found  = self.step(state)
            if found['outcome'] != FORCED:
                return found['outcome'] , trace
            
            seen = {c['id'] for c in state['clues']}
            result = engine.verdict(found['cell'] , found['verdict'])
            
            if result['code'] != 'ACCEPTED':
                return result['code'] , trace
            
            revealed = [c['id'] for c in engine.knowledge()['clues'] if c['id'] not in seen]
            trace.append(dict(step = len(trace) + 1 , cell = found['cell'],
                              verdict = found['verdict'],
                              clue_ids = found['clues_ids'] ,
                              sat_queries = len(found['queries']) , 
                              revealed = revealed))
            
    
    def unique_check(self , all_clues , n):
        layout = [dict(id = f'{chr(65 + col)}{row}' , row = row , column = col + 1)
                  for row in range(1 , n + 1) for col in range(n)]
        
        kb = self.build_kb(dict(layout = layout , known = {} , clues = list(all_clues)))
        n_vars = kb.n_primary + kb.n_aux
        
        first = self.solve(kb.clauses , n_vars , ())
        
        if not first.sat:
            return NO_SOLUTION
        
        # Forbit exactly this solution
        block = [-v if _value(first.model , v) else v for v in range(1 , kb.n_primary + 1)]
        again = self.solve(kb.clauses + [block] , n_vars , ())
        return MULTIPLE if again.sat else UNIQUE
            