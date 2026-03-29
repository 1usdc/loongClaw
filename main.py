'\nAnotherMe 入口：加载工具与 Agent，启动前端对话 API（无终端交互，仅在前端对话页交互）。\n'
_D='/assets'
_C='frontend'
_B='assets'
_A=True
import os,sys
from contextlib import asynccontextmanager
from pathlib import Path
from dotenv import load_dotenv
BASE_DIR=Path(__file__).resolve().parent
load_dotenv(dotenv_path=BASE_DIR/'.env',override=_A)
import uvicorn
from fastapi import FastAPI
from fastapi.responses import FileResponse,Response
from fastapi.staticfiles import StaticFiles
from utils.db import migrate_from_json_if_needed
from routes import chat,sessions,memory,pages,proxy,skills,tasks,tts,ui_bridge
@asynccontextmanager
async def lifespan(app:FastAPI):'启动时：确保 data、skills 目录存在；确保 SQLite 表存在并迁移旧 JSON；启动定时任务调度；供路由使用应用根目录。';app.state.base_dir=BASE_DIR;(BASE_DIR/'data').mkdir(parents=_A,exist_ok=_A);(BASE_DIR/'skills').mkdir(parents=_A,exist_ok=_A);migrate_from_json_if_needed();tasks.start_scheduler();yield;tasks.stop_scheduler()
app=FastAPI(title='AnotherMe Chat API',version='0.1.0',lifespan=lifespan)
_frontend_candidate=BASE_DIR.parent/_C
UI_DIR=_frontend_candidate if _frontend_candidate.is_dir()else BASE_DIR/_C
SPA_DIST=UI_DIR/'dist'
if SPA_DIST.is_dir()and(SPA_DIST/_B).is_dir():app.mount(_D,StaticFiles(directory=str(SPA_DIST/_B)),name='spa-assets')
elif(UI_DIR/_B).is_dir():app.mount(_D,StaticFiles(directory=str(UI_DIR/_B)),name='raw-assets')
@app.get('/favicon.ico',include_in_schema=False)
def favicon():
	'返回 favicon，消除浏览器默认请求的 404。';A=UI_DIR/_B/'icons'/'logo.svg'
	if A.is_file():return FileResponse(A,media_type='image/svg+xml')
	return Response(status_code=204)
app.include_router(pages.router)
app.include_router(chat.router)
app.include_router(sessions.router)
app.include_router(skills.router)
app.include_router(tts.router)
app.include_router(memory.router)
app.include_router(tasks.router)
app.include_router(ui_bridge.router)
app.include_router(proxy.router)
if __name__=='__main__':
	print('AnotherMe 已启动');port=int(os.getenv('PORT','8765'));print(f"请打开浏览器访问: http://localhost:{port}/\n")
	try:uvicorn.run('main:app',host='0.0.0.0',port=port,reload=False)
	except OSError as e:
		if e.errno==48:print(f"端口 {port} 已被占用。可先查看占用进程并结束：");print(f"  lsof -i :{port}");print(f"  kill -9 <PID>   # 将 <PID> 替换为上面命令输出的进程号")
		raise