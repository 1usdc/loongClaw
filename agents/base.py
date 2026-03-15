'\nAgent 共享逻辑与默认实现：消息转 API 格式、OpenAI 兼容 API、工具循环及默认 Agent（直连 API、技能检索注入）。\n'
_P='OPENAI_API_KEY'
_O='N1N_API_KEY'
_N='assistant'
_M='description'
_L='system'
_K='arguments'
_J='args'
_I='tool_calls'
_H='function'
_G=False
_F='id'
_E='user'
_D='role'
_C='content'
_B='name'
_A=None
import json,os
from typing import Any,Callable,List,Optional
from langchain_core.messages import SystemMessage,HumanMessage,AIMessage,ToolMessage
from openai import OpenAI
from tools import TOOLS,record_step,tool_map
from tools.skill_tools import get_skill_summaries_for_agent,search_skills_by_keyword
def tools_openai():'工具定义转为 OpenAI function 格式。';return[{'type':_H,_H:{_B:A.name,_M:A.description or'','parameters':A.get_input_schema().model_json_schema()}}for A in TOOLS]
def _format_messages_for_step_log(messages:list,max_chars:int|_A=4000,max_tool_content:int|_A=500):
	'\n    将消息列表格式化为可读字符串，用于步骤明细中「传给 AI 的内容」展示或写入。\n    max_chars 为 None 时不截断总长度；max_tool_content 为 None 时不截断 tool 内容（写入会话时用完整数据）。\n    ';G=max_tool_content;F=max_chars;D=[];H=0
	for A in messages:
		if isinstance(A,SystemMessage):E,B=_L,A.content or''
		elif isinstance(A,HumanMessage):E,B=_E,A.content or''
		elif isinstance(A,AIMessage):
			E,B=_N,A.content or''
			if getattr(A,_I,_A):B+=' [tool_calls: '+', '.join((A.get(_B)or'?')+'('+json.dumps(A.get(_J)or{},ensure_ascii=_G)+')'for A in A.tool_calls)+']'
		elif isinstance(A,ToolMessage):
			I=A.content or''
			if G is not _A and len(I)>G:B=I[:G]+'...'
			else:B=I
			E='tool'
		else:continue
		C=f"[{E}]\n{B}"
		if F is not _A and H+len(C)>F:C=C[:F-H]+'\n...';D.append(C);break
		D.append(C);H+=len(C)
	return'\n\n'.join(D)if D else''
def messages_to_openai(messages:list):
	'LangChain messages -> OpenAI API messages。';B=[]
	for A in messages:
		if isinstance(A,SystemMessage):B.append({_D:_L,_C:A.content})
		elif isinstance(A,HumanMessage):B.append({_D:_E,_C:A.content})
		elif isinstance(A,AIMessage):
			C={_D:_N,_C:A.content or''}
			if getattr(A,_I,_A):C[_I]=[{_F:A.get(_F,''),'type':_H,_H:{_B:A.get(_B,''),_K:json.dumps(A.get(_J)or{})}}for A in A.tool_calls]
			B.append(C)
		elif isinstance(A,ToolMessage):B.append({_D:'tool','tool_call_id':A.tool_call_id,_C:A.content})
	return B
def _safe_json_loads(raw:str):
	'安全解析 JSON 字符串，失败时返回空字典。'
	if not raw:return{}
	try:A=json.loads(raw);return A if isinstance(A,dict)else{}
	except Exception:return{}
