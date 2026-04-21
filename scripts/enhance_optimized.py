#!/usr/bin/env python3
"""
优化版翻译脚本 - 降低成本
策略：不使用 Function Calling，直接请求 JSON 输出
"""

import os
import json
import sys
from pathlib import Path

# 简单示例：不使用 LangChain，直接调用 API
# 这样避免了 Function Calling 的 Schema 开销

OPTIMIZED_PROMPT = """你是一位数学论文分析专家。请分析以下论文，用中文输出 JSON 格式：

标题: {title}
摘要: {summary}

请输出以下格式的 JSON：
{{
  "tldr": "一句话核心贡献",
  "motivation": "研究背景",
  "techniques": "数学技术",
  "main_theorems": "主要定理", 
  "significance": "理论意义"
}}

只输出 JSON，不要有其他内容。"""

# 预计可节省 30-40% 的 tokens
# 因为避免了 Function Calling 的 schema 开销
print("优化方案：")
print("1. 不使用 LangChain with_structured_output")
print("2. 直接调用 API，手动解析 JSON")
print("3. 预计单篇消耗从 4000 tokens 降至 2500 tokens")
print("4. 全量成本从 ¥171 降至 ¥107 (节省 ¥64)")
