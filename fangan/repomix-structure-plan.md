# Hippocampus 代码长期记忆系统 — 结构化方案

> **实现状态图例**：✅ 已完成 | 🚧 部分完成 | ❌ 未实现 | 📋 规划中

## 1. 系统定位 ✅

基于 Repomix 构建代码库的"宏观地图"（长期记忆），为 AI 提供项目全局认知。
后续结合 repomap 的动态上下文（工作记忆），实现从全局到局部的完整感知链。

### 核心目标
- 生成稳定的结构快照，便于 AI/人类快速理解仓库结构
- 支持分层按需注入，适应不同规模项目（200 ~ 30,000 文件）
- 输出结构演化图，展示目录规模与变化趋势
- 生成可注入模型的轻量结构信息（控制在 25k token 以内）

## 2. 数据层级体系 ✅

### 2.1 六级缩放模型 ✅

```
Level 0: 项目全景 — 项目整体 desc（结合 L1 摘要 + README 等）
Level 1: 模块级   — 逻辑分组摘要（LLM 基于 L2 聚类生成，不依赖目录结构）
Level 2: 文件级   — 每文件 desc + 语义 tags
Level 3: 签名级   — 每文件的 class/function 定义列表 + 每个签名一句话 desc
Level 4: 骨架级   — 代码骨架（compress，签名+关键行）
Level 5: 源码级   — 完整源码（按需读取，不预生成）
```

生成顺序为自底向上：L3(tree-sitter) → L2(LLM逐文件) → L1(LLM聚类) → L0(LLM汇总)。

Level 1-3 存储在统一索引文件（hippocampus-index.json）中，支持按 token 预算逐层展开。
Level 4-5 体积过大，独立存储，按需拉取。

### 2.2 各级 token 成本（以 200 文件项目为例）✅

| 级别 | 内容 | 典型体积 | 生成方式 |
|---|---|---|---|
| L0 项目全景 | 项目整体 desc（1 段） | ~0.2k token | LLM 汇总 L1 + README |
| L1 逻辑模块 | 8-15 个模块 × desc | ~1k token | LLM 基于 L2 聚类 |
| L2 文件 desc+tags | 200 文件 × desc+tags | ~5k token | LLM 逐文件 |
| L3 函数签名+desc | 1300 函数 × (名+desc) | ~17k token | tree-sitter 提名 + LLM 生成 desc |
| **L0-L3 合计** | **统一索引全量** | **~23k token** | |
| L4 代码骨架 | compress 输出 | ~308k token | repomix |
| L5 完整源码 | full 输出 | ~437k token | repomix |

## 3. 产物清单 🚧

每次运行生成以下产物：

### 3.1 结构类产物（repomix 直接输出）🚧

1) **结构快照**（repomix-structure.json）❌
   - repomix JSON 元数据模式，含 directoryStructure，不含文件内容
   - 命令：`repomix --style json --no-files --include-full-directory-structure`
   - **状态**：未实现，当前使用 tree.json 替代

2) **代码骨架**（repomix-compress.json）❌
   - repomix compress 模式，tree-sitter 提取的代码结构
   - 命令：`repomix --compress --style json`
   - **状态**：未实现，当前直接使用 tree-sitter 提取签名

### 3.2 派生产物（外部工具生成）🚧

3) **结构树数据**（tree.json）✅
   - 由目录结构 + 文件统计生成，代码行数作为节点规模，带稳定 ID
   - **实现**：`hippo tree` 命令

4) **结构差异**（tree-diff.json）✅
   - 对比基线快照（main 或上次快照），标记新增/删除/移动/增长/缩减
   - **实现**：`hippo tree-diff` 命令

5) **交互式可视化**（hippocampus-viz.html）❌
   - 基于 ECharts 的单文件交互式可视化，支持目录/模块双视图切换
   - 侧边栏联动 L0-L3 desc 钻取，颜色映射可切换（模块/行数/core_score/语言）
   - 叠加层：变更标记（tree-diff）+ 问题徽章（insights）
   - 底部趋势条：架构健康度历史曲线
   - **状态**：未实现，详见 Section 13

6) **结构提示词**（structure-prompt.md）✅
   - <=10k 字符，不含代码块
   - 汇总结构概览、行数 Top 目录、近期变化摘要
   - **实现**：`hippo structure-prompt` 命令

7) **动态裁剪内容**（repomix-compress-trimmed.json）✅
   - 基于 compress 按 token 预算裁剪
   - 按目录层级逐层展开，预算用完就停
   - **实现**：`hippo trim` 命令

8) **统一索引**（hippocampus-index.json）✅
   - 树形结构，dirs 和 files 分层存储
   - dirs: 每目录 desc + stats + tags（L1）
   - files: 每文件 desc + tags（L2）+ 函数签名列表（L3）
   - LLM 生成 desc/tags，tree-sitter 提取签名，合并为一个文件
   - 支持按 token 预算逐层展开查询
   - 典型体积：200 文件全量 ~10k token
   - **实现**：`hippo index` 命令

## 4. 分层注入策略 ✅

### 4.1 问题：全量注入不可扩展 ✅

统一索引（L1-L3）的全量 token 随项目规模线性增长：

| 项目规模 | 文件数 | L1 目录 | L2 文件desc | L3 签名 | L1-L3 全量 |
|---|---|---|---|---|---|
| 小型 | 200 | ~1.2k | ~5k | ~4k | **~10k** |
| 中型 | 800 | ~3k | ~16k | ~15k | **~34k** |
| 大型 | 3,000 | ~6k | ~60k | ~50k | **~116k** |
| 超大型 | 30,000 | ~30k | ~600k | ~500k | **~1.1M** |

小型项目可全量注入。中型开始需要裁剪。

### 4.2 核心目录分类（Core Directory Classification）✅

注入第二层时需要决定哪些目录展开文件列表。这不是硬编码，而是基于评分的动态分类。

#### 评分公式

```
core_score(dir) =
    0.30 × (dir.lines / total_lines)          # 代码占比
  + 0.25 × (dir.files / total_files)          # 文件占比
  + 0.20 × role_bonus(dir)                    # 角色加成
  + 0.15 × (recent_changes / total_changes)   # 近期活跃度
  + 0.10 × (inbound_refs / max_inbound_refs)  # 被引用频率
```

#### role_bonus 定义（基于 tag vocab 的 role 维度）

| 目录 role tag | bonus | 理由 |
|---|---|---|
| `entrypoint` | 1.0 | 入口文件，理解系统行为的起点 |
| `lib` | 0.8 | 核心业务逻辑 |
| `config` | 0.4 | 影响全局行为但代码量少 |
| `test` | 0.2 | 重要但非核心认知 |
| `docs`, `asset`, `ci` | 0.0 | 辅助性目录 |

#### 分类阈值

```
core_score >= 0.3  →  core（始终展开到文件级）
core_score >= 0.1  →  secondary（预算充足时展开）
core_score <  0.1  →  peripheral（仅保留目录摘要）
```

#### 任务相关性覆盖（Task-Dependent Override）

当 Architect 分解任务指定了 `target_module` 时，该模块及其父目录强制标记为 core，不受评分限制：

```python
if task.target_module:
    for dir in ancestors(task.target_module) + [task.target_module]:
        dir.core = True  # 强制覆盖
```

这确保"修复邮件 bug"时 `lib/mail/` 即使评分低也会被展开。

### 4.3 Token 预算驱动的逐层展开 ✅

核心算法：从 L1 开始逐层展开，每层展开前检查剩余预算，不够就停。
目录按 `core_score` 降序排列，确保最重要的目录优先获得预算。

#### 展开算法伪代码

```python
def build_context(index, budget, task=None):
    """根据 token 预算从索引中构建注入上下文"""
    output = []
    remaining = budget

    # ── Phase 1: L1 目录摘要（始终注入） ──
    dirs = sorted(index.root.all_dirs(), key=lambda d: d.core_score, reverse=True)
    for d in dirs:
        line = f"{d.path}/（{d.stats.files} 文件）: {d.desc}"
        cost = estimate_tokens(line)
        if remaining < cost:
            break
        output.append(line)
        remaining -= cost
    # Phase 1 结束后 AI 拥有全局目录认知
```

```python
    # ── Phase 2: L2 核心目录的文件列表 ──
    core_dirs = [d for d in dirs if d.core or (task and d.path in task.target_modules)]
    core_dirs.sort(key=lambda d: d.core_score, reverse=True)

    for d in core_dirs:
        files = sorted(d.files, key=lambda f: f.lines, reverse=True)
        for f in files:
            line = f"{f.path}: {f.desc}"
            cost = estimate_tokens(line)
            if remaining < cost:
                break  # 当前目录预算不足，跳到下一个目录
            output.append(line)
            remaining -= cost
    # Phase 2 结束后 AI 能定位到核心模块的具体文件
```

```python
    # ── Phase 3: L3 签名（按需拉取，不在默认注入中） ──
    # 由 AI 通过 query API 主动请求
    # 此处仅在 budget 充裕且有 task 指定时自动注入
    if task and task.target_files and remaining > 500:
        for fpath in task.target_files:
            fnode = index.get_file(fpath)
            if not fnode:
                continue
            sig_lines = [f"  → {s.name} ({s.kind})" for s in fnode.signatures]
            block = f"{fnode.path}: {fnode.desc}\n" + "\n".join(sig_lines)
            cost = estimate_tokens(block)
            if remaining < cost:
                break
            output.append(block)
            remaining -= cost

    return "\n".join(output), budget - remaining  # 返回上下文文本和实际消耗
```

#### 展开输出示例

**Phase 1 输出（~1k token）：**
```
lib/（45 文件）: 核心库，含 provider 通信、终端管理、国际化、邮件、记忆模块
bin/（32 文件）: CLI 入口脚本集合，每个 provider 有 ask/pend/ping 三件套
test/（25 文件）: 单元测试
docs/（12 文件）: 项目文档
```

**Phase 2 输出（~3k token，仅 core 目录）：**
```
lib/terminal.py: 终端检测与适配，支持 tmux/wezterm/原生终端
lib/providers.py: provider 注册与发现，管理可用的 AI 后端
lib/i18n.py: 国际化支持模块，管理中英文消息翻译
bin/ask: 统一异步提问 CLI
bin/pend: 查看 AI 最新回复
```

**Phase 3 输出（按需，~2k token/次）：**
```
lib/mail/daemon.py: 邮件守护进程，定时检查并发送通知
  → MailDaemon (class)
  → start (method)
  → stop (method)
  → dispatch (method)
```

### 4.4 注入预算汇总 ✅

| 项目规模 | 第一层(目录摘要) | 第二层(重点文件) | 默认注入 | 第三层(按需/次) |
|---|---|---|---|---|
| 200 文件 | ~1k | ~3k | **~4k** | ~2k |
| 800 文件 | ~2.4k | ~6k | **~8k** | ~2-3k |
| 3,000 文件 | ~3k | ~10k | **~13k** | ~2-3k |
| 30,000 文件 | ~10k | ~15k | **~25k** | ~3-5k |

始终保持默认注入在 25k token 以内，不管项目多大。

### 4.5 查询与展开 API（Context Query API）✅

AI agent 通过以下接口按需获取不同层级的索引数据。可实现为 MCP tool、CLI 命令或 Python API。

#### 双格式策略：存储 JSON，注入 Markdown

```
存储层（磁盘）：hippocampus-index.json
  → 工具读写、程序化查询、增量更新
  → JSON 结构化，支持精确过滤

注入层（AI 上下文）：API 返回的 content 字段
  → 渲染为 Markdown，直接塞入 prompt
  → 省 token（比 JSON 少 ~30% 语法开销）
  → AI 理解更自然（接近训练数据分布）
```

| 层级 | 注入格式 | 理由 |
|---|---|---|
| L0 项目全景 | Markdown | 理解型，`#` 标题即可 |
| L1 模块摘要 | Markdown | 理解型，`##` + 一句话 |
| L2 文件列表 | Markdown | 理解型，`path: desc` 逐行 |
| L3 签名列表 | Markdown | 缩进列表 `→ name (kind)` |
| 查询结果 | JSON | 数据型，AI 可能需要程序化处理 |

#### 4.5.1 `hippo_overview` — 获取全局概览 ✅

获取 Phase 1 + Phase 2 的默认注入内容。每次新会话或清理上下文后首先调用。

```
请求：
  hippo_overview(budget=8000)

响应（元数据 JSON + 注入内容 Markdown）：
  {
    "consumed_tokens": 4200,
    "layers_included": ["L0", "L1", "L2_core"],
    "content": "<见下方 Markdown>"
  }
```

**content 字段渲染为 Markdown：**

```markdown
# claude_codex
多 AI provider 协作的 CLI 工具集，通过 tmux 多窗格管理同时与 Claude、Gemini、Codex 等 AI 后端交互。
架构：CLI 工具集 + 守护进程 | 200 文件 | 8 模块 | Python

## provider-comm（18 文件）
AI provider 通信层，管理请求/响应
→ lib/askd/daemon.py, lib/providers.py, bin/ask

## cli-entry（32 文件）
命令行入口脚本集合，用户交互的起点
→ bin/ask, bin/pend, bin/ping

## terminal-mgmt（12 文件）
终端检测、会话管理与适配
→ lib/terminal.py, lib/tmux.py

---
lib/terminal.py: 终端检测与适配，支持 tmux/wezterm/原生终端
lib/providers.py: provider 注册与发现，管理可用的 AI 后端
lib/i18n.py: 国际化支持模块，管理中英文消息翻译
bin/ask: 统一异步提问 CLI
bin/pend: 查看 AI 最新回复
```

