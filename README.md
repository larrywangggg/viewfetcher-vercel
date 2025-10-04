# ViewFetcher · Vercel 版本

一个用于在 Web 端批量抓取 YouTube / Instagram / TikTok 视频数据的小型应用。后端使用 FastAPI 暴露 REST 接口，前端为静态页面，通过调用 `/api` 接口完成上传、抓取和展示。

## 功能概览
- 上传 `.csv` 或 `.xlsx` 文件（至少包含 `platform`, `url`）。
- 支持可选的 YouTube API Key（仅 YouTube 数据需要）。
- Instagram / TikTok 通过 `yt-dlp` 抓取公开数据。
- 计算互动率 `engagement_rate = (likes + comments) / views * 100%`。
- 数据存入数据库（默认 SQLite，推荐配置云数据库）。
- 提供历史查询和 CSV 导出接口。

## 本地开发
```bash
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn api.index:app --reload --port 8000
```
打开浏览器访问 `http://localhost:8000` 即可看到中文界面（静态文件）。

## Vercel 部署
1. 将仓库推送到 GitHub 并在 Vercel 创建项目。
2. 在 Vercel 项目设置里新增以下环境变量：
   - `DATABASE_URL`：指向外部数据库（例如 Neon/Supabase Postgres）。
   - 可选：`YOUTUBE_API_KEY` 如果希望默认提供。
3. Vercel 会自动识别：
   - 根目录下的 `index.html` / `script.js` / `styles.css` 作为静态前端。
   - `api/index.py` 作为 Python Serverless Function（已在 `vercel.json` 指定 runtime）。
4. 部署完成后访问对应的域名即可使用。

> 注意：Serverless 环境是无状态的，无法使用本地 SQLite 文件持久化数据。请务必配置 `DATABASE_URL` 指向托管数据库。

## 常用 API
- `POST /api/fetch`：上传文件并执行抓取。
- `GET /api/results?limit=200`：查询最新结果。
- `GET /api/export`：导出 CSV。

## 目录结构
```
.
├── api/index.py            # FastAPI 入口
├── index.html              # 中文前端页面
├── script.js / styles.css  # 前端脚本与样式
├── viewfetcher/            # Python 业务模块
│   ├── db.py               # SQLAlchemy 封装
│   ├── fetchers.py         # 平台抓取逻辑
│   └── processor.py        # 文件解析 + 批量处理
├── requirements.txt
├── runtime.txt
└── vercel.json
```

## 进一步扩展
- 将静态页面替换为 React/Next.js 以获得更丰富的交互。
- 为 `POST /api/fetch` 增加任务排队或异步执行，避免大批量请求超时。
- 根据团队需求增加鉴权、用户管理等模块。
