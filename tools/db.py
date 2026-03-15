'\nSQLite 数据层：数据库存于 data/database/loongclaw.db。\n记忆改为文件存储（见 tools.memory_tools），personas / skill_ratings / config 仍在本库。\n'
_J='INSERT OR REPLACE INTO config (key, value) VALUES (?, ?)'
_I='SELECT value FROM config WHERE key = ?'
_H='INSERT INTO skill_ratings (skill_key, data) VALUES (?, ?)'
_G='created_at'
_F='avatar'
_E='INSERT INTO personas (id, name, avatar, created_at) VALUES (?, ?, ?, ?)'
_D='value'
_C='data'
_B=False
_A='skill_key'
import json,sqlite3
from pathlib import Path
from typing import Any
BASE_DIR=Path(__file__).resolve().parents[1]
DATA_DIR=BASE_DIR/_C
DB_DIR=DATA_DIR/'database'
DB_PATH=DB_DIR/'loongclaw.db'
def _ensure_data_dir():A=True;DATA_DIR.mkdir(parents=A,exist_ok=A);DB_DIR.mkdir(parents=A,exist_ok=A)
def get_connection():'获取可读写的 SQLite 连接；自动创建 data/database 目录与数据库文件。';_ensure_data_dir();A=sqlite3.connect(str(DB_PATH),check_same_thread=_B);A.row_factory=sqlite3.Row;return A
def init_schema(conn:sqlite3.Connection):'创建表结构（若不存在）。记忆存于 data/memory/ 文件，不在此库。';conn.executescript('\n        CREATE TABLE IF NOT EXISTS personas (\n            id TEXT PRIMARY KEY,\n            name TEXT NOT NULL,\n            avatar TEXT,\n            created_at TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS skill_ratings (\n            skill_key TEXT PRIMARY KEY,\n            data TEXT NOT NULL\n        );\n        CREATE TABLE IF NOT EXISTS config (\n            key TEXT PRIMARY KEY,\n            value TEXT NOT NULL\n        );\n    ');conn.commit()
def _conn():'获取连接并确保 schema 已初始化。';A=get_connection();init_schema(A);return A
def db_load_personas():
	'从 SQLite 加载分身列表。';A=_conn()
	try:B=A.execute('SELECT id, name, avatar, created_at FROM personas ORDER BY created_at ASC').fetchall();return[dict(A)for A in B]
	finally:A.close()
def db_add_persona(rec:dict[str,Any]):
	'插入一条分身。';A=rec;B=_conn()
	try:B.execute(_E,(A['id'],A['name'],A.get(_F)or'',A[_G]));B.commit()
	finally:B.close()
def db_update_persona(persona_id:str,name:str,avatar:str|None):
	'更新分身名称与头像；avatar 为 None 表示不修改头像。返回是否找到。';C=avatar;B=persona_id;A=_conn()
	try:
		if C is not None:D=A.execute('UPDATE personas SET name = ?, avatar = ? WHERE id = ?',(name,C,B))
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
			D=json.loads(A[_C])if A[_C]else{}
			if isinstance(D,dict):C.append({_A:A[_A],**D})
		return C
	finally:B.close()
def db_save_skill_ratings(items:list[dict[str,Any]]):
	'将评分列表写入 SQLite；每项需含 skill_key，其余字段存为 JSON。';A=_conn()
	try:
		A.execute('DELETE FROM skill_ratings')
		for B in items:
			if not isinstance(B,dict)or not B.get(_A):continue
			C=B[_A];D={A:B for(A,B)in B.items()if A!=_A};A.execute(_H,(C,json.dumps(D,ensure_ascii=_B)))
		A.commit()
	finally:A.close()
def db_remove_skill_rating(skill_key:str):
	'从评分表删除指定 skill_key；返回是否删除。';A=_conn()
	try:B=A.execute('DELETE FROM skill_ratings WHERE skill_key = ?',[skill_key]);A.commit();return B.rowcount>0
	finally:A.close()
def db_upsert_skill_rating_entry(entry:dict[str,Any]):
	'单条更新：按 skill_key 合并到已有记录或插入新记录。';F=entry;B=F.get(_A)
	if not B:return
	C={A:B for(A,B)in F.items()if A!=_A};A=_conn()
	try:
		D=A.execute('SELECT data FROM skill_ratings WHERE skill_key = ?',[B]).fetchone()
		if D:
			E=json.loads(D[_C])if D[_C]else{}
			if isinstance(E,dict):E.update(C);C=E
		A.execute('INSERT OR REPLACE INTO skill_ratings (skill_key, data) VALUES (?, ?)',(B,json.dumps(C,ensure_ascii=_B)));A.commit()
	finally:A.close()
CONFIG_KEY_COMMAND_WHITELIST='command_whitelist'
def db_get_config(key:str):
	'读取 config 表；返回 JSON 解析后的 dict，不存在返回 None。';B=_conn()
	try:
		A=B.execute(_I,[key]).fetchone()
		if not A or not A[_D]:return
		return json.loads(A[_D])
	finally:B.close()
def db_set_config(key:str,value:dict[str,Any]):
	'写入 config 表（JSON 序列化）。';A=_conn()
	try:A.execute(_J,(key,json.dumps(value,ensure_ascii=_B)));A.commit()
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
							if isinstance(D,dict)and D.get('id'):A.execute(_E,(D['id'],D.get('name')or'',D.get(_F)or'',D.get(_G)or''))
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
							if isinstance(E,dict)and E.get(_A):I=E[_A];J={A:B for(A,B)in E.items()if A!=_A};A.execute(_H,(I,json.dumps(J,ensure_ascii=_B)))
						A.commit()
				except Exception:pass
		H=A.execute(_I,[CONFIG_KEY_COMMAND_WHITELIST]).fetchone()
		if not H or not H[_D]:
			B=DATA_DIR/'command_whitelist.json'
			if B.is_file():
				try:
					C=json.loads(B.read_text(encoding=G))
					if isinstance(C,dict):A.execute(_J,(CONFIG_KEY_COMMAND_WHITELIST,json.dumps(C,ensure_ascii=_B)));A.commit()
				except Exception:pass
	finally:A.close()