#### 4.5.2 `hippo_expand` — 展开指定目录/文件 ✅

AI 定位到目标后，请求更细粒度的信息。支持目录级展开（L2）和文件级展开（L3）。

```
请求：
  hippo_expand(path="lib/mail/", level="L3", budget=2000)

响应（元数据 JSON + 注入内容 Markdown）：
  {
    "path": "lib/mail/",
    "consumed_tokens": 1800,
    "level": "L3",
    "content": "<见下方 Markdown>"
  }
```

**content 字段渲染为 Markdown：**

```markdown
### mail-notify / lib/mail/

lib/mail/daemon.py: 邮件守护进程，定时检查并发送通知
  → MailDaemon (class)
  → start (method)
  → stop (method)
  → dispatch (method)

lib/mail/adapters/gmail.py: Gmail SMTP 适配器
  → GmailAdapter (class)
  → send (method)
  → connect (method)
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `path` | string | 目录或文件的相对路径 |
| `level` | `L2` / `L3` | 展开到文件级还是签名级 |
| `budget` | int | 本次展开的 token 上限 |

#### 4.5.3 `hippo_search` — 按标签/关键词搜索 ✅

AI 不确定目标在哪个目录时，通过语义标签或关键词定位。

```
请求：
  hippo_search(tags=["daemon", "mail"], pattern="notify", limit=10)

响应：
  {
    "matches": [
      {"path": "lib/mail/daemon.py", "desc": "邮件守护进程...", "score": 0.95},
      {"path": "lib/mail/adapters/slack.py", "desc": "Slack webhook 适配器...", "score": 0.72},
      {"path": "bin/notify", "desc": "通知发送 CLI...", "score": 0.68}
    ],
    "consumed_tokens": 180
  }
```

| 参数 | 类型 | 说明 |
|---|---|---|
| `tags` | string[] | 从 tag vocab 中选择，取交集 |
| `pattern` | string | 文件名/desc 的模糊匹配 |
| `limit` | int | 最多返回条数，默认 10 |

#### 4.5.4 `hippo_diff` — 查询结构变更 ✅

获取两个版本之间的结构差异，用于理解近期代码演化。

```
请求：
  hippo_diff(baseline="main", scope="lib/mail/")

响应：
  {
    "added": ["lib/mail/adapters/slack.py"],
    "modified": ["lib/mail/daemon.py (+32 lines)"],
    "deleted": [],
    "summary": "lib/mail/ 新增 Slack 适配器，daemon.py 增加了 dispatch 路由"
  }
```

## 5. 多 AI 分层协作方案 ❌

### 5.1 动机 ❌

单个 AI 的上下文窗口有限。注入宏观信息会挤占微观操作空间，注入微观信息会失去全局视野。这是认知带宽的物理限制，不是 token 优化能解决的。

解决方案：不同颗粒度的认知由不同 AI 角色承担。

### 5.2 三层 AI 角色

| 角色 | 上下文 | 职责 | 决策类型 |
|---|---|---|---|
| Architect | 目录摘要 + 模块关系（~3k） | 理解全局，分解任务 | "放在哪个模块" |
| Navigator | 模块文件 desc + 签名（~5k） | 定位文件，规划方案 | "改哪些文件" |
| Coder | 目标文件代码 + repomap（~20k） | 写代码，跑测试 | "怎么写代码" |

### 5.3 可伸缩：按需激活

不是所有任务都需要三层：

| 任务复杂度 | 激活角色 | 示例 |
|---|---|---|
| 目标明确 | Coder | "修复 i18n.py 第 42 行的 bug" |
| 需要定位 | Navigator + Coder | "给邮件模块加 Slack 支持" |
| 需要全局分析 | 三层全部 | "重构整个通信层统一接口" |
| 跨系统 | 4-5 层 | "把单体应用拆成微服务" |

AI 角色绑定缩放范围：Architect(Level 0-2)、Navigator(Level 2-4)、Coder(Level 4-5)。

### 5.4 每层上下文消耗对比

| 项目规模 | Architect | Navigator | Coder | 三层合计 | 单AI全量 |
|---|---|---|---|---|---|
| 200 文件 | ~1k | ~2k | ~6k | **~9k** | ~8.6k |
| 800 文件 | ~2.4k | ~2k | ~6k | **~10k** | ~34k |
| 3,000 文件 | ~6k | ~2k | ~6k | **~14k** | ~135k |

小项目多 AI 无优势。中大型项目多 AI 每层轻松，单 AI 已接近窗口上限。

### 5.5 按角色注入规范（Per-Role Injection）

每个角色启动时自动注入对应层级的索引数据，通过 `hippo_overview` / `hippo_expand` API 获取。

#### Architect 注入

```
触发：新任务到达
调用：hippo_overview(budget=5000)
注入内容：
  - L1 全量目录摘要（始终）
  - L2 core 目录的文件列表（预算允许时）
  - 不注入 L3 签名
目的：理解全局模块划分，决定任务分配到哪个模块
```

#### Navigator 注入

```
触发：收到 Architect 的 task-breakdown，含 target_module
调用：hippo_expand(path=target_module, level="L3", budget=5000)
注入内容：
  - 目标模块的 L2 文件列表（始终）
  - 目标模块的 L3 签名（预算允许时）
  - 不注入其他模块的详情
目的：定位具体文件，规划修改方案
```

#### Coder 注入

```
触发：收到 Navigator 的 modification-plan，含 target_files
调用：hippo_expand(path=target_file, level="L3", budget=2000)
注入内容：
  - 目标文件的 L3 签名（始终）
  - 相关文件的签名（通过 repomap 动态补充）
  - 不注入全局目录信息
目的：知道具体 API 接口，直接写代码
```

#### 注入时序图

```
用户提交任务
  │
  ├─→ Architect: hippo_overview(5000)  ← L1 + L2_core
  │     │
  │     └─→ 输出 task-breakdown.json (target_module: "lib/mail/")
  │
  ├─→ Navigator: hippo_expand("lib/mail/", "L3", 5000)  ← L2 + L3
  │     │
  │     └─→ 输出 modification-plan.json (files: ["daemon.py", "slack.py"])
  │
  └─→ Coder: hippo_expand("lib/mail/daemon.py", "L3", 2000)  ← L3
        │
        └─→ 读取完整源码 + repomap 动态上下文 → 写代码
```

### 5.6 共享工作区

AI 之间不直接对话，通过共享文件系统协作：

```
.hippocampus/
  context/                           ← 预生成的上下文数据（只读）
    hippocampus-index.json           ← 统一索引（L1+L2+L3 合并）
    tag-vocab.json                   ← Tag 词表
    tree.json                        ← 结构树（可视化用）
    tree-diff.json                   ← 结构差异

  tasks/                             ← 任务流转（各角色读写）
    current-task.json                ← 用户写入的原始需求
    task-breakdown.json              ← Architect 输出的任务分解
    modification-plan.json           ← Navigator 输出的修改计划

  feedback/                          ← 回传通道（下级 → 上级）
    coder-report.json                ← Coder 的执行结果/问题反馈
    navigator-escalation.json        ← Navigator 的上报请求

  state/                             ← 状态追踪
    active-roles.json                ← 当前激活的角色
    decision-log.json                ← 跨角色的关键决策记录
```

### 5.7 层间通信协议

层间传递结构化 JSON，而非自然语言。

**Architect → Navigator：**
```json
{
  "task": "邮件通知支持 Slack webhook",
  "target_module": "lib/mail/",
  "context": "用户希望在现有 Gmail/Outlook 之外新增 Slack 通道",
  "constraints": "不改现有适配器接口"
}
```

**Navigator → Coder：**
```json
{
  "task": "新增 Slack 适配器",
  "files_to_modify": ["lib/mail/adapters/slack.py (new)", "lib/mail/daemon.py"],
  "plan": "新增 SlackAdapter 实现 send() 接口，在 daemon.py 的 dispatch() 中注册",
  "interface_contract": "class SlackAdapter: def send(self, message: Message) -> bool"
}
```

**Coder → Navigator（回传）：**
```json
{
  "subtask_id": 1,
  "status": "done | blocked | failed",
  "changes": ["lib/mail/adapters/slack.py (new, 85 lines)"],
  "tests": "pass | fail | skipped",
  "notes": "可选，执行中发现的额外信息",
  "need": "可选，blocked/failed 时说明需要什么"
}
```

**Navigator → Architect（上报）：**
```json
{
  "type": "scope_expansion",
  "message": "Slack 适配器需要修改 lib/providers.py，超出 lib/mail/ 范围",
  "suggestion": "需要将 lib/providers.py 也纳入修改范围"
}
```

### 5.8 上下文清理策略

清理由工作边界事件触发，而非定时或按 token 用量。
清理本身就是同步机制：清理后重新读取共享工作区，拿到其他 agent 的最新输出。

| 角色 | 清理触发条件 | 重新注入成本 |
|---|---|---|
| Architect | 每个新任务 | ~3k token（目录摘要） |
| Navigator | 切换目标模块 | ~5k token（模块详情） |
| Coder | 每个子任务完成 | ~1k plan + 按需读文件 |

### 5.9 迭代机制（Coder ↔ Navigator 循环）

Navigator 是迭代循环的驱动者，持有修改计划全貌，逐个子任务分配给 Coder。

**迭代循环：**
```
┌→ Navigator 取第一个 pending 子任务 → 发给 Coder
│   Coder 执行 → 写入 coder-report.json
│   Navigator 读取 report:
│     done      → 标记完成，取下一个 ──→ 继续循环
│     done+notes → 评估是否影响后续 ──→ 继续或修订
│     blocked   → 补充信息重发 ────────→ 重试当前子任务
│     failed    → 修订计划 ────────────→ 重试或回退
│     超出范围  → 上报 Architect ──────→ 等待重新规划
└─────────────────────────────────────┘
全部 done → 任务完成
```

**子任务状态机：**
```
pending → in_progress → done
                      → blocked → (Navigator 补充) → in_progress
                      → failed  → (Navigator 修订) → in_progress
                      → escalated → (Architect 重新规划)
```

**Navigator 每次收到回传后的三个动作：**
1. 更新计划状态 — 标记子任务完成/失败，记录实际变更
2. 评估后续影响 — Coder 的 notes 可能暴露新信息，影响后续子任务
3. 判断是否上报 — 超出模块范围的问题交给 Architect

### 5.10 实现路径

**路径 1：ccb 多 provider 分工**
```
Claude（Architect）→ /ask codex → Codex（Navigator）→ /ask gemini → Gemini（Coder）
```
优点：利用现有 ccb 基础设施。缺点：provider 能力差异不一定匹配角色。

**路径 2：同 provider 多 agent**
```
Claude-Architect → Claude-Navigator → Claude-Coder（各自独立会话）
```
优点：角色和上下文精确控制。缺点：需要 agent 编排框架。

**路径 3：ccb 混合模式（推荐）**
```
ccb 编排层（已有多 pane 管理能力）
  ├── pane 1: AI + 目录摘要 → Architect
  ├── pane 2: AI + 模块详情 → Navigator
  └── pane 3: AI + 文件代码 → Coder
通过 /ask 传递任务，/pend 获取结果
```
优点：最符合 ccb 现有架构。缺点：需要定义上下文自动注入机制。

## 6. 文件索引生成方案（file-index-gen）🚧

### 6.1 流水线 ✅

```
repomix --compress --style json
       ↓
  本地提取签名和首行注释（零成本）
       ↓
  逐文件调用 LLM（compress 内容 + 目录结构 + tag 词表）
       ↓
  输出校验（tag ∈ vocab）
       ↓
  file-index.json
