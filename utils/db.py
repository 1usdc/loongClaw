'\nSQLite 数据层：数据库存于 data/database/sqlite.db。\n记忆改为文件存储（见 utils.memory），personas / skill_ratings / config 仍在本库。\n'
_S='INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)'
_R='SELECT value FROM config WHERE key = ?'
_Q='INSERT INTO skill_ratings (skill_key, data) VALUES (?, ?)'
_P='avatar'
_O='INSERT INTO personas (id, name, avatar, created_at) VALUES (?, ?, ?, ?)'
_N='updated_at'
_M='next_run_at'
_L='status'
_K='prompt'
_J='interval_seconds'
_I='start_time'
_H='value'
_G='created_at'
_F='data'
_E='id'
_D=True
_C=False
_B='skill_key'
_A=None
import json,sqlite3
from pathlib import Path
from typing import Any
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/_F
DB_DIR=DATA_DIR/'database'
DB_PATH=DB_DIR/'sqlite.db'
def _ensure_data_dir():DATA_DIR.mkdir(parents=_D,exist_ok=_D);DB_DIR.mkdir(parents=_D,exist_ok=_D)
def get_connection():'获取可读写的 SQLite 连接；自动创建 data/database 目录与数据库文件。';_ensure_data_dir();A=sqlite3.connect(str(DB_PATH),check_same_thread=_C);A.row_factory=sqlite3.Row;return A
def init_schema(conn:sqlite3.Connection):'创建表结构（若不存在）。记忆存于 data/memory/ 文件，不在此库。';conn.executescript("\n        CREATE TABLE IF NOT EXISTS personas (\n            id TEXT PRIMARY KEY,\n            name TEXT NOT NULL,\n            avatar TEXT,\n            created_at TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS skill_ratings (\n            skill_key TEXT PRIMARY KEY,\n            data TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS config (\n            key TEXT PRIMARY KEY,\n            value TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS scheduled_tasks (\n            id TEXT PRIMARY KEY,\n            start_time TEXT NOT NULL,\n            interval_seconds INTEGER NOT NULL,\n            prompt TEXT NOT NULL,\n            status TEXT NOT NULL DEFAULT 'active',\n            next_run_at TEXT,\n            created_at TEXT NOT NULL,\n            updated_at TEXT NOT NULL\n        );\n    ");conn.commit()
def _conn():'获取连接并确保 schema 已初始化。';A=get_connection();init_schema(A);return A
def db_load_personas():
	'从 SQLite 加载分身列表。';A=_conn()
	try:B=A.execute('SELECT id, name, avatar, created_at FROM personas ORDER BY created_at ASC').fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_add_persona(rec:dict[str,Any]):
	'插入一条分身。';A=rec;B=_conn()
	try:B.execute(_O,(A[_E],A['name'],A.get(_P)or'',A[_G]));B.commit()
	finally:B.close()
def db_update_persona(persona_id:str,name:str,avatar:str|_A):
	'更新分身名称与头像；avatar 为 None 表示不修改头像。返回是否找到。';C=avatar;B=persona_id;A=_conn()
	try:
		if C is not _A:D=A.execute('UPDATE personas SET name = ?, avatar = ? WHERE id = ?',(name,C,B))
		else:D=A.execute('UPDATE personas SET name = ? WHERE id = ?',(name,B))
		A.commit();return D.rowcount>0
	finally:A.close()
def db_delete_persona(persona_id:str):
	'删除分身；返回是否找到并删除。';A=_conn()
	try:B=A.execute('DELETE FROM personas WHERE id = ?',[persona_id]);A.commit();return B.rowcount>0
	finally:A.close()
def db_load_skill_ratings():
	'从 SQLite 加载评分列表，格式与原 JSON 一致：[{ skill_key, count?, ... }, ...]。';B=_conn()
	try:
		E=B.execute('SELECT skill_key, data FROM skill_ratings').fetchall();C=[]
		for A in E:
			D=json.loads(A[_F])if A[_F]else{}
			if isinstance(D,dict):C.append({_B:A[_B],**D})
		return C
	finally:B.close()
def db_save_skill_ratings(items:list[dict[str,Any]]):
	'将评分列表写入 SQLite；每项需含 skill_key，其余字段存为 JSON。';A=_conn()
	try:
		A.execute('DELETE FROM skill_ratings')
		for B in items:
			if not isinstance(B,dict)or not B.get(_B):continue
			C=B[_B];D={A:B for(A,B)in B.items()if A!=_B};A.execute(_Q,(C,json.dumps(D,ensure_ascii=_C)))
		A.commit()
	finally:A.close()
def db_remove_skill_rating(skill_key:str):
	'从评分表删除指定 skill_key；返回是否删除。';A=_conn()
	try:B=A.execute('DELETE FROM skill_ratings WHERE skill_key = ?',[skill_key]);A.commit();return B.rowcount>0
	finally:A.close()
