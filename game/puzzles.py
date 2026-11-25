"""Original authored case data only. Never served to the frontend or agent."""
from .logic import CRIMINAL, INNOCENT, evaluate

NAMES = ['An','Bách','Chi','Đào','Giang','Hà','Khôi','Lan','Minh','Nam','Oanh','Phúc','Quỳnh','Sơn','Trâm','Vân']
JOBS = [
    'Nông dân',
    'Thợ may',
    'Thợ đóng giày',
    'Ngư dân',
    'Thợ dệt',
    'Thợ rèn',
    'Thợ mộc',
    'Thợ làm nến',
    'Thợ xây',
    'Thợ làm bánh',
    'Thương nhân',
    'Đầu bếp',
    'Chủ quán rượu',
    'Người đưa thư',
    'Người chăn cừu',
    'Thợ mỏ',
    'Người làm vườn',
    'Thợ đóng thuyền',
    'Lính gác',
    'Thầy thuốc',
    'Người đánh xe ngựa',
    'Chủ nhà trọ',
    'Người lái đò',
    'Người nấu rượu',
    'Thợ làm gốm',
    'Tiều phu',
    'Nhà giả kim',
]


# Small constructors serialize the existing schema; no additional clue language.
def fact(cell,status):
    return dict(type='FACT',cells=[cell],status=status)


def same(a,b):
    return dict(type='SAME',cells=[a,b])


def different(a,b):
    return dict(type='DIFFERENT',cells=[a,b])


def count(kind,k,region):
    return dict(type=kind,k=k,region=region)


def cells(*ids):
    return dict(kind='LIST',cells=list(ids))


def row(n):
    return dict(kind='ROW',row=n)


def column(letter):
    return dict(kind='COLUMN',column=ord(letter)-64)


def neighbors(cell):
    return dict(kind='NEIGHBORS',cell=cell)


def compare(a, status_a, b, status_b):
    return dict(type='COMPARE', left=dict(cell=a, status=status_a), right=dict(cell=b, status=status_b))


def contiguous(row_number, status):
    return dict(type='CONTIGUOUS', region=row(row_number), status=status)


def case(pid,title,size,names,jobs,labels,authored,initial):
    layout=[dict(id=f'{chr(65+i%size)}{i//size+1}',row=i//size+1,column=i%size+1,
                 name=name,profession=jobs[i]) for i,name in enumerate(names[:size*size])]
    solution={p['id']:value for p,value in zip(layout,labels)}
    clues={owner:dict(id='clue-'+owner,owner=owner,**clue) for owner,clue in authored.items()}
    assert len(layout)==size*size and set(clues)==set(solution)
    assert all(evaluate(clue,solution,layout) for clue in clues.values())
    return dict(id=pid,title=title,size=size,layout=layout,solution=solution,clues=clues,initial=initial)


def tutorial():
    return case('village-3','Đêm chuông câm',3,NAMES,JOBS,
        [False,True,False,True,False,False,True,True,False],{
        'A1':fact('C1',INNOCENT),
        'A2':count('EXACTLY',1,cells('B1','B2')),
        'C1':count('AT_MOST',0,cells('C1','C2')),
        'C2':count('EXACTLY',1,cells('B1','B2','C3')),
        'C3':count('EXACTLY',2,column('A')),
        'A3':count('EXACTLY',2,row(3)),
        'B3':same('B3','B1'),
        'B1':different('B1','B2'),
        'B2':count('EXACTLY',1,neighbors('C1')),
    },['A1','A2'])


def north_gate():
    return case('village-4','Tro tàn bên cổng Bắc',4,NAMES,JOBS,
        [False,True,False,False,True,False,False,True,True,True,False,True,False,True,False,True],{
        # Overlapping budgets force D1 innocent and A3 criminal together.
        'A1':count('EXACTLY',1,cells('D1','B1','C1')),
        'A2':count('EXACTLY',2,cells('B1','C1','A3')),
        'D1':count('EXACTLY',1,cells('B1','B2')),
        'A3':fact('B2',INNOCENT),
        'B2':different('B2','D2'),
        'B1':count('AT_MOST',0,column('C')),
        'C1':count('EXACTLY',2,row(2)),
        'C2':count('EXACTLY',3,row(3)),
        'C3':count('EXACTLY',2,row(4)),
        'C4':count('EXACTLY',2,column('A')),
        'D2':count('EXACTLY',3,column('D')),
        'B3':same('B3','B4'),
        'D3':count('AT_LEAST',2,row(4)),
        'A4':count('EXACTLY',3,neighbors('A4')),
        'B4':count('EXACTLY',3,column('B')),
        'D4':count('EXACTLY',4,neighbors('B2')),
    },['A1','A2'])


