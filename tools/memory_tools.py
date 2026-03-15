'\n记忆与分身：记忆存于 data/memory/{persona_id}/（长期 MEMORY.md + 按日追加 YYYY-MM-DD.md）；\n分身等存于 data/database/loongclaw.db（SQLite）。\n'
_O='frontend'
_N='未命名'
_M='MEMORY.md'
_L='updated_at'
_K='content'
_J='persona_id'
_I=False
_H='\n'
_G='utf-8'
_F=True
_E='name'
_D='created_at'
_C='id'
_B='avatar'
_A=None
import random,re,uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from tools.db import db_add_persona as _db_add_persona,db_delete_persona as _db_delete_persona,db_load_personas as _db_load_personas,db_update_persona as _db_update_persona
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/'data'
MEMORY_DIR=DATA_DIR/'memory'
_frontend_candidate=BASE_DIR.parent/_O
_frontend_dir=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_O
UI_AVATAR_DIR=_frontend_dir/'assets'/_B
DEFAULT_PERSONA_ID='default'
DEFAULT_AVATAR='01.svg'
_MEMORY_LINE_PATTERN=re.compile('^-\\s+([a-f0-9]+)\\t([^\\t]+)\\t(.*)$',re.DOTALL)
def _persona_memory_dir(persona_id:str):'某分身的记忆目录：data/memory/{persona_id}/';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;A=MEMORY_DIR/B;A.mkdir(parents=_F,exist_ok=_F);return A
def _parse_memory_line(line:str,persona_id:str):
	'解析一行记忆，返回 {id, persona_id, content, created_at, updated_at} 或 None。';A=line;A=A.strip()
	if not A or not A.startswith('-'):return
	B=_MEMORY_LINE_PATTERN.match(A)
	if not B:return
	D,C,E=B.group(1),B.group(2),B.group(3);return{_C:D,_J:persona_id,_K:E,_D:C,_L:C}
def _read_memories_from_file(path:Path,persona_id:str):
	'从单个 .md 文件读取所有记忆行。';A=[]
	if not path.is_file():return A
	try:
		C=path.read_text(encoding=_G)
		for D in C.splitlines():
			B=_parse_memory_line(D,persona_id)
			if B:A.append(B)
	except Exception:pass
	return A
def _append_memory_line(path:Path,mid:str,created_at:str,content:str):
	'向文件追加一行记忆；内容中的换行替换为空格。';A=(content or'').replace(_H,' ').strip();B=f"- {mid}\t{created_at}\t{A}\n";path.parent.mkdir(parents=_F,exist_ok=_F)
	with path.open('a',encoding=_G)as C:C.write(B)
def _find_memory_line(memory_id:str):
	'在 data/memory 下查找包含该 id 的文件、行号与整行内容；未找到返回 None。'
	if not MEMORY_DIR.is_dir():return
	for A in MEMORY_DIR.iterdir():
		if not A.is_dir():continue
		F=A.name
		for B in A.glob('*.md'):
			try:
				D=B.read_text(encoding=_G).splitlines()
				for(E,C)in enumerate(D):
					if C.strip().startswith(f"- {memory_id}\t"):return B,E,C
			except Exception:continue
def get_avatar_options():
	'返回 avatar 目录下内置头像文件名列表（如 01.svg, 02.svg）。'
	if not UI_AVATAR_DIR.is_dir():return[]
	B=[]
	for A in UI_AVATAR_DIR.iterdir():
		if A.is_file()and A.suffix.lower()in('.svg','.png','.jpg','.jpeg','.webp'):B.append(A.name)
	return sorted(B)
def load_memories(persona_id:str|_A=_A):
	'\n    从 data/memory/{persona_id}/ 加载记忆：MEMORY.md（长期）+ 按日 YYYY-MM-DD.md，合并后按时间倒序。\n    ';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=_persona_memory_dir(B);A=[];A.extend(_read_memories_from_file(D/_M,B))
	for C in sorted(D.glob('*.md'),reverse=_F):
		if C.name==_M:continue
		if re.match('^\\d{4}-\\d{2}-\\d{2}\\.md$',C.name):A.extend(_read_memories_from_file(C,B))
	A.sort(key=lambda x:x.get(_D,''),reverse=_F);return A
def load_personas():
	'加载分身列表。第一个分身固定使用 01.svg 头像（若未保存过则用该默认值）。';C='分身1';A=_db_load_personas();A=[A for A in A if A.get(_C)and A.get(_E)];D=set(get_avatar_options())
	if not any(A.get(_C)==DEFAULT_PERSONA_ID for A in A):E={_C:DEFAULT_PERSONA_ID,_E:C,_B:DEFAULT_AVATAR,_D:_now_iso()};A.insert(0,E)
	for B in A:
		if B.get(_C)==DEFAULT_PERSONA_ID and(B.get(_E)or'').strip()=='默认':B[_E]=C;break
	for B in A:
		if not B.get(_B)or B.get(_B)not in D:B[_B]=DEFAULT_AVATAR
	return A
