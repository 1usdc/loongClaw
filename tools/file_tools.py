'\n文件与 shell 工具：读文件、执行 bash 命令。\n'
_D='错误: 无法解析路径。'
_C='文件路径（相对项目根或绝对路径，须在项目内）'
_B='错误: path 不能为空。'
_A=None
import os,shlex,subprocess
from pathlib import Path
from typing import Annotated
from langchain_core.tools import tool
BASE_DIR=os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SAFE_EXEC_ROOT=BASE_DIR
PROJECT_ROOT=BASE_DIR
DEFAULT_TIMEOUT=30
MAX_TIMEOUT=120
DEFAULT_ALLOWED_COMMANDS={'ls','pwd','echo','cat','python','python3','pip','pip3','git','rg','which','whoami','env','head','tail','wc','sort','uniq','date','curl','wget','npm','node'}
DEFAULT_BLOCKED_TOKEN_PATTERNS='&&','||',';','|','>','<','$(','`'
DEFAULT_BLOCKED_COMMAND_KEYWORDS='rm','mv','cp','chmod','chown','sudo','shutdown','reboot','mkfs','dd','kill','pkill','killall'
def _load_exec_policy():
	'\n    从 SQLite config 表（key=command_whitelist）读取执行策略；\n    不存在或格式异常时使用内置默认值。\n    ';E=set(DEFAULT_ALLOWED_COMMANDS);F=tuple(DEFAULT_BLOCKED_TOKEN_PATTERNS);G=tuple(DEFAULT_BLOCKED_COMMAND_KEYWORDS);C=DEFAULT_TIMEOUT;D=MAX_TIMEOUT
	try:from tools.db import db_get_config as M,CONFIG_KEY_COMMAND_WHITELIST as N;B=M(N)
	except Exception:B=_A
	if isinstance(B,dict):
		H=B.get('allowed_commands')
		if isinstance(H,list):
			A={str(A).strip()for A in H if str(A).strip()}
			if A:E=A
		I=B.get('blocked_token_patterns')
		if isinstance(I,list):
			A=tuple(str(A)for A in I if str(A))
			if A:F=A
		J=B.get('blocked_command_keywords')
		if isinstance(J,list):
			A=tuple(str(A).strip()for A in J if str(A).strip())
			if A:G=A
		K=B.get('default_timeout');L=B.get('max_timeout')
		if isinstance(K,int):C=max(1,K)
		if isinstance(L,int):D=max(1,L)
		if C>D:C=D
	return E,F,G,C,D
def _resolve_read_path(path:str):
	'\n    解析读文件路径：支持相对项目根的路径，且必须落在项目根内。\n    返回 (resolved_abs_path, error_message)；成功时 error_message 为空。\n    ';B=path
	if not B or not B.strip():return _A,_B
	C=B.strip().replace('\\',os.sep)
	if os.path.isabs(C):A=os.path.normpath(C)
	else:A=os.path.normpath(os.path.join(PROJECT_ROOT,C))
	try:A=os.path.realpath(A)
	except OSError:return _A,f"错误: 路径无法解析: {B}"
	D=os.path.realpath(PROJECT_ROOT)
	if not(A==D or A.startswith(D+os.sep)):return _A,f"错误: 路径必须在项目根内: {B}"
	if not os.path.isfile(A):return _A,f"错误: 不是文件或不存在: {B}"
	return A,''
def _resolve_write_path(path:str):
	'\n    解析写文件路径：支持相对项目根的路径，且必须落在项目根内；目标可为新文件，父目录不存在则创建。\n    返回 (resolved_abs_path, error_message)；成功时 error_message 为空。\n    ';B=path
	if not B or not B.strip():return _A,_B
	C=B.strip().replace('\\',os.sep);D=os.path.realpath(PROJECT_ROOT)
	if os.path.isabs(C):A=os.path.normpath(C)
	else:A=os.path.normpath(os.path.join(PROJECT_ROOT,C))
	if os.path.exists(A):
		try:A=os.path.realpath(A)
		except OSError:pass
		if os.path.isdir(A):return _A,f"错误: 路径是目录而非文件: {B}"
	else:A=os.path.abspath(A)
	if not(A==D or A.startswith(D+os.sep)):return _A,f"错误: 路径必须在项目根内: {B}"
	return A,''
@tool(description='读取项目内指定路径的文本文件内容；路径可为相对项目根，如 skills/技能名/SKILL.md。')
def read_file(path:Annotated[str,_C]):
	'读取项目内指定路径的文本文件内容。路径相对项目根时如 skills/weather/SKILL.md。';A,B=_resolve_read_path(path)
	if B or A is _A:return B or _D
	with open(A,'r',encoding='utf-8',errors='replace')as C:return C.read()
@tool(description='向项目内指定路径写入文本内容；路径可为相对项目根，如 skills/技能名/SKILL.md；父目录不存在会自动创建。')
def write_file(path:Annotated[str,_C],content:Annotated[str,'要写入的完整文本内容']):
	'向项目内指定路径写入文本内容。路径相对项目根时如 skills/weather/SKILL.md。';A,C=_resolve_write_path(path)
	if C or A is _A:return C or _D
	try:
		B=os.path.dirname(A)
		if B and not os.path.isdir(B):os.makedirs(B,exist_ok=True)
		with open(A,'w',encoding='utf-8')as D:D.write(content)
		return'已写入: '+path
	except OSError as E:return f"错误: 写入失败: {E}"
@tool(description='安全执行一条白名单命令：限制目录、限制超时、禁止危险命令。')
def exec_bash(command:Annotated[str,'要执行的命令（仅允许白名单命令，不支持管道和重定向）'],working_dir:Annotated[str,'可选工作目录（必须在项目目录内）']='',timeout_sec:Annotated[int,'超时时间（秒，默认 30，最大 120）']=DEFAULT_TIMEOUT):
	'安全执行一条白名单命令：限制目录、限制超时、禁止危险命令。';N='错误: command 不能为空。';I=timeout_sec;F=command;A=working_dir;O,P,Q,R,S=_load_exec_policy()
	if not F or not F.strip():return N
	J=F.strip()
	if any(A in J for A in P):return'错误: 不允许使用管道、重定向、命令拼接或命令替换符号。'
	try:G=shlex.split(J)
	except ValueError as H:return f"错误: 命令解析失败: {H}"
	if not G:return N
	B=G[0]
	if B not in O:return f"错误: 命令不在白名单中: {B}"
	if B in Q:return f"错误: 禁止执行危险命令: {B}"
	C=I if isinstance(I,int)else R;C=max(1,min(C,S));K=SAFE_EXEC_ROOT
	if A and A.strip():
		D=os.path.realpath(os.path.join(SAFE_EXEC_ROOT,A));L=os.path.realpath(SAFE_EXEC_ROOT)
		if not D.startswith(L+os.sep)and D!=L:return'错误: working_dir 必须在项目目录内。'
		if not os.path.isdir(D):return f"错误: working_dir 不存在: {A}"
		K=D
	try:
		E=subprocess.run(G,capture_output=True,text=True,timeout=C,cwd=K,shell=False);M=E.stdout or'';T=E.stderr or''
		if E.returncode!=0:return f"exit code: {E.returncode}\nstdout:\n{M}\nstderr:\n{T}"
		return M.strip()or'(no output)'
	except subprocess.TimeoutExpired:return f"错误: 命令超时（{C} 秒）"
	except Exception as H:return f"错误: {H}"