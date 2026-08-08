# GitHub AI 周榜（03-github-rank-weekly）

## 目标

每周从 GitHub 获取 AI 相关开源库的最新排名，生成自包含 HTML 周报并部署到 GitHub Pages，持续更新并探讨趋势。

## 已确认决策（grill-me 会话，Round 1 用户拍板）

1. **交付物**：HTML 文档（自包含单文件），用 ui-ux-pro-max 技能做设计。
2. **AI 范围**：混合方案 = 精选种子清单 + topic 搜索发现新面孔。
3. **排名口径**：复合 = 周增量为主，总星标、日均增幅为参考列。
4. **更新机制**：GitHub Actions 定时生成周报并开 PR，由用户以 lile 身份审核合并。
5. **语言**：中文为主，仓库名/作者/英文简介保留原文。

## 已采纳推荐（Round 2，按推荐执行）

- **Q1 数据源**：官方 GitHub REST API（Search API + repos 端点），周快照差值计算增量；token 用 `GITHUB_TOKEN`（Actions 自带，只读够用）。OSS Insight 留作后续增强。
- **Q2 榜单规模**：主榜 Top 30（周增量），总星 ≥ 1000，排除 fork / 归档 / 模板仓库；4–6 个分类子榜各 Top 10。
- **Q3 文件组织**：`index.html`（最新一周）+ `archive/YYYY-MM-DD.html` 历史存档；部署到 GitHub Pages。
- **Q4 报告内容**：本周摘要 → 主榜 → 新面孔榜 → 分类子榜 → 近 4 周趋势图 → 数据与方法说明 → "探讨"点评区；点评为自动生成草稿 + 人工在 PR 审核时润色。
- **Q5 种子清单**：`data/seed_repos.json`，首批约 120 个仓库、9 类（LLM 框架、Agent、RAG、向量数据库、推理/部署、训练/微调、评测/安全、MLOps、多模态），每季度人工 review。
- **Q6 设计**（ui-ux-pro-max 生成）：暗色 OLED 主题为默认 + 亮色切换；slate 深色底（#0F172A）+ 绿色强调（#22C55E）；Fira Code / Fira Sans；Top 30 横向条形图 + 近 4 周趋势折线图；SVG 图标（不用 emoji）；WCAG AA/AAA；响应式 375/768/1024/1440。

## 关键事实（grilling 会话中查证）

- GitHub 没有官方 trending API，`github.com/trending` 只能抓 HTML；Search API 不能按"周新增 star"排序，周增量只能靠快照差值。
- stargazer 接口有 4 万条（400 页）分页上限，超大仓库拿不到完整 star 历史。
- OSS Insight 提供公开 beta API（趋势仓库、集合排名），可作交叉校验/日增幅真实值来源。

## 目录结构约定

- `data/seed_repos.json`：精选种子清单
- `data/snapshots/YYYY-MM-DD.json`：每周快照（保留全部历史）
- `index.html`：最新一周报告
- `archive/YYYY-MM-DD.html`：历史报告
- `src/`：Python 源码；`tests/`：验收测试

## 验收测试原则

- 所有测试可量化、可检查（pytest）。
- 每完成一个可运行阶段，跑通测试后以 lile 身份 git 提交，提交信息简要描述修改点。
