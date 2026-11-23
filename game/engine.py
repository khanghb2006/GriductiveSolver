from copy import deepcopy
from threading import RLock
from .logic import (CRIMINAL, INNOCENT, UNKNOWN, ExhaustiveAgent,
                    referenced_cells, proof_support, evaluate)
from .puzzles import PUZZLES


def clue_text(clue, layout):
    cells = ' · '.join(referenced_cells(clue, layout))
    kind = clue['type']
    if kind == 'FACT':
        return f'{cells} là ' + ('Đồng phạm.' if clue['status'] == CRIMINAL else 'Vô can.')
    if kind == 'SAME':
        return f'{cells}: hai người có cùng trạng thái.'
    if kind == 'DIFFERENT':
        return f'{cells}: một Đồng phạm và một Vô can.'
    prefix = {'EXACTLY':'Đúng', 'AT_LEAST':'Ít nhất', 'AT_MOST':'Nhiều nhất'}[kind]
    return f'{prefix} {clue["k"]} Đồng phạm trong nhóm: {cells}.'


class GameEngine:
    def __init__(self, puzzle_id='village-3', agent=None):
        self.agent = agent or ExhaustiveAgent()
        self.lock = RLock()
        self.load(puzzle_id)

    def load(self, puzzle_id):
        self.puzzle = deepcopy(PUZZLES[puzzle_id])
        self.known = {c: CRIMINAL if self.puzzle['solution'][c] else INNOCENT
                      for c in self.puzzle['initial']}
        self.hint_level = 0
        self.history = []

    def knowledge(self):
        return deepcopy(dict(layout=self.puzzle['layout'], known=self.known,
                             clues=[self.puzzle['clues'][c] for c in self.known]))

    def view(self):
        p = self.puzzle
        clues = []
        for clue in self.knowledge()['clues']:
            owner = clue['owner']
            clues.append(clue | dict(cells=referenced_cells(clue,p['layout']),
                text=clue_text(clue,p['layout']),
                heading='Lời trăn trối' if self.known[owner] == CRIMINAL else 'Lời chứng',
                flavor='Tiếng chuông đã tắt. Nhưng sự thật thì chưa.'))
        return dict(puzzle_id=p['id'], title=p['title'], size=p['size'],
            layout=deepcopy(p['layout']), known=dict(self.known), clues=clues,
            progress=len(self.known), total=len(p['layout']),
            completed=len(self.known)==len(p['layout']), history=list(self.history))

    def verdict(self, cell, status):
        if cell not in self.puzzle['solution'] or status not in (CRIMINAL, INNOCENT):
            return dict(code='INVALID_REQUEST', message='Phán quyết không hợp lệ.')
        if cell in self.known:
            return dict(code='ALREADY_REVEALED', message='Nhân vật đã được xét xử.')
        state = self.knowledge()
        result = self.agent.classify(state)
        # Validate all public evidence against the authored assignment before any mutation.
        solution = self.puzzle['solution']
        if not result.model_count or any((s == CRIMINAL) != solution[c] for c,s in self.known.items()) or not all(
                evaluate(c, solution, state['layout']) for c in state['clues']):
            return dict(code='DATA_ERROR', message='Dữ kiện mâu thuẫn. Phiên tòa tạm dừng.')
        forced = result.statuses.get(cell, UNKNOWN)
        if forced == UNKNOWN:
            return dict(code='NOT_PROVABLE', message='Chưa đủ căn cứ để phán.')
        if (forced == CRIMINAL) != solution[cell]:
            return dict(code='DATA_ERROR', message='Kết luận lệch dữ liệu màn. Phiên tòa tạm dừng.')
        if status != forced:
            return dict(code='CONTRADICTED', message='Bằng chứng chỉ ra điều ngược lại.')
        self.known[cell] = status
        self.hint_level = 0
        self.history.append(dict(step=len(self.history)+1, cell=cell, status=status))
        return dict(code='ACCEPTED', message=f'{cell}: phán quyết được chứng minh.')

    def auto_step(self):
        if len(self.known) == len(self.puzzle['layout']):
            return dict(code='COMPLETE', message='Phiên tòa hoàn tất. Sự thật đã sáng tỏ.')
        result = self.agent.classify(self.knowledge())
        if not result.model_count:
            return dict(code='DATA_ERROR', message='Dữ kiện mâu thuẫn. Phiên tòa tạm dừng.')
        for cell in self.puzzle['layout']:
            status = result.statuses.get(cell['id'], UNKNOWN)
            if cell['id'] not in self.known and status != UNKNOWN:
                return self.verdict(cell['id'],status)
        return dict(code='STUCK', message='Không còn phán quyết có thể chứng minh.')

    def hint(self):
        state = self.knowledge()
        result = self.agent.classify(state)
        if not result.model_count:
            return dict(code='DATA_ERROR',message='Dữ kiện mâu thuẫn. Phiên tòa tạm dừng.')
        candidates = [(c,s) for c,s in result.statuses.items() if s != UNKNOWN]
        if not candidates:
            return dict(code='NO_HINT',message='Không còn suy luận mới từ các lời khai hiện có.',clue_ids=[])
        supports = [proof_support(self.agent,state,c,s) for c,s in candidates]
        def overlaps(clues):
            counts = [c for c in clues if 'region' in c]
            return any(set(referenced_cells(a,state['layout'])) & set(referenced_cells(b,state['layout']))
                       for i,a in enumerate(counts) for b in counts[i+1:])
        support = next((cs for cs in supports if overlaps(cs)),supports[0])
        self.hint_level += 1
        message = ('Thử đối chiếu hai lời khai đếm các nhóm nhà chồng lên nhau.' if overlaps(support)
                   else 'Đối chiếu lời khai với các trạng thái đã xác minh; xét quan hệ hoặc số người còn lại.')
        return dict(code='HINT', message=message if self.hint_level == 1 else
                    'Các lời khai liên quan đã được đánh dấu. Chọn từng lời khai để xem vùng.',
                    clue_ids=[] if self.hint_level == 1 else [c['id'] for c in support], level=self.hint_level)
