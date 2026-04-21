# math.AP 历史数据处理脚本

用于从 Kaggle 下载的 arXiv metadata 中提取 math.AP 分类的论文，并进行 AI 增强处理。

## 文件说明

| 文件 | 说明 |
|------|------|
| `extract_historical_data.py` | 从历史 metadata 中提取指定分类的论文，按日期生成 JSONL 文件 |
| `batch_ai_enhance.py` | 批量对 JSONL 文件进行 AI 增强处理，支持断点续传 |
| `run_historical_pipeline.sh` | 统一入口脚本，整合提取和 AI 增强流程 |

## 快速开始

### 1. 准备数据

确保 Kaggle 下载的 metadata 文件放在正确位置：

```
arxiv_history_metadata/
└── arxiv-metadata-oai-snapshot.json
```

### 2. 环境变量设置

```bash
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # 可选
export LANGUAGE="Chinese"                           # 可选，默认 Chinese
export MAX_WORKERS="4"                              # 可选，默认 4
```

### 3. 运行处理流程

#### 完整流程（推荐）

```bash
./scripts/run_historical_pipeline.sh all
```

#### 分步执行

```bash
# 步骤 1: 提取历史数据
./scripts/run_historical_pipeline.sh extract

# 步骤 2: AI 增强处理
./scripts/run_historical_pipeline.sh enhance
```

#### 查看统计信息

```bash
./scripts/run_historical_pipeline.sh stats
```

## 详细说明

### 数据提取 (`extract_historical_data.py`)

**功能**：
- 读取 `arxiv_history_metadata/arxiv-metadata-oai-snapshot.json`
- 筛选 `math.AP` 分类的论文
- 按 `update_date` 字段分组
- 生成每日的 JSONL 文件到 `data/` 目录

**参数**：

```bash
python scripts/extract_historical_data.py \
    --input arxiv_history_metadata/arxiv-metadata-oai-snapshot.json \
    --output data/ \
    --categories math.AP \
    --start-date 2007-01-01 \
    --end-date 2025-12-31 \
    --force
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--input` | 输入的 metadata JSON 文件 | `arxiv_history_metadata/arxiv-metadata-oai-snapshot.json` |
| `--output` | 输出的 JSONL 文件目录 | `data/` |
| `--categories` | 要提取的分类列表 | `math.AP` |
| `--start-date` | 开始日期 (YYYY-MM-DD) | 无限制 |
| `--end-date` | 结束日期 (YYYY-MM-DD) | 无限制 |
| `--force` | 强制重新生成已存在的文件 | False |

**增量模式**：
- 如果 `data/{date}.jsonl` 已存在，则跳过该日期
- 使用 `--force` 可强制重新生成

### 批量 AI 增强 (`batch_ai_enhance.py`)

**功能**：
- 扫描 `data/` 目录下未进行 AI 增强的 JSONL 文件
- 调用 `ai/enhance.py` 进行批量处理
- 支持断点续传（记录处理进度到 `scripts/.enhance_progress.json`）

**参数**：

```bash
python scripts/batch_ai_enhance.py \
    --data-dir data/ \
    --max-workers 4 \
    --language Chinese
```

| 参数 | 说明 | 默认值 |
|------|------|--------|
| `--data-dir` | 数据目录路径 | `data/` |
| `--max-workers` | 并发处理数 | 4 |
| `--language` | 输出语言 | Chinese |
| `--dry-run` | 只显示将要处理的文件 | False |
| `--reset-progress` | 重置处理进度 | False |
| `--stats` | 显示统计信息 | False |

**断点续传**：
- 进度保存在 `scripts/.enhance_progress.json`
- 中断后重新运行会自动跳过已处理的文件
- 使用 `--reset-progress` 可重置进度

## 处理时间预估

基于约 56,596 篇 math.AP 论文：

| 步骤 | 时间预估 | 说明 |
|------|---------|------|
| 数据提取 | 5-10 分钟 | 遍历 5GB JSON 文件 |
| AI 增强 | 8-16 小时 | 单线程，约 0.5-1 秒/篇 |
| AI 增强 (4并发) | 2-4 小时 | 推荐配置 |
| AI 增强 (8并发) | 1-2 小时 | 需要更高的 API 限制 |

## 存储空间预估

| 类型 | 大小 |
|------|------|
| 原始 JSONL | ~200-300 MB |
| AI 增强后 | ~1-1.5 GB |
| **总计** | **~1.5-2 GB** |

## 数据格式

### 输入（历史数据）

```json
{
  "id": "0704.0125",
  "title": "Anisotropic thermo-elasticity in 2D...",
  "authors": "Michael Reissig and Jens Wirth",
  "categories": "math.AP",
  "abstract": "In this note we develop tools...",
  "update_date": "2008-04-10",
  "comments": "22 pages;"
}
```

### 输出（项目格式）

```json
{
  "id": "0704.0125",
  "pdf": "https://arxiv.org/pdf/0704.0125",
  "abs": "https://arxiv.org/abs/0704.0125",
  "authors": ["Michael Reissig", "Jens Wirth"],
  "title": "Anisotropic thermo-elasticity in 2D...",
  "categories": ["math.AP"],
  "comment": "22 pages;",
  "summary": "In this note we develop tools..."
}
```

### AI 增强后

```json
{
  "id": "0704.0125",
  "pdf": "https://arxiv.org/pdf/0704.0125",
  "abs": "https://arxiv.org/abs/0704.0125",
  "authors": ["Michael Reissig", "Jens Wirth"],
  "title": "Anisotropic thermo-elasticity in 2D...",
  "categories": ["math.AP"],
  "comment": "22 pages;",
  "summary": "In this note we develop tools...",
  "AI": {
    "tldr": "一句话总结",
    "motivation": "研究背景和动机",
    "techniques": "数学技术和证明方法",
    "main_theorems": "主要定理和结果",
    "significance": "理论意义和应用"
  }
}
```

## 常见问题

### Q: 可以处理其他数学分类吗？

可以，修改 `--categories` 参数：

```bash
./scripts/run_historical_pipeline.sh extract --categories math.AP math.DG math.FA
```

### Q: 如何只处理特定日期范围？

```bash
python scripts/extract_historical_data.py \
    --start-date 2020-01-01 \
    --end-date 2024-12-31
```

### Q: AI 增强中断了怎么办？

重新运行相同的命令即可，会自动跳过已处理的文件：

```bash
./scripts/run_historical_pipeline.sh enhance
```

### Q: 如何强制重新 AI 增强？

```bash
# 重置进度
./scripts/run_historical_pipeline.sh clean

# 重新处理
./scripts/run_historical_pipeline.sh enhance
```

### Q: API 调用费用预估？

- 约 56,596 篇论文
- 假设每篇约 500 tokens 输入，300 tokens 输出
- DeepSeek 价格约 0.001-0.002 元/千 tokens
- **预估总费用：约 50-100 元**

## 注意事项

1. **API 限制**：大量 API 调用可能触发速率限制，建议适当调整 `MAX_WORKERS`
2. **存储空间**：确保有足够的磁盘空间（约 2GB）
3. **网络稳定性**：AI 增强过程需要稳定的网络连接
4. **中断恢复**：处理过程中可以随时中断，进度会自动保存
