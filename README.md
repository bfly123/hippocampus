# Hippocampus

[English](#english) | [中文](#中文)

---

## 中文

这是个代码库架构图软件，可以生成代码地图（项目提示词）和代码导航（智能获取相关代码片段），以及更多功能，例如可视化等，供用户自己研究。

## 核心功能

- **代码地图生成**：自动分析代码库结构，生成项目提示词（structure prompt）
- **智能索引**：构建可搜索的代码索引，支持快速导航和代码片段检索
- **增量更新**：基于文件变更的智能缓存，只处理修改部分
- **可视化**：生成交互式 HTML 架构可视化
- **架构度量**：集成 `architec` 工具，输出架构质量评分

## 安装

```bash
./install.sh
```

或手动安装：

```bash
python -m pip install -e ".[dev,repomap,llm]"
```

## 快速开始

```bash
# 分析当前目录
hippo .

# 分析指定仓库
hippo /path/to/repo

# 增量更新
hippo update

# 强制全量刷新
hippo refresh .

# 查看输出概览
hippo overview
```

## 输出文件

运行后在 `.hippocampus/` 目录生成：

- `hippocampus-index.json` - 完整代码索引
- `structure-prompt.md` - 项目结构提示词
- `structure-prompt-map.md` - 地图视图
- `structure-prompt-deep.md` - 深度视图
- `hippocampus-viz.html` - 可视化页面
- `architect-metrics.json` - 架构度量（需安装 `architec`）

## LLM 配置

配置文件位置：

- `~/.llmgateway/config.yaml` - LLM 提供商、API 密钥、并发设置
- `~/.hippocampus/config.yaml` - Hippo 阶段到模型层级的映射

最小配置示例：

```yaml
# ~/.llmgateway/config.yaml
version: 1
settings:
  strong_model: gpt-4
  weak_model: gpt-3.5-turbo
  max_concurrent: 30
provider:
  provider_type: openai
  api_key: sk-...
```

```yaml
# ~/.hippocampus/config.yaml
version: 1
tasks:
  phase_1:
    tier: weak
  phase_2a:
    tier: strong
  phase_3b:
    tier: strong
```

## Python API

```python
from hippocampus import build_tree, extract_signatures, generate_structure_prompt

extract_signatures("/path/to/repo")
build_tree("/path/to/repo")
generate_structure_prompt("/path/to/repo", profile="map")
```

## 开发

```bash
python -m pip install -e ".[dev,repomap,llm]"
pytest -q
```

## License

MIT License. See [LICENSE](LICENSE).

---

## English

A codebase architecture mapping tool that generates code maps (structure prompts) and intelligent code navigation (smart code snippet retrieval), plus additional features like visualization for users to explore.

### Core Features

- **Code Map Generation**: Automatically analyze codebase structure and generate structure prompts
- **Smart Indexing**: Build searchable code index for fast navigation and snippet retrieval
- **Incremental Updates**: Intelligent caching based on file changes, only processes modified parts
- **Visualization**: Generate interactive HTML architecture visualization
- **Architecture Metrics**: Integrate with `architec` tool for architecture quality scoring

### Installation

```bash
./install.sh
```

Or manual installation:

```bash
python -m pip install -e ".[dev,repomap,llm]"
```

### Quick Start

```bash
# Analyze current directory
hippo .

# Analyze specific repository
hippo /path/to/repo

# Incremental update
hippo update

# Force full refresh
hippo refresh .

# View output overview
hippo overview
```

### Output Files

After running, files are generated in `.hippocampus/` directory:

- `hippocampus-index.json` - Complete code index
- `structure-prompt.md` - Project structure prompt
- `structure-prompt-map.md` - Map view
- `structure-prompt-deep.md` - Deep view
- `hippocampus-viz.html` - Visualization page
- `architect-metrics.json` - Architecture metrics (requires `architec`)

### LLM Configuration

Configuration file locations:

- `~/.llmgateway/config.yaml` - LLM provider, API key, concurrency settings
- `~/.hippocampus/config.yaml` - Hippo phase-to-tier mapping

Minimal configuration example:

```yaml
# ~/.llmgateway/config.yaml
version: 1
settings:
  strong_model: gpt-4
  weak_model: gpt-3.5-turbo
  max_concurrent: 30
provider:
  provider_type: openai
  api_key: sk-...
```

```yaml
# ~/.hippocampus/config.yaml
version: 1
tasks:
  phase_1:
    tier: weak
  phase_2a:
    tier: strong
  phase_3b:
    tier: strong
```

### Python API

```python
from hippocampus import build_tree, extract_signatures, generate_structure_prompt

extract_signatures("/path/to/repo")
build_tree("/path/to/repo")
generate_structure_prompt("/path/to/repo", profile="map")
```

### Development

```bash
python -m pip install -e ".[dev,repomap,llm]"
pytest -q
```

### License

MIT License. See [LICENSE](LICENSE).
