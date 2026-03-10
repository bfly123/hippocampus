# The "Hippocampus" Code Intelligence System: A Blueprint
## 基于 Repomix (LTM) 和 Aider-Logic (WM) 的代码库记忆与进化系统

### 1. 核心理念 (Core Philosophy)

该系统模仿人类开发者的认知模式，旨在解决 AI 在处理大型代码库时面临的 "上下文窗口限制" 和 "全局架构认知缺失" 问题。

*   **长期记忆 (Long-Term Memory, LTM):** 负责项目的“世界观”。对项目历史、整体架构、设计原则的宏观认知。由 **Repomix** 生成的快照和向量数据库驱动。
*   **工作记忆 (Working Memory, WM):** 负责项目的“工作台”。对当前正在编辑的文件、函数调用关系的微观、高精度认知。由 **Tree-sitter** 实时解析和 **PageRank** 算法驱动。

### 2. 系统架构 (System Architecture)

```mermaid
graph TD
    User[User / Developer] -->|Request| Agent[AI Agent (Hippocampus)]
    
    subgraph "Long-Term Memory (LTM) - The Library"
        Repomix[Repomix Tool]
        Snapshot[Project Snapshot (XML)]
        VectorDB[Vector Database (Chroma/FAISS)]
        ArchDocs[Architecture Docs (ADR/MAP)]
        
        Repomix -->|Compress & Pack| Snapshot
        Snapshot -->|Chunking| VectorDB
        VectorDB -->|Retrieval| Agent
        ArchDocs -->|Retrieval| Agent
    end
    
    subgraph "Working Memory (WM) - The Workbench"
        TreeSitter[Tree-sitter Parser]
        PageRank[PageRank Algorithm]
        RepoMap[Dynamic Repo Map]
        CurrentFiles[Active File Context]
        
        TreeSitter -->|Parse & Link| PageRank
        PageRank -->|Rank Symbols| RepoMap
        RepoMap -->|Inject| Agent
        CurrentFiles -->|Inject| Agent
    end
    
    Agent -->|Code Changes| Codebase[Source Code]
    Codebase -->|Trigger Update| Repomix
```

### 3. 功能模块详解 (Modules)

#### 3.1 长期记忆层 (LTM Layer) - "架构师视角"
**目标:** 维护项目的“世界观”，回答“去哪改”、“为什么这么设计”的问题。

*   **组件 A: 全量骨架快照 (Skeleton Snapshot)**
    *   **核心工具:** `repomix` (配置为 `--compress` 模式)
    *   **产物:** `.hippocampus/snapshot.xml` (包含项目所有文件的类/函数签名树，移除实现细节)。
    *   **机制:** 每次 Git Commit/Merge 后触发更新。
    *   **用途:** 提供代码库的全景地图，支持架构 Diff 分析。

*   **组件 B: 语义索引 (Semantic Index)**
    *   **核心工具:** `LlamaIndex` / `ChromaDB`
    *   **数据源:** 
        1.  `snapshot.xml` 的切片。
        2.  `docs/` 目录下的所有文档。
        3.  `ARCH.md` (架构决策记录)。
    *   **用途:** 支持自然语言的模糊查询 (e.g., "如何新增一个 API 接口？")。

*   **组件 C: 演进可视化 (Evolution Visualization)**
    *   **核心工具:** `Gource` (视频化) 或 `D3.js` (Web 交互式)。
    *   **数据源:** Git Log + Repomix Snapshots。
    *   **用途:** 生成项目成长的动态视频或交互式树图，直观展示模块的膨胀、枯萎和重构过程。

#### 3.2 工作记忆层 (WM Layer) - "工程师视角"
**目标:** 维护当前的“手术台”，回答“这个变量是什么类型”、“调用这个函数需要传什么参数”的问题。

*   **组件 A: 动态代码地图 (Dynamic Repo Map)**
    *   **核心工具:** 自定义脚本 (基于 `tree-sitter` + `networkx`)。
    *   **算法逻辑:**
        1.  **Scan:** 提取所有文件的 Symbol (Def & Ref)。
        2.  **Graph:** 建立 `File A -> calls -> File B` 的引用图。
        3.  **Rank:** 运行 PageRank 计算文件重要性。
        4.  **Focus:** 结合用户 Prompt 关键词，动态调整权重。
        5.  **Trim:** 根据 Token 预算，生成精简的代码地图。
    *   **用途:** 作为 System Prompt 的一部分，常驻对话上下文。

*   **组件 B: 焦点上下文 (Focus Context)**
    *   **内容:** 用户明确指定或 AI 决定修改的文件的**完整源代码**。
    *   **用途:** 供 AI 进行精确的代码编辑和补全。

### 4. 标准工作流 (The Workflow)

**场景示例:** "将 User 模块的数据存储从 SQLite 迁移到 PostgreSQL"

