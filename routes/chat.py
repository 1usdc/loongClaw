'\n聊天 API 路由：POST /api/chat、POST /api/chat/stream（SSE 流式）\n'
_N='session_id'
_M='prompt'
_L='user_input'
_K='duration'
_J='.,;:!?)'
_I='https?://[^\\s)\\]]+'
_H='请输入内容。'
_G='message'
_F='default'
_E='user'
_D='role'
_C='step'
_B='content'
_A=None
import json,re,threading
from queue import Empty,Queue
from fastapi import APIRouter,Request
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
from agents import run_agent_loop,analyze_conversation_for_memory
from tools.session_tools import extract_ui_schema_payload
from tools.session_tools import get_and_clear_next_open_url
from tools.session_tools import get_step_contents
from tools.session_tools import strip_ui_schema_from_reply
from tools.memory_tools import add_memory
from tools.session_tools import create_session_id,load_history,append_turn,list_sessions,delete_session
router=APIRouter(tags=['chat'])
class ChatHistoryItem(BaseModel):'单条对话历史。缺省 role/content 避免前端漏传或 history 项不完整时 422。';role:str=_E;content:str=''
class ChatRequest(BaseModel):'聊天请求体。';message:str='';persona_id:str|_A=_A;session_id:str|_A=_A;history:list[ChatHistoryItem]|_A=_A
class ChatResponse(BaseModel):'聊天响应：文本回复、可选超链接、各步骤返回内容、会话 ID。';reply:str;link:str|_A=_A;stepContents:list|_A=_A;ui_schema:dict|_A=_A;session_id:str|_A=_A
def _process_message(user_input:str,persona_id:str|_A=_A,history:list|_A=_A,session_id:str|_A=_A):
	'\n    处理用户消息，执行 Agent 循环，返回回复、计时与超链接。\n    若传 session_id 则从会话存储加载历史并追加本轮；否则新建 session_id，使用传入的 history。\n    对话结束后写入当前分身记忆并持久化到会话文件。\n    ';C=session_id;B=user_input;A=history;F=persona_id or _F
	if not B:return ChatResponse(reply=_H,link=_A,stepContents=_A,ui_schema=_A,session_id=C)
	if C:
		try:A=load_history(F,C)
		except Exception:A=A or _A
	else:C=create_session_id();A=A if A else _A
	H=run_agent_loop(B,history=A);I=extract_ui_schema_payload(H);D=strip_ui_schema_from_reply(H);J=get_and_clear_next_open_url()
	if J:G=J
	else:K=re.search(_I,D);G=K.group(0).rstrip(_J)if K else _A
	L,M=get_step_contents();E=_A
	if L and(B or'').strip():
		N={_C:_L,_B:(B or'').strip(),_K:''}
		if M is not _A:N[_M]=M
		E=[N,*L]
	try:append_turn(F,C,B,D,step_contents=E,link=G,ui_schema=I)
	except Exception:pass
	try:
		P,O=analyze_conversation_for_memory(B,D)
		if P and O:add_memory(F,O)
	except Exception:pass
	return ChatResponse(reply=D,link=G,stepContents=E if E else _A,ui_schema=I,session_id=C)
