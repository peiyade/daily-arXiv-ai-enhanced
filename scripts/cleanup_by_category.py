#!/usr/bin/env python3
"""
清理 data 文件夹中的 JSONL 文件
- 如果文件中所有论文都是 math.AP 类别的，保留
- 如果文件中所有论文都是 CS 类别的，删除
- 如果是混合的，输出统计信息
"""

import json
import os
from pathlib import Path
from collections import defaultdict

DATA_DIR = Path("data")


def is_cs_category(cat: str) -> bool:
    """判断是否为 CS 类别"""
    return cat.startswith("cs.")


def is_math_ap_category(cat: str) -> bool:
    """判断是否为 math.AP 类别"""
    return cat == "math.AP"


def analyze_file(filepath: Path) -> dict:
    """分析单个文件中的论文类别"""
    stats = {
        "total": 0,
        "math_ap_only": 0,  # 只有 math.AP 类别的论文
        "cs_only": 0,       # 只有 CS 类别的论文
        "mixed": 0,         # 混合类别的论文
        "other": 0,         # 其他（非 math.AP 非 CS）
    }
    
    with open(filepath, 'r', encoding='utf-8') as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            
            try:
                paper = json.loads(line)
                categories = paper.get("categories", [])
                stats["total"] += 1
                
                # 分析类别
                has_math_ap = any(is_math_ap_category(c) for c in categories)
                has_cs = any(is_cs_category(c) for c in categories)
                has_other = any(not is_math_ap_category(c) and not is_cs_category(c) for c in categories)
                
                if has_math_ap and not has_cs and not has_other:
                    stats["math_ap_only"] += 1
                elif has_cs and not has_math_ap and not has_other:
                    stats["cs_only"] += 1
                elif has_math_ap and has_cs:
                    stats["mixed"] += 1
                elif has_cs:
                    stats["cs_only"] += 1  # 有CS，可能有其他非math的非CS
                elif has_math_ap:
                    stats["math_ap_only"] += 1  # 有math.AP，可能有其他非CS的非math
                else:
                    stats["other"] += 1
                    
            except json.JSONDecodeError:
                continue
    
    return stats


def main():
    # 获取所有原始 jsonl 文件（不包括 _AI_enhanced 后缀的）
    jsonl_files = sorted([f for f in DATA_DIR.glob("*.jsonl") 
                          if "_AI_enhanced" not in f.name])
    
    print(f"找到 {len(jsonl_files)} 个原始 JSONL 文件")
    print("=" * 60)
    
    files_to_delete = []      # 纯 CS 文件
    files_to_keep = []        # 纯 math.AP 文件
    mixed_files = []          # 混合文件
    
    for filepath in jsonl_files:
        stats = analyze_file(filepath)
        
        if stats["total"] == 0:
            continue
            
        # 判断文件类型
        if stats["cs_only"] == stats["total"]:
            # 纯 CS 文件
            files_to_delete.append((filepath.name, stats))
        elif stats["math_ap_only"] == stats["total"]:
            # 纯 math.AP 文件
            files_to_keep.append((filepath.name, stats))
        else:
            # 混合文件
            mixed_files.append((filepath.name, stats))
    
    # 输出统计结果
    print(f"\n📊 统计结果：")
    print(f"  - 纯 math.AP 文件: {len(files_to_keep)} 个")
    print(f"  - 纯 CS 文件: {len(files_to_delete)} 个 (待删除)")
    print(f"  - 混合文件: {len(mixed_files)} 个")
    
    if files_to_delete:
        print(f"\n🗑️  以下纯 CS 文件将被删除：")
        for name, stats in files_to_delete[:20]:  # 只显示前20个
            print(f"    - {name} ({stats['total']} 篇论文)")
        if len(files_to_delete) > 20:
            print(f"    ... 还有 {len(files_to_delete) - 20} 个文件")
    
    if mixed_files:
        print(f"\n⚠️  以下混合文件需要关注：")
        for name, stats in mixed_files[:10]:
            print(f"    - {name}: math.AP={stats['math_ap_only']}, CS={stats['cs_only']}, 混合={stats['mixed']}, 其他={stats['other']}")
        if len(mixed_files) > 10:
            print(f"    ... 还有 {len(mixed_files) - 10} 个文件")
    
    # 确认删除
    if files_to_delete:
        print(f"\n⚠️  即将删除 {len(files_to_delete)} 个纯 CS 文件，确认吗？")
        confirm = input("输入 'yes' 确认删除: ").strip().lower()
        
        if confirm == 'yes':
            deleted_count = 0
            for name, stats in files_to_delete:
                filepath = DATA_DIR / name
                try:
                    filepath.unlink()
                    deleted_count += 1
                except Exception as e:
                    print(f"  ❌ 删除失败 {name}: {e}")
            print(f"\n✅ 已删除 {deleted_count} 个文件")
        else:
            print("\n❌ 取消删除操作")
    else:
        print(f"\n✅ 没有发现需要删除的纯 CS 文件")


if __name__ == "__main__":
    main()
