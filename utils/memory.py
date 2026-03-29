'\n记忆与分身：记忆存于 data/memory/{persona_id}/（长期 MEMORY.md + 按日追加 YYYY-MM-DD.md）；\n分身等存于 data/database/sqlite.db（SQLite）。\n'
_P='assets'
_O='frontend'
_N='MEMORY.md'
_M='updated_at'
_L='content'
_K='persona_id'
_J='未命名'
_I=False
_H='\n'
_G='utf-8'
_F='created_at'
_E=True
_D='name'
_C='id'
_B='avatar'
_A=None
import random,re,uuid
from datetime import datetime,timezone
from pathlib import Path
from typing import Any
from utils.db import db_add_persona as _db_add_persona,db_delete_persona as _db_delete_persona,db_load_personas as _db_load_personas,db_update_persona as _db_update_persona
from utils.prompt import save_persona_prompt as _save_persona_prompt
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/'data'
MEMORY_DIR=DATA_DIR/'memory'
_frontend_candidate=BASE_DIR.parent/_O
_frontend_dir=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_O
_avatar_candidates=_frontend_dir/_P/_B,_frontend_dir/'dist'/_P/_B
UI_AVATAR_DIR=next((A for A in _avatar_candidates if A.is_dir()),_avatar_candidates[0])
DEFAULT_PERSONA_ID='default'
DEFAULT_AVATAR='01.svg'
_MEMORY_LINE_PATTERN=re.compile('^-\\s+([a-f0-9]+)\\t([^\\t]+)\\t(.*)$',re.DOTALL)
def _persona_memory_dir(persona_id:str):'某分身的记忆目录：data/memory/{persona_id}/';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;A=MEMORY_DIR/B;A.mkdir(parents=_E,exist_ok=_E);return A
def _parse_memory_line(line:str,persona_id:str):
	'解析一行记忆，返回 {id, persona_id, content, created_at, updated_at} 或 None。';A=line;A=A.strip()
	if not A or not A.startswith('-'):return
	B=_MEMORY_LINE_PATTERN.match(A)
	if not B:return
	D,C,E=B.group(1),B.group(2),B.group(3);return{_C:D,_K:persona_id,_L:E,_F:C,_M:C}
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
	'向文件追加一行记忆；内容中的换行替换为空格。';A=(content or'').replace(_H,' ').strip();B=f"- {mid}\t{created_at}\t{A}\n";path.parent.mkdir(parents=_E,exist_ok=_E)
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
	'\n    从 data/memory/{persona_id}/ 加载记忆：MEMORY.md（长期）+ 按日 YYYY-MM-DD.md，合并后按时间倒序。\n    ';B=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=_persona_memory_dir(B);A=[];A.extend(_read_memories_from_file(D/_N,B))
	for C in sorted(D.glob('*.md'),reverse=_E):
		if C.name==_N:continue
		if re.match('^\\d{4}-\\d{2}-\\d{2}\\.md$',C.name):A.extend(_read_memories_from_file(C,B))
	A.sort(key=lambda x:x.get(_F,''),reverse=_E);return A
def load_personas():
	'加载分身列表。第一个分身固定使用 01.svg 头像（若未保存过则用该默认值）。';C='数字分身1';A=_db_load_personas();A=[A for A in A if A.get(_C)and A.get(_D)];D=set(get_avatar_options())
	if not any(A.get(_C)==DEFAULT_PERSONA_ID for A in A):E={_C:DEFAULT_PERSONA_ID,_D:C,_B:DEFAULT_AVATAR,_F:_now_iso()};A.insert(0,E)
	for B in A:
		if B.get(_C)==DEFAULT_PERSONA_ID and(B.get(_D)or'').strip()=='默认':B[_D]=C;break
	for B in A:
		if not B.get(_B)or B.get(_B)not in D:B[_B]=DEFAULT_AVATAR
	return A
def _now_iso():return datetime.now(timezone.utc).isoformat(timespec='seconds')
def _id():return uuid.uuid4().hex[:12]
def _random_avatar():'从内置头像列表中随机返回一个文件名；无头像时返回空字符串。';A=get_avatar_options();return random.choice(A)if A else''
def _is_valid_avatar(av:str,opts:list[str]):
	'头像有效：为内置文件名或在线 URL。';A=av
	if not(A or'').strip():return _I
	A=(A or'').strip()
	if A in opts:return _E
	return A.startswith('http://')or A.startswith('https://')