@router.post('/api/chat',response_model=ChatResponse)
def chat(req:ChatRequest):'\n    发送用户消息，执行 Agent 循环（路由 + 工具/技能），返回回复、计时与可选超链接（供前端内嵌预览）。\n    可带 session_id 以继续已有会话（服务端从存储加载历史）；不带则新建会话并返回 session_id。\n    ';A=req;B=[{_D:getattr(A,_D,A.get(_D,_E)),_B:getattr(A,_B,_A)or A.get(_B,'')or''}for A in A.history or[]];return _process_message((A.message or'').strip(),persona_id=A.persona_id,history=B if B else _A,session_id=(A.session_id or'').strip()or _A)
def _stream_chat_events(user_input:str,persona_id:str|_A=_A,history:list|_A=_A,session_id:str|_A=_A):
	'\n    生成 SSE 事件：先流式推送各步骤 (step)，再流式推送最终回复 (text)，最后推送 done（含 session_id）。\n    若带 session_id 则从存储加载历史；否则新建会话。对话结束后持久化到会话文件并写入记忆。\n    ';W='reply_done';M=False;I='type';H='text';D=session_id;C=user_input;A=history;J=persona_id or _F
	if D:
		try:A=load_history(J,D)
		except Exception:A=A or _A
	else:D=create_session_id();A=A if A else _A
	E=Queue();F=[]
	def X(step_name:str,content):E.put((_C,step_name,content))
	def Y(text_piece:str):E.put((H,text_piece,_A))
	def Z():
		try:B=run_agent_loop(C,history=A,on_step=X,on_text_delta=Y);F.append(B)
		except Exception as D:F.append(f"错误: {D}")
		finally:E.put((W,_A,_A))
	threading.Thread(target=Z,daemon=True).start()
	while True:
		try:K,N,a=E.get(timeout=60)
		except Empty:B=json.dumps({I:'error',_G:'timeout'});yield f"data: {B}\n\n";return
		if K==_C:B=json.dumps({I:_C,_C:N,_B:a},ensure_ascii=M);yield f"data: {B}\n\n"
		elif K==H:B=json.dumps({I:H,H:N},ensure_ascii=M);yield f"data: {B}\n\n"
		elif K==W:break
	O=F[0]if F else'';P=extract_ui_schema_payload(O);G=strip_ui_schema_from_reply(O);b=get_and_clear_next_open_url();Q=re.search(_I,G);R=b or(Q.group(0).rstrip(_J)if Q else _A);S,T=get_step_contents();L=_A
	if S and(C or'').strip():
		U={_C:_L,_B:(C or'').strip(),_K:''}
		if T is not _A:U[_M]=T
		L=[U,*S]
	try:append_turn(J,D,C,G,step_contents=L,link=R,ui_schema=P)
	except Exception:pass
	try:
		c,V=analyze_conversation_for_memory(C,G)
		if c and V:add_memory(J,V)
	except Exception:pass
	B=json.dumps({I:'done','reply':G,'link':R,'stepContents':L,'ui_schema':P,_N:D},ensure_ascii=M);yield f"data: {B}\n\n"
@router.post('/api/chat/stream')
async def chat_stream(request:Request):
	'\n    流式聊天：SSE 先推送中间步骤 (step)，再流式推送最终回复 (text)，最后推送 done（含 link/stepContents/session_id）。\n    带 session_id 时从服务端加载历史；否则新建会话并在 done 中返回 session_id。\n    使用 Request 手动解析 body，避免 build 下 Pydantic 校验导致 422。\n    ';G='persona_id'
	try:A=await request.json()
	except Exception:A={}
	H=(A.get(_G)if isinstance(A.get(_G),str)else'')or'';I=A.get(G)if A.get(G)is not _A else _A;D=(A.get(_N)or'').strip()or _A;E=A.get('history');C=[]
	if isinstance(E,list):
		for B in E:
			if not isinstance(B,dict):continue
			C.append({_D:B.get(_D)or _E if isinstance(B.get(_D),str)else _E,_B:B.get(_B)or''if isinstance(B.get(_B),str)else''})
	F=H.strip()
	if not F:return ChatResponse(reply=_H,link=_A,stepContents=_A,ui_schema=_A,session_id=D)
	return StreamingResponse(_stream_chat_events(F,persona_id=I,history=C if C else _A,session_id=D),media_type='text/event-stream',headers={'Cache-Control':'no-cache','X-Accel-Buffering':'no'})
@router.get('/api/chat/sessions')
def list_chat_sessions(persona_id:str|_A=_A):
	'\n    列出当前分身下的所有会话，按修改时间倒序。\n    返回 { "sessions": [{"session_id", "updated_at", "preview"}, ...] }。\n    ';B=persona_id or _F
	try:A=list_sessions(B)
	except Exception:A=[]
	return{'sessions':A}
@router.delete('/api/chat/session')
def delete_chat_session(persona_id:str|_A=_A,session_id:str|_A=_A):
	'\n    删除指定会话；session_id 必填。返回 { "ok": true } 或 404。\n    ';from fastapi import HTTPException as A;C=persona_id or _F;B=(session_id or'').strip()
	if not B:raise A(status_code=400,detail='session_id 必填')
	if not delete_session(C,B):raise A(status_code=404,detail='会话不存在或已删除')
	return{'ok':True}