RED_NAMES=['An','Ân','Bách','Bình','Chi','Dũng','Đào','Đức','Giang','Hà','Hạnh','Huy','Khôi','Lan','Linh','Minh','Nam','Oanh','Phúc','Quỳnh','Sơn','Trâm','Vân','Xuân','Yên']
RED_JOBS = JOBS[2:] + JOBS[:2]


def red_moon_puzzle():
    return case('village-5','Đêm trăng đỏ',5,RED_NAMES,RED_JOBS,
        [False,False,True,False,True,True,False,True,False,False,True,True,False,True,True,False,True,True,False,False,True,False,False,True,False],{
        'A1':count('AT_MOST',0,cells('B1','B2')),
        'A2':count('EXACTLY',1,cells('C1','D1')),
        'B1':count('EXACTLY',1,cells('C1','D1','C3')),
        'B2':count('EXACTLY',2,row(2)),
        'C3':count('AT_MOST',0,neighbors('E1')),
        'C1':count('EXACTLY',2,row(1)),
        'E1':count('EXACTLY',2,column('E')),
        'D1':count('EXACTLY',2,column('D')),
        'D2':count('EXACTLY',2,row(2)),
        'C2':same('C2','A3'),
        'A3':count('EXACTLY',3,column('A')),
        'E2':count('AT_MOST',0,cells('A4','C5','E5')),
        'A4':count('EXACTLY',1,neighbors('A5')),
        'C5':count('EXACTLY',2,row(5)),
        'A5':same('A5','D5'),
        'D5':different('D5','D4'),
        'E5':count('EXACTLY',2,row(4)),
        'D3':count('EXACTLY',3,neighbors('E4')),
        'B4':count('EXACTLY',3,neighbors('A3')),
        'B3':count('AT_LEAST',5,neighbors('B3')),
        'E3':count('EXACTLY',2,column('B')),
        'C4':different('C4','B5'),
        'D4':count('EXACTLY',2,row(4)),
        'E4':count('EXACTLY',2,column('E')),
        'B5':count('EXACTLY',4,row(3)),
    },['A1','A2'])


def mist_wharf_puzzle():
    names=['Ánh','Bảo','Cẩm','Dạ','Đan','Đông','Hiền','Hòa','Khanh','Liên','Lộc','Mai','Ngân','Nhi','Nhung','Phong','Quân','Thảo','Thi','Thu','Tiên','Tú','Uyên','Vi','Vũ']
    jobs = JOBS[9:] + JOBS[:9]
    return case('village-5-mist','Bến sương mù',5,names,jobs,
        [False,True,True,False,True,False,True,False,False,True,True,False,False,True,False,True,False,True,False,True,False,True,False,True,False],{
        'A1':count('AT_MOST',0,cells('A2','C2','D2')),
        'E1':count('EXACTLY',1,cells('A3','B3')),
        'A2':count('EXACTLY',1,cells('A3','B3','C3')),
        'C2':count('EXACTLY',2,row(2)),
        'D2':count('EXACTLY',2,neighbors('A1')),
        'B2':count('EXACTLY',3,row(1)),
        'B1':count('EXACTLY',2,column('D')),
        'C3':count('EXACTLY',3,neighbors('E3')),
        'E2':count('AT_MOST',0,cells('D1','B3','E3')),
        'B3':count('EXACTLY',3,column('B')),
        'D1':count('EXACTLY',2,row(3)),
        'E3':same('E3','A5'),
        'A3':count('EXACTLY',2,column('A')),
        'A4':count('EXACTLY',2,neighbors('A5')),
        'A5':count('AT_LEAST',1,cells('D4','E4')),
        'C1':count('AT_MOST',0,cells('C5','E5','B4')),
        'D3':count('EXACTLY',2,column('C')),
        'C4':count('EXACTLY',2,neighbors('E5')),
        'E4':count('EXACTLY',3,row(4)),
        'C5':count('EXACTLY',3,neighbors('C5')),
        'B5':different('B5','E5'),
        'D4':same('D4','C5'),
        'B4':count('AT_MOST',0,cells('B4','C5')),
        'D5':count('EXACTLY',2,row(5)),
        'E5':count('EXACTLY',3,column('E')),
    },['A1','E1'])


