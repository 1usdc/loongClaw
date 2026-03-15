'\n技能架构工具：大类 → 技能目录（内含 SKILL.md，可选 scripts/references/assets），列出/读取/写入技能。\n技能不由后端 subprocess 直接执行：由 Agent 用 read_file 读 SKILL.md、用 exec_bash 执行命令；参数经 SKILL_ARGS_JSON 传入，结果从 stdout/stderr 读取。\n执行前可根据 SKILL.md 的 metadata.requires.python 与 metadata.install 用 exec_bash 安装依赖。\n'
_H='SKILL.md'
_G=False
_F='当前无技能。'
_E='skill_key'
_D='keywords'
_C='name'
_B=None
_A='description'
import json,os,re
from datetime import datetime,timezone
from pathlib import Path
from typing import Annotated,Any
from langchain_core.tools import tool
try:import yaml
except ImportError:yaml=_B
SKILLS_ROOT='skills'
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/'data'
_skill_frontmatter_cache=_B
def load_skill_frontmatter_cache(force_refresh:bool=_G):
	'\n    动态加载所有技能的 frontmatter 到内存。\n    扫描 skills/ 下含 SKILL.md 的目录，解析每个 SKILL.md 的 YAML frontmatter，返回 skill_name -> frontmatter 字典。\n    若 force_refresh=True 或缓存未初始化则重新扫描；否则返回已有缓存。\n    ';global _skill_frontmatter_cache
	if _skill_frontmatter_cache is not _B and not force_refresh:return _skill_frontmatter_cache
	C=BASE_DIR/SKILLS_ROOT;B={}
	if not C.is_dir():_skill_frontmatter_cache=B;return B
	for A in sorted(C.iterdir()):
		if not A.is_dir()or A.name.startswith('.')or A.name=='README.md':continue
		E=A/_H
		if not E.is_file():continue
		D=_parse_skill_frontmatter(str(A))
		if D:B[A.name]=D
	_skill_frontmatter_cache=B;return B
def get_skill_frontmatter_cache(force_refresh:bool=_G):'返回技能 frontmatter 缓存（懒加载）。';return load_skill_frontmatter_cache(force_refresh=force_refresh)
def refresh_skill_frontmatter_cache():'在导入或更新技能后调用，使下次读取使用最新 frontmatter。';load_skill_frontmatter_cache(force_refresh=True)
def get_skill_summaries_for_agent():
	'\n    从内存缓存生成供 Agent 使用的技能摘要列表（name, description, keywords, location），\n    便于技能 prompt 注入：Agent 用 read_file(location) 读 SKILL.md，用 exec_bash 执行。\n    ';F=get_skill_frontmatter_cache();E=[]
	for(B,C)in F.items():
		G=(C.get(_C)or'').strip()or B;H=(C.get(_A)or'').strip();A=C.get(_D)
		if isinstance(A,str):D=[A.strip()for A in A.split(',')if A.strip()]
		elif isinstance(A,list):D=[str(A).strip()for A in A if str(A).strip()]
		else:D=[]
		I=f"{SKILLS_ROOT}/{B}/SKILL.md";E.append({_C:B,'display_name':G,_A:H,_D:D,'location':I})
	return E
SCORE_CRITERIA={_A:(15,'技能描述（frontmatter description 或正文描述）'),'when_to_use':(20,'使用场景（## 使用场景 或等同内容）'),'steps':(25,'步骤与说明（## 步骤与说明 或等同内容）'),'script':(25,'可执行脚本（scripts/main.py 存在）'),'references':(15,'参考资料（references/ 目录存在且含文件）')}
SKILL_MD_TEMPLATE='---\nname: {skill_name}\ndescription: {description}\nkeywords: {keywords}\ncreated_at: {created_at}\n---\n\n# {title}\n\n{description}\n\n## 使用场景\n{when_to_use}\n\n## 步骤与说明\n{steps}\n'
def _load_ratings():'从 SQLite 加载评分列表，格式为 []，每项为 { skill_key, count?, ... }。';from tools.db import db_load_skill_ratings as A;return A()
def get_skill_ratings_list():'供 API 使用：返回评分列表，格式为 [{ skill_key, ... }, ...]。';return _load_ratings()
def _save_ratings(data:list):'保存评分列表到 SQLite。';from tools.db import db_save_skill_ratings as A;A(data)
def _find_rating_entry(ratings:list,skill_key:str):
	'在数组中找到 skill_key 对应的项（dict），不存在返回 None。'
	for A in ratings:
		if isinstance(A,dict)and A.get(_E)==skill_key:return A
