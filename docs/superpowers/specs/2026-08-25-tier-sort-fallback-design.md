# AI 新闻推送优先级 + 兜底方案

日期：2026-08-25
作者：opencode

## 概述

解决两个问题：
1. **触发器冗余**：当前只有 cron-job.org 触发，cron-job.org 挂了就没推送。需要 GitHub Actions schedule 作为兜底，但要避免重复推送。
2. **新闻排序**：用户希望化学/材料相关内容和中国大模型厂家新闻排在前面。

## 设计

### 1. 兜底触发（state-based 去重）

**daily.yml**：保留 GitHub Actions schedule 作为备份
```yaml
on:
  schedule:
    # 兜底：cron-job.org 挂了时启用
    # 时间设稍晚于 cron-job.org (8:05 / 20:05)，避免同时触发
    - cron: '5 0,12 * * *'   # Beijing 8:05 / 20:05 (cron-job.org 后 5 分钟)
  workflow_dispatch:
    inputs:
      mode:
        description: 'morning or evening'
        required: true
        default: 'morning'

concurrency:
  group: ai-news-pipeline
  cancel-in-progress: false
```

**state.py 扩展**：
- 持久化 `last_pushes: list[dict]`，每个 dict 包含 `{mode, ts}`
- 提供 `was_pushed_today(mode) -> bool`：判断今天该 mode 是否已推送过
- 提供 `record_push(mode)`：追加新推送记录

**main.py 入口**：
```python
def run(mode: str) -> int:
    state = StateStore("state.json")
    
    # 兜底去重：如果今天该 mode 已推送过（cron-job.org 成功了），跳过
    if state.was_pushed_today(mode):
        log.info(f"{mode} push already done today, skipping (fallback no-op)")
        return 0
    
    # ... 现有逻辑 ...
    
    # 推送成功后记录
    if state.add([it.url for it in processed]) and code == 200:
        state.record_push(mode)
        state.save()
```

**数据流**：
```
cron-job.org 8:00 → workflow_dispatch → run("morning")
  → state.was_pushed_today("morning")? → False
  → fetch + process + push
  → state.record_push("morning") → state.json 标记
  
GitHub Actions 8:05 → schedule → run("morning")  
  → state.was_pushed_today("morning")? → True (8:00 那次记录了)
  → log "skipping", return 0（不推送）

如果 cron-job.org 挂了，GitHub Actions 8:05 触发
  → state.was_pushed_today("morning")? → False
  → 正常推送 ✓
```

### 2. 排序分级（三层 tier）

**processor.py 新增 tier 评分**：

```python
_COMPANY_BOOST_KEYWORDS = (
    # 化学/材料 AI 公司
    "晶泰", "XtalPi", "晶泰科技",
    "深势", "深势科技", "DP Technology",
    "Citrine", "Citrine Informatics",
    "Kebotix", "Atinary",
    # 国内大模型厂家
    "智谱", "Zhipu", "GLM",
    "百川", "百川智能", "Baichuan",
    "Kimi", "月之暗面", "Moonshot",
    "通义", "通义千问", "Qwen",
    "文心一言", "百度", "Baidu", "ERNIE",
    "豆包", "字节跳动", "ByteDance", "Doubao",
    "混元", "腾讯", "Tencent", "Hunyuan",
    "盘古", "华为", "Huawei", "Pangu",
    "DeepSeek", "深度求索",
    "阶跃", "StepFun",
    "MiniMax", "稀宇科技",
    "上海 AI Lab", "上海人工智能实验室", "Shanghai AI Lab",
)

_CHINESE_SOURCE_NAMES = ("量子位", "机器之心", "36氪", "新智元")
```

**分级逻辑**：
- Tier 1 (最高优先)：标题/摘要含化学关键词 OR 含公司关键词
- Tier 2 (次优先)：来自中文信源（量子位等）
- Tier 3 (默认)：其余

**排序**：
```python
def _tier(it) -> int:
    text = (it.title_zh + it.summary_zh).lower()
    if any(kw.lower() in text for kw in _SCI_BOOST_KEYWORDS) or any(kw in text for kw in _COMPANY_BOOST_KEYWORDS):
        return 1
    if it.source in _CHINESE_SOURCE_NAMES:
        return 2
    return 3

# Sort by tier asc, then importance desc
processed.sort(key=lambda p: (_tier(p), -p.importance))
```

**输出顺序**：
1. Tier 1：化学/材料 + 晶泰/深势/智谱等公司新闻
2. Tier 2：国内 AI 厂家新闻（量子位等）
3. Tier 3：其他（OpenAI/Anthropic/TechCrunch 等）

### 3. 不做的事（YAGNI）

- 不改阈值（仍 ≥6 / top 15）
- 不改推送格式
- 不加新 RSS 源
- 不改 cron-job.org 配置

## 风险与权衡

| 风险 | 缓解 |
|---|---|
| state.json 在 GitHub Actions 跑前没更新（cron-job 失败） | GitHub Actions 的 cron 也会自己跑 → 兜底成功 |
| 极端情况两个 cron 同时跑 | concurrency 块让第二个等待第一个完成 |
| 排序调整让用户错过通用 AI 新闻 | Tier 1 通常 ≥ 8 分；top 15 仍能容下各类 |