def analyze_conversation_for_memory(client:OpenAI,model:str,user_input:str,reply:str,max_summary_chars:int=500):
	'\n    判断本轮对话是否包含与用户相关的、值得长期记忆的信息；若值得则生成简短总结。\n    返回 (是否应写入记忆, 总结文本)；若不值得或出错则返回 (False, "")。\n    ';H='STORE';A=(user_input or'').strip();B=(reply or'').strip()
	if not A and not B:return _G,''
	I=A[:800]+('…'if len(A)>800 else'');J=B[:1200]+('…'if len(B)>1200 else'');K='你是记忆分析助手。根据「用户消息」与「助手回复」，判断是否包含与用户本人相关的、值得长期记住的信息。\n值得存储的示例：用户的偏好、决定、承诺、个人事实、待办、重要约定、明确说「记住」的内容等。\n不值得存储的示例：纯闲聊、一次性问答、工具执行结果无用户上下文、寒暄、无关紧要的确认。\n若不值得存储，只回复一行：NO_STORE\n若值得存储，先回复一行：STORE\n然后空一行，再写一段简短中文总结（一两句话，不超过 200 字），不要重复用户/助手原文。';L=f"用户消息：\n{I}\n\n助手回复：\n{J}"
	try:
		M=client.chat.completions.create(model=model,messages=[{_D:_L,_C:K},{_D:_E,_C:L}],temperature=.2,max_tokens=400);C=(M.choices[0].message.content or'').strip()
		if not C:return _G,''
		E=C.upper()
		if E.startswith('NO_STORE'):return _G,''
		if E.startswith(H):
			N=C.split('\n');F=[]
			for(O,D)in enumerate(N):
				if O==0 and D.strip().upper()==H:continue
				if D.strip():F.append(D.strip())
			G=' '.join(F).strip()
			if G:return True,G[:max_summary_chars]
		return _G,''
	except Exception:return _G,''
def summarize_conversation(client:OpenAI,model:str,messages_list:List[dict],max_summary_chars:int=1500):
	'\n    将较早的对话交给模型做摘要，返回一条紧凑的摘要文本。\n    messages_list 为 [{"role": "user"|"assistant", "content": str}, ...]。\n    ';C=messages_list
	if not C:return''
	A=[]
	for D in C:
		F=(D.get(_D)or _E).lower();B=(D.get(_C)or'').strip()
		if not B:continue
		G='用户'if F==_E else'助手';A.append(f"{G}：{B[:800]}"+('…'if len(B)>800 else''))
	if not A:return''
	H='请用一段简短的中文概括以下对话的主要话题、用户诉求与关键结论（控制在 300 字内）：\n\n'+'\n\n'.join(A)
	try:I=client.chat.completions.create(model=model,messages=[{_D:_E,_C:H}],temperature=.3,max_tokens=500);E=(I.choices[0].message.content or'').strip();return E[:max_summary_chars]if E else''
	except Exception:return'（摘要生成失败，已省略更早对话）'
def _history_to_langchain(history:List[dict]):
	'将 [{"role":"user"|"assistant","content":str}, ...] 转为 LangChain 消息列表。';A=[]
	for B in history:
		D=(B.get(_D)or _E).lower();C=B.get(_C)or''
		if D==_E:A.append(HumanMessage(content=C))
		else:A.append(AIMessage(content=C))
	return A
def _prune_old_tool_results(messages:list,keep_recent:int=3,max_chars_per_old:int=800):
	'\n    仅裁切较早的 ToolMessage 内容以减轻 context 体积，不改对话本身。\n    保留最近 keep_recent 条工具结果完整，更早的截断到 max_chars_per_old 字符。\n    原地修改 messages。\n    ';D=max_chars_per_old;C=keep_recent;A=messages;E=[A for(A,B)in enumerate(A)if isinstance(B,ToolMessage)]
	if len(E)<=C:return
	H=E[:-C]
	for F in H:
		B=A[F]
		if not isinstance(B,ToolMessage):continue
		G=B.content or''
		if len(G)<=D:continue
		A[F]=ToolMessage(content=G[:D]+'\n\n…（结果已截断，仅保留最近若干条完整）',tool_call_id=B.tool_call_id)
def chat_with_tools(client:OpenAI,model:str,messages:list,temperature:float=0,on_text_delta:Optional[Callable[[str],_A]]=_A):
	'调用 OpenAI 兼容 API（stream=True），返回 AIMessage（含 content 与 tool_calls）。';J=on_text_delta;P=client.chat.completions.create(model=model,messages=messages_to_openai(messages),tools=tools_openai(),temperature=temperature,stream=True);K=[];B={}
	for Q in P:
		L=getattr(Q,'choices',_A)or[]
		if not L:continue
		C=getattr(L[0],'delta',_A)
		if not C:continue
		D=getattr(C,_C,_A)
		if D:
			K.append(D)
			if J:J(D)
		R=getattr(C,_I,_A)or[]
		for E in R:
			A=getattr(E,'index',0)or 0;F=B.setdefault(A,{_F:'',_B:'',_K:''});M=getattr(E,_F,_A)
			if M:F[_F]=M
			G=getattr(E,_H,_A)
			if G:
				N=getattr(G,_B,_A)
				if N:F[_B]+=N
				O=getattr(G,_K,_A)
				if O:F[_K]+=O
	H=[]
	for A in sorted(B.keys()):I=B[A];H.append({_F:I[_F]or f"call_{A}",_B:I[_B],_J:_safe_json_loads(I[_K])})
	return AIMessage(content=''.join(K),tool_calls=H if H else[])
