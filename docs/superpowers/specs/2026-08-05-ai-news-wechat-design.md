# AI 新闻微信聚合 — 设计文档

日期：2026-08-05
作者：opencode

## 概述

构建一个自动化 pipeline，每天两次从约 20 个 AI 专业信源（官方实验室博客、学术、社区、中文媒体）抓取内容，用 LLM（DeepSeek）翻译为中文、做重要性评分与一句话摘要，按阈值筛选后通过 PushPlus 推送到个人微信。零运维：fork → 填 2 个 Secrets → 启用 Actions 即可。

## 目标与非目标

### 目标
- 中文输出：标题 + 2句摘要 + 重要性 0-10
- 重要性 >= 6 的条目入选，每日报每次推送最多 15 条
- 早报覆盖过去 12 小时，晚报覆盖过去 12 小时，与 cron 节奏对齐
- 单一入口 `main.py --mode morning|evening`，其余模块化

### 非目标（v1）
- 不构建 Web UI
- 不支持多个微信用户（推送目标是单接收方）
- 不做长期知识库 / 全文搜索
- 不持久化文章正文，只保留 URL 用于去重

## 架构

```
GitHub Actions cron (00:00 / 12:00 UTC ≈ 08:00 / 20:00 Asia/Shanghai)
        |
   main.py 入口
        |
   sources.py（信源清单）
        |
   fetcher.py（RSS 抓取 → 去重 → state 持久化）
        |
   processor.py（DeepSeek 批量翻译+评分+摘要 → 筛选）
        |
   publisher.py（PushPlus 推微信）
```

### 模块边界

| 文件 | 职责 | 依赖 |
|---|---|---|
| `main.py` | 串接，解析 CLI 参数，调用各模块 | 其它全部 |
| `sources.py` | 静态信源 list（name, url, region, kind） | 无 |
| `fetcher.py` | `fetch_all(sources, since_hours) -> list[Item]` | feedparser, requests |
| `processor.py` | `enrich(items) -> list[Processed]` 调 LLM 并筛选 | openai 兼容 SDK |
| `publisher.py` | `publish_pushplus(title, md)` | requests |
| `state.py` | 读写 `state.json`（已推送 URL） | 无 |

每个模块独立可测，公共接口签名：
- `Item(url, title, source, snippet, published)`
- `Processed(url, title_zh, summary_zh, importance, category)`

## 信源（约 20 个）

| 类别 | 名称 | URL |
|---|---|---|
| 官方实验室 | OpenAI Blog | openai.com/blog/rss.xml |
| 官方实验室 | Anthropic News | anthropic.com/news/rss.xml |
| 官方实验室 | Google DeepMind Blog | deepmind.google/blog/rss.xml |
| 官方实验室 | Meta AI Blog | ai.meta.com/blog/rss/ |
| 官方实验室 | Hugging Face Blog | huggingface.co/blog/feed.xml |
| 学术 | arXiv cs.AI | export.arxiv.org/rss/cs.AI |
| 学术 | arXiv cs.CL | export.arxiv.org/rss/cs.CL |
| 学术 | arXiv cs.LG | export.arxiv.org/rss/cs.LG |
| 学术 | Papers with Code | paperswithcode.com/area/ai |
| 社区 | Hacker News (top) | hnrss.org/newest |
| 社区 | Reddit r/MachineLearning | reddit.com/r/MachineLearning/.rss |
| 社区 | Reddit r/LocalLLaMA | reddit.com/r/LocalLLaMA/.rss |
| 媒体 | TechCrunch AI | techcrunch.com/category/artificial-intelligence/feed/ |
| 媒体 | VentureBeat AI | venturebeat.com/category/ai/feed/ |
| 媒体 | The Verge AI | theverge.com/ai-artificial-intelligence/rss/index.xml |
| 媒体 | The Decoder | thedecoder.ai/feed |
| 通讯 | Import AI | importai.substack.com/feed |
| 通讯 | The Batch | deeplearning.ai/the-batch/feed |
| 中文 | 机器之心 | jiqizhixin.com/rss |
| 中文 | 量子位 | qbitai.com/feed |
| 中文 | 36氪AI | 36kr.com/feed |