```

### 6.2 逐文件调用 LLM（L2 + L3 desc 合并生成）🚧

每个文件独立调用，一次性生成文件级和函数级描述：
- 输入：目录结构（~4k token） + 单文件 compress 内容（平均 ~5k token） + tag 词表 + module 词表
- 输出：文件 desc + tags + module_id + 每个函数/类的一句话 desc
- 函数名列表由 tree-sitter 预提取，LLM 只需为每个名字补充 desc
- 首次全量约 N 次调用，后续基于 git diff 仅处理增量文件

### 6.3 Tag 词表机制（tag-vocab.json）✅

预定义封闭词表，按维度组织：

```json
{
  "role": ["entrypoint", "lib", "config", "test", "docs", "ci", "script", "asset"],
  "domain": ["cli", "api", "ui", "auth", "i18n", "mail", "memory", "terminal", "web", "mcp"],
  "pattern": ["daemon", "adapter", "parser", "formatter", "handler", "provider", "util"],
  "tech": ["python", "shell", "javascript", "yaml", "css", "powershell"]
}
```

**自治词表扩展（带去重守卫）：**
1. 优先从词表中选择已有 tag
2. 如果词表不够用，先检查是否有语义等价的已有词：
   - 同义词（async ≈ asynchronous → 用 async）
   - 上下位关系（email ⊂ mail → 用 mail）
   - 缩写关系（config ≈ configuration → 用 config）
3. 仅当新概念和词表中所有词都不重叠时，才提议新 tag
4. 新 tag 命名规则：全小写、连字符连接、不超过 15 字符

**滚动词表：**
每处理一个文件后，被接受的新 tag 立即加入词表，下一个文件的 prompt 中包含更新后的词表。

**批后去重审计：**
全部文件处理完后，对新增 tag 做语义去重检查，发现重叠则合并并更新所有引用。

### 6.4 稳定性保证（四层防护）✅

| 层级 | 机制 | 防护目标 |
|---|---|---|
| Prompt 约束 | 封闭词表 + 强制选择 | 防止随意造词 |
| 去重守卫 | 提议前先比对语义 | 防止近义词泛滥 |
| 滚动词表 | 新词实时加入后续 prompt | 防止同概念多词 |
| 批后审计 | 全量完成后检查合并 | 兜底漏网近义词 |

### 6.5 输出校验 ✅

脚本拿到 LLM 输出后做硬校验：
- 所有 tag 必须存在于当前词表中
- 不在词表内的 tag 拒绝写入，触发报警或重试

### 6.6 增量更新（基于 git diff 的分级联动）❌

首次全量生成后，后续基于 `git diff` 检测变更，按级联规则决定哪些层需要重新生成。

#### 6.6.1 变更检测

```bash
git diff --name-status <baseline>..<current>
# 输出：
# A  lib/mail/adapters/slack.py    ← 新增
# M  lib/mail/daemon.py            ← 修改
# D  lib/mail/adapters/legacy.py   ← 删除
# R  lib/old_name.py lib/new_name.py  ← 重命名
```

将变更分类汇总：

```python
changes = {
    "added": [...],
    "modified": [...],
    "deleted": [...],
    "renamed": [{"from": ..., "to": ...}]
}
```

#### 6.6.2 L3 + L2 层：直接跟随文件变更

| 变更类型 | L3 签名 | L2 desc+tags | 操作 |
|---|---|---|---|
| A (新增) | 生成 | 生成 | Phase 0 + Phase 1 |
| M (修改) | 重生成 | 重生成 | Phase 0 + Phase 1 |
| D (删除) | 删除 | 删除 | 从索引中移除节点 |
| R (重命名) | 更新 ID | 内容不变则复用 | 仅更新 path 和 id |

#### 6.6.3 L1 层：模块级联动（条件触发）

不是每次文件变更都需要更新 L1。通过阈值判断：

```python
def should_update_L1(changes, index):
    affected_modules = set()

    # 新增文件需要分配 module_id
    for file in changes["added"]:
        mid = assign_module(file, index.module_vocab)  # 从现有词表选
        if mid == "NONE_FIT":
            return "full_recluster"  # 现有模块都不合适，需重新聚类
        affected_modules.add(mid)

    # 统计每个模块的变更比例
    for file in changes["modified"] + changes["deleted"]:
        mid = index.get_module(file)
        affected_modules.add(mid)

    for mid in affected_modules:
        total = index.module_file_count(mid)
        changed = count_changes_in_module(mid, changes)
        if changed / total > 0.3:
            yield mid, "regenerate_desc"  # 该模块 desc 可能过时
        else:
            yield mid, "skip"            # 变更不足，保留原 desc
```

#### L1 触发条件汇总

| 条件 | 动作 | 成本 |
|---|---|---|
| 新文件可归入现有模块 | 批量分配 module_id（1 次调用） | ~5k token |
| 新文件无法归入现有模块 | 重新运行模块聚类（Phase 2 全量） | ~11k token |
| 某模块 >30% 文件变更 | 重新生成该模块 L1 desc（1 次调用） | ~2k token |
| 某模块文件全部删除 | 删除该模块 | 0 |
| 文件数变化 >20% | 重新运行模块聚类（Phase 2 全量） | ~11k token |

#### 6.6.4 L0 层：项目级联动（极少触发）

| 条件 | 动作 | 成本 |
|---|---|---|
| 模块词表发生变化（新增/删除模块） | 重新生成 L0 | ~3k token |
| README.md 被修改 | 重新生成 L0 | ~3k token |
| 文件总数变化 >30% | 重新生成 L0 | ~3k token |
| 其他 | 不触发 | 0 |

#### 6.6.5 增量更新决策流程图

```
git diff <baseline>..<current>
  │
  ▼
┌─────────────────────────┐
│ 分类变更文件 A/M/D/R    │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│ L3+L2: 逐文件处理       │
│  A/M → Phase 0 + 1      │
│  D   → 删除节点          │
│  R   → 更新 ID / 重生成  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────────┐
│ 新增文件能归入现有模块吗？  │
├── 能 → 批量分配 module_id   │
├── 不能 → 重新聚类(Phase 2)  │
└────────────┬────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 受影响模块变更比例 >30%？        │
├── 是 → 重新生成该模块 L1 desc    │
├── 否 → 保留原 L1 desc            │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 模块词表变化 / README变更 /      │
│ 文件总数变化 >30%？              │
├── 是 → 重新生成 L0 项目全景      │
├── 否 → 保留原 L0                 │
└────────────┬─────────────────────┘
             │
             ▼
┌──────────────────────────────────┐
│ 合并变更 → 更新 index.json       │
└──────────────────────────────────┘
```

### 6.7 统一索引格式（hippocampus-index.json）✅

统一索引采用**树形结构**，将 L0（项目全景）、L1（逻辑模块）、L2（文件 desc+tags）、L3（函数签名）合并为一个文件，支持按层级逐步展开查询。

#### 顶层结构

```json
{
  "version": 2,
  "schema": "hippocampus-index/v2",
  "generated_at": "2025-02-07T12:00:00Z",
  "vocab_version": "v1.2",
  "project": { ... },
  "modules": [ ... ],
  "stats": {
    "total_dirs": 40,
    "total_files": 200,
    "total_modules": 8,
    "total_signatures": 1300,
    "total_lines": 28000
  },
  "root": { ... }
}
```

#### 项目节点（L0）

```json
{
  "overview": "claude_codex 是一个多 AI provider 协作的命令行工具集...",
  "architecture": "CLI 工具集 + 守护进程架构",
  "scale": {"files": 200, "modules": 8, "primary_lang": "python"}
}
```

#### 模块节点（L1 — 逻辑分组，不依赖目录）

```json
{
  "id": "mod:provider-comm",
  "desc": "AI provider 通信层，管理与 Claude/Gemini/Codex 等后端的请求发送、响应接收和连接管理。包含守护进程和适配器模式。",
  "file_count": 18,
  "line_count": 4200,
  "key_files": ["lib/askd/daemon.py", "lib/providers.py", "bin/ask"]
}
```

#### 目录节点（物理结构，保留）

```json
{
  "id": "dir:lib/mail",
  "type": "dir",
  "name": "mail",
  "desc": "邮件通知子系统，支持 Gmail/Outlook 适配器",
  "tags": ["mail", "daemon", "adapter"],
  "stats": {
    "files": 8,
    "lines": 2400,
    "subdirs": 2
  },
  "core": true,
  "core_score": 0.82,
  "dirs": { ... },
  "files": [ ... ]
}
```

#### 文件节点（L2 + L3）

```json
{
  "id": "file:lib/mail/daemon.py",
  "type": "file",
  "name": "daemon.py",
  "lang": "python",
  "desc": "邮件守护进程，定时检查并发送通知",
  "tags": ["daemon", "mail", "python"],
  "module": "mail-notify",
  "lines": 320,
  "signatures": [
    {"name": "MailDaemon", "kind": "class", "line": 15, "desc": "邮件守护进程主类，管理轮询和分发"},
    {"name": "start", "kind": "method", "line": 28, "parent": "MailDaemon", "desc": "启动轮询守护进程"},
    {"name": "stop", "kind": "method", "line": 45, "parent": "MailDaemon", "desc": "停止守护进程并清理资源"},
    {"name": "dispatch", "kind": "method", "line": 62, "parent": "MailDaemon", "desc": "按适配器类型分发通知消息"},
    {"name": "POLL_INTERVAL", "kind": "const", "line": 8, "desc": "轮询间隔秒数"}
  ]
}
```

#### 完整树形示例（缩略）

```json
{
  "version": 2,
  "schema": "hippocampus-index/v2",
  "root": {
    "id": "dir:.",
    "type": "dir",
    "name": "claude_codex",
    "desc": "多 AI provider 协作的 CLI 工具集",
    "stats": {"files": 200, "lines": 28000, "subdirs": 8},
    "dirs": {
      "bin": {
        "id": "dir:bin",
        "desc": "CLI 入口脚本集合",
        "stats": {"files": 32, "lines": 4200, "subdirs": 0},
        "core": true,
        "files": [
          {"id": "file:bin/ask", "name": "ask", "desc": "统一异步提问 CLI", "tags": ["cli","entrypoint"], "signatures": [...]},
          {"id": "file:bin/pend", "name": "pend", "desc": "查看 AI 最新回复", "tags": ["cli","entrypoint"], "signatures": [...]}
        ]
      },
      "lib": {
        "id": "dir:lib",
        "desc": "核心库，含 provider 通信、终端管理等",
        "stats": {"files": 45, "lines": 12000, "subdirs": 3},
        "core": true,
        "dirs": {
          "mail": {
            "id": "dir:lib/mail",
            "desc": "邮件通知子系统",
            "stats": {"files": 8, "lines": 2400, "subdirs": 2},
            "core": false,
            "files": [...]
          }
        },
        "files": [
          {"id": "file:lib/terminal.py", "name": "terminal.py", "desc": "终端检测与适配", "tags": ["lib","terminal"], "signatures": [...]}
        ]
      },
      "test": {
        "id": "dir:test",
        "desc": "单元测试",
        "stats": {"files": 25, "lines": 5000, "subdirs": 0},
        "core": false,
        "files": [...]
      }
    },
    "files": [
      {"id": "file:README.md", "name": "README.md", "desc": "项目说明文档", "tags": ["docs"], "signatures": []}
    ]
  }
}
```

#### ID 规范

| 类型 | 格式 | 示例 |
|---|---|---|
| 目录 | `dir:<相对路径>` | `dir:lib/mail` |
| 文件 | `file:<相对路径>` | `file:lib/mail/daemon.py` |
| 签名 | `sig:<文件路径>#<名称>` | `sig:lib/mail/daemon.py#MailDaemon` |

ID 基于相对路径生成，文件重命名/移动时 ID 自动变化。通过 git diff 检测路径变更，旧 ID 标记为 deleted，新路径生成新 ID。

#### Schema 版本演化

- `version` 字段标识 schema 大版本，不兼容变更时递增
- 工具读取索引时先检查 `version`，不兼容则提示重新生成
- 字段新增属于兼容变更，不递增版本号（消费端忽略未知字段）

### 6.8 三层数据合并流程（L1+L2+L3 → hippocampus-index.json）✅

统一索引由三个独立数据源合并而成，各源独立生成、独立更新。

#### 数据源

| 源 | 内容 | 生成方式 | 产物 |
|---|---|---|---|
| L1 目录摘要 | 每目录 desc + stats + tags | LLM 聚合（基于目录下文件的 desc） | `dir-summary.json` |
| L2 文件描述 | 每文件 desc + tags | LLM 逐文件（基于 compress 内容） | `file-desc.json` |
| L3 代码签名 | 每文件 class/function/const 列表 | tree-sitter 本地提取 | `code-signatures.json` |

#### 合并算法

```python
def merge_index(dir_summary, file_desc, code_sigs, structure):
    """将三层数据合并为统一树形索引"""

    # 1. 以 repomix structure 的目录树为骨架
    root = build_tree_from_structure(structure)

    # 2. 挂载 L1：目录摘要
    for dir_node in root.walk_dirs():
        summary = dir_summary.get(dir_node.path)
        if summary:
            dir_node.desc = summary.desc
            dir_node.tags = summary.tags

    # 3. 挂载 L2：文件描述
    for file_node in root.walk_files():
        desc = file_desc.get(file_node.path)
        if desc:
            file_node.desc = desc.desc
            file_node.tags = desc.tags

    # 4. 挂载 L3：代码签名
    for file_node in root.walk_files():
        sigs = code_sigs.get(file_node.path, [])
        file_node.signatures = sigs

    # 5. 计算 core_score（自底向上聚合）
    compute_core_scores(root)

    return root
```

### 6.9 L1 逻辑分组生成（不依赖目录结构）❌

L1 层不再绑定目录结构，而是基于 L2 的文件 desc + tags 由 LLM 聚类生成。

#### 为什么不用目录

- 扁平项目（所有文件在根目录）：目录分组无意义
- 过深嵌套（Java 风格 `com/company/project/...`）：前 N 层无信息量
- 混合职责目录（`src/` 下混放 auth、mail、config）：目录不反映逻辑边界

#### 生成流程（两阶段）

```
阶段 1：定义模块词表（一次性，项目级）
  输入：所有文件的 path + desc + tags 汇总（~5k token）
  输出：module-vocab.json（8-15 个逻辑模块）

阶段 2：文件分配（逐文件，可与 L2 合并执行）
  输入：单文件 desc + tags + module-vocab
  输出：该文件所属的 module_id
```

#### 阶段 1：模块词表生成 Prompt

```
以下是一个代码项目的所有文件及其功能描述。
请分析项目的功能架构，将文件归纳为 8-15 个逻辑模块。

要求：
- 每个模块用一个简短 id（全小写、连字符）和一句话 desc
- 模块应反映功能域，而非目录结构
- 相似职责的文件归入同一模块
- 输出 JSON 数组

文件列表：
{files_summary}
```

#### 阶段 1 输出示例（module-vocab.json）