SYSTEM_PROMPT_TEMPLATE='你是以「创造力」为核心的助手，能力均通过对话创建技能获得，仅可使用下列工具。\n\n## 工具\n\n**文件与执行**\n- read_file(path)：读取项目内指定路径的文本文件；path 可为相对项目根的路径，如 skills/技能名/SKILL.md。\n- write_file(path, content)：向项目内指定路径写入文本；path 可为相对项目根，如 skills/技能名/SKILL.md、skills/技能名/scripts/main.py；父目录不存在会自动创建。\n- exec_bash(command, working_dir?)：在项目根或指定 working_dir（相对项目根）下执行 shell 命令；执行技能时可将 working_dir 设为技能目录（如 skills/技能名）。\n\n**技能发现（目录 skills/技能名/）**\n- list_skill_tree()：列出所有技能及其描述（来自内存中的 frontmatter）。\n- search_skills(query)：按关键词检索技能，缩小候选后再用 read_file 查看或 exec_bash 执行。\n\n**技能读写与执行**：技能的读、写统一用 read_file / write_file。读技能用 read_file(skills/技能名/SKILL.md)；创建技能用 write_file 写入 SKILL.md 和（可选）scripts/main.py。执行时根据 SKILL.md 中的 run、scripts 等说明，在技能目录下用 exec_bash 执行（working_dir 设为该技能目录）。\n\n## 工作流\n\n根据系统注入的「已加载技能」（含 path）用 read_file(path) 查看 SKILL.md，再按文档用 exec_bash 执行；无合适技能时用 write_file 创建 skills/新技能名/SKILL.md 及 scripts/main.py，再按同上方式执行。\n\n## UI 输出（强约束）\n\n如需用户填写参数，直接输出 RJSF 格式的表单描述。表单必须用字段名 `ui_schema`，值是标准 JSON Schema（包含 `type: "object"` 和 `properties` 字段，可选 `required`、`title`、`description`），始终只返回一个 JSON 对象。\n\n示例：\n{"ui_schema":{"title":"表单标题","type":"object","properties":{"name":{"type":"string","title":"姓名"},"level":{"type":"string","title":"等级","enum":["高","中","低"]}},"required":["name"]}}\n\n最后用自然语言总结回复用户。'
def _run_agent_loop_core(client:OpenAI,model:str,system_prompt:str,user_input:str,max_turns:int=10,history_prefix:Optional[List[dict]]=_A,summary_before_history:Optional[str]=_A,on_step:Optional[Callable[[str,Any],_A]]=_A,on_text_delta:Optional[Callable[[str],_A]]=_A):
	'\n    OpenClaw 风格 Agent 循环：多轮调用 API、执行工具直到无 tool_calls 或达 max_turns。\n\n    @param history_prefix 当前对话中最近若干条 [{"role","content"}]，拼在 system 与当前 user 之间\n    @param summary_before_history 更早对话的摘要，会追加到 system_prompt 后\n    @param on_step 可选；每记录一步时回调 (step_name, content)，用于推送步骤\n    @param on_text_delta 可选；收到模型文本增量时回调 (text_piece)，用于真正流式文本\n    ';Q=history_prefix;P='(max turns reached)';K=summary_before_history;J='final_reply';C=on_step;L=system_prompt
	if K and K.strip():L=L+'\n\n## 更早的对话摘要\n'+K.strip()
	A=[SystemMessage(content=L)]
	if Q:A.extend(_history_to_langchain(Q))
	A.append(HumanMessage(content=user_input));M=0;R=0
	while M<max_turns:
		_prune_old_tool_results(A,keep_recent=3,max_chars_per_old=800);V=A[R:];F=_format_messages_for_step_log(V,max_chars=_A,max_tool_content=_A);G=chat_with_tools(client,model,A,on_text_delta=on_text_delta);H=getattr(G,_I,_A)or[];W=(G.content or'').strip();S=W or''
		if H:X=', '.join(A.get(_B,'?')for A in H);S=f"[tool_calls: {X}]"
		record_step('llm_response',S,input_sent=f"turn={M+1}",prompt_sent=F)
		if not H:
			B=(G.content or'').strip()or'(no reply)';record_step(J,B,input_sent=F,prompt_sent=F)
			if C:C(J,B)
			return B
		A.append(G)
		for I in H:
			D=I.get(_B,'');T=I.get(_J)if isinstance(I.get(_J),dict)else{};Y=I.get(_F,'');U=D;Z=D+'('+json.dumps(T,ensure_ascii=_G)+')'
			if D in tool_map:
				try:N=tool_map[D].invoke(T);E=N if isinstance(N,str)else str(N)
				except Exception as a:E=f"Error: {a}"
			else:E=f"Unknown tool: {D}"
			A.append(ToolMessage(content=E,tool_call_id=Y));record_step(U,E,input_sent=Z,prompt_sent=F)
			if C:C(U,E)
		R=len(A);M+=1
	B=P
	for O in reversed(A):
		if isinstance(O,AIMessage)and getattr(O,_C,_A):B=(O.content or'').strip()or P;break
	record_step(J,B,input_sent=P,prompt_sent='')
	if C:C(J,B)
	return B