注：实际 URL 以信源官方当前 RSS 为准，sources.py 提供但 README 标注若不可访问应替换。

## LLM 策略

- Provider：DeepSeek（`https://api.deepseek.com/v1`，OpenAI 兼容）
- 模型：`deepseek-chat`
- 批大小：一次 prompt 处理 20 条文章（成本可控，JSON 输出稳定）
- 输入字段：title, url, snippet
- 输出字段：title_zh, summary_zh, importance(0-10), category
- Prompt 模板见 `processor.py` 顶部常量
- 阈值：`importance >= 6`
- 排序：importance desc，取前 15 条
- Fallback：LLM 失败时退化为纯抓取（英文标题 + URL），无中文摘要

## 数据流

```
1. fetch_all() → list[Item]  约 50-150 条（取决于当日源活跃度）
2. state.json 去重（保留 7 天） → list[Item']
3. processor.enrich() 调 LLM → list[Processed]  20 条左右
4. 筛选 importance>=6 + 排序 + 截 top15 → final list
5. publisher 拼 markdown → PushPlus POST
6. 把 final list 的 url 写回 state.json
```

## 部署

- GitHub Actions，workflow `daily.yml`：
  - cron 两次：`0 0 * * *` 和 `0 12 * * *`（UTC）
  - 配套 Python 3.11 setup，pip install -r requirements.txt
  - 跑 `python main.py --mode morning|evening`
- 必需 Secrets：
  - `DEEPSEEK_API_KEY`
  - `PUSHPLUS_TOKEN`
- 可选 Secrets（v2 扩展用）：
  - `LLM_MODEL` 覆盖默认模型
  - `PUSHPLUS_TOPIC` 推给分组（多人多 channel）
- state.json 用 `actions/upload-artifact` + 下次 `download-artifact` 实现跨 job 持久化，或简化为 actions/cache

## 错误处理

- 单 RSS 源失败：捕获异常 + log warning，继续其它源
- LLM 单条失败：标记 importance=0 跳过，不中断批次
- LLM 整批失败：重试 1 次，仍失败则推送英文版（仅标题+URL）
- PushPlus HTTP 失败：重试 2 次（指数回退），最终失败写到 `output/failed_<timestamp>.md`
- 全 pipeline 异常：exit code 1，让 Actions 显示红色 + 日志

## 测试策略（pytest）

不依赖真实网络：

- `tests/test_fetcher.py`：mock `feedparser` 返回 5 条 fixture，验证去重 + 时间窗口过滤
- `tests/test_processor.py`：mock DeepSeek client，验证 prompt 构造 + 阈值筛选 + 输出解析
- `tests/test_publisher.py`：mock `requests.post`，验证 markdown 拼接 + URL 正确调用

CI：`.github/workflows/ci.yml` push 时跑 `pytest -q`

## 风险与权衡

| 风险 | 缓解 |
|---|---|
| RSS 源失效或 URL 变动 | README 列明如何替换，错误日志标出 failure |
| PushPlus 免费版限频 200条/天 | 远低于阈值 |
| DeepSeek API 抖动 | retry + fallback 英文版 |
| GitHub Actions cron 延迟 | 用户接受延迟，可选配 EasyCron 触发 workflow_dispatch |
| LLM JSON 解析失败 | 重试 + 退化路径 |

## 后续扩展（v2）

- 多接收方：通过 PUSHPLUS_TOPIC 推给分组
- 自定义信源：sources.py 改一行即可
- Web 静态归档：GitHub Pages 累积历史日报
- Slack/邮件 fallback
- 重要性动态阈值：基于当周活跃度自适应
