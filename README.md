# my_stock_tols

A 股股票 + 基金每日智能推荐系统，基于多因子量化筛选 + DeepSeek AI 分析。

## 参考项目
1. akshare: https://github.com/akfamily/akshare
2. meihuayishu : https://github.com/muyen/meihua-yishu

## 功能

- **每日预测推荐**：10 只股票（3 激进 + 5 稳健 + 2 适中）+ **约 14 只基金**（6 ETF + 4 股票型 + 4 混合型；东财 ETF 不可用时自动多推开放式基金补足）
- **新闻与政策**：结合市场要闻（央视/东财）与政策/宏观要闻（财经早餐），注入 AI 分析并**按日入库**，便于后续分析
- **政策与新闻驱动板块**：结合**十四五/十五五规划**与当日要闻，由 AI 生成「今日关注板块」（如新能源、半导体、医药等），写入报告并注入股票/基金分析
- **新闻因子**：个股近期新闻（东方财富）+ 市场要闻（央视财经），利好/利空关键词打分，并注入 AI 分析
- **周易卦象**：按日期得当日卦象（六十四卦），写入报告并供 DeepSeek 参考（传统文化角度，不构成投资依据）
- **DeepSeek AI 分析**：结合技术面、新闻面与卦象对每只推荐标的进行研判
- **每日自动复盘**：对比推荐与实际表现，计算命中率
- **历史追踪**：SQLite 存储所有推荐和复盘记录
- **定时调度**：支持自动化每日运行
- **个人持仓**：记录买入价、数量、目标价、止损、计划卖出日，并与当日推荐对照
- **回测**：基于历史推荐记录，用 [AKQuant](https://github.com/akfamily/akquant) 做「推荐日收盘买、次日收盘卖」的回测，复盘时可评估策略表现
- **Web 版**：FastAPI + Vue3，无登录（开源版 AI Key 自行在设置中配置），底部导航：每日预测、持仓、历史、设置；设置页仅配置 AI（支持 DeepSeek / OpenAI / Claude，可用 LiteLLM 统一代理）

## 快速开始

```bash
# 1. 安装依赖
pip install -r requirements.txt

# 2. 配置 AI API Key（分析功能必填，支持 DeepSeek/OpenAI/Claude，可用 LiteLLM）
cp .env.example .env
# 编辑 .env，填入 AI_API_KEY（或沿用 DEEPSEEK_API_KEY），可选 AI_BASE_URL、AI_MODEL

# 3. 执行推荐
python main.py predict

# 4. 执行复盘（收盘后）
python main.py review

# 5. 查看历史命中率
python main.py history

# 6. 查看某日要闻与政策（供后续分析）
python main.py context 2026-03-12

# 7. 个人持仓与卖出计划
python main.py position list
python main.py position add 600000 2026-03-01 10.5 100 --name 浦发银行 --target-price 12 --stop-loss 9.5 --plan-sell-date 2026-04-01
python main.py position plan --id 1 --target-price 13 --plan-sell-date 2026-05-01

# 8. 基于历史推荐做回测（需先 pip install akquant）
python main.py backtest --start 2026-02-01 --end 2026-03-12 --cash 100000

# 9. 启动定时调度（后台运行）
python main.py schedule
```

### Web 版（可选）

```bash
# 后端（在项目根目录）
pip install -r requirements.txt   # 含 fastapi / sqlmodel 等
python -m uvicorn backend.main:app --reload --host 0.0.0.0 --port 8000

# 前端（另开终端）
cd frontend
npm install
npm run dev
# 浏览器打开 http://localhost:5173，无需登录；在「设置」中配置 AI API Key 后即可使用分析功能
```

- **每日预测**：今日推荐（依赖 CLI 已生成的当日推荐）
- **持仓**：增删改持仓与卖出计划
- **历史**：按日期筛选，进入某日可看预测+复盘详情，并可运行回测
- **设置**：仅配置 AI（API Key / Base URL / 模型），支持 DeepSeek、OpenAI、Claude；使用 LiteLLM 时选「自定义」并填代理地址

### 服务器上用 PM2 管理后端

后端支持用 [PM2](https://pm2.keymetrics.io/) 常驻运行，项目根目录已提供 `ecosystem.config.cjs`。

**首次在服务器上：**

```bash
# 1. 进入项目根目录
cd /path/to/my_stock_tols

# 2. 确保依赖与 .env 已配置（pip install -r requirements.txt、复制 .env.example 为 .env 并填写 AI_API_KEY 等）

# 3. 启动后端（PM2 会以后台进程运行，进程名为 stock-api）
pm2 start ecosystem.config.cjs
```

**常用 PM2 命令：**

```bash
pm2 list              # 查看进程
pm2 logs stock-api    # 看日志
pm2 restart stock-api # 重启
pm2 stop stock-api    # 停止
pm2 delete stock-api  # 从 PM2 中移除
```

若使用虚拟环境，请编辑 `ecosystem.config.cjs`，把 `interpreter` 注释去掉并改为 venv 的 Python 路径（如 `.venv/bin/python`）。

## 项目结构

```
├── main.py                 # CLI 入口
├── scheduler.py            # 定时调度（每日 08:30 预测 / 16:30 复盘）
├── config/
│   └── settings.py         # 配置中心
├── core/
│   ├── data_fetcher.py     # AKShare 数据获取（含重试与降级）
│   ├── news_fetcher.py     # 个股/市场新闻获取与情感打分（东方财富+央视）
│   ├── zhouyi.py           # 周易卦象（按日期得当日卦，供报告与 AI）
│   ├── stock_screener.py   # 股票多因子筛选（技术+行情+新闻）
│   ├── fund_screener.py    # 基金筛选（ETF + 开放式）
│   ├── ai_analyzer.py      # DeepSeek AI 分析
│   ├── reviewer.py         # 复盘引擎
│   └── report_generator.py # Markdown 报告生成
├── strategies/
│   └── indicators.py       # 技术指标（MA/MACD/RSI/KDJ/BOLL 等）
├── storage/
│   └── db.py               # SQLite 存储（推荐、复盘、每日汇总、**每日要闻与政策**）
├── backend/                 # Web 后端（FastAPI + SQLModel）
│   ├── main.py
│   ├── database.py
│   ├── models.py            # User
│   ├── auth.py
│   ├── deps.py
│   └── routers/             # auth, positions, predictions, backtest, config
├── frontend/                # Web 前端（Vite + Vue 3）
├── output/                  # 生成的报告
└── data/                    # SQLite 数据库
```

## 筛选策略

### 股票（多因子打分）

| 因子 | 权重 | 说明 |
|------|------|------|
| 技术面 | 50% | MA 排列、MACD/KDJ 金叉、RSI、布林带 |
| 行情面 | 35% | 量比、换手率、涨跌幅、市盈率、60 日趋势 |
| **新闻面** | **15%** | 东方财富个股近期新闻，利好/利空关键词 + 时效性打分；AI 分析时注入市场要闻（央视财经） |

### 风格分配

| 风格 | 占比 | 选股偏好 |
|------|------|---------|
| 激进型 | 30% (3只) | 高动量、高量比、突破形态 |
| 稳健型 | 50% (5只) | 均线多头、低PE、大市值 |
| 适中型 | 20% (2只) | 综合评分最高 |

## 技术栈

- **数据源**: AKShare（东方财富/新浪行情；日 K 东财失败时用腾讯备选；市场要闻央视失败时用东财资讯备选）
- **慢速拉取**: 可选 `SLOW_FETCH=true`（默认）拉长请求间隔，减轻限流、提高拉全率；`FETCH_INTERVAL_*` 可调间隔秒数
- **AI 分析**: 统一 OpenAI 兼容接口，支持 DeepSeek / OpenAI / Claude；可配 Base URL + 模型，使用 LiteLLM 时填代理地址即可
- **存储**: SQLite
- **调度**: APScheduler
- **日志**: Loguru


### Capacitor 打包安卓（在 frontend 目录操作）

用 WebView 包一层 Vue 打包结果，可调部分原生能力（相机、文件、推送等）。**以下命令均在 `frontend` 目录执行。**

流程概览：
1. 打包前端：`npm run build`
2. 安装并初始化（若尚未做）：`npm i @capacitor/core @capacitor/cli @capacitor/android`，`npx cap init "股票推荐" "com.mystock.tools" --web-dir=dist`
3. 添加 Android 平台：`npx cap add android`
4. 每次改前端后同步：`npm run build` 再 `npx cap sync`（或 `npm run cap:sync`）
5. 用 Android Studio 打开 `frontend/android` 目录，编译、签名、生成 APK/AAB

优点：和 Vue/Vite 集成简单，官方文档全，生态成熟。

注意：需安装 Android Studio 和 SDK。

**前端请求的后端地址**：前端和后端在同一台服务器时，网页版用相对路径即可，无需改配置。**只有打包安卓 App 时**需要把接口地址写成服务器 URL：
- **变量名**：`VITE_API_BASE`
- **打包安卓时**在 frontend 目录执行：`VITE_API_BASE=https://你的域名 npm run build`，再 `npx cap sync`（不要结尾斜杠）。这样打出来的 App 会请求你这台服务器上的接口。
