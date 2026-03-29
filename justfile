# 打包产物目录用：仅含 build 内可用命令（pack 时复制为 build/justfile） (Minimal recipes for packaged build/; copied to build/justfile by pack)
set shell := ["bash", "-cu"]

# 列出可用 recipe (List available recipes)
default:
    @just --list

# 固定版本号 (Print pinned version)
version:
    @echo "1.0.0"

# 启动后端（前台）(Start backend, foreground)
start:
    bash scripts/start-py.sh --py

# start-d 别名 (Alias for start-d)
start-D: start-d

# 启动后端（后台）(Start backend, daemon)
start-d:
    bash scripts/start-py.sh --py --daemon
