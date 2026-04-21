#!/usr/bin/env python3
"""
从 arXiv 历史 metadata 中提取指定分类的论文，按日期生成 JSONL 文件。

Usage:
    python scripts/extract_historical_data.py \
        --input arxiv_history_metadata/arxiv-metadata-oai-snapshot.json \
        --output data/ \
        --categories math.AP \
        --start-date 2007-01-01 \
        --end-date 2025-12-31
"""

import json
import argparse
import os
import re
from datetime import datetime
from pathlib import Path
from collections import defaultdict
try:
    from tqdm import tqdm
except ImportError:
    # 如果没有 tqdm，使用简单的替代方案
    def tqdm(iterable, **kwargs):
        total = kwargs.get('total', '?')
        desc = kwargs.get('desc', '')
        print(f"{desc} (总数: {total})")
        return iterable


def parse_authors(authors_str: str) -> list:
    """将作者字符串解析为列表"""
    if not authors_str:
        return []
    # 先按 " and " 分割，再按 ", " 分割
    authors = []
    for part in re.split(r'\s+and\s+', authors_str):
        for author in part.split(', '):
            author = author.strip()
            if author:
                authors.append(author)
    return authors


def convert_record(raw: dict) -> dict:
    """将历史数据格式转换为项目格式"""
    arxiv_id = raw.get("id", "")
    return {
        "id": arxiv_id,
        "pdf": f"https://arxiv.org/pdf/{arxiv_id}",
        "abs": f"https://arxiv.org/abs/{arxiv_id}",
        "authors": parse_authors(raw.get("authors", "")),
        "title": raw.get("title", "").replace("\n", " ").strip(),
        "categories": raw.get("categories", "").split(),
        "comment": raw.get("comments"),
        "summary": raw.get("abstract", "").strip()
    }


def should_include(paper: dict, target_categories: list) -> bool:
    """检查论文是否包含目标分类"""
    paper_categories = paper.get("categories", [])
    for target in target_categories:
        if target in paper_categories:
            return True
    return False


def process_historical_data(
    input_file: str,
    output_dir: str,
    categories: list,
    start_date: str = None,
    end_date: str = None,
    force: bool = False
):
    """处理历史数据文件"""
    
    print(f"开始处理历史数据...")
    print(f"输入文件: {input_file}")
    print(f"输出目录: {output_dir}")
    print(f"目标分类: {categories}")
    if start_date:
        print(f"开始日期: {start_date}")
    if end_date:
        print(f"结束日期: {end_date}")
    
    # 解析日期范围
    start_dt = datetime.strptime(start_date, "%Y-%m-%d") if start_date else None
    end_dt = datetime.strptime(end_date, "%Y-%m-%d") if end_date else None
    
    # 按日期分组的论文
    papers_by_date = defaultdict(list)
    
    # 统计信息
    total_lines = 0
    matched_papers = 0
    skipped_by_date = 0
    
    # 第一次遍历：统计总行数
    print("\n统计文件行数...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for _ in f:
            total_lines += 1
    print(f"总共 {total_lines:,} 条记录")
    
    # 第二次遍历：提取数据
    print(f"\n提取 {', '.join(categories)} 分类的论文...")
    with open(input_file, 'r', encoding='utf-8') as f:
        for line in tqdm(f, total=total_lines, desc="处理中"):
            try:
                raw = json.loads(line.strip())
                
                # 检查分类
                if not should_include(raw, categories):
                    continue
                
                # 检查日期
                update_date = raw.get("update_date", "")
                if not update_date:
                    continue
                
                try:
                    paper_dt = datetime.strptime(update_date, "%Y-%m-%d")
                except ValueError:
                    continue
                
                if start_dt and paper_dt < start_dt:
                    skipped_by_date += 1
                    continue
                if end_dt and paper_dt > end_dt:
                    skipped_by_date += 1
                    continue
                
                # 转换并保存
                converted = convert_record(raw)
                papers_by_date[update_date].append(converted)
                matched_papers += 1
                
            except json.JSONDecodeError:
                continue
            except Exception as e:
                print(f"\n处理记录时出错: {e}")
                continue
    
    print(f"\n提取完成:")
    print(f"  - 匹配论文数: {matched_papers:,}")
    print(f"  - 日期范围跳过: {skipped_by_date:,}")
    print(f"  - 涉及日期数: {len(papers_by_date)}")
    
    # 生成 JSONL 文件
    print(f"\n生成 JSONL 文件...")
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    generated_files = 0
    skipped_files = 0
    
    for date_str in sorted(papers_by_date.keys()):
        output_file = output_path / f"{date_str}.jsonl"
        
        # 检查是否已存在
        if output_file.exists() and not force:
            skipped_files += 1
            continue
        
        # 写入文件
        papers = papers_by_date[date_str]
        with open(output_file, 'w', encoding='utf-8') as f:
            for paper in papers:
                f.write(json.dumps(paper, ensure_ascii=False) + '\n')
        
        generated_files += 1
        
    print(f"\n文件生成完成:")
    print(f"  - 新生成: {generated_files}")
    print(f"  - 已存在跳过: {skipped_files}")
    
    # 打印日期范围
    if papers_by_date:
        dates = sorted(papers_by_date.keys())
        print(f"\n数据日期范围: {dates[0]} ~ {dates[-1]}")
        
        # 打印每日论文数统计
        paper_counts = [len(papers_by_date[d]) for d in dates]
        print(f"每日论文数统计:")
        print(f"  - 最少: {min(paper_counts)} 篇")
        print(f"  - 最多: {max(paper_counts)} 篇")
        print(f"  - 平均: {sum(paper_counts)/len(paper_counts):.1f} 篇")


def main():
    parser = argparse.ArgumentParser(
        description="从 arXiv 历史 metadata 中提取指定分类的论文"
    )
    parser.add_argument(
        "--input",
        type=str,
        default="arxiv_history_metadata/arxiv-metadata-oai-snapshot.json",
        help="输入的 metadata JSON 文件路径"
    )
    parser.add_argument(
        "--output",
        type=str,
        default="data/",
        help="输出的 JSONL 文件目录"
    )
    parser.add_argument(
        "--categories",
        type=str,
        nargs="+",
        default=["math.AP"],
        help="要提取的分类列表，如: math.AP math.DG"
    )
    parser.add_argument(
        "--start-date",
        type=str,
        help="开始日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--end-date",
        type=str,
        help="结束日期 (YYYY-MM-DD)"
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="强制重新生成已存在的文件"
    )
    
    args = parser.parse_args()
    
    # 检查输入文件
    if not os.path.exists(args.input):
        print(f"错误: 输入文件不存在: {args.input}")
        print("请确保 arxiv_history_metadata/arxiv-metadata-oai-snapshot.json 文件存在")
        return
    
    process_historical_data(
        input_file=args.input,
        output_dir=args.output,
        categories=args.categories,
        start_date=args.start_date,
        end_date=args.end_date,
        force=args.force
    )


if __name__ == "__main__":
    main()
