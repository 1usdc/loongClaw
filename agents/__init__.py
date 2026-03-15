'\n多 Agent 注册与执行；当前仅一个 Agent，未指定时使用默认。\n'
_E='analyze_for_memory'
_D='strengths'
_C='run_agent_loop'
_B='n1n'
_A=None
import os
from tools import record_step,start_timing_session
from.import base
AGENTS={_B:{'name':_B,_D:base.STRENGTHS,_C:base.run_agent_loop,_E:base.analyze_for_memory}}
DEFAULT_AGENT_ID=os.getenv('OPENAGI_AGENT',_B)
def get_agent(agent_id:str|_A=_A):
	'\n    获取指定 Agent 的配置（name, strengths, run_agent_loop）。\n    若 agent_id 为 None 或未注册，使用默认 Agent。\n    ';A=(agent_id or DEFAULT_AGENT_ID).strip().lower()
	if A not in AGENTS:return AGENTS[DEFAULT_AGENT_ID]
	return AGENTS[A]
def run_agent_loop(user_input:str,max_turns:int=10,agent_id:str|_A=_A,history:list|_A=_A,on_step=_A,on_text_delta=_A):
	'\n    运行一轮对话：未指定 agent_id 时使用默认 Agent 执行并调用技能。\n    history 为当前对话内上下文 [{"role":"user"|"assistant","content":str}, ...]，超过 10 条时更早的会做摘要。\n    on_step 若提供，每步会回调 (step_name, content)，用于流式推送。\n    on_text_delta 若提供，每个文本增量会回调 (text_piece)。\n    ';start_timing_session();A=get_agent(agent_id)
	try:return A[_C](user_input,max_turns=max_turns,history=history,on_step=on_step,on_text_delta=on_text_delta)
	except Exception as B:record_step('error',str(B),input_sent=_A,prompt_sent=_A);raise
def interactive_chat(agent_id:str|_A=_A):
	'\n    交互式对话：使用默认或指定的 Agent 执行并调用技能；输入 exit/quit/q 或空行结束。\n    ';A=get_agent(agent_id);C,D=A['name'],A[_D];print(f"当前 Agent: {C}（擅长: {D}）");print('输入你的问题，输入 exit / quit / q 或空行结束。\n')
	while True:
		try:B=input('你: ').strip()
		except EOFError:break
		if not B or B.lower()in('exit','quit','q'):print('再见。');break
		start_timing_session();E=A[_C](B);print('\n助手:',E,'\n')
def analyze_conversation_for_memory(user_input:str,reply:str):
	'\n    判断本轮对话是否包含与用户相关的、值得长期记忆的信息；若值得则返回总结。\n    供对话结束后写入记忆前调用。返回 (是否应写入, 总结文本)。\n    ';B=get_agent(_A);A=B.get(_E)
	if not A:return False,''
	return A(user_input or'',reply or'')