1.  **意图分析 (Intent Analysis):**
    *   AI 识别到这是一个涉及数据层和领域模型的重构任务。

2.  **LTM 检索 (Retrieval):**
    *   AI Query: "User module location", "Database config location".
    *   LTM Return: `src/domain/user.ts`, `src/infra/db/config.ts`.

3.  **WM 构建 (Context Loading):**
    *   AI 锁定修改目标。
    *   WM 生成 Repo Map: 包含 `config.ts` (全量), `user.ts` (全量), 以及被高度引用的 `typeorm` 驱动的签名 (骨架)。

4.  **执行 (Execution):**
    *   AI 生成代码修改。
    *   Agent 调用工具应用修改并运行测试。

5.  **记忆固化 (Consolidation):**
    *   任务完成，Repomix 更新快照。
    *   AI 自动生成一条 Architecture Decision Record (ADR): "Migrated to PostgreSQL".

### 5. 工具链清单 (Toolchain)

*   **Analysis:** `repomix` (Node.js) - 生成 LTM 快照。
*   **Parsing:** `tree-sitter` (Python bindings) - WM 实时分析。
*   **Vector DB:** `chromadb` (Python) - LTM 检索。
*   **Graph Algo:** `networkx` (Python) - PageRank 计算。

### 6. 现状分析与发展路线 (Roadmap)

#### 6.1 我们已有的 (Existing Capabilities)
基于当前的 `claude_codex` 项目：
*   **基础通信架构 (`askd`):** 已经有一套成熟的 Daemon-Client 架构，支持多 AI Provider (Gemini, Claude, Codex) 的统一调用。
*   **基础上下文管理 (`lib/memory`):**
    *   `ContextTransfer`: 能够提取聊天记录和 Tool 调用统计。
    *   `ClaudeSessionParser`: 能解析 Claude 的会话文件。
    *   `formatter.py`: 能将上下文格式化为 Markdown/JSON。
*   **CLI 工具链 (`bin/ccb-*`):** 已经有 `ask`, `ping`, `transfer` 等基础命令。
*   **简易骨架 (Prototype):** 刚才实现的基于 `ast` 的 `skeleton.py` (原型)。

#### 6.2 我们需要发展的 (To Be Developed)
为了实现 Hippocampus 架构，我们需要填补以下空白：

*   **长期记忆组件 (LTM):**
    *   **集成 Repomix:** 需要引入 `repomix` 工具，并编写 `ccb arch snapshot` 命令来生成 XML 快照。
    *   **架构文档自动维护:** 编写 Agent Skill，用于对比 Repomix 快照并自动更新 `ARCH.md`。
    *   **向量库集成:** 引入 `chromadb` 或 `llama-index`，对快照和文档建立语义索引。

*   **工作记忆组件 (WM):**
    *   **Tree-sitter 集成:** 引入 `tree-sitter` Python 库，替代简单的 `ast` 模块，以支持多语言解析。
    *   **Repo Map 算法:** 实现类似 Aider 的 PageRank 算法，计算文件引用权重。
    *   **动态剪裁逻辑:** 实现根据 Token 预算动态生成 System Prompt 的逻辑。

*   **闭环工作流:**
    *   实现 `ccb-merge` (知识融合脚本)。
    *   实现 Git Hook 或 Cron Job，将 "代码变更" 与 "记忆更新" 自动挂钩。
    *   **可视化引擎:** 集成 `Gource` 或编写 D3.js 脚本，将 Git Log 和 Repomix 数据转化为可视化的架构演进图。

#### 6.3 最终实现的功能 (Final Capabilities)
当路线图完成后，我们将拥有：

1.  **全知全能的咨询师:**
    *   你可以问: "项目里负责鉴权的逻辑在哪？历史上改动过几次？"
    *   AI 基于 LTM 瞬间回答，无需手动 grep。

2.  **极高精度的 Coding Agent:**
    *   你可以说: "给 Login 增加验证码功能。"
    *   AI 基于 WM 自动提取 `auth.py`, `db.py`, `ui.js` 的精确上下文，一次性写对代码，不会瞎编函数名。

3.  **自我进化的文档:**
    *   你只管写代码。
    *   系统自动维护 `ARCH.md` 和 `MAP.md`，新人入职直接看文档，永远是最新的。

4.  **低成本运行:**
    *   通过 Repomix 压缩和 Repo Map 剪裁，大幅减少 Token 消耗，用更便宜的模型也能干大活。

5.  **架构时光机 (Architecture Time Machine):**
    *   提供一个 Web 界面或视频，让你可视化地看到："上个月 Authentication 模块还是一个小文件，怎么这个月变成了一坨大泥球？"
    *   帮助 Tech Lead 及时发现架构腐烂的苗头。
