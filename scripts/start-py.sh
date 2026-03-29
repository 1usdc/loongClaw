#!/bin/bash
# 启动后端：安装 podman/uv、创建环境、安装依赖、构建前端、启动 main.py
# 从项目根执行：just start 或 just start-d
# 也可直接调用：bash scripts/start-py.sh [-d|--daemon]

set -e
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# 自动识别 just 命令是在项目根还是 build 目录执行：
# 1) 项目根执行 just：PWD 含 backend-py/
# 2) build 目录执行 just：PWD 含 main.py + pyproject.toml
# 3) 其他场景回退到脚本所在路径推断
if [ -d "$PWD/backend-py" ] && [ -d "$PWD/scripts" ]; then
  ROOT="$PWD"
  BACKEND="$ROOT/backend-py"
elif [ -f "$PWD/main.py" ] && [ -f "$PWD/pyproject.toml" ]; then
  ROOT="$PWD"
  BACKEND="$ROOT"
elif [ -f "$SCRIPT_DIR/../main.py" ] && [ -f "$SCRIPT_DIR/../pyproject.toml" ]; then
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  BACKEND="$ROOT"
else
  ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
  BACKEND="$ROOT/backend-py"
fi

DAEMON=0
for _arg in "$@"; do
  case "$_arg" in
    -d|--daemon) DAEMON=1 ;;
  esac
done

if [ ! -d "$BACKEND" ]; then
  echo "错误: backend 目录不存在: $BACKEND"
  echo "请确认从正确的项目根执行（项目根应包含 backend-py/ 与 scripts/）"
  exit 1
fi

if [ -f "$BACKEND/main.py" ]; then
  cd "$BACKEND"
elif [ -f "$BACKEND/build/main.py" ]; then
  cd "$BACKEND/build"
else
  echo "未找到 main.py（backend-py/ 与 backend-py/build/ 均无），请先执行: just pack"
  exit 1
fi

# ---------- podman ----------
if ! command -v podman >/dev/null 2>&1; then
  echo "未检测到 podman，开始自动安装..."
  if command -v brew >/dev/null 2>&1; then
    brew install podman
  elif command -v apt-get >/dev/null 2>&1; then
    apt-get update -qq && apt-get install -y -qq podman || true
  elif command -v dnf >/dev/null 2>&1; then
    dnf install -y podman 2>/dev/null || true
  elif command -v yum >/dev/null 2>&1; then
    yum install -y podman 2>/dev/null || true
  elif command -v apk >/dev/null 2>&1; then
    apk add --no-cache podman 2>/dev/null || true
  fi
fi

if ! command -v podman >/dev/null 2>&1; then
  echo "未找到 podman，请先手动安装 podman。"
  exit 1
fi

if [ "$(uname -s)" = "Darwin" ]; then
  if ! podman machine inspect >/dev/null 2>&1; then
    echo "初始化 podman machine..."
    podman machine init
  fi
  echo "启动 podman machine..."
  if ! podman machine start >/dev/null 2>&1; then
    if ! podman machine list 2>/dev/null | grep -q "Currently running"; then
      echo "podman machine 启动失败，请手动执行: podman machine start"
      exit 1
    fi
  fi
fi

# ---------- 异步预拉取常用镜像 ----------
_img_python="${ANOTHERCLAW_PODMAN_IMAGE_PYTHON:-docker.io/library/python:3.12}"
_img_node="${ANOTHERCLAW_PODMAN_IMAGE_NODE:-docker.io/library/node:22}"
_img_shell="${ANOTHERCLAW_PODMAN_IMAGE_SHELL:-docker.io/library/bash:5.2}"
_img_go="${ANOTHERCLAW_PODMAN_IMAGE_GO:-docker.io/library/golang:1.22}"
_img_java="${ANOTHERCLAW_PODMAN_IMAGE_JAVA:-docker.io/library/openjdk:21-jdk}"
_img_rust="${ANOTHERCLAW_PODMAN_IMAGE_RUST:-docker.io/library/rust:latest}"
_img_php="${ANOTHERCLAW_PODMAN_IMAGE_PHP:-docker.io/library/php:8.3-cli}"
_img_default="${ANOTHERCLAW_PODMAN_IMAGE:-${_img_shell}}"
for _img in "$_img_python" "$_img_node" "$_img_shell" "$_img_go" "$_img_java" "$_img_rust" "$_img_php" "$_img_default"; do
  [ -z "$_img" ] && continue
  if ! podman image exists "$_img" >/dev/null 2>&1; then
    echo "后台预拉取镜像: $_img"
    (podman pull "$_img" >/dev/null 2>&1 || true) &
  fi
