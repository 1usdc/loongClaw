'\n记忆与分身 API：GET/POST /api/personas、PUT/DELETE /api/personas/{id}；\nGET/POST /api/memories、PUT/DELETE /api/memories/{id}。\n'
_I='/api/memories/{memory_id}'
_H='content'
_G='/api/memories'
_F='/api/personas/{persona_id}'
_E='/api/personas'
_D='image/jpeg'
_C='frontend'
_B='avatar'
_A=None
from pathlib import Path
from fastapi import APIRouter,HTTPException
from fastapi.responses import FileResponse
from tools.memory_tools import add_memory as add_memory_tool,add_persona,delete_memory as delete_memory_tool,delete_persona,get_avatar_options,load_memories,load_personas,update_memory as update_memory_tool,update_persona
router=APIRouter(tags=['memory'])
BASE_DIR=Path(__file__).resolve().parents[1]
_frontend_candidate=BASE_DIR.parent/_C
_frontend_dir=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_C
UI_AVATAR_DIR=_frontend_dir/'assets'/_B
_AVATAR_MEDIA_TYPES={'.svg':'image/svg+xml','.png':'image/png','.jpg':_D,'.jpeg':_D,'.webp':'image/webp'}
@router.get('/api/avatars')
def get_avatars():'返回内置头像文件名列表（对应 GET /api/avatar/{filename}）。';return{'avatars':get_avatar_options()}
def _serve_avatar_file(filename:str):
	'仅允许 get_avatar_options() 中的文件名，从 UI_AVATAR_DIR 返回文件。';A=filename;C=get_avatar_options()
	if not A or A not in C:raise HTTPException(status_code=404,detail='头像不存在')
	B=UI_AVATAR_DIR/A
	if not B.is_file():raise HTTPException(status_code=404,detail='头像文件不存在')
	D=_AVATAR_MEDIA_TYPES.get(B.suffix.lower(),'application/octet-stream');return FileResponse(B,media_type=D)
@router.get('/api/avatar/{filename}')
def get_avatar(filename:str):'返回内置头像图片文件。';return _serve_avatar_file(filename)
@router.get('/static/assets/avatar/{filename}')
def get_avatar_legacy(filename:str):'兼容旧路径 /static/assets/avatar/{filename}（如缓存或旧构建仍请求该路径时）。';return _serve_avatar_file(filename)
@router.get(_E)
def get_personas():'返回分身列表（第一个为默认分身）。';return{'personas':load_personas()}
@router.post(_E)
def post_persona(body:dict):'新增分身。body: { "name": "xxx", "avatar": "01.svg" 可选 }。';A=(body.get('name')or'').strip()or'未命名';B=body.get(_B);C=add_persona(A,avatar=B);return C
@router.put(_F)
def put_persona(persona_id:str,body:dict):
	'更新分身名称与头像。body: { "name": "xxx", "avatar": "01.svg" 可选 }。';B=(body.get('name')or'').strip()or'未命名';C=body.get(_B);A=update_persona(persona_id,B,avatar=C)
	if A is _A:raise HTTPException(status_code=404,detail='分身不存在或不可修改')
	return A
@router.delete(_F)
def delete_persona_route(persona_id:str):
	'删除分身。';A=delete_persona(persona_id)
	if not A:raise HTTPException(status_code=404,detail='分身不存在或不可删除')
	return{'ok':True}
@router.get(_G)
def get_memories(persona_id:str|_A=_A):'返回记忆列表；可选 persona_id 筛选。';return{'memories':load_memories(persona_id)}
@router.post(_G)
def post_memory(body:dict):'新增记忆。body: { "persona_id": "xxx", "content": "xxx" }。';A=(body.get('persona_id')or'').strip()or'default';B=(body.get(_H)or'').strip();C=add_memory_tool(A,B);return C
@router.put(_I)
def put_memory(memory_id:str,body:dict):
	'更新记忆内容。body: { "content": "xxx" }。';B=(body.get(_H)or'').strip();A=update_memory_tool(memory_id,B)
	if A is _A:raise HTTPException(status_code=404,detail='记忆不存在')
	return A
@router.delete(_I)
def delete_memory_route(memory_id:str):
	'删除记忆。';A=delete_memory_tool(memory_id)
	if not A:raise HTTPException(status_code=404,detail='记忆不存在')
	return{'ok':True}