```json
{
  "modules": [
    {"id": "cli-entry", "desc": "命令行入口脚本，用户交互的起点"},
    {"id": "provider-comm", "desc": "AI provider 通信层，管理请求/响应"},
    {"id": "terminal-mgmt", "desc": "终端检测、会话管理与适配"},
    {"id": "mail-notify", "desc": "邮件与消息通知子系统"},
    {"id": "i18n", "desc": "国际化与多语言支持"},
    {"id": "memory", "desc": "上下文记忆与会话持久化"},
    {"id": "config", "desc": "配置加载、校验与管理"},
    {"id": "test", "desc": "单元测试与集成测试"}
  ]
}
```

#### 阶段 2：文件分配（与 L2 合并执行）

阶段 2 可以和 L2 的 desc+tags 生成合并为一次 LLM 调用，零额外成本：

```
原 L2 Prompt：
  "为这个文件生成 desc 和 tags"

合并后 Prompt：
  "为这个文件生成 desc、tags，并从以下模块词表中选择所属模块：
   {module_vocab}
   输出：{desc, tags, module_id}"
```

#### 稳定性保证

| 机制 | 说明 |
|---|---|
| 模块词表固定 | 阶段 1 生成后锁定，阶段 2 只做选择题 |
| 增量文件复用词表 | 新文件从已有词表中选模块，不会产生新模块 |
| 词表演化受控 | 项目重大重构时才重新运行阶段 1 |

#### 与目录结构的关系

逻辑分组**不替代**目录结构，而是作为补充层：

```
hippocampus-index.json 中每个文件节点：
  {
    "path": "src/auth_handler.py",
    "dir": "src/",              ← 物理位置（目录）
    "module": "auth",           ← 逻辑归属（LLM 聚类）
    "desc": "...",
    "tags": [...]
  }
```

查询时可按 `dir` 或 `module` 两种维度聚合，适应不同项目结构。

### 6.10 L1 模块描述生成（自底向上聚合）❌

模块词表（6.9 阶段 1）只有简短的 id + 一句话 desc。L1 层需要更丰富的模块描述，基于该模块下所有文件的 L2 信息聚合生成。

#### 生成流程

```
输入：某模块下所有文件的 path + desc + tags（从 L2 筛选）
输出：该模块的详细描述（2-3 句话）+ 统计 + 关键文件列表
```

#### Prompt

```
以下是 "{module_id}" 模块的所有文件：
{files_in_module}

请生成该模块的描述，包含：
1. desc: 2-3 句话概括模块职责和核心能力
2. key_files: 列出最重要的 3-5 个文件及其作用
3. stats: 文件数、总行数
```

### 6.11 L0 项目全景描述生成 ❌

L0 是整个索引的最顶层，为 AI 提供"一段话理解整个项目"的能力。

#### 输入源

| 来源 | 内容 | 作用 |
|---|---|---|
| L1 模块摘要 | 所有模块的 id + desc | 功能架构全貌 |
| README.md | 项目自述文件 | 项目定位、使用方式 |
| package.json / pyproject.toml | 项目元数据 | 名称、版本、依赖 |
| LICENSE | 许可证类型 | 项目性质 |

#### Prompt

```
以下是一个代码项目的信息，请生成项目全景描述。

项目元数据：
{metadata}

README 摘要：
{readme_summary}

功能模块：
{module_summaries}

请输出：
1. overview: 3-5 句话描述项目定位、核心能力和技术栈
2. architecture: 一句话概括架构风格（如 CLI 工具集、Web 服务、库等）
3. scale: 文件数、模块数、主要语言
```

#### 输出示例

```json
{
  "overview": "claude_codex 是一个多 AI provider 协作的命令行工具集，通过 tmux 多窗格管理同时与 Claude、Gemini、Codex 等 AI 后端交互。支持异步提问、回复轮询、连通性检测，并提供邮件通知、国际化、上下文记忆等辅助能力。基于 Python + Shell 实现。",
  "architecture": "CLI 工具集 + 守护进程架构",
  "scale": {"files": 200, "modules": 8, "primary_lang": "python"}
}
```

### 6.12 完整生成流水线（四阶段）🚧

```
Phase 0: 并行预处理（零 LLM 成本）
  ├─ repomix --compress → 代码骨架
  └─ tree-sitter        → L3 签名名称列表
  （两者读源码，互不依赖，可并行）

Phase 1: LLM 逐文件（主要成本，N 次调用）
  输入：代码骨架 + L3 签名名称 + tag 词表
  输出：文件 desc + tags + 每函数 desc
  （不含 module_id，因为模块词表还没生成）

Phase 2: LLM 聚类（2-3 次调用）
  2a: 模块词表生成（1 次，输入所有文件 path+desc+tags ~5k token）
  2b: 批量分配 module_id（1-2 次，~5k token + 模块词表）
  （不需要逐文件调用，一次批量搞定）

Phase 3: LLM 聚合（~10 次调用）
  3a: L1 模块描述（每模块 1 次，8-15 次）
  3b: L0 项目全景（1 次，输入 L1 摘要 + README）

Phase 4: 合并 → hippocampus-index.json
```

#### 依赖关系图

```
Phase 0（并行）:
  源码 ──→ repomix --compress ──→ 代码骨架 ─┐
  源码 ──→ tree-sitter ──→ L3 签名名称 ─────┤
                                             ↓
Phase 1（逐文件）:                    LLM × N 次
                                      ↓
                              L2 desc+tags + L3 函数desc
                                      ↓
Phase 2（聚类）:              LLM 1次 → 模块词表
                              LLM 1次 → 批量 module_id
                                      ↓
Phase 3（聚合）:              LLM × 模块数 → L1 模块描述
                              LLM 1次 → L0 项目全景
                                      ↓
Phase 4:                      合并 → hippocampus-index.json
```

#### LLM 调用次数汇总（200 文件项目）

| 阶段 | 步骤 | 调用次数 | 输入 token | 说明 |
|---|---|---|---|---|
| Phase 0 | repomix + tree-sitter | 0 | 0 | 本地并行，零 LLM 成本 |
| Phase 1 | L2 desc+tags + L3 函数desc | 200 | ~1.8M | 逐文件，主要成本 |
| Phase 2 | 模块词表生成 | 1 | ~5k | 汇总所有 path+desc+tags |
| Phase 2 | 批量分配 module_id | 1-2 | ~6k | 同上 + 模块词表 |
| Phase 3 | L1 模块描述 | 8-15 | ~20k | 每模块一次 |
| Phase 3 | L0 项目全景 | 1 | ~3k | L1 摘要 + README |
| **合计** | | **~212** | **~1.83M** | 首次全量 |

#### 设计要点

- **Phase 0 可并行**：repomix 和 tree-sitter 都只读源码，互不依赖
- **Phase 1 是主要成本**：L3 函数 desc 与 L2 合并生成，不增加调用次数，仅增加输出 token（每函数 ~10 token，1300 函数 ≈ ~13k token）
- **Phase 2 批量分配**：module_id 不逐文件调用，所有文件的 path+desc+tags 汇总仅 ~5k token，一次批量完成
- **增量更新时**：仅变更文件重跑 Phase 1，Phase 2/3 视变更范围决定是否重跑

### 6.13 各阶段 LLM Prompt 模板 🚧

每个 Phase 的 Prompt 需要精确控制注入信息、输出格式和约束条件。

#### 6.13.0 通用 Prompt 工程原则

**desc 语言策略：**

```
desc 语言跟随项目主语言环境：
  - 项目 README / 注释以中文为主 → desc 用中文
  - 项目 README / 注释以英文为主 → desc 用英文
  - 混合语言 → desc 用英文（更通用）

检测方式：Phase 0 时扫描 README 前 500 字符，
  中文字符占比 > 30% → 判定为中文项目
  否则 → 英文项目

语言参数注入到所有 Prompt 的约束段：
  "desc 使用 {lang}，简洁准确"
```

**模型与参数建议：**

| 阶段 | 推荐模型 | temperature | 理由 |
|---|---|---|---|
| Phase 1 逐文件 | 快速模型（Haiku/Flash） | 0.0 | 量大、格式固定、不需要创造性 |
| Phase 2a 模块词表 | 强模型（Sonnet/Pro） | 0.3 | 需要全局理解和抽象能力 |
| Phase 2b 批量分配 | 快速模型 | 0.0 | 选择题，不需要创造性 |
| Phase 3a 模块描述 | 中等模型 | 0.2 | 需要概括能力但格式固定 |
| Phase 3b 项目全景 | 强模型 | 0.3 | 需要综合理解 |

**各阶段 token 预算：**

| 阶段 | 输入上限 | 输出上限 | 说明 |
|---|---|---|---|
| Phase 1 | ~10k/文件 | ~500/文件 | 目录树 4k + compress 5k + 签名 1k |
| Phase 2a | ~6k | ~2k | 所有文件 path+desc+tags 汇总 |
| Phase 2b | ~7k | ~4k | 同上 + 模块词表 |
| Phase 3a | ~3k/模块 | ~500/模块 | 单模块文件列表 |
| Phase 3b | ~4k | ~500 | L1 摘要 + README 截取 |

#### Phase 1 Prompt：逐文件生成 L2 + L3 desc

```
## 角色
你是代码分析器，为代码文件生成结构化描述。

## 输入
项目目录结构：
{directory_tree}

Tag 词表（只能从中选择）：
{tag_vocab}

该文件的 tree-sitter 签名列表：
{signature_names}

该文件的 compress 内容：
{compressed_content}

## 输出要求（严格 JSON）
{
  "desc": "一句话描述文件职责（<=50字）",
  "tags": ["从词表中选择, 3-8个"],
  "suggested_tags": ["词表不够时提议新词, 附理由"],
  "signatures": [
    {"name": "签名名", "desc": "一句话描述该函数/类职责（<=30字）"}
  ],
  "insights": ["可选，发现的架构问题"]
}

## 示例

输入签名列表：MailDaemon, start, stop, dispatch, POLL_INTERVAL
输入 compress 内容：（略）

输出：
{
  "desc": "邮件守护进程，定时轮询并分发通知消息",
  "tags": ["daemon", "mail", "python"],
  "suggested_tags": [],
  "signatures": [
    {"name": "MailDaemon", "desc": "邮件守护进程主类，管理轮询和分发"},
    {"name": "start", "desc": "启动轮询守护循环"},
    {"name": "stop", "desc": "停止守护进程并清理资源"},
    {"name": "dispatch", "desc": "按适配器类型分发通知消息"},
    {"name": "POLL_INTERVAL", "desc": "轮询间隔秒数常量"}
  ],
  "insights": []
}

## 约束
- desc 使用 {lang}，简洁准确
- tags 必须从词表中选择，不得自造
- suggested_tags 仅当词表确实缺少该概念时才提议，附一句理由
- signatures 的 name 必须与输入的签名列表一一对应，不得遗漏或新增
- insights 仅在发现明显问题时填写（文件 >500 行、函数 >50 个、职责混杂等）
- 不要输出代码，不要解释推理过程
```

#### Phase 2a Prompt：模块词表生成

```
## 角色
你是软件架构分析师，负责识别项目的功能模块划分。

## 输入
以下是项目所有文件的路径、描述和标签：
{files_summary}
（格式：path | desc | tags）

## 输出要求（严格 JSON）
{
  "modules": [
    {"id": "全小写连字符", "desc": "一句话描述模块职责"}
  ],
  "insights": ["可选，项目级架构问题"]
}

## 示例

输入（截取）：
bin/ask | 统一异步提问 CLI | cli, entrypoint
bin/pend | 查看 AI 最新回复 | cli, entrypoint
lib/askd/daemon.py | 异步提问守护进程 | daemon, provider
lib/providers.py | provider 注册与发现 | provider, lib
lib/terminal.py | 终端检测与适配 | terminal, lib
lib/i18n.py | 国际化支持 | i18n, lib
lib/mail/daemon.py | 邮件守护进程 | daemon, mail
test/test_providers.py | provider 单元测试 | test

输出：
{
  "modules": [
    {"id": "cli-entry", "desc": "命令行入口脚本，用户交互的起点"},
    {"id": "provider-comm", "desc": "AI provider 通信层，管理请求/响应"},
    {"id": "terminal-mgmt", "desc": "终端检测、会话管理与适配"},
    {"id": "mail-notify", "desc": "邮件与消息通知子系统"},
    {"id": "i18n", "desc": "国际化与多语言支持"},
    {"id": "infra", "desc": "通用工具、配置与基础设施"},
    {"id": "test", "desc": "单元测试与集成测试"}
  ],
  "insights": [
    "provider-comm 和 terminal-mgmt 存在 5 个文件标签高度重叠，建议确认边界"
  ]
}

## 约束
- 模块数量 8-15 个，反映功能域而非目录结构
- id 全小写、连字符连接、不超过 20 字符
- 每个文件应能归入且仅归入一个模块
- 通用工具类文件归入 "infra" 或 "util" 模块
- insights 仅在发现明显问题时填写（职责重叠、孤立文件群、模块边界模糊等）
```

#### Phase 2b Prompt：批量分配 module_id

