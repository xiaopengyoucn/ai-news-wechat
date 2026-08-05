# AI 新闻微信聚合

每天两次自动抓取约 20 个 AI 信源，用 DeepSeek 翻译+评分+摘要，通过 PushPlus 推送到个人微信。

## 部署（5 分钟）

1. Fork 本仓库到你自己的 GitHub。
2. 注册 [pushplus.plus](https://pushplus.plus) 微信扫码绑定，拿到 `PUSHPLUS_TOKEN`。
3. 注册 [DeepSeek](https://platform.deepseek.com) 拿到 `DEEPSEEK_API_KEY`。
4. 在 fork 的仓库 **Settings → Secrets and variables → Actions** 新建：
   - `DEEPSEEK_API_KEY`
   - `PUSHPLUS_TOKEN`
   - （可选）`PUSHPLUS_TOPIC`、`LLM_MODEL`（默认 deepseek-chat）
5. 进入 **Actions** 页面启用 workflows。
6. （可选）配 [EasyCron](https://easycron.com) 等外部触发器以减少延迟。
7. （可选）本地试跑：`DEEPSEEK_API_KEY=... PUSHPLUS_TOKEN=... python main.py --mode morning`

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

## 本地开发

```bash
python -m venv .venv
source .venv/bin/activate  # 或 .venv\Scripts\activate
pip install -r requirements.txt
pytest -q
```

## 许可

MIT