done

# ---------- uv ----------
if ! command -v uv >/dev/null 2>&1; then
  echo "未检测到 uv，开始自动安装..."
  if ! command -v curl >/dev/null 2>&1; then
    echo "未找到 curl，尝试先安装 curl..."
    if command -v apt-get >/dev/null 2>&1; then
      apt-get update -qq && apt-get install -y -qq curl || true
    elif command -v apk >/dev/null 2>&1; then
      apk add --no-cache curl 2>/dev/null || true
    elif command -v dnf >/dev/null 2>&1; then
      dnf install -y curl 2>/dev/null || true
    elif command -v yum >/dev/null 2>&1; then
      yum install -y curl 2>/dev/null || true
    fi
  fi
  if ! command -v curl >/dev/null 2>&1; then
    echo "无法安装 curl，请先在系统中安装 curl 或预装 uv。"
    exit 1
  fi
  curl -LsSf https://astral.sh/uv/install.sh | sh
  export PATH="$HOME/.local/bin:$PATH"
  if ! command -v uv >/dev/null 2>&1; then
    echo "uv 安装后仍不可用，请检查 PATH（建议加入 ~/.local/bin）"
    exit 1
  fi
fi

# ---------- venv / 依赖 ----------
if [ ! -x ".venv/bin/python" ]; then
  echo "创建虚拟环境 .venv..."
  uv venv .venv
fi

VENV_PY=".venv/bin/python"

if [ -f "pyproject.toml" ]; then
  echo "安装依赖 (uv sync)..."
  uv sync
else
  echo "未找到 pyproject.toml，请在项目根或执行 just pack 后的 build 目录下运行。"
  exit 1
fi

if [ -z "${OPENAI_API_KEY}" ] && [ -f ".env" ]; then
  _val=$(grep -E '^\s*OPENAI_API_KEY\s*=' .env 2>/dev/null | head -1 | sed 's/^[^=]*=//' | sed "s/^[\"']//;s/[\"']$//")
  [ -n "${_val}" ] && export OPENAI_API_KEY="${_val}"
  unset _val
fi

# ---------- 前端构建 ----------
if [ -f "frontend/package.json" ]; then FRONTEND_DPATH="frontend"; else FRONTEND_DPATH="../frontend"; fi
if [ ! -d "$FRONTEND_DPATH/dist" ] && [ -f "$FRONTEND_DPATH/package.json" ]; then
  echo "前端尚未构建，开始 pnpm install && pnpm build..."
  if command -v pnpm >/dev/null 2>&1; then
    (cd "$FRONTEND_DPATH" && pnpm install --frozen-lockfile 2>/dev/null || pnpm install && pnpm build)
  elif command -v npm >/dev/null 2>&1; then
    (cd "$FRONTEND_DPATH" && npm i -g pnpm 2>/dev/null && pnpm install && pnpm build)
  else
    echo "警告: 未找到 pnpm/npm，跳过前端构建。请手动执行 cd frontend && pnpm build"
  fi
fi

# ---------- 启动 ----------
echo "启动 main.py..."
if [ "$DAEMON" -eq 1 ]; then
  nohup "$VENV_PY" main.py >> anotherclaw.log 2>&1 &
  echo "已后台启动，PID: $!"
  echo "日志: $(pwd)/anotherclaw.log"
  exit 0
fi
exec "$VENV_PY" main.py