```
## 角色
你是文件分类器，将文件分配到已定义的模块中。

## 输入
模块词表：
{module_vocab}

文件列表（path | desc | tags）：
{files_summary}

## 输出要求（严格 JSON）
[
  {"path": "文件路径", "module_id": "模块id"}
]

## 示例

模块词表：
  cli-entry | 命令行入口脚本
  provider-comm | AI provider 通信层
  mail-notify | 邮件与消息通知
  test | 单元测试与集成测试

文件列表（截取）：
  bin/ask | 统一异步提问 CLI | cli, entrypoint
  lib/askd/daemon.py | 异步提问守护进程 | daemon, provider
  lib/mail/daemon.py | 邮件守护进程 | daemon, mail
  test/test_providers.py | provider 单元测试 | test

输出：
[
  {"path": "bin/ask", "module_id": "cli-entry"},
  {"path": "lib/askd/daemon.py", "module_id": "provider-comm"},
  {"path": "lib/mail/daemon.py", "module_id": "mail-notify"},
  {"path": "test/test_providers.py", "module_id": "test"}
]

## 约束
- 每个文件必须且只能分配一个 module_id
- module_id 必须来自模块词表，不得自造
- 如果某文件确实无法归入任何模块，标记为 "_unclassified"
- 输出数组长度必须等于输入文件数量，不得遗漏
```

#### Phase 3a Prompt：L1 模块描述生成

```
## 角色
你是模块文档编写者，为代码模块生成结构化描述。

## 输入
模块 id：{module_id}
该模块下所有文件：
{files_in_module}
（格式：path | desc | tags | 行数）

## 输出要求（严格 JSON）
{
  "desc": "2-3 句话概括模块职责和核心能力",
  "key_files": ["最重要的 3-5 个文件路径"],
  "stats": {"files": N, "lines": N},
  "insights": ["可选，模块级架构问题"]
}

## 示例

模块 id：provider-comm
文件列表：
  lib/askd/daemon.py | 异步提问守护进程，管理请求队列 | daemon, provider | 420
  lib/providers.py | provider 注册与发现 | provider, lib | 180
  lib/askd/router.py | 请求路由，按 provider 分发 | provider, handler | 95
  bin/ask | 统一异步提问 CLI 入口 | cli, entrypoint | 60

输出：
{
  "desc": "AI provider 通信层，负责与 Claude/Gemini/Codex 等后端的请求发送、响应接收和连接管理。核心是守护进程 + 路由分发模式，通过适配器支持多种 provider。",
  "key_files": ["lib/askd/daemon.py", "lib/providers.py", "lib/askd/router.py"],
  "stats": {"files": 4, "lines": 755},
  "insights": ["daemon.py 420 行且包含队列管理和连接管理，建议拆分"]
}

## 约束
- desc 使用 {lang}，概括模块整体职责，不要罗列文件
- key_files 按重要性排序，最多 5 个
- insights 仅在发现明显问题时填写（模块膨胀、文件错放、缺少测试等）
```

#### Phase 3b Prompt：L0 项目全景生成

```
## 角色
你是项目文档编写者，为整个代码项目生成全景描述。

## 输入
项目元数据：
{metadata}

README 内容（截取前 2000 字）：
{readme_content}

所有模块摘要：
{module_summaries}
（格式：module_id | desc | 文件数 | 行数）

## 输出要求（严格 JSON）
{
  "overview": "3-5 句话描述项目定位、核心能力和技术栈",
  "architecture": "一句话概括架构风格",
  "scale": {"files": N, "modules": N, "primary_lang": "语言"},
  "insights": ["可选，项目全局架构问题"]
}

## 示例

项目元数据：name=claude_codex, version=0.3.0, lang=python
README（截取）：多 AI provider 协作的 CLI 工具集...
模块摘要：
  cli-entry | 命令行入口脚本 | 32 文件 | 4200 行
  provider-comm | AI provider 通信层 | 18 文件 | 4200 行
  terminal-mgmt | 终端检测与适配 | 12 文件 | 2800 行
  mail-notify | 邮件通知子系统 | 8 文件 | 2400 行
  i18n | 国际化支持 | 4 文件 | 600 行
  memory | 上下文记忆 | 6 文件 | 1200 行
  infra | 通用工具与配置 | 15 文件 | 3000 行
  test | 测试 | 25 文件 | 5000 行

输出：
{
  "overview": "claude_codex 是一个多 AI provider 协作的命令行工具集，通过 tmux 多窗格管理同时与 Claude、Gemini、Codex 等 AI 后端交互。支持异步提问、回复轮询、连通性检测，并提供邮件通知、国际化、上下文记忆等辅助能力。基于 Python + Shell 实现。",
  "architecture": "CLI 工具集 + 守护进程架构",
  "scale": {"files": 120, "modules": 8, "primary_lang": "python"},
  "insights": [
    "cli-entry 和 provider-comm 行数相当但职责差异大，确认 bin/ 下脚本是否应归入 provider-comm",
    "test 模块 25 文件覆盖 120 个源文件，覆盖率约 20%，建议补充"
  ]
}

## 约束
- overview 使用 {lang}，概括项目整体而非罗列模块
- architecture 一句话，描述架构风格（如 CLI 工具集、Web 服务、monorepo 等）
- scale 中 files 为源文件数（不含测试），primary_lang 为代码量最大的语言
- insights 仅在发现全局性问题时填写（模块失衡、架构风险、覆盖率不足等）
```

#### 6.13.1 输出校验与重试策略

每次 LLM 调用后，脚本对输出做硬校验。校验失败时自动重试，最多 3 次。

**校验规则矩阵：**

| 阶段 | 校验项 | 失败处理 |
|---|---|---|
| Phase 1 | JSON 可解析 | 重试，附加 "请输出合法 JSON" |
| Phase 1 | tags ⊂ vocab | 拒绝非法 tag，仅重试该字段 |
| Phase 1 | signatures 数量 = 输入签名数 | 重试，附加遗漏的签名名称 |
| Phase 1 | desc 长度 ≤ 50 字 | 截断，不重试 |
| Phase 2a | modules 数量 8-15 | 重试，附加 "当前 N 个，请调整到 8-15" |
| Phase 2a | id 格式合规 | 自动修正（小写化、替换空格为连字符） |
| Phase 2b | 输出数组长度 = 输入文件数 | 重试，附加遗漏的文件路径 |
| Phase 2b | module_id ∈ vocab | 重试，附加合法词表 |
| Phase 3a | key_files ⊂ 该模块文件 | 过滤非法路径，不重试 |
| Phase 3b | scale.files 合理范围 | 用实际统计值覆盖，不重试 |

**重试 Prompt 模板：**

```
你上次的输出存在以下问题：
{validation_errors}

请修正后重新输出完整 JSON。仅输出 JSON，不要解释。

上次输出（供参考）：
{previous_output}
```

**重试策略：**

```
第 1 次重试：附加校验错误信息，temperature 不变
第 2 次重试：附加校验错误 + 上次输出，temperature 降为 0.0
第 3 次重试失败：
  - Phase 1：标记该文件为 _failed，跳过，最终报告中列出
  - Phase 2/3：中断流水线，人工介入
```

#### 6.13.2 增量更新 Prompt（基于 git diff）

文件变更后，增量更新的 Prompt 与全量生成不同——需要注入旧版信息作为参考，减少不必要的漂移。

**Phase 1 增量 Prompt（修改文件重生成 L2 + L3）：**

```
## 角色
你是代码分析器，为变更后的代码文件更新结构化描述。

## 输入
该文件的旧版描述（供参考，减少不必要变更）：
{old_desc}
{old_tags}
{old_signatures_with_desc}

该文件的变更摘要：
{diff_summary}

该文件的新版 compress 内容：
{compressed_content}

该文件的新版 tree-sitter 签名列表：
{signature_names}

Tag 词表：
{tag_vocab}

## 输出要求（严格 JSON，格式同全量）
{
  "desc": "...", "tags": [...], "suggested_tags": [...],
  "signatures": [...], "insights": [...]
}

## 约束
- 如果文件职责未变，desc 应保持不变或仅微调措辞
- 新增签名需要新 desc，未变签名复用旧 desc
- 删除的签名从列表中移除
- tags 仅在职责确实变化时才调整
```

**Phase 2b 增量 Prompt（新增文件分配 module_id）：**

```
## 角色
你是文件分类器，将新增文件分配到已有模块中。

## 输入
模块词表：
{module_vocab}

新增文件列表（path | desc | tags）：
{new_files_summary}

## 输出要求（严格 JSON）
[
  {"path": "文件路径", "module_id": "模块id", "confidence": "high|medium|low"}
]

## 约束
- module_id 必须来自模块词表
- confidence=low 表示该文件与所有模块匹配度都不高，可能需要新模块
- 如果 >30% 的文件 confidence=low，建议触发 Phase 2a 重新聚类
```

### 6.14 LLM 后端接入层 ✅

hippocampus 流水线中 LLM 的角色是**纯文本生成**——不需要 agent 能力（不读文件、不跑命令、不多轮对话）。所有 I/O 操作由 Pipeline 脚本负责，LLM 只是"prompt 进、JSON 出"的无状态函数。

#### 6.14.1 职责划分

```
Pipeline 脚本（Python）              LLM 后端
━━━━━━━━━━━━━━━━━━━━━              ━━━━━━━━
读源码 / 运行 tree-sitter            （不参与）
组装 prompt（模板 + 数据）  ──发送──→  生成 JSON 文本
解析 JSON ←──────────────── 返回 ←──  （纯文本输出）
校验 + 重试 + 写入文件               （不参与）
```

| 操作 | 执行者 | 说明 |
|---|---|---|
| 读源码、运行 repomix / tree-sitter | Pipeline 脚本 | 本地 I/O |
| 组装 prompt | Pipeline 脚本 | 拼接模板 + 文件内容 + 词表 |
| **生成 desc / tags / module_id** | **LLM** | **唯一职责，无状态** |
| 解析 LLM 输出 | Pipeline 脚本 | `json.loads()` |
| 校验输出合法性 | Pipeline 脚本 | tag ∈ vocab、签名数匹配等 |
| 重试失败调用 | Pipeline 脚本 | 最多 3 次（见 6.13.1） |
| 并发控制 | Pipeline 脚本 | asyncio + semaphore |
| 写 hippocampus-index.json | Pipeline 脚本 | `json.dump()` |

#### 6.14.2 为什么不用 agent 工具（opencode / claude-code 等）

hippocampus 的 LLM 调用是**批处理模式**，与交互式 agent 的需求完全不同：

| 维度 | hippocampus 需求 | agent 工具特点 |
|---|---|---|
| 调用模式 | 200+ 次独立无状态调用 | 多轮有状态对话 |
| 并发 | 需要 20-50 路并发 | 单会话串行 |
| 输出格式 | 严格 JSON，需程序化校验 | 自由文本，面向人类 |
| 工具能力 | 不需要（不读文件、不跑命令） | 核心能力但此处多余 |
| 重试控制 | 需要精确控制（附加校验错误） | 无法自定义重试逻辑 |
| 模型选择 | 按阶段切换（Haiku/Sonnet） | 通常固定一个模型 |

用 agent 工具做批量 completion 是杀鸡用牛刀，且慢、不可控。

#### 6.14.3 技术方案：LiteLLM 统一接入层