def _now_iso():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _id():return uuid.uuid4().hex[:12]
def _random_avatar():'从内置头像列表中随机返回一个文件名；无头像时返回空字符串。';A=get_avatar_options();return random.choice(A)if A else''
def add_memory(persona_id:str,content:str,memory_id:str|_A=_A,long_term:bool=_I):
	'\n    新增一条记忆，写入 data/memory/{persona_id}/。\n    默认追加到按日文件 YYYY-MM-DD.md；long_term=True 时追加到 MEMORY.md。\n    ';A=content;B=_now_iso();C=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=memory_id or _id();A=(A or'').strip();E=_persona_memory_dir(C)
	if long_term:F=E/_M
	else:G=datetime.now(timezone.utc).strftime('%Y-%m-%d');F=E/f"{G}.md"
	_append_memory_line(F,D,B,A);return{_C:D,_J:C,_K:A,_D:B,_L:B}
def update_memory(memory_id:str,content:str):
	'更新一条记忆（在对应 .md 文件中替换该行）。';B=memory_id;E=_find_memory_line(B)
	if not E:return
	C,F,H=E;I=_now_iso();G=(content or'').replace(_H,' ').strip();D=_MEMORY_LINE_PATTERN.match(H.strip())
	if not D:return
	J=f"- {B}\t{D.group(2)}\t{G}\n";A=C.read_text(encoding=_G).splitlines()
	if F>=len(A):return
	A[F]=J.strip();C.write_text(_H.join(A)+(_H if A else''),encoding=_G);return{_C:B,_J:C.parent.name,_K:G,_D:D.group(2),_L:I}
def delete_memory(memory_id:str):
	'删除一条记忆（从对应 .md 文件中移除该行）。';B=_find_memory_line(memory_id)
	if not B:return _I
	C,D,E=B;A=C.read_text(encoding=_G).splitlines()
	if D>=len(A):return _I
	A.pop(D);C.write_text(_H.join(A)+(_H if A else''),encoding=_G);return _F
def append_memory_from_chat(user_input:str,reply:str,persona_id:str|_A=_A,max_content_len:int=2000):
	'\n    根据一轮对话生成并保存一条记忆（简短摘要）。\n    用于对话结束后自动调用。persona_id 为空时使用第一个分身。\n    ';B=max_content_len;C=(user_input or'').strip();A=(reply or'').strip()
	if not C and not A:return
	D=f"用户: {C[:500]}\n助手: {A[:B]}"
	if len(A)>B:D+='...'
	return add_memory(persona_id or DEFAULT_PERSONA_ID,D)
def add_persona(name:str,avatar:str|_A=_A):
	'新增分身。avatar 为空时从内置头像中随机分配一个。';C=_id();D=get_avatar_options();A=(avatar or'').strip()
	if not A or A not in D:A=_random_avatar()
	B={_C:C,_E:(name or _N).strip(),_B:A,_D:_now_iso()};_db_add_persona(B);return B
def update_persona(persona_id:str,name:str,avatar:str|_A=_A):
	'更新分身名称与头像。第一个分身可改名、改头像，不可删除。avatar 为 None 表示不修改。';E=avatar;D=name;C=persona_id;F=get_avatar_options();I=_db_load_personas()
	for A in I:
		if A.get(_C)==C:
			B=_A
			if E is not _A:
				G=(E or'').strip()
				if C==DEFAULT_PERSONA_ID:B=G if G in F else A.get(_B)or DEFAULT_AVATAR
				else:B=G if G in F else A.get(_B)or _random_avatar()
			if _db_update_persona(C,(D or _N).strip(),B):return{**A,_E:(D or _N).strip(),_B:B if B is not _A else A.get(_B)}
			return A
	if C==DEFAULT_PERSONA_ID:
		H=(E or'').strip()if E is not _A else DEFAULT_AVATAR
		if F and H not in F:H=DEFAULT_AVATAR
		_db_add_persona({_C:DEFAULT_PERSONA_ID,_E:(D or'默认').strip(),_B:H,_D:_now_iso()});return{_C:DEFAULT_PERSONA_ID,_E:(D or'默认').strip(),_B:H,_D:_now_iso()}
def delete_persona(persona_id:str):
	'删除分身；其记忆保留但 persona_id 可显示为已删除。';A=persona_id
	if A==DEFAULT_PERSONA_ID:return _I
	return _db_delete_persona(A)