def _rating_entry_to_dict(entry:dict):
	'从数组项中去掉 skill_key，得到仅含评分字段的 dict，供前端 rating 使用。';A=entry
	if not isinstance(A,dict):return{}
	return{A:B for(A,B)in A.items()if A!=_E}
def remove_skill_from_ratings(skill_key:str):'从评分表中移除指定技能。';from tools.db import db_remove_skill_rating as A;A(skill_key)
def add_skill_usage(action_name:str):
	'\n    内部函数：记录技能使用次数 +1，供后端或扩展调用。\n    若 action_name 不存在则自动创建。\n    ';C='count';B=action_name
	if not B or not B.strip():return
	D=B.strip();from tools.db import db_load_skill_ratings as F,db_upsert_skill_rating_entry as E;G=F();A=_find_rating_entry(G,D)
	if A is not _B:A[C]=A.get(C,0)+1;E(A)
	else:E({_E:D,C:1})
@tool(description='记录用户对技能的指定动作；参数为技能名和动作，自动+1，若不存在则创建，用于统计技能每种操作的使用频次。')
def record_skill_usage(skill_name:Annotated[str,'技能名，如 open_url'],action_name:Annotated[str,'动作，例如 like, copy, recall']):
	'\n    记录用户对技能的指定动作。参数为技能名和动作，自动+1，若不存在则创建。\n    用于统计技能每种操作的使用频次。\n    ';H='错误: action_name 不能为空。';G='错误: skill_name 不能为空。';E=action_name;D=skill_name
	if not D or not isinstance(D,str):return G
	if not E or not isinstance(E,str):return H
	B=D.strip();A=E.strip()
	if not B:return G
	if not A:return H
	from tools.db import db_load_skill_ratings as I,db_upsert_skill_rating_entry as F;J=I();C=_find_rating_entry(J,B)
	if C is not _B:C[A]=C.get(A,0)+1;F(C)
	else:F({_E:B,A:1})
	return f"已记录: {B} 的动作 {A} 使用次数 +1。"
def _skill_dir(base:str,skill_name:str):'技能目录路径：skills/技能名/（无大类，与 README 目录结构一致）';return os.path.join(base,skill_name)
def _skill_md_path(skill_dir:str):'技能主文档路径：技能目录/SKILL.md';return os.path.join(skill_dir,_H)
def _skill_meta_for_search(skill_dir:str):
	'返回 (name, description, keywords) 供关键词检索。';D=skill_dir;B=_parse_skill_frontmatter(D);E=(B.get(_C)or'').strip()or os.path.basename(D);F=(B.get(_A)or'').strip();A=B.get(_D)
	if isinstance(A,str):C=[A.strip()for A in A.split(',')if A.strip()]
	elif isinstance(A,list):C=[str(A).strip()for A in A if str(A).strip()]
	else:C=[]
	return E,F,C
def _format_skill_line(skill_name:str,description:str):
	'格式化单条技能为 Agent 可读：技能名 + 描述，便于根据描述用 read_file(location) + exec_bash 执行。';A=skill_name;B=(description or'').strip()[:200]
	if B:return f"  - {A}: {B}"
	return f"  - {A}/ (SKILL.md)"
