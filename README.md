# GitHub AI 周榜

每周从 GitHub 获取 AI 相关开源库的最新排名，自动生成自包含 HTML 周报（暗色/亮色双主题），合并后部署到 GitHub Pages。

## 功能

- **混合选库**：107 个精选种子仓库（9 大分类）+ GitHub Search API 按 topic 自动发现新面孔。
- **复合排名口径**：主榜按「本周新增 star」（快照差值）排序，展示总星标与日均估算；另设新面孔榜与分类子榜。
- **离线演示**：无需 token 也能跑通全链路（`sample` 子命令）。
- **可回溯**：每周快照与历史报告全部提交进仓库。
- **自动更新**：GitHub Actions 每周一（北京时间 08:30）生成快照与周报并开 PR，人工审核点评后合并，Pages 自动发布。

## 快速开始

```bash
# 1. 环境（uv：https://docs.astral.sh/uv/）
uv venv .venv
uv pip install --python .venv/bin/python -e ".[dev]"

# 2. 离线演示（无需网络/token）
.venv/bin/python -m github_ai_weekly sample
# 打开 demo/index.html 查看

# 3. 真实抓取（需要 GitHub token）
export GITHUB_TOKEN=ghp_xxx
.venv/bin/python -m github_ai_weekly fetch
.venv/bin/python -m github_ai_weekly report
```

命令一览：

| 命令 | 说明 |
| --- | --- |
| `fetch [--date YYYY-MM-DD]` | 抓取本周快照到 `data/snapshots/` |
| `report [--notes 点评...]` | 由最近快照生成 `index.html` + `archive/` 存档 |
| `sample` | 生成三周离线演示数据与周报到 `demo/`（不入库） |

## 部署到 GitHub Pages

1. 把仓库推到 GitHub。
2. 打开仓库 **Settings → Pages**，Source 选择 **GitHub Actions**。
3. 之后每次合并到 `main`，`.github/workflows/pages.yml` 会自动发布。
4. 每周一 `.github/workflows/weekly.yml` 会生成快照与周报并开 PR；审核（可润色「本周探讨」点评）后合并即发布。

## 目录结构

```text
data/seed_repos.json            精选种子清单（9 分类，107 仓库）
data/snapshots/YYYY-MM-DD.json  每周快照（保留全部历史）
index.html                      最新一周报告
archive/YYYY-MM-DD.html         历史报告
src/github_ai_weekly/           源码（抓取/排名/报告/CLI）
tests/                          pytest 验收测试
.github/workflows/              每周 PR 与 Pages 部署
```

## 开发文档

面向后续更新迭代的完整手册（架构、数据流、模块、配置、扩展指南、踩坑记录）见 [docs/DEVELOPMENT.md](docs/DEVELOPMENT.md)。

## 榜单口径

- 总星标 ≥ 1000，排除 fork、已归档与模板仓库。
- 周增量 = 本期快照 − 上期快照；日均估算 = 周增量 ÷ 7。
- 分类：种子清单预设；发现仓库按自身 topic 推断，未命中显示「未分类」。
- 已知局限：GitHub 无官方 trending API，Search API 不能按周增量排序，因此采用快照差值；超大仓库 stargazer 历史有 4 万条上限，日均列为估算值。

## 自定义

- 种子清单：编辑 `data/seed_repos.json`（`owner`/`repo`/`category`），建议每季度 review。
- 榜单参数：`src/github_ai_weekly/config.py` 中的 `MIN_STARS`、`TOP_N`、`CATEGORY_TOP_N`。
- topic 发现规则：`config.py` 的 `TOPIC_QUERIES` 与 `TOPIC_TO_CATEGORY`。
- 附加点评：`report --notes "……"`，或直接在 PR 中修改生成的 HTML。

## 测试

```bash
.venv/bin/python -m pytest
```

当前 27 项测试覆盖：API 客户端、快照校验、排名计算、HTML 确定性渲染与转义、CLI 演示链路。
