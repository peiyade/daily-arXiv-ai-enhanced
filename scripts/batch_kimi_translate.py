#!/usr/bin/env python3
"""
使用 kimi-cli 批量翻译论文
策略：分批处理，每批 N 篇论文，减少 kimi-cli 启动开销
"""

import json
import subprocess
import os
from pathlib import Path
from typing import List, Dict
import sys

DATA_DIR = Path("data")
BATCH_SIZE = 3  # 每批处理的论文数量（减少以避免超时）

def call_kimi_translate(papers_batch: List[Dict]) -> List[Dict]:
    """
    调用 kimi-cli 翻译一批论文
    """
    num_papers = len(papers_batch)
    
    # 构建论文列表文本
    papers_text = ""
    for i, paper in enumerate(papers_batch):
        papers_text += f"\n--- 论文 {i} ---\n"
        papers_text += f"Title: {paper['title']}\n"
        papers_text += f"Abstract: {paper['summary']}\n"
    
    # 构建完整提示词
    prompt = f"""你是一位专业的数学论文翻译专家。请将以下 {num_papers} 篇数学论文的标题和摘要翻译成中文，并为每篇论文提供结构化分析。

要求：
1. 标题翻译要准确、学术化
2. 摘要翻译要流畅，保留数学符号（用 $...$ 包裹）
3. 对每篇论文提供以下结构化信息：
   - tldr: 一句话核心贡献（中文）
   - motivation: 研究背景和动机（中文）
   - techniques: 主要数学技术/方法（中文）
   - main_theorems: 主要定理/结果（中文）
   - significance: 理论意义和影响（中文）

请按以下 JSON 格式返回（只返回 JSON，不要有其他内容）：
[{{"index": 0, "title_zh": "中文标题", "summary_zh": "中文摘要", "tldr": "一句话总结", "motivation": "研究背景...", "techniques": "数学技术...", "main_theorems": "主要定理...", "significance": "意义..."}}]

以下是论文列表：
{papers_text}"""
    
    # 调用 kimi-cli
    cmd = ["kimi-cli", "--quiet", "-p", prompt]
    
    try:
        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300  # 5分钟超时
        )
        
        if result.returncode != 0:
            print(f"Error: {result.stderr}", file=sys.stderr)
            return None
        
        # 解析返回的 JSON
        output = result.stdout.strip()
        print(f"  Raw output length: {len(output)}")
        print(f"  Output preview: {output[:200]}...")
        
        # 提取 JSON 部分（去除可能的 markdown 代码块）
        if "```json" in output:
            output = output.split("```json")[1].split("```")[0].strip()
        elif "```" in output:
            output = output.split("```")[1].split("```")[0].strip()
        
        translations = json.loads(output)
        return translations
        
    except subprocess.TimeoutExpired:
        print("Timeout waiting for kimi-cli", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error calling kimi-cli: {e}", file=sys.stderr)
        return None


def process_file(input_file: Path, output_file: Path, limit: int = None):
    """处理单个文件"""
    # 读取原始论文
    papers = []
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if line:
                papers.append(json.loads(line))
    
    if limit:
        papers = papers[:limit]
    
    print(f"Processing {input_file.name}: {len(papers)} papers")
    
    # 分批处理
    translated_papers = []
    for i in range(0, len(papers), BATCH_SIZE):
        batch = papers[i:i+BATCH_SIZE]
        print(f"  Batch {i//BATCH_SIZE + 1}/{(len(papers)-1)//BATCH_SIZE + 1}: {len(batch)} papers")
        
        translations = call_kimi_translate(batch)
        
        if translations is None:
            print(f"  Failed to translate batch, skipping...")
            # 使用原始数据
            for paper in batch:
                translated_papers.append(paper)
            continue
        
        # 合并翻译结果
        for j, paper in enumerate(batch):
            trans = next((t for t in translations if t.get("index") == j), None)
            if trans:
                paper["AI"] = {
                    "tldr": trans.get("tldr", ""),
                    "motivation": trans.get("motivation", ""),
                    "techniques": trans.get("techniques", ""),
                    "main_theorems": trans.get("main_theorems", ""),
                    "significance": trans.get("significance", ""),
                    "title_zh": trans.get("title_zh", ""),
                    "summary_zh": trans.get("summary_zh", "")
                }
            translated_papers.append(paper)
    
    # 写入输出文件
    with open(output_file, 'w', encoding='utf-8') as f:
        for paper in translated_papers:
            f.write(json.dumps(paper, ensure_ascii=False) + '\n')
    
    print(f"  Saved to {output_file.name}")


def main():
    # 测试模式：只处理前 3 篇论文
    test_file = DATA_DIR / "2026-03-24.jsonl"
    if test_file.exists():
        output_file = DATA_DIR / "2026-03-24_AI_kimi.jsonl"
        process_file(test_file, output_file, limit=3)
    else:
        print(f"Test file {test_file} not found")


if __name__ == "__main__":
    main()
