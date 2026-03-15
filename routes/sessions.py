'\n会话 API：按会话读取消息（GET /api/sessions/session）。会话列表由 GET /api/chat/sessions 提供。\n'
_B='.jsonl'
_A=None
import json
from pathlib import Path
from fastapi import APIRouter
from tools.session_tools import SESSIONS_DIR
router=APIRouter(tags=['sessions'])
def _session_file(persona_id:str,session_id:str):
	'返回会话文件路径（.json 或 .jsonl），不存在则 None。';B=SESSIONS_DIR/persona_id
	for C in('.json',_B):
		A=B/f"{session_id}{C}"
		if A.is_file():return A
def _read_session_messages(path:Path):
	'从 .json 或 .jsonl 读取消息列表，每条含 index、role、content、step_contents(可选)、link(可选)。';N='assistant';M='user_input';L='user';K='index';G='content';E='link';D='step_contents';C='role';J=path.read_text(encoding='utf-8',errors='replace');H=[]
	if path.suffix==_B:
		for(I,F)in enumerate(J.strip().splitlines(),start=1):
			F=F.strip()
			if not F:continue
			try:
				A=json.loads(F);B={K:I,C:A.get(C,L),G:(A.get(G)or A.get(M)or'').strip()}
				if A.get(C)==N:
					if A.get(D)is not _A:B[D]=A[D]
					if A.get(E)is not _A:B[E]=A[E]
				H.append(B)
			except json.JSONDecodeError:continue
	else:
		try:
			O=json.loads(J);P=O.get('turns')or[]
			for(I,A)in enumerate(P,start=1):
				B={K:I,C:A.get(C,L),G:(A.get(G)or A.get(M)or'').strip()}
				if A.get(C)==N:
					if A.get(D)is not _A:B[D]=A[D]
					if A.get(E)is not _A:B[E]=A[E]
				H.append(B)
		except json.JSONDecodeError:pass
	return H
@router.get('/api/sessions/session')
def get_session_detail(persona_id:str|_A=_A,session_id:str|_A=_A):
	'\n    统一按会话取消息：支持 .json/.jsonl，返回带 index 的 messages。\n    无 session_id 或会话不存在时返回 200 + 空 messages，供恢复聊天与查看会话记录共用。\n    ';E='messages';D='session_id';C='persona_id';A=persona_id or'default';B=(session_id or'').strip()
	if not B:return{C:A,D:_A,E:[]}
	F=_session_file(A,B)
	if not F:return{C:A,D:B,E:[]}
	G=_read_session_messages(F);return{C:A,D:B,E:G}