def _get_client():'按当前环境变量创建 OpenAI 客户端。';A=os.getenv(_O)or os.getenv(_P)or'';B=os.getenv('OPENAI_BASE_URL','https://api.n1n.ai/v1');return OpenAI(api_key=A,base_url=B)
def _get_model():return os.getenv('OPENAI_MODEL','gpt-5')
STRENGTHS='通用对话、工具调用'
KEEP_RECENT_MESSAGES=10
def run_agent_loop(user_input:str,max_turns:int=10,history=_A,on_step=_A,on_text_delta=_A):
	'\n    默认 Agent 入口：按用户意图做技能检索注入系统提示；若 history 超过 KEEP_RECENT_MESSAGES 条，\n    更早的做摘要，最近若干条保留原文。然后执行工具循环。\n    ';H=user_input;A=history
	if not(os.getenv(_O)or os.getenv(_P)or'').strip():return'尚未配置 API 密钥。请打开前端「设置」页，设置 OPENAI_API_KEY 后再试；或先在项目根或 build 目录的 .env 中配置后重启服务。'
	I=_get_client();J=_get_model();K=get_skill_summaries_for_agent()
	if K:
		D=['\n## 已加载技能（用 read_file(path) 读 SKILL.md，再按文档用 exec_bash 执行）\n']
		for E in K:
			F=E.get(_B)or'';L=E.get('location')or f"skills/{F}/SKILL.md";M=(E.get(_M)or'').strip()[:200]
			if M:D.append(f"- {F}  path: {L}  — {M}")
			else:D.append(f"- {F}  path: {L}")
		B=SYSTEM_PROMPT_TEMPLATE+'\n'.join(D)
	else:B=SYSTEM_PROMPT_TEMPLATE
	C=search_skills_by_keyword(H or'')
	if C and C.strip()and'当前无技能'not in C:B=B+'\n\n与当前用户意图相关的技能（可优先选用）：\n'+C
	G=_A;N=_A
	if A and len(A)>0:
		if len(A)>KEEP_RECENT_MESSAGES:N=summarize_conversation(I,J,A[:-KEEP_RECENT_MESSAGES]);G=A[-KEEP_RECENT_MESSAGES:]
		else:G=A
	return _run_agent_loop_core(client=I,model=J,system_prompt=B,user_input=H,max_turns=max_turns,history_prefix=G,summary_before_history=N,on_step=on_step,on_text_delta=on_text_delta)
def analyze_for_memory(user_input:str,reply:str):'判断对话是否包含与用户相关的信息并生成总结，供写入记忆前调用。';return analyze_conversation_for_memory(_get_client(),_get_model(),user_input or'',reply or'')