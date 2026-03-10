# Aider RepoMap Integration

## Overview

Hippocampus 集成了 Aider 的 RepoMap 符号级别分析功能，提供更精确的文件排序能力。

## 安装

### 基础安装（不含符号分析）

```bash
pip install -e .
```

### 完整安装（含符号分析）

```bash
pip install -e ".[repomap]"
```

这将安装以下额外依赖：
- `tree-sitter>=0.25.2`
- `tree-sitter-language-pack>=0.13.0`
- `diskcache>=5.6.0`
- `pygments>=2.17.0`

## 使用方法

### 1. 使用 Symbol Ranking 进行 Trim

```bash
# 使用符号级别排序（实验性）
hippo trim --ranking symbol --budget 10000

# 默认使用 graph 排序（推荐）
hippo trim --ranking graph --budget 10000

# 使用启发式排序（最快）
hippo trim --ranking heuristic --budget 10000
```

### 2. 调试命令：查看符号排序

```bash
# 查看单个文件的符号排序
hippo repomap --files src/hippocampus/cli.py --limit 20

# 查看多个文件的符号排序
hippo repomap --files src/hippocampus/cli.py --files src/hippocampus/tools/ranker.py
```

输出示例：
```
Symbol ranking for 1 file(s):
Rank   File                          Line   Symbol              Kind
------------------------------------------------------------------------
1      src/hippocampus/cli.py        138    count_nodes         def
2      src/hippocampus/cli.py        318    run                 def
3      src/hippocampus/cli.py        19     _resolve_paths      def
...
```

## 架构说明

### 组件结构

```
src/hippocampus/tools/
├── repomap_adapter.py      # Aider RepoMap 适配器
├── tree_sitter_compat.py   # tree-sitter API 兼容性补丁
└── ranker.py               # SymbolRanker 实现
```

### SymbolRanker 工作原理

1. **符号提取**: 使用 Aider RepoMap 提取代码符号（函数、类等）
2. **PageRank 排序**: 基于符号引用关系构建依赖图并排序
3. **评分聚合**: 使用指数衰减将符号分数聚合到文件级别
4. **混合策略**: 60% 符号分析 + 40% 启发式，平衡准确性和鲁棒性

### 优雅降级

如果 RepoMap 依赖不可用或运行时出错，SymbolRanker 会自动降级到 GraphRanker：

```python
# 自动降级示例
$ hippo trim --ranking symbol
Warning: SymbolRanker dependencies not available, falling back to GraphRanker
  Install with: pip install -e '.[repomap]'
```

## 性能特点

### 缓存机制

Aider RepoMap 使用 diskcache 缓存符号提取结果：
- 首次扫描较慢（大型仓库可能需要几分钟）
- 后续运行非常快（缓存命中）
- 缓存位置：`.aider.tags.cache.v4/`

### 性能对比

| 排序方法 | 首次运行 | 缓存命中 | 准确性 | 稳定性 |
|---------|---------|---------|--------|--------|
| heuristic | 极快 | 极快 | 中等 | 高 |
| graph | 快 | 快 | 高 | 高 |
| symbol | 慢 | 快 | 最高 | 实验性 |

## 限制和注意事项

### 实验性功能

SymbolRanker 目前是**实验性功能**，原因：
1. 依赖 tree-sitter 生态系统，API 变化频繁
2. 需要额外的依赖安装
3. 首次运行较慢

### 已知问题

1. **tree-sitter API 兼容性**
   - 通过兼容性补丁解决
   - 如遇问题，请使用 GraphRanker（默认）

2. **语言支持**
   - 依赖 tree-sitter-language-pack 支持的语言
   - Python, JavaScript, TypeScript, Go, Rust 等主流语言支持良好

## 故障排除

### 问题：SymbolRanker 不可用

```bash
# 检查依赖
python3 -c "from hippocampus.tools.repomap_adapter import check_repomap_available; print(check_repomap_available())"

# 重新安装依赖
pip install -e ".[repomap]" --force-reinstall
```

### 问题：符号提取失败

```bash
# 使用 verbose 模式查看详细信息
hippo trim --ranking symbol --budget 10000 --verbose

# 清除缓存重试
rm -rf .aider.tags.cache.v4/
```

## 技术细节

### tree-sitter 兼容性补丁

由于 tree-sitter 0.25.x 移除了 `Query.captures()` 方法，我们实现了兼容性补丁：

```python
# tree_sitter_compat.py
class QueryWrapper:
    def captures(self, node):
        # 使用新的 QueryCursor API
        cursor = tree_sitter.QueryCursor(self._query)
        matches = cursor.matches(node)
        # 转换为旧 API 格式
        return aggregate_captures(matches)
```

### 路径处理契约

- `chat_files` / `other_files`: 接受相对路径，内部转换为绝对路径
- `mentioned_files`: 接受相对路径，保持相对路径（Aider 内部使用）
- `mentioned_idents`: 符号名称，直接传递

## 未来改进

1. **性能优化**: 增量更新缓存
2. **更多语言支持**: 扩展 tree-sitter 语言包
3. **深度集成**: 与 Hippocampus 索引系统深度集成
4. **稳定性提升**: 等待 tree-sitter 生态系统稳定

## 参考资料

- [Aider RepoMap 文档](https://aider.chat/docs/repomap.html)
- [tree-sitter 文档](https://tree-sitter.github.io/tree-sitter/)
- [Hippocampus GraphRanker 评审](plans/rippling-cuddling-crystal.md)