def lakeside_puzzle():
    # Both initial extensions are necessary to prove the first move (B2).
    return case('village-3-links','Dấu chân ven hồ',3,NAMES,JOBS,
        [True,False,True,True,True,False,True,True,False],{
        'A1':compare('B3',INNOCENT,'C3',CRIMINAL),
        'A2':contiguous(2,CRIMINAL),
        'B2':count('EXACTLY',2,neighbors('A1')),
        'B1':count('EXACTLY',4,neighbors('A2')),
        'C2':count('EXACTLY',3,neighbors('B3')),
        'A3':count('EXACTLY',2,row(3)),
        'B3':count('EXACTLY',2,row(1)),
        'C1':count('EXACTLY',1,column('C')),
        'C3':count('EXACTLY',2,neighbors('C3')),
    },['A1','A2'])


def quiet_street_puzzle():
    # Same-role comparison + a contiguous INNOCENT block first force C3.
    return case('village-4-links','Dãy nhà im tiếng',4,NAMES,JOBS[5:]+JOBS[:5],
        [True,True,True,False,True,True,False,False,
         True,False,False,False,True,True,True,True],{
        'A1':compare('A1',CRIMINAL,'C2',CRIMINAL),
        'A2':contiguous(3,INNOCENT),
        'C3':count('EXACTLY',1,row(3)),
        'B3':count('EXACTLY',3,neighbors('C2')),
        'B1':count('EXACTLY',2,neighbors('D3')),
        'B2':count('EXACTLY',2,row(2)),
        'C2':count('EXACTLY',1,neighbors('D2')),
        'D2':count('EXACTLY',4,neighbors('A2')),
        'A3':count('EXACTLY',6,neighbors('B3')),
        'D3':count('EXACTLY',4,neighbors('A3')),
        'A4':count('EXACTLY',1,neighbors('D4')),
        'B4':count('EXACTLY',2,neighbors('C4')),
        'C4':count('EXACTLY',1,column('D')),
        'C1':count('EXACTLY',5,neighbors('B2')),
        'D1':count('EXACTLY',2,neighbors('A4')),
        'D4':count('EXACTLY',3,row(1)),
    },['A1','A2'])


PUZZLES={p['id']:p for p in (tutorial(),north_gate(),red_moon_puzzle(),mist_wharf_puzzle(),
                            lakeside_puzzle(),quiet_street_puzzle())}

# Server-only walkthrough checkpoints, also used to verify clue dependency in tests.
DEMO_PROOFS={
    'village-3':dict(prefix=[('C1',INNOCENT),('C2',INNOCENT)],target='C3',status=INNOCENT,clue_ids=['clue-A2','clue-C2']),
    'village-4':dict(prefix=[],target='D1',status=INNOCENT,clue_ids=['clue-A1','clue-A2']),
    'village-5':dict(prefix=[('B1',INNOCENT),('B2',INNOCENT)],target='C3',status=INNOCENT,clue_ids=['clue-A2','clue-B1']),
    'village-5-mist':dict(prefix=[('A2',INNOCENT)],target='C3',status=INNOCENT,clue_ids=['clue-E1','clue-A2']),
    'village-3-links':dict(prefix=[],target='B2',status=CRIMINAL,clue_ids=['clue-A1','clue-A2']),
    'village-4-links':dict(prefix=[],target='C3',status=INNOCENT,clue_ids=['clue-A1','clue-A2']),
}