CONFIG_KEY_COMMAND_WHITELIST='command_whitelist'
def db_get_config(key:str):
	'读取 config 表；返回 JSON 解析后的 dict，不存在返回 None。';B=_conn()
	try:
		A=B.execute(_R,[key]).fetchone()
		if not A or not A[_H]:return
		return json.loads(A[_H])
	finally:B.close()
def db_set_config(key:str,value:dict[str,Any]):
	'写入 config 表（JSON 序列化）。';A=_conn()
	try:A.execute(_S,(key,json.dumps(value,ensure_ascii=_C)));A.commit()
	finally:A.close()
def db_list_scheduled_tasks():
	'列出所有定时任务，按创建时间倒序。';A=_conn()
	try:B=A.execute('SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks ORDER BY created_at DESC').fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_get_scheduled_task(task_id:str):
	'按 id 获取一条定时任务。';A=_conn()
	try:B=A.execute('SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks WHERE id = ?',(task_id,)).fetchone();return dict(B)if B else _A
	finally:A.close()
def db_create_scheduled_task(rec:dict[str,Any]):
	'创建定时任务。rec 需含 id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at。';A=rec;B=_conn()
	try:B.execute('INSERT INTO scheduled_tasks (id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?)',(A[_E],A[_I],A[_J],A[_K],A.get(_L,'active'),A.get(_M),A[_G],A[_N]));B.commit()
	finally:B.close()
def db_update_scheduled_task(task_id:str,*,start_time:str|_A=_A,interval_seconds:int|_A=_A,prompt:str|_A=_A,status:str|_A=_A,next_run_at:str|_A=_A,updated_at:str):
	'更新定时任务；仅传要改的字段。返回是否找到。';H=next_run_at;G=status;F=prompt;E=interval_seconds;D=start_time;C=task_id;B=_conn()
	try:
		A=B.execute('SELECT * FROM scheduled_tasks WHERE id = ?',(C,)).fetchone()
		if not A:return _C
		A=dict(A)
		if D is not _A:A[_I]=D
		if E is not _A:A[_J]=E
		if F is not _A:A[_K]=F
		if G is not _A:A[_L]=G
		if H is not _A:A[_M]=H
		A[_N]=updated_at;B.execute('UPDATE scheduled_tasks SET start_time=?, interval_seconds=?, prompt=?, status=?, next_run_at=?, updated_at=? WHERE id=?',(A[_I],A[_J],A[_K],A[_L],A[_M],A[_N],C));B.commit();return _D
	finally:B.close()
def db_delete_scheduled_task(task_id:str):
	'删除定时任务。返回是否找到并删除。';A=_conn()
	try:B=A.execute('DELETE FROM scheduled_tasks WHERE id = ?',(task_id,));A.commit();return B.rowcount>0
	finally:A.close()
def db_get_tasks_due(next_run_before:str):
	"获取 next_run_at <= next_run_before 且 status='active' 的任务，用于调度执行。";A=_conn()
	try:B=A.execute("SELECT id, start_time, interval_seconds, prompt, status, next_run_at, created_at, updated_at FROM scheduled_tasks WHERE status = 'active' AND next_run_at IS NOT NULL AND next_run_at <= ?",(next_run_before,)).fetchall();return[dict(A)for A in B]
	finally:A.close()
def migrate_from_json_if_needed():
	'若 SQLite 表为空且对应 JSON 文件存在，则从 JSON 导入数据。';G='utf-8';A=get_connection();init_schema(A)
	try:
		F=A.execute('SELECT COUNT(*) FROM personas').fetchone()[0]
		if F==0:
			B=DATA_DIR/'personas.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=G))
					if isinstance(C,list):
						for D in C:
							if isinstance(D,dict)and D.get(_E):A.execute(_O,(D[_E],D.get('name')or'',D.get(_P)or'',D.get(_G)or''))
						A.commit()
				except Exception:pass
		F=A.execute('SELECT COUNT(*) FROM skill_ratings').fetchone()[0]
		if F==0:
			B=DATA_DIR/'skill_ratings.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=G))
					if isinstance(C,list):
						for E in C:
							if isinstance(E,dict)and E.get(_B):I=E[_B];J={A:B for(A,B)in E.items()if A!=_B};A.execute(_Q,(I,json.dumps(J,ensure_ascii=_C)))
						A.commit()
				except Exception:pass
		H=A.execute(_R,[CONFIG_KEY_COMMAND_WHITELIST]).fetchone()
		if not H or not H[_H]:
			B=DATA_DIR/'command_whitelist.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=G))
					if isinstance(C,dict):A.execute(_S,(CONFIG_KEY_COMMAND_WHITELIST,json.dumps(C,ensure_ascii=_C)));A.commit()
				except Exception:pass
	finally:A.close()