采用 [LiteLLM](https://github.com/BerriAI/litellm) 作为 LLM 调用层，一套代码支持 100+ provider，用户按偏好/成本自由切换。

```
hippocampus Pipeline 脚本
  └─ litellm.acompletion()       ← 异步调用，支持并发
       ├─ anthropic/claude-3-5-haiku   ← Phase 1（快速便宜）
       ├─ anthropic/claude-sonnet-4-0  ← Phase 2a/3b（强模型）
       ├─ openai/gpt-4o-mini           ← 用户可切换
       ├─ gemini/gemini-2.0-flash      ← 用户可切换
       └─ ollama/llama3                ← 本地模型（离线/隐私）
```

**选择 LiteLLM 的理由：**

| 维度 | LiteLLM | 直接用单一 SDK |
|---|---|---|
| Provider 覆盖 | 100+（Anthropic/OpenAI/Google/Ollama/...） | 1 个 |
| API 兼容性 | OpenAI SDK 格式统一 | 各家 SDK 不同 |
| 异步支持 | `acompletion()` 原生异步 | 需自行封装 |
| Rate limit | 内置处理 | 需自行实现 |
| Fallback | 内置 provider 降级 | 需自行实现 |
| 依赖 | `pip install litellm` | 各家 SDK 分别安装 |

#### 6.14.4 配置文件设计

```yaml
# .hippocampus/config.yaml
llm:
  # 按阶段指定模型（LiteLLM model 格式：provider/model-name）
  phase_models:
    phase_1:  "anthropic/claude-3-5-haiku-latest"   # 批量逐文件，快速便宜
    phase_2a: "anthropic/claude-sonnet-4-0"          # 模块词表，需全局理解
    phase_2b: "anthropic/claude-3-5-haiku-latest"    # 批量分配，选择题
    phase_3a: "anthropic/claude-3-5-haiku-latest"    # 模块描述，概括能力
    phase_3b: "anthropic/claude-sonnet-4-0"          # 项目全景，综合理解

  # 并发与重试
  max_concurrent: 20    # Phase 1 并发数（受 API rate limit 约束）
  retry_max: 3          # 校验失败最大重试次数
  timeout: 30           # 单次调用超时（秒）

  # temperature（按阶段，通常不需要用户修改）
  temperature:
    phase_1: 0.0
    phase_2a: 0.3
    phase_2b: 0.0
    phase_3a: 0.2
    phase_3b: 0.3

  # 可选：fallback 模型（主模型失败时降级）
  fallback_model: "openai/gpt-4o-mini"
```

**API Key 来源（优先级）：**

```
1. 环境变量（推荐）：ANTHROPIC_API_KEY, OPENAI_API_KEY, GEMINI_API_KEY 等
   → LiteLLM 自动读取，无需配置
2. 配置文件：.hippocampus/config.yaml 中显式指定
   → 仅用于特殊场景（如自定义 base_url）
3. .env 文件：项目根目录 .env
   → LiteLLM 支持自动加载
```

用户只需 `export ANTHROPIC_API_KEY=sk-xxx` 即可开始使用，零配置。

#### 6.14.5 核心调用逻辑（伪代码）

```python
import asyncio
import litellm
from litellm import acompletion

class HippoLLM:
    """hippocampus LLM 调用层 — 纯 completion，无 agent 能力"""

    def __init__(self, config):
        self.config = config
        self.semaphore = asyncio.Semaphore(config.max_concurrent)

    async def call(self, phase: str, prompt: str) -> dict:
        """单次 LLM 调用，返回解析后的 JSON"""
        model = self.config.phase_models[phase]
        temp = self.config.temperature.get(phase, 0.0)

        async with self.semaphore:
            response = await acompletion(
                model=model,
                messages=[{"role": "user", "content": prompt}],
                temperature=temp,
                timeout=self.config.timeout
            )

        text = response.choices[0].message.content
        return json.loads(text)
```

**带校验的重试封装：**

```python
    async def call_with_retry(self, phase, prompt, validator):
        """调用 LLM 并校验输出，失败自动重试"""
        last_output = None
        for attempt in range(self.config.retry_max):
            try:
                result = await self.call(phase, prompt)
                errors = validator(result)
                if not errors:
                    return result

                # 校验失败 → 构造重试 prompt
                last_output = result
                prompt = RETRY_TEMPLATE.format(
                    validation_errors="\n".join(errors),
                    previous_output=json.dumps(result, ensure_ascii=False)
                )
            except (json.JSONDecodeError, litellm.exceptions.Timeout) as e:
                if attempt == self.config.retry_max - 1:
                    raise
        return last_output  # 最终仍失败，返回最后一次输出供人工处理
```

**Phase 1 批量并发执行：**

```python
async def run_phase1(llm, files, tag_vocab, dir_tree):
    """Phase 1: 逐文件并发生成 L2 + L3 desc"""
    tasks = []
    for f in files:
        prompt = PHASE1_TEMPLATE.format(
            directory_tree=dir_tree,
            tag_vocab=json.dumps(tag_vocab),
            signature_names=f.signature_names,
            compressed_content=f.compress_content
        )
        validator = make_phase1_validator(tag_vocab, f.signature_names)
        tasks.append(llm.call_with_retry("phase_1", prompt, validator))

    # 并发执行，semaphore 控制并发数
    results = await asyncio.gather(*tasks, return_exceptions=True)

    succeeded, failed = [], []
    for f, r in zip(files, results):
        if isinstance(r, Exception):
            failed.append((f.path, str(r)))
        else:
            succeeded.append((f.path, r))

    return succeeded, failed
```

#### 6.14.6 API 成本估算（200 文件项目，首次全量）

| 阶段 | 模型 | 调用次数 | 输入 token | 输出 token | 估算费用 |
|---|---|---|---|---|---|
| Phase 1 | Haiku | ~200 | ~1.8M | ~100k | ~$0.20 |
| Phase 2a | Sonnet | 1 | ~5k | ~2k | ~$0.02 |
| Phase 2b | Haiku | 1-2 | ~6k | ~4k | ~$0.01 |
| Phase 3a | Haiku | 8-15 | ~20k | ~5k | ~$0.02 |
| Phase 3b | Sonnet | 1 | ~4k | ~500 | ~$0.01 |
| **合计** | | **~215** | **~1.83M** | **~112k** | **~$0.26** |

注：价格基于 2025 年 Anthropic 定价估算，实际费用随 provider 和模型变化。增量更新仅处理变更文件，成本按比例降低。

## 7. 架构优化分析（Architecture Insights）❌

在生成/更新索引的过程中，LLM 已经"看过"了项目的全部结构信息。可以零额外成本地在各阶段顺便输出架构建议。

### 7.1 Insight 类型分类体系

每个 insight 由 `type`（类型编码）、`severity`（严重等级）、`scope`（作用域）、`msg`（描述）组成。

#### 类型编码（按作用域分组）

**文件级（Phase 1 产生）：**

| type | 含义 | 触发条件 |
|---|---|---|
| `file-too-large` | 文件过大 | 行数 > 500 |
| `too-many-symbols` | 函数/类过多 | 签名数 > 30 |
| `mixed-responsibility` | 职责混杂 | tags 跨 2+ 个不相关 domain |
| `god-class` | 上帝类 | 单 class 方法数 > 20 |
| `deep-nesting` | 嵌套过深 | 缩进层级 > 5（compress 可检测） |
| `no-docstring` | 缺少文档 | 公开 API 无注释（可选检测） |

**模块级（Phase 3a 产生）：**

| type | 含义 | 触发条件 |
|---|---|---|
| `module-bloat` | 模块膨胀 | 文件数 > 25 或行数 > 8000 |
| `module-tiny` | 模块过小 | 文件数 < 3 |
| `missing-test` | 缺少测试 | 模块内 test 标签文件 = 0 |
| `misplaced-file` | 文件错放 | 文件 desc/tags 与所属模块不匹配 |
| `high-coupling` | 高耦合 | 模块内文件 tags 与其他模块高度重叠 |

**项目级（Phase 2a / 3b 产生）：**

| type | 含义 | 触发条件 |
|---|---|---|
| `module-overlap` | 模块职责重叠 | 两个模块 desc 语义相似度高 |
| `orphan-files` | 孤立文件 | 多个文件 confidence=low |
| `imbalanced-modules` | 模块失衡 | 最大模块 / 最小模块文件数比 > 5:1 |
| `low-test-coverage` | 测试覆盖不足 | test 文件数 / 源文件数 < 0.2 |
| `single-point-of-failure` | 单点风险 | 某关键文件无同模块替代且行数 > 500 |

**增量级（增量更新时产生）：**

| type | 含义 | 触发条件 |
|---|---|---|
| `module-growth` | 模块持续膨胀 | 连续 3 次更新该模块文件数增长 |
| `desc-drift` | 描述漂移 | 文件 desc 与上版差异大但代码变更小 |
| `new-coupling` | 新增耦合 | 新增文件的 tags 跨多个模块 |

#### 严重等级

| severity | 含义 | 处理方式 |
|---|---|---|
| `info` | 信息提示 | 记录，不主动展示 |
| `warn` | 值得关注 | 报告中高亮，建议人工审查 |
| `critical` | 需要行动 | 报告中置顶，阻断性问题 |

**等级判定规则：**

```
file-too-large:
  500-1000 行 → info
  1000-3000 行 → warn
  >3000 行 → critical

module-bloat:
  25-40 文件 → warn
  >40 文件 → critical

missing-test:
  非核心模块 → info
  核心模块（core_score > 0.3）→ warn
```

### 7.2 Insight 结构化格式与收集机制

#### 单条 Insight 格式

```json
{
  "type": "file-too-large",
  "severity": "warn",
  "scope": "file:lib/mail/daemon.py",
  "phase": "phase-1",
  "msg": "该文件 1200 行，建议按职责拆分为路由层和数据层",
  "metrics": {"lines": 1200, "symbols": 42},
  "suggestion": "拆分为 daemon_router.py 和 daemon_store.py"
}
```

| 字段 | 类型 | 说明 |
|---|---|---|
| `type` | string | 7.1 中定义的类型编码 |
| `severity` | enum | `info` / `warn` / `critical` |
| `scope` | string | 作用域，格式同索引 ID（`file:...` / `mod:...` / `project`） |
| `phase` | string | 产生阶段（`phase-1` / `phase-2a` / `phase-3a` / `phase-3b` / `incremental`） |
| `msg` | string | 人类可读的问题描述 |
| `metrics` | object | 可选，触发该 insight 的量化指标 |
| `suggestion` | string | 可选，具体改进建议 |

#### 收集流程

```
Phase 1 逐文件 → LLM 输出 insights[] → 附加 scope=file:xxx, phase=phase-1
                                          ↓
Phase 2a 聚类 → LLM 输出 insights[] → 附加 scope=project, phase=phase-2a
                                          ↓
Phase 3a 聚合 → LLM 输出 insights[] → 附加 scope=mod:xxx, phase=phase-3a
                                          ↓
Phase 3b 全景 → LLM 输出 insights[] → 附加 scope=project, phase=phase-3b
                                          ↓
                    汇总 → 去重 → 排序 → architecture-report.json
```

**去重规则：** 同一 scope + type 的 insight 只保留最新一条。例如 Phase 1 和 Phase 3a 都报告了 `file-too-large` on `file:lib/mail/daemon.py`，保留 Phase 3a 的（信息更全面）。

#### 脚本侧补充 Insight（非 LLM 产生）

部分 insight 可以由脚本直接计算，不需要 LLM 判断：

```python
# Phase 4 合并后，脚本自动检测
def compute_script_insights(index):
    insights = []

    # 模块失衡检测
    sizes = [m.file_count for m in index.modules]
    if max(sizes) / max(min(sizes), 1) > 5:
        insights.append({
            "type": "imbalanced-modules",
            "severity": "warn",
            "scope": "project",
            "phase": "phase-4",
            "msg": f"最大模块 {max(sizes)} 文件，最小 {min(sizes)} 文件，比例 > 5:1",
            "metrics": {"max": max(sizes), "min": min(sizes)}
        })

    # 测试覆盖率检测
    src = sum(1 for f in index.files if "test" not in f.tags)
    test = sum(1 for f in index.files if "test" in f.tags)
    if src > 0 and test / src < 0.2:
        insights.append({
            "type": "low-test-coverage",
            "severity": "warn",
            "scope": "project",
            "phase": "phase-4",
            "msg": f"测试文件 {test} 个 / 源文件 {src} 个，覆盖率 {test/src:.0%}",
            "metrics": {"test_files": test, "src_files": src}
        })

    return insights
```

### 7.3 Insights 汇总与存储

#### 存储目录

```
.hippocampus/
  insights/
    architecture-report.json    ← 最新一次全量/增量分析结果
    architecture-history.jsonl  ← 历史记录（每次生成追加一条）
```

#### architecture-report.json 格式

```json
{
  "version": 1,
  "generated_at": "2025-02-08T12:00:00Z",
  "baseline": "abc1234",
  "current": "def5678",
  "mode": "incremental",
  "summary": {
    "total": 12,
    "by_severity": {"critical": 1, "warn": 5, "info": 6},
    "by_scope": {"file": 8, "module": 3, "project": 1}
  },
  "insights": [
    {
      "type": "file-too-large",
      "severity": "critical",
      "scope": "file:src/god_file.py",
      "phase": "phase-1",
      "msg": "该文件 3200 行，包含 52 个函数，建议按职责拆分",
      "metrics": {"lines": 3200, "symbols": 52},
      "suggestion": "按路由/存储/校验三个职责拆分为独立文件"
    }
  ]
}
```

#### architecture-history.jsonl 格式

每次生成/增量更新后追加一行，用于趋势分析：

```jsonl
{"ts":"2025-02-01T12:00:00Z","commit":"abc1234","mode":"full","total":8,"critical":0,"warn":3,"info":5,"top_types":["file-too-large","missing-test"]}
{"ts":"2025-02-08T12:00:00Z","commit":"def5678","mode":"incremental","total":12,"critical":1,"warn":5,"info":6,"top_types":["file-too-large","module-bloat","missing-test"]}
```

### 7.4 趋势分析（跨版本对比）

单次 insight 是快照，趋势分析才能发现**方向性问题**——某个模块在持续膨胀，某类问题在反复出现。

#### 数据源

基于 `architecture-history.jsonl` 的历史记录，每条包含 commit、时间戳、各等级计数和 top_types。

#### 趋势指标

```python
def compute_trends(history, window=5):
    """基于最近 window 条记录计算趋势"""
    recent = history[-window:]
    trends = {}

    # 1. 总 insight 数趋势
    counts = [r["total"] for r in recent]
    trends["total_trend"] = "rising" if counts[-1] > counts[0] * 1.2 else \
                            "falling" if counts[-1] < counts[0] * 0.8 else "stable"

    # 2. critical 趋势
    crits = [r["critical"] for r in recent]
    trends["critical_trend"] = "rising" if crits[-1] > crits[0] else \
                               "resolved" if crits[-1] == 0 and crits[0] > 0 else "stable"

    # 3. 反复出现的类型（连续 3+ 次出现）
    type_freq = {}
    for r in recent:
        for t in r["top_types"]:
            type_freq[t] = type_freq.get(t, 0) + 1
    trends["recurring"] = [t for t, c in type_freq.items() if c >= 3]

    return trends
```

#### 趋势报告输出

```json
{
  "window": 5,
  "total_trend": "rising",
  "critical_trend": "stable",
  "recurring": ["file-too-large", "missing-test"],
  "module_growth": [
    {"module": "provider-comm", "file_count_history": [15, 16, 18, 18, 21], "trend": "rising"}
  ],
  "resolved_since_last": ["orphan-files"],
  "new_since_last": ["module-bloat"]
}
```

#### 趋势触发动作

| 趋势 | 动作 |
|---|---|
| `total_trend=rising` 连续 3 次 | 在报告中标注 "架构健康度下降" |
| `critical_trend=rising` | 报告置顶警告 |
| `recurring` 类型存在 | 标注为 "长期未解决问题" |
| 某模块 `file_count` 连续增长 | 标注 "模块膨胀趋势"，建议拆分 |

### 7.5 与多 AI 协作的集成

Insights 不仅是静态报告，还应融入 Section 5 定义的多 AI 协作流程中，让各角色在决策时参考架构建议。

#### 各角色如何消费 Insights

| 角色 | 消费方式 | 场景 |
|---|---|---|
| Architect | `hippo_overview` 注入时附带 critical/warn 级 insight 摘要 | 任务分解时避开高风险模块，或将重构纳入计划 |
| Navigator | `hippo_expand` 注入时附带目标模块的 insight | 规划修改方案时考虑已知问题（如文件过大则建议拆分而非继续追加） |
| Coder | 不主动注入 insight | 仅在 Navigator 的 plan 中体现（如 "daemon.py 过大，新功能写入新文件"） |

#### Architect 注入示例

`hippo_overview` 返回的 Markdown 末尾追加 insights 摘要：

```markdown
# claude_codex
多 AI provider 协作的 CLI 工具集...

## provider-comm（18 文件）
AI provider 通信层...

## mail-notify（8 文件）
邮件与消息通知...

---
⚠ 架构提示（2 warn, 1 critical）：
- [critical] src/god_file.py: 3200 行，建议拆分
- [warn] provider-comm: 模块持续膨胀（15→21 文件），建议拆分
- [warn] 测试覆盖率 18%，建议补充核心模块测试
```

#### Navigator 注入示例

`hippo_expand("lib/mail/", "L3")` 返回时附带模块级 insight：

```markdown
### mail-notify / lib/mail/

lib/mail/daemon.py: 邮件守护进程（320 行）
  → MailDaemon, start, stop, dispatch

lib/mail/adapters/gmail.py: Gmail 适配器
  → GmailAdapter, send, connect

---
⚠ 该模块提示：
- [info] 0 个测试文件，建议补充
```

#### 实现方式

```python
def inject_insights(content, insights, scope, max_items=5):
    """在注入内容末尾追加相关 insights"""
    relevant = [i for i in insights
                if i["scope"] == scope or i["scope"] == "project"]
    relevant.sort(key=lambda i: {"critical": 0, "warn": 1, "info": 2}[i["severity"]])

    if not relevant:
        return content

    lines = ["\n---", f"⚠ 架构提示（{len(relevant)} 条）："]
    for i in relevant[:max_items]:
        lines.append(f"- [{i['severity']}] {i['msg']}")

    return content + "\n".join(lines)
```

### 7.6 呈现格式（面向不同受众）

Insights 的消费者有三类：AI agent、开发者（CLI）、团队（CI 报告）。同一份数据需要不同的渲染方式。

#### 7.6.1 AI 注入格式（Markdown，嵌入上下文）

已在 7.5 中定义。特点：
- 嵌入 `hippo_overview` / `hippo_expand` 返回的 content 末尾
- 仅展示 critical + warn，info 级别不注入（节省 token）
- 最多 5 条，按 severity 降序
- 格式：`- [severity] msg`

#### 7.6.2 开发者 CLI 格式

通过 `hippo insights` 命令查看，终端友好：

```
$ hippo insights

Architecture Report (2025-02-08, commit def5678)
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

🔴 CRITICAL (1)
  src/god_file.py
    3200 行，52 个函数，建议按职责拆分为路由/存储/校验三个文件

🟡 WARN (5)
  provider-comm
    模块持续膨胀（15→21 文件），建议拆分为 provider-core 和 provider-adapters
  provider-comm
    0 个测试文件，建议补充核心模块测试
  project
    测试覆盖率 18%（25 test / 140 src），建议提升至 30%+
  ...

📊 趋势（最近 5 次）
  总 insight 数：8 → 12 ↑ rising
  反复出现：file-too-large, missing-test
  已解决：orphan-files ✓

$ hippo insights --severity warn --scope mod:provider-comm
  # 过滤查看特定模块的 warn 级别问题
```

#### 7.6.3 CI 报告格式（JSON + Markdown summary）

CI 流程中生成两个产物：

**1. 机器可读：architecture-report.json**（7.3 已定义）

**2. 人类可读：architecture-summary.md**

```markdown
## Architecture Health Report

**Commit:** def5678 | **Date:** 2025-02-08 | **Mode:** incremental

| Severity | Count | Trend |
|---|---|---|
| 🔴 Critical | 1 | — |
| 🟡 Warn | 5 | ↑ +2 |
| ℹ️ Info | 6 | — |

### Critical Issues

1. **src/god_file.py** — 3200 行，52 个函数
   > 建议按职责拆分为路由/存储/校验三个文件

### Top Warnings

1. **provider-comm** — 模块持续膨胀（15→21 文件）
2. **project** — 测试覆盖率 18%

### Recurring (3+ versions)

- `file-too-large` — 连续 5 次出现
- `missing-test` — 连续 4 次出现
```

## 8. 代码签名提取（code-sig-extract）✅

### 8.1 定位

Phase 0 的核心步骤之一，与 repomix --compress 并行执行。零 LLM 成本，本地确定性提取。
输出的签名名称列表作为 Phase 1 的输入，LLM 为每个签名补充 desc。

### 8.2 提取内容

对每个源码文件，提取以下符号定义：

| 符号类型 | 提取信息 | 示例 |
|---|---|---|
| class | 名称、起始行号 | `class MailDaemon` |
| function / method | 名称、起始行号、所属 class（如有） | `def dispatch(self, msg)` |
| const / variable（模块级） | 名称、起始行号 | `POLL_INTERVAL = 30` |
| interface / type（TS/Go） | 名称、起始行号 | `interface Config {}` |
| export（JS/TS） | 名称、起始行号 | `export function init()` |

### 8.3 tree-sitter 查询文件来源

复用 aider 项目维护的 `.scm` 查询文件（MIT 协议），覆盖 30+ 语言：

```
主要语言覆盖：
  Python, JavaScript, TypeScript, Go, Rust, Java, C, C++,
  C#, Ruby, PHP, Swift, Kotlin, Scala, Lua, Elixir,
  Bash, PowerShell, YAML, TOML, HCL, Dockerfile, ...

查询文件位置：
  .hippocampus/queries/<lang>.scm

更新方式：
  从 aider 仓库同步，或按需自定义扩展
```

### 8.4 输出格式（code-signatures.json）

```json
{
  "version": 1,
  "generated_at": "2025-02-08T12:00:00Z",
  "files": {
    "lib/mail/daemon.py": {
      "lang": "python",
      "signatures": [
        {"name": "POLL_INTERVAL", "kind": "const", "line": 8},
        {"name": "MailDaemon", "kind": "class", "line": 15},
        {"name": "start", "kind": "method", "line": 28, "parent": "MailDaemon"},
        {"name": "stop", "kind": "method", "line": 45, "parent": "MailDaemon"},
        {"name": "dispatch", "kind": "method", "line": 62, "parent": "MailDaemon"}
      ]
    }
  }
}
```

注意：此阶段只有 `name`、`kind`、`line`、`parent`，**不含 `desc`**。desc 由 Phase 1 LLM 生成后在 Phase 4 合并写入 hippocampus-index.json。

### 8.5 与流水线的关系

```
Phase 0（并行）:
  源码 → tree-sitter + .scm → code-signatures.json（签名名称）
  源码 → repomix --compress → repomix-compress.json（代码骨架）
                    ↓
Phase 1:  code-signatures.json 的签名名称列表
        + repomix-compress.json 的文件内容
        → LLM 为每个签名生成 desc
                    ↓
Phase 4:  签名（含 desc）合并入 hippocampus-index.json
```

### 8.6 不支持的文件处理

| 情况 | 处理 |
|---|---|
| 无对应 .scm 查询的语言 | signatures 为空数组，Phase 1 仍生成文件 desc |
| 二进制文件 / 资源文件 | 跳过，不进入签名提取 |
| 空文件 | signatures 为空数组 |

## 9. 需要新增的工具 🚧

| 工具 | 功能 | 依赖 | 状态 |
|---|---|---|---|
| 结构树生成器 | 解析 directoryStructure + 行数聚合 → tree.json | repomix 输出 | ✅ 已实现 |
| 结构差异生成器 | 比对两份 tree.json → tree-diff.json | tree.json | ✅ 已实现 |
| 交互式可视化渲染器 | index + diff + report + history → hippocampus-viz.html | hippocampus-index.json | ❌ 未实现 |
| 结构提示词生成器 | 树摘要 + 变化摘要 → structure-prompt.md | tree.json | ✅ 已实现 |
| 动态裁剪器 | 按 token 预算裁剪 compress → trimmed.json | compress 输出 | ✅ 已实现 |
| 统一索引生成器 | 四阶段流水线（Phase 0-4）→ hippocampus-index.json | compress 输出 + tree-sitter | 🚧 部分实现 |
| 代码签名提取器 | tree-sitter 提取 → code-signatures.json | 源码 + .scm | ✅ 已实现 |

## 10. CI 流程（GitHub Actions）❌

触发条件：push（所有分支）、pull_request

步骤：
1. repomix 生成结构快照
2. repomix --compress 生成代码骨架
3. tree-sitter 提取代码签名
4. 生成 tree.json
5. 生成 tree-diff.json
6. 生成 hippocampus-index.json（四阶段流水线，增量模式）
7. 动态裁剪 compress 到目标 token 预算
8. 渲染 hippocampus-viz.html（读取 index + diff + report + history）
9. 生成 structure-prompt.md
10. 上传分支产物
11. main 产物发布到 gh-pages

## 11. 产物目录 🚧

两种存储场景：

- **本地开发**：产物存放在项目根目录的 `.hippocampus/` 下（见 Section 5.6），供本地 AI agent 直接读取
- **CI 构建**：产物存放在 `artifacts/structure/<branch>/` 下，作为构建产物上传；main 分支同步到 gh-pages

### 11.1 CI 产物（artifacts）

```
artifacts/structure/<branch>/
  repomix-structure.json
  repomix-compress.json
  repomix-compress-trimmed.json
  hippocampus-index.json
  module-vocab.json
  code-signatures.json
  tag-vocab.json
  tree.json
  tree-diff.json
  hippocampus-viz.html
  architecture-report.json
  architecture-history.jsonl
  structure-prompt.md

gh-pages/structure/main/latest/
  hippocampus-viz.html
  hippocampus-index.json
  tree.json
  tree-diff.json
  architecture-report.json
  architecture-history.jsonl
  structure-prompt.md
  repomix-compress-trimmed.json
  code-signatures.json
```

## 12. Repomix 参考 ✅

### 可输出内容
- 文件摘要、目录结构、文件内容、Git diff、Git 日志、说明指令

### 输出样式
xml / markdown / json / plain

### 常用参数
- `--style json|xml|markdown|plain`
- `--no-files`（仅元数据）
- `--compress`（tree-sitter 提取代码骨架）
- `--include-full-directory-structure`
- `--include / --ignore`（范围控制）
- `--split-output <size>`
- `--include-diffs / --include-logs`
- `--remove-comments / --remove-empty-lines / --truncate-base64`

## 13. 交互式可视化（hippocampus-viz.html）❌

替代原有的静态 tree.html，基于 ECharts 构建单文件交互式可视化，直接消费 hippocampus 现有数据产物，零额外数据生成。

### 13.1 数据源与消费关系

```
hippocampus-index.json ──→ 主视图（treemap / sunburst）
                           侧边栏（L0-L3 desc 钻取）
                           颜色映射（core_score / module）

tree-diff.json ──────────→ 变更叠加层（新增/修改/删除标记）

architecture-report.json → 问题标记层（insight 徽章）

architecture-history.jsonl → 底部趋势图（健康度曲线）
```

**关键设计原则：可视化不生成新数据，只渲染已有产物。**

四个 JSON 文件由流水线（Phase 0-4）生成，可视化只做读取和渲染。

### 13.2 整体布局

```
┌─ 工具栏 ──────────────────────────────────────────────────────────┐
│ [目录视图|模块视图]  [treemap|sunburst]  颜色:[行数|core|module]  │
│ 叠加:[□变更 □问题]   搜索:[________]                              │
├───────────────────────────────────────┬────────────────────────────┤
│                                       │ 面包屑: project > mod > file│
│                                       │                            │
│          主视图区域（70%）             │     侧边栏（30%）          │
│                                       │                            │
│   ECharts treemap / sunburst          │  ┌─ L0 项目全景 ─────────┐│
│                                       │  │ 多AI协作CLI工具集...   ││
│   点击色块 → 钻取下一层               │  └────────────────────────┘│
│   右键 → 展开到源码                   │  ┌─ L1 当前模块 ─────────┐│
│                                       │  │ provider-comm          ││
│                                       │  │ AI通信层，管理请求...  ││
│                                       │  │ 关键: daemon.py, ...   ││
│                                       │  └────────────────────────┘│
│                                       │  ┌─ L2 当前文件 ─────────┐│
│                                       │  │ daemon.py (320行)      ││
│                                       │  │ 邮件守护进程，定时...  ││
│                                       │  │ tags: daemon,mail      ││
│                                       │  └────────────────────────┘│
│                                       │  ┌─ L3 函数列表 ─────────┐│
│                                       │  │ → MailDaemon (class)   ││
│                                       │  │   管理轮询和分发       ││
│                                       │  │ → start (method)       ││
│                                       │  │   启动轮询守护循环     ││
│                                       │  │ → dispatch (method)    ││
│                                       │  │   按适配器分发消息     ││
│                                       │  └────────────────────────┘│
│                                       │  ┌─ ⚠ Insights ──────────┐│
│                                       │  │ [warn] 320行，建议拆分 ││
│                                       │  └────────────────────────┘│
├───────────────────────────────────────┴────────────────────────────┤
│  底部趋势条（可折叠）                                              │
│  ▁▂▃▄▅▆ insight总数   ▁▁▂▂▃▅ critical数   commit时间轴 →        │
└───────────────────────────────────────────────────────────────────┘
```

四个区域各自的数据源：

| 区域 | 数据源 | 渲染内容 |
|---|---|---|
| 主视图 | `index.root`（目录树）或 `index.modules`（模块树） | treemap / sunburst |
| 侧边栏 | `index.project` + 当前选中节点的 desc/tags/signatures | L0-L3 desc 钻取 |
| 叠加层 | `tree-diff.json` + `architecture-report.json` | 变更标记 + insight 徽章 |
| 趋势条 | `architecture-history.jsonl` | 健康度折线图 |

### 13.3 双视图模式：目录 vs 模块

hippocampus-index.json 同时包含**物理结构**（目录树 `root`）和**逻辑结构**（模块列表 `modules`）。可视化提供两种视图切换。

#### 目录视图（默认）

数据源：`index.root`，按 `dirs` / `files` 递归展开。

```
ECharts treemap 数据映射：
  index.root
    └─ dirs（递归）
         └─ files
              └─ value = file.lines（面积 = 代码行数）
```

```javascript
// index.root → ECharts treemap data
function dirToTreemap(dirNode) {
  const children = [];
  // 子目录
  for (const [name, sub] of Object.entries(dirNode.dirs || {})) {
    children.push(dirToTreemap(sub));
  }
  // 文件
  for (const f of dirNode.files || []) {
    children.push({
      name: f.name,
      value: f.lines,
      // 携带完整元数据，供侧边栏使用
      _meta: { id: f.id, desc: f.desc, tags: f.tags,
               module: f.module, lang: f.lang,
               signatures: f.signatures }
    });
  }
  return {
    name: dirNode.name,
    children,
    _meta: { id: dirNode.id, desc: dirNode.desc,
             tags: dirNode.tags, stats: dirNode.stats,
             core_score: dirNode.core_score }
  };
}
```

#### 模块视图

数据源：`index.modules` + 从 `index.root` 中按 `file.module` 重新分组。

```
ECharts treemap 数据映射：
  index.modules[]
    └─ 从 root 中筛选 file.module == module.id 的所有文件
         └─ value = file.lines
```

```javascript
// index.modules + index.root → 按模块分组的 treemap data
function modulesToTreemap(index) {
  const filesByModule = {};

  // 遍历目录树，按 module 字段分组
  function collectFiles(dirNode) {
    for (const f of dirNode.files || []) {
      const mid = f.module || '_unclassified';
      (filesByModule[mid] = filesByModule[mid] || []).push(f);
    }
    for (const sub of Object.values(dirNode.dirs || {})) {
      collectFiles(sub);
    }
  }
  collectFiles(index.root);

  // 每个模块 → treemap 节点
  return index.modules.map(mod => ({
    name: mod.id,
    children: (filesByModule[mod.id] || []).map(f => ({
      name: f.name,
      value: f.lines,
      _meta: { id: f.id, desc: f.desc, tags: f.tags,
               module: f.module, signatures: f.signatures }
    })),
    _meta: { id: mod.id, desc: mod.desc,
             file_count: mod.file_count, line_count: mod.line_count,
             key_files: mod.key_files }
  }));
}
```

#### 两种视图的对比

| 维度 | 目录视图 | 模块视图 |
|---|---|---|
| 分组依据 | 物理目录结构 `root.dirs` | 逻辑模块 `modules` + `file.module` |
| 层级深度 | 跟随目录嵌套（可能很深） | 固定两层（模块 → 文件） |
| 适合场景 | 了解文件物理位置 | 了解功能架构 |
| 扁平项目 | 只有一个大色块 | 仍能看到逻辑分组 |
| 颜色默认 | 按目录着色 | 按模块着色 |

### 13.4 颜色映射策略

工具栏提供颜色模式切换，每种模式从 hippocampus-index.json 的不同字段取值。

#### 模式 A：按模块着色（默认）

```
数据源：file._meta.module
映射：每个 module_id → 一个固定色相（HSL 色环均分）
效果：同模块文件同色，快速识别功能域分布
```

```javascript
function colorByModule(modules) {
  const hueStep = 360 / modules.length;
  const palette = {};
  modules.forEach((m, i) => {
    palette[m.id] = `hsl(${i * hueStep}, 65%, 55%)`;
  });
  return palette;
}
```

#### 模式 B：按代码行数着色（热力图）

```
数据源：file.lines
映射：行数 → 绿(少) → 黄(中) → 红(多)
效果：快速发现大文件（红色色块）
阈值：<200 绿 | 200-500 黄 | 500-1000 橙 | >1000 红
```

#### 模式 C：按 core_score 着色

```
数据源：dir.core_score（目录视图）或 file 所属 dir 的 core_score
映射：score → 深蓝(核心) → 浅灰(边缘)
效果：快速识别项目核心区域
```

#### 模式 D：按语言着色

```
数据源：file.lang
映射：python→蓝 | javascript→黄 | shell→绿 | yaml→灰 | ...
效果：了解技术栈分布
```

### 13.5 叠加层（Overlay）

工具栏的复选框控制两个独立叠加层，可同时开启。叠加层不改变色块颜色，而是在色块上添加**边框和徽章**。

#### 变更叠加层（数据源：tree-diff.json）

```
tree-diff.json 结构：
  { "added": [...], "modified": [...], "deleted": [...] }

映射到 treemap 色块：
  added    → 绿色虚线边框 + "+" 角标
  modified → 橙色实线边框 + "M" 角标
  deleted  → 红色叉号（独立浮层，因为文件已不在树中）
```

```javascript
function applyDiffOverlay(chart, diff) {
  const markData = [];
  for (const path of diff.added) {
    markData.push({ id: 'file:' + path, borderColor: '#4caf50',
                    borderWidth: 3, borderType: 'dashed', badge: '+' });
  }
  for (const path of diff.modified) {
    markData.push({ id: 'file:' + path, borderColor: '#ff9800',
                    borderWidth: 3, borderType: 'solid', badge: 'M' });
  }
  // 通过 ECharts rich text 或 markPoint 实现角标
  return markData;
}
```

#### 问题叠加层（数据源：architecture-report.json）

```
architecture-report.json 中每条 insight 有 scope 字段：
  scope = "file:lib/mail/daemon.py"  → 标记到对应文件色块
  scope = "mod:provider-comm"        → 标记到模块视图的模块色块
  scope = "project"                  → 标记到根节点

映射到 treemap 色块：
  critical → 红色脉冲动画边框 + "!" 徽章
  warn     → 黄色实线边框 + "⚠" 徽章
  info     → 不显示（仅在侧边栏中列出）
```

```javascript
function applyInsightOverlay(chart, report) {
  const markData = [];
  for (const insight of report.insights) {
    if (insight.severity === 'info') continue;  // info 不叠加
    markData.push({
      id: insight.scope,
      borderColor: insight.severity === 'critical' ? '#f44336' : '#ffc107',
      borderWidth: insight.severity === 'critical' ? 4 : 2,
      badge: insight.severity === 'critical' ? '!' : '⚠',
      tooltip: insight.msg
    });
  }
  return markData;
}
```

### 13.6 侧边栏联动（L0-L3 desc 钻取）

侧边栏是 desc 的核心呈现区域。根据主视图中用户点击的节点类型，自动渲染对应层级的描述信息。

#### 点击事件 → 侧边栏内容映射

| 用户点击 | 侧边栏显示 | 数据来源 |
|---|---|---|
| 空白区域 / 根节点 | L0 项目全景 | `index.project.overview` |
| 目录色块（目录视图） | L0 + 该目录 desc | `dirNode.desc` + `dirNode.stats` |
| 模块色块（模块视图） | L0 + L1 模块描述 | `modules[].desc` + `key_files` |
| 文件色块 | L0 + L1 + L2 文件描述 | `fileNode.desc` + `tags` + `module` |
| 文件色块双击 | L0 + L1 + L2 + L3 签名列表 | `fileNode.signatures[]` |

#### 侧边栏渲染逻辑

侧边栏始终保持**面包屑导航**，从 L0 到当前选中层级逐级展示，上层 desc 折叠为单行摘要。

```javascript
function renderPanel(node, index, report) {
  const panel = document.getElementById('panel');
  let html = '';

  // L0 始终显示（折叠为单行）
  html += `<div class="level l0">
    <h4>📦 ${index.project.scale.files} 文件 | ${index.stats.total_modules} 模块</h4>
    <p class="collapsed">${index.project.overview}</p>
  </div>`;

  // L1 模块（如果能确定）
  const mod = node._meta.module
    ? index.modules.find(m => m.id === node._meta.module)
    : null;
  if (mod) {
    html += `<div class="level l1">
      <h4>📂 ${mod.id}（${mod.file_count} 文件）</h4>
      <p>${mod.desc}</p>
      <small>关键: ${mod.key_files.join(', ')}</small>
    </div>`;
  }

  // L2 文件（如果选中的是文件）
  if (node._meta.id?.startsWith('file:')) {
    html += `<div class="level l2">
      <h4>📄 ${node.name}（${node._meta.lines || node.value} 行）</h4>
      <p>${node._meta.desc}</p>
      <div class="tags">${(node._meta.tags||[])
        .map(t => '<span class="tag">' + t + '</span>').join(' ')}</div>
    </div>`;

    // L3 签名列表
    if (node._meta.signatures?.length) {
      html += `<div class="level l3"><h4>⚙ 签名</h4><ul>`;
      for (const sig of node._meta.signatures) {
        html += `<li><code>${sig.name}</code>
          <span class="kind">${sig.kind}</span>
          <span class="sig-desc">${sig.desc}</span></li>`;
      }
      html += '</ul></div>';
    }
  }

  // Insights（筛选当前 scope）
  const scopeId = node._meta.id;
  const relevant = (report?.insights || [])
    .filter(i => i.scope === scopeId || i.scope === 'project');
  if (relevant.length) {
    html += `<div class="level insights"><h4>⚠ 问题</h4><ul>`;
    for (const i of relevant) {
      html += `<li class="${i.severity}">[${i.severity}] ${i.msg}</li>`;
    }
    html += '</ul></div>';
  }

  panel.innerHTML = html;
}
```

### 13.7 底部趋势条

可折叠区域，数据源为 `architecture-history.jsonl`，展示项目健康度随时间的变化。

#### 数据加载

```javascript
// jsonl → 数组
async function loadHistory(url) {
  const text = await fetch(url).then(r => r.text());
  return text.trim().split('\n').map(JSON.parse);
}
```

#### 图表配置

使用 ECharts 折线图，X 轴为 commit 时间，双 Y 轴：

```
左 Y 轴：insight 总数（柱状图，按 severity 堆叠）
右 Y 轴：文件总数（折线，反映项目规模增长）
X 轴：  commit 时间戳
```

```javascript
function renderTrend(history) {
  const trendChart = echarts.init(document.getElementById('trend'));
  trendChart.setOption({
    tooltip: { trigger: 'axis' },
    legend: { data: ['critical', 'warn', 'info', '文件数'] },
    xAxis: { type: 'category',
             data: history.map(h => h.ts.slice(0, 10)) },
    yAxis: [
      { type: 'value', name: 'Insights' },
      { type: 'value', name: '文件数' }
    ],
    series: [
      { name: 'critical', type: 'bar', stack: 'insights',
        data: history.map(h => h.critical),
        itemStyle: { color: '#f44336' } },
      { name: 'warn', type: 'bar', stack: 'insights',
        data: history.map(h => h.warn),
        itemStyle: { color: '#ffc107' } },
      { name: 'info', type: 'bar', stack: 'insights',
        data: history.map(h => h.info),
        itemStyle: { color: '#90caf9' } },
      { name: '文件数', type: 'line', yAxisIndex: 1,
        data: history.map(h => h.files || 0),
        itemStyle: { color: '#666' } }
    ]
  });
}
```

### 13.8 技术实现汇总

#### 文件结构

```
hippocampus-viz.html          ← 单文件，可直接浏览器打开
  内嵌：
    ECharts CDN（~1MB gzip 后 ~300KB）
    JS 逻辑（~400 行）
    CSS 样式（~100 行）
  读取（同目录）：
    hippocampus-index.json
    tree-diff.json
    architecture-report.json
    architecture-history.jsonl
```

#### 依赖关系

```
hippocampus-viz.html
  ├─ 必须：hippocampus-index.json（主视图 + 侧边栏）
  ├─ 可选：tree-diff.json（变更叠加层，无则隐藏按钮）
  ├─ 可选：architecture-report.json（问题叠加层，无则隐藏按钮）
  └─ 可选：architecture-history.jsonl（趋势条，无则隐藏区域）
```

只有 `hippocampus-index.json` 是必须的，其余三个文件缺失时对应功能自动降级隐藏。