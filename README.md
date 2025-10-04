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

# 快速启动（自动打开浏览器）
./dev.sh

# 或手动运行服务
# uvicorn api.index:app --reload --port 8000
```
打开浏览器访问 `http://localhost:8000` 即可看到中文界面（静态文件）。

## Vercel 部署
1. 将仓库推送到 GitHub 并在 Vercel 创建项目。
2. 在 Vercel 项目设置里新增以下环境变量：
   - `DATABASE_URL`：指向外部数据库（例如 Neon/Supabase Postgres）。
   - `YOUTUBE_API_KEY`：你的 YouTube API key（部署时可使用 Vercel Secret）。
   - 可选 `INSTAGRAM_SESSIONID`：你的 Instagram `sessionid`（用于提升 Reels 抓取成功率）。
3. Vercel 会自动识别：
   - 根目录下的 `index.html` / `script.js` / `styles.css` 作为静态前端。
   - `api/index.py` 作为 Python Serverless Function（已在 `vercel.json` 指定 runtime）。
4. 部署完成后访问对应的域名即可使用。

> 注意：Serverless 环境是无状态的，无法使用本地 SQLite 文件持久化数据。请务必配置 `DATABASE_URL` 指向托管数据库。

### Vercel Secret 示例
使用 Vercel CLI 可以将敏感值写入 Secret，然后映射到环境变量：

```bash
# 1. 登录 Vercel（如未登录）
vercel login

# 2. 添加 Secret（输入时粘贴你的 Key，例如 YOUTUBE_API_KEY 内部值）
vercel secrets add viewfetcher-youtube-key

# 3. 关联到环境变量（Production & Preview 环境）
vercel env add YOUTUBE_API_KEY production @viewfetcher-youtube-key
vercel env add YOUTUBE_API_KEY preview @viewfetcher-youtube-key

# 若需 Instagram sessionid
vercel secrets add viewfetcher-instagram-session
vercel env add INSTAGRAM_SESSIONID production @viewfetcher-instagram-session
vercel env add INSTAGRAM_SESSIONID preview @viewfetcher-instagram-session
```

也可以直接在 Vercel Dashboard → Settings → Environment Variables 中粘贴上述值。API Key 仅用于服务器端调用，不会暴露在前端。

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
