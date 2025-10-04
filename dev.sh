#!/usr/bin/env bash
# 简单的本地开发启动脚本：启动 uvicorn 并自动打开浏览器。
set -euo pipefail

cd "$(dirname "$0")"

HOST=${HOST:-127.0.0.1}
PORT=${PORT:-8000}

UVICORN_BIN=${UVICORN_BIN:-}
if [[ -z "$UVICORN_BIN" ]]; then
  if [[ -x .venv/bin/uvicorn ]]; then
    UVICORN_BIN=".venv/bin/uvicorn"
  elif command -v uvicorn >/dev/null 2>&1; then
    UVICORN_BIN="$(command -v uvicorn)"
  else
    echo "找不到 uvicorn，请先激活虚拟环境或执行 pip install -r requirements.txt" >&2
    exit 1
  fi
fi

"$UVICORN_BIN" api.index:app --host "$HOST" --port "$PORT" --reload &
UVICORN_PID=$!

cleanup() {
  kill "$UVICORN_PID" >/dev/null 2>&1 || true
}
trap cleanup INT TERM

sleep 2
if command -v open >/dev/null 2>&1; then
  open "http://$HOST:$PORT"
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://$HOST:$PORT"
else
  python -m webbrowser "http://$HOST:$PORT" >/dev/null 2>&1 || true
fi

wait "$UVICORN_PID"