def search_skills_by_keyword(query:str):
	'\n    按关键词/描述检索本地技能，返回与 query 匹配的技能列表（含 frontmatter 描述）。\n    匹配规则：query 按空格分词，每个词需出现在技能名、description 或 keywords 中（不区分大小写）。\n    若 query 为空则返回全部技能（等价 list_skill_tree）。使用内存中的 frontmatter 缓存。\n    ';B=get_skill_frontmatter_cache()
	if not B:
		if not(BASE_DIR/SKILLS_ROOT).is_dir():return f"技能根目录不存在: {SKILLS_ROOT}，可先用 write_file 创建 skills/技能名/SKILL.md 以自动形成目录。"
		return _F
	G=[A.strip().lower()for A in(query or'').strip().split()if A.strip()];C=[]
	for D in sorted(B.keys()):
		E=B[D];I=(E.get(_C)or'').strip()or D;H=(E.get(_A)or'').strip();A=E.get(_D)
		if isinstance(A,str):F=[A.strip()for A in A.split(',')if A.strip()]
		elif isinstance(A,list):F=[str(A).strip()for A in A if str(A).strip()]
		else:F=[]
		J=' '.join([I,H]+F).lower()
		if G and not all(A in J for A in G):continue
		C.append(_format_skill_line(D,H))
	return'\n'.join(C)if C else _F
@tool(description='列出技能树：skills/ 下各技能目录及描述（来自 SKILL.md frontmatter），便于根据描述用 read_file(location) + exec_bash 执行。')
def list_skill_tree():
	'\n    列出技能树：从内存中的 frontmatter 缓存读取各技能名称与描述。\n    返回可读列表（技能名: 描述），便于用 read_file(skills/技能名/SKILL.md) 查看、exec_bash 执行。\n    ';A=get_skill_frontmatter_cache()
	if not A:
		if not(BASE_DIR/SKILLS_ROOT).is_dir():return f"技能根目录不存在: {SKILLS_ROOT}，可先用 write_file 创建 skills/技能名/SKILL.md 以自动形成目录。"
		return _F
	B=[]
	for C in sorted(A.keys()):D=(A[C].get(_A)or'').strip();B.append(_format_skill_line(C,D))
	return'\n'.join(B)if B else _F
@tool(description='按关键词检索本地技能，返回匹配的技能列表（格式同 list_skill_tree）；用户表达意图后先调用此工具缩小候选，再用 read_file(path) + exec_bash 执行。')
def search_skills(query:Annotated[str,'检索关键词，支持多词（空格分隔）；匹配技能名、描述或 keywords']):'\n    按关键词检索本地技能，返回匹配的技能列表（格式同 list_skill_tree）。\n    用户表达意图后先调用此工具缩小候选，再用 read_file(skills/技能名/SKILL.md) 查看、exec_bash 执行。\n    ';return search_skills_by_keyword(query)
def _parse_skill_frontmatter(skill_dir:str):
	'\n    读取技能目录下 SKILL.md 的 frontmatter，解析为字典。\n    返回的 metadata 含 requires.python（列表）与 install（列表）。\n    ';A=os.path.join(skill_dir,_H)
	if not os.path.isfile(A):return{}
	try:B=Path(A).read_text(encoding='utf-8')
	except Exception:return{}
	if not B.strip().startswith('---'):return{}
	C=re.match('^---\\s*\\n(.*?)\\n---\\s*\\n?',B,flags=re.DOTALL)
	if not C:return{}
	E=C.group(1)
	if not yaml:return{}
	try:D=yaml.safe_load(E);return D if isinstance(D,dict)else{}
	except Exception:return{}
def write_skill(skill_name:str,content:str,use_template:bool=_G,title:str='',when_to_use:str='',steps:str=''):
	B=content;A=skill_name;C=_skill_dir(SKILLS_ROOT,A);D=_skill_md_path(C);os.makedirs(C,exist_ok=True)
	if use_template:E=SKILL_MD_TEMPLATE.format(title=title or A,skill_name=A,description=B,created_at=datetime.now(timezone.utc).isoformat(timespec='seconds'),when_to_use=when_to_use or'(请补充使用场景)',steps=steps or'(请补充步骤)')
	else:E=B
	with open(D,'w',encoding='utf-8')as F:F.write(E)
	return f"已写入技能: {D}"