def add_memory(persona_id:str,content:str,memory_id:str|_A=_A,long_term:bool=_I):
	'\n    新增一条记忆，写入 data/memory/{persona_id}/。\n    默认追加到按日文件 YYYY-MM-DD.md；long_term=True 时追加到 MEMORY.md。\n    ';A=content;B=_now_iso();C=(persona_id or DEFAULT_PERSONA_ID).strip()or DEFAULT_PERSONA_ID;D=memory_id or _id();A=(A or'').strip();E=_persona_memory_dir(C)
	if long_term:F=E/_N
	else:G=datetime.now(timezone.utc).strftime('%Y-%m-%d');F=E/f"{G}.md"
	_append_memory_line(F,D,B,A);return{_C:D,_K:C,_L:A,_F:B,_M:B}
def update_memory(memory_id:str,content:str):
	'更新一条记忆（在对应 .md 文件中替换该行）。';B=memory_id;E=_find_memory_line(B)
	if not E:return
	C,F,H=E;I=_now_iso();G=(content or'').replace(_H,' ').strip();D=_MEMORY_LINE_PATTERN.match(H.strip())
	if not D:return
	J=f"- {B}\t{D.group(2)}\t{G}\n";A=C.read_text(encoding=_G).splitlines()
	if F>=len(A):return
	A[F]=J.strip();C.write_text(_H.join(A)+(_H if A else''),encoding=_G);return{_C:B,_K:C.parent.name,_L:G,_F:D.group(2),_M:I}
def delete_memory(memory_id:str):
	'删除一条记忆（从对应 .md 文件中移除该行）。';B=_find_memory_line(memory_id)
	if not B:return _I
	C,D,E=B;A=C.read_text(encoding=_G).splitlines()
	if D>=len(A):return _I
	A.pop(D);C.write_text(_H.join(A)+(_H if A else''),encoding=_G);return _E
def append_memory_from_chat(user_input:str,reply:str,persona_id:str|_A=_A,max_content_len:int=2000):
	'\n    根据一轮对话生成并保存一条记忆（简短摘要）。\n    用于对话结束后自动调用。persona_id 为空时使用第一个分身。\n    ';B=max_content_len;C=(user_input or'').strip();A=(reply or'').strip()
	if not C and not A:return
	D=f"用户: {C[:500]}\n助手: {A[:B]}"
	if len(A)>B:D+='...'
	return add_memory(persona_id or DEFAULT_PERSONA_ID,D)
def add_persona(name:str,avatar:str|_A=_A):
	'新增分身。avatar 可为内置文件名或在线 URL，为空时从内置头像中随机分配。';C=_id();D=get_avatar_options();B=(avatar or'').strip()
	if not B or not _is_valid_avatar(B,D):B=_random_avatar()
	A={_C:C,_D:(name or _J).strip(),_B:B,_F:_now_iso()};_db_add_persona(A);_save_persona_prompt(A[_C],prompt=_A,avatar=A[_B],name=A[_D]);return A
def update_persona(persona_id:str,name:str,avatar:str|_A=_A):
	'更新分身名称与头像。第一个分身可改名、改头像，不可删除。avatar 为 None 表示不修改。';F=avatar;E=name;B=persona_id;H=get_avatar_options();K=_db_load_personas()
	for A in K:
		if A.get(_C)==B:
			C=_A
			if F is not _A:
				G=(F or'').strip()
				if B==DEFAULT_PERSONA_ID:C=G if _is_valid_avatar(G,H)else A.get(_B)or DEFAULT_AVATAR
				else:C=G if _is_valid_avatar(G,H)else A.get(_B)or _random_avatar()
			if _db_update_persona(B,(E or _J).strip(),C):J=C if C is not _A else A.get(_B);_save_persona_prompt(B,prompt=_A,avatar=J,name=(E or _J).strip());return{**A,_D:(E or _J).strip(),_B:J}
			return A
	if B==DEFAULT_PERSONA_ID:
		D=(F or'').strip()if F is not _A else DEFAULT_AVATAR
		if not _is_valid_avatar(D,H):D=DEFAULT_AVATAR
		I=(E or'默认').strip();_db_add_persona({_C:DEFAULT_PERSONA_ID,_D:I,_B:D,_F:_now_iso()});_save_persona_prompt(DEFAULT_PERSONA_ID,prompt=_A,avatar=D,name=I);return{_C:DEFAULT_PERSONA_ID,_D:I,_B:D,_F:_now_iso()}
def delete_persona(persona_id:str):
	'删除分身；其记忆保留但 persona_id 可显示为已删除。';A=persona_id
	if A==DEFAULT_PERSONA_ID:return _I
	return _db_delete_persona(A)