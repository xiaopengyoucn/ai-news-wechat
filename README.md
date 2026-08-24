# AI 新闻微信聚合

每天两次自动抓取约 20 个 AI 信源，用 DeepSeek 翻译+评分+摘要，通过 PushPlus 推送到个人微信。

## 部署（5 分钟）

### 方式 A：一键脚本（推荐）

```bash
# git-bash / WSL / macOS / Linux
./deploy.sh

# Windows PowerShell
.\deploy.ps1
```

脚本会：检查 gh CLI → 提示输入仓库名/公开性 → 创建仓库 → push → 交互配置 Secrets → 启用 Actions → 可选试跑。

### 方式 B：手动部署

1. Fork 本仓库到你自己的 GitHub。
2. 注册 [pushplus.plus](https://pushplus.plus) 微信扫码绑定，拿到 `PUSHPLUS_TOKEN`。
3. 注册 [DeepSeek](https://platform.deepseek.com) 拿到 `DEEPSEEK_API_KEY`。
4. 在 fork 的仓库 **Settings → Secrets and variables → Actions** 新建：
   - `DEEPSEEK_API_KEY`
   - `PUSHPLUS_TOKEN`
   - （可选）`PUSHPLUS_TOPIC`、`LLM_MODEL`（默认 deepseek-chat）
5. 进入 **Actions** 页面启用 workflows。
6. （可选）配 [EasyCron](https://easycron.com) 等外部触发器以减少延迟。

## 配置项

| 环境变量 | 必填 | 默认 |
|---|---|---|
| `DEEPSEEK_API_KEY` | ✅ | - |
| `PUSHPLUS_TOKEN` | ✅ | - |
| `PUSHPLUS_TOPIC` | ❌ | - |
| `LLM_MODEL` | ❌ | `deepseek-chat` |

## 信源失效

如果某个 RSS URL 失效，编辑 `sources.py`，把对应行的 `url` 字段替换为新 RSS，提交后 Actions 自动生效。
失效的源会打印到 Actions 日志中：`source <name> fetch failed: ...`。

## 当前信源（19 个）

**通用 AI（12）**：OpenAI News, Google DeepMind, BAIR Blog, arXiv cs.AI/CL/LG, Hacker News, TechCrunch AI, VentureBeat AI, The Verge AI, The Decoder, 量子位

**AI for Science + 化学化工/聚合物/复合材料（7）**：
- Nature Chemistry（化学顶刊）
- Nature Materials（材料科学）
- Nature Computational Science（AI+科学）
- arXiv cond-mat.soft（聚合物/软物质）
- arXiv cond-mat.mtrl-sci（材料科学）
- arXiv q-bio.BM（生物分子）
- Phys.org Chemistry（化学新闻，含高分子/复合材料）

**重要性 boost**：含 polymer/composite/catalyst/electrolyte/合金/复合材料 等关键词的条目自动 +2 分（封顶 10）。

## 推送时间精准化（EasyCron）

GitHub Actions cron 可能延后 30+ 分钟。推荐用 EasyCron 外部触发精准在 08:00 / 20:00 Asia/Shanghai：

```bash
bash setup-easycron.sh
```

脚本会输出 EasyCron 配置指南 + 测试一次 GitHub workflow_dispatch。

## 本地开发

### 一键脚本

```bash
# git-bash / WSL / macOS / Linux
./setup.sh

# Windows PowerShell
.\setup.ps1
```

### 手动

```bash
python -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

手动试跑一次：
```bash
DEEPSEEK_API_KEY=... PUSHPLUS_TOKEN=... python main.py --mode morning
```

## 许可

MIT
