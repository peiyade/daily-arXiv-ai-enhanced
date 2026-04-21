#!/usr/bin/env python3
"""
详细分析混合文件中的类别分布
"""

import json
from pathlib import Path
from collections import Counter

DATA_DIR = Path("data")


def analyze_categories(filepath: Path) -> dict:
    """分析文件中的具体类别分布"""
    all_categories = []
    math_ap_count = 0
    cs_count = 0
    papers_with_both = 0
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                paper = json.loads(line)
                categories = paper.get("categories", [])
                all_categories.extend(categories)
                
                has_math_ap = "math.AP" in categories
                has_cs = any(c.startswith("cs.") for c in categories)
                
                if has_math_ap:
                    math_ap_count += 1
                if has_cs:
                    cs_count += 1
                if has_math_ap and has_cs:
                    papers_with_both += 1
                    
            except json.JSONDecodeError:
                continue
    
    return {
        "all_cats": Counter(all_categories),
        "math_ap": math_ap_count,
        "cs": cs_count,
        "both": papers_with_both
    }


def main():
    # 获取所有原始 jsonl 文件
    jsonl_files = sorted([f for f in DATA_DIR.glob("*.jsonl") 
                          if "_AI_enhanced" not in f.name])
    
    # 全局统计
    global_cats = Counter()
    total_files = 0
    files_with_cs = []
    files_with_math_ap_only = 0
    
    for filepath in jsonl_files:
        stats = analyze_categories(filepath)
        global_cats.update(stats["all_cats"])
        total_files += 1
        
        if stats["cs"] > 0:
            files_with_cs.append((filepath.name, stats))
        elif stats["math_ap"] > 0:
            files_with_math_ap_only += 1
    
    print(f"总共分析了 {total_files} 个文件")
    print(f"\n📊 类别分布（Top 20）：")
    for cat, count in global_cats.most_common(20):
        print(f"  {cat}: {count}")
    
    print(f"\n🔍 包含 CS 论文的文件数量: {len(files_with_cs)}")
    if files_with_cs:
        print(f"\n包含 CS 论文的文件列表（前 20）：")
        for name, stats in files_with_cs[:20]:
            cat_list = ", ".join([f"{k}={v}" for k, v in stats["all_cats"].most_common(5)])
            print(f"  {name}: math.AP={stats['math_ap']}, CS={stats['cs']}, 混合={stats['both']} | {cat_list}")
    
    # 检查是否有纯 CS 文件
    pure_cs_files = [(name, stats) for name, stats in files_with_cs if stats["math_ap"] == 0]
    print(f"\n🗑️ 纯 CS 文件数量: {len(pure_cs_files)}")
    if pure_cs_files:
        print("纯 CS 文件列表：")
        for name, stats in pure_cs_files:
            print(f"  - {name}")


if __name__ == "__main__":
    main()
