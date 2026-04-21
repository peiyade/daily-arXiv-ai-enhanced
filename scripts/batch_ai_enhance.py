#!/usr/bin/env python3
"""
批量对历史数据 JSONL 文件进行 AI 增强处理。

Usage:
    python scripts/batch_ai_enhance.py \
        --data-dir data/ \
        --max-workers 4 \
        --language Chinese
"""

import json
import argparse
import os
import sys
import subprocess
import time
from pathlib import Path
from datetime import datetime

# 加载 .env 文件
script_dir = Path(__file__).parent
env_file = script_dir.parent / "ai" / ".env"
if env_file.exists():
    import dotenv
    dotenv.load_dotenv(env_file)
    print(f"✓ 已加载环境变量: {env_file}")
try:
    from tqdm import tqdm
except ImportError:
    # 如果没有 tqdm，使用简单的替代方案
    class tqdm:
        def __init__(self, iterable=None, **kwargs):
            self.iterable = iterable
            self.total = kwargs.get('total', '?')
            self.desc = kwargs.get('desc', '')
            self.n = 0
            if self.desc:
                print(f"{self.desc} (总数: {self.total})")
        
        def __iter__(self):
            for item in self.iterable:
                self.n += 1
                yield item
        
        def __enter__(self):
            return self
        
        def __exit__(self, *args):
            pass
        
        def set_postfix(self, *args, **kwargs):
            pass

# 进度文件路径
PROGRESS_FILE = Path(__file__).parent / ".enhance_progress.json"


def load_progress():
    """加载已处理的进度"""
    if PROGRESS_FILE.exists():
        with open(PROGRESS_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {"completed": [], "failed": []}


def save_progress(progress: dict):
    """保存处理进度"""
    with open(PROGRESS_FILE, 'w', encoding='utf-8') as f:
        json.dump(progress, f, indent=2, ensure_ascii=False)


def find_unprocessed_files(data_dir: str, language: str, reverse: bool = False) -> list:
    """查找未进行 AI 增强的 JSONL 文件"""
    data_path = Path(data_dir)
    progress = load_progress()
    completed = set(progress.get("completed", []))
    
    unprocessed = []
    
    # 查找所有原始 JSONL 文件（非 AI 增强的），按日期排序
    jsonl_files = sorted(data_path.glob("*.jsonl"))
    if reverse:
        jsonl_files = jsonl_files[::-1]  # 从新到久排序
    
    for jsonl_file in jsonl_files:
        # 跳过 AI 增强后的文件
        if "_AI_enhanced_" in jsonl_file.name:
            continue
        
        # 获取日期
        date_str = jsonl_file.stem
        
        # 检查是否已处理
        if date_str in completed:
            continue
        
        # 检查 AI 增强文件是否已存在
        enhanced_file = data_path / f"{date_str}_AI_enhanced_{language}.jsonl"
        if enhanced_file.exists():
            # 如果文件存在但未记录在进度中，添加到进度
            progress["completed"].append(date_str)
            continue
        
        unprocessed.append({
            "date": date_str,
            "input": jsonl_file,
            "output": enhanced_file
        })
    
    # 保存更新后的进度
    save_progress(progress)
    
    return unprocessed


def process_single_file(input_file: Path, output_file: Path, max_workers: int, language: str, verbose: bool = True) -> bool:
    """处理单个文件"""
    ai_dir = Path(__file__).parent.parent / "ai"
    
    # 设置环境变量 (继承父进程已加载的环境变量)
    env = os.environ.copy()
    env["LANGUAGE"] = language
    env["MODEL_NAME"] = env.get("MODEL_NAME", "deepseek-chat")
    
    # 确保 API Key 已设置
    if not env.get("OPENAI_API_KEY"):
        print(f"  ⚠️ 警告: OPENAI_API_KEY 未设置，尝试从 .env 加载")
        env_file = ai_dir / ".env"
        if env_file.exists():
            try:
                import dotenv
                dotenv.load_dotenv(env_file, override=True)
                env = os.environ.copy()
            except ImportError:
                pass
    
    # 使用绝对路径
    enhance_script = ai_dir / "enhance.py"
    
    cmd = [
        sys.executable,
        str(enhance_script),
        "--data", str(input_file.absolute()),
        "--max_workers", str(max_workers),
        "--verbose"
    ]
    
    # DeepSeek API 建议: 单文件处理超时设为 30 分钟 (每篇论文约 10-30 秒)
    # 计算合理的超时时间: 论文数量 × 30 秒 × 并发数系数
    try:
        # 先数一下文件有多少行(论文数)
        line_count = sum(1 for _ in open(input_file))
        # 每篇论文 30 秒，加上并发开销
        timeout_seconds = max(300, line_count * 30 // max(max_workers, 1) + 60)
    except:
        timeout_seconds = 1800  # 默认 30 分钟
    
    print(f"\n{'='*70}")
    print(f"📄 处理文件: {input_file.name}")
    print(f"   论文数: {line_count} 篇")
    print(f"   超时: {timeout_seconds//60} 分钟")
    print(f"{'='*70}")
    
    try:
        if verbose:
            # 实时输出模式 - 可以看到详细的 API 调用日志
            print("🔍 启动详细日志输出模式...\n")
            process = subprocess.Popen(
                cmd,
                cwd=ai_dir,
                env=env,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,  # 合并 stderr 到 stdout
                text=True,
                bufsize=1,  # 行缓冲
                universal_newlines=True
            )
            
            # 实时读取输出
            start_time = time.time()
            last_output_time = start_time
            
            for line in process.stdout:
                print(line, end='')  # 实时打印
                last_output_time = time.time()
                
                # 检查是否超时（通过监控输出活动）
                if time.time() - last_output_time > timeout_seconds:
                    print(f"\n⏰ 超过 {timeout_seconds} 秒没有输出，判定为超时")
                    process.kill()
                    return False
            
            process.wait(timeout=10)  # 等待进程结束
            
            if process.returncode == 0:
                print(f"\n✅ 文件处理完成: {input_file.name}")
                return True
            else:
                print(f"\n❌ 处理失败 (exit code: {process.returncode}): {input_file.name}")
                return False
        else:
            # 静默模式 - 只显示进度
            result = subprocess.run(
                cmd,
                cwd=ai_dir,
                env=env,
                capture_output=True,
                text=True,
                timeout=timeout_seconds
            )
            
            if result.returncode == 0:
                return True
            else:
                print(f"\n处理失败: {input_file}")
                print(f"错误: {result.stderr}")
                return False
            
    except subprocess.TimeoutExpired:
        print(f"\n⏰ 处理超时: {input_file}")
        return False
    except Exception as e:
        print(f"\n💥 处理异常: {input_file}, 错误: {e}")
        import traceback
        traceback.print_exc()
        return False


def batch_process(
    data_dir: str,
    max_workers: int,
    language: str,
    dry_run: bool = False,
    resume: bool = True,
    reverse: bool = False,
    limit: int = None,
    verbose: bool = True
):
    """批量处理文件"""
    
    print(f"开始批量 AI 增强处理...")
    print(f"数据目录: {data_dir}")
    print(f"语言: {language}")
    print(f"并发数: {max_workers}")
    print(f"处理顺序: {'从新到久' if reverse else '从久到新'}")
    print(f"详细日志: {'开启' if verbose else '关闭'}")
    if limit:
        print(f"限制数量: 前 {limit} 个文件")
    
    # 查找未处理的文件
    unprocessed = find_unprocessed_files(data_dir, language, reverse=reverse)
    
    if limit:
        unprocessed = unprocessed[:limit]
    
    if not unprocessed:
        print("\n没有需要处理的文件")
        return
    
    print(f"\n找到 {len(unprocessed)} 个待处理文件")
    
    if dry_run:
        print("\n[DRY RUN] 将要处理的文件:")
        for item in unprocessed[:10]:
            print(f"  - {item['date']}: {item['input'].name}")
        if len(unprocessed) > 10:
            print(f"  ... 还有 {len(unprocessed) - 10} 个文件")
        return
    
    # 加载进度
    progress = load_progress()
    
    # 处理文件
    success_count = 0
    fail_count = 0
    
    try:
        with tqdm(unprocessed, desc="AI 增强处理") as pbar:
            for item in pbar:
                date_str = item["date"]
                input_file = item["input"]
                
                pbar.set_postfix({"当前": date_str})
                
                # 处理文件
                success = process_single_file(
                    input_file=input_file,
                    output_file=item["output"],
                    max_workers=max_workers,
                    language=language,
                    verbose=verbose
                )
                
                if success:
                    progress["completed"].append(date_str)
                    success_count += 1
                else:
                    if date_str not in progress["failed"]:
                        progress["failed"].append(date_str)
                    fail_count += 1
                
                # 保存进度
                save_progress(progress)
                
    except KeyboardInterrupt:
        print("\n\n用户中断处理")
        print(f"已处理: {success_count}, 失败: {fail_count}")
        print("进度已保存，可以稍后使用 --resume 继续")
        return
    
    # 打印统计
    print(f"\n处理完成:")
    print(f"  - 成功: {success_count}")
    print(f"  - 失败: {fail_count}")
    
    if fail_count > 0:
        print(f"\n失败的日期: {progress['failed']}")


def reset_progress():
    """重置进度"""
    if PROGRESS_FILE.exists():
        PROGRESS_FILE.unlink()
        print("进度已重置")
    else:
        print("没有进度文件需要重置")


def show_stats(data_dir: str, language: str):
    """显示统计信息"""
    data_path = Path(data_dir)
    progress = load_progress()
    
    # 统计文件
    all_jsonl = list(data_path.glob("*.jsonl"))
    raw_files = [f for f in all_jsonl if "_AI_enhanced_" not in f.name]
    enhanced_files = [f for f in all_jsonl if "_AI_enhanced_" in f.name]
    
    completed = set(progress.get("completed", []))
    failed = set(progress.get("failed", []))
    
    print("=" * 50)
    print("AI 增强处理统计")
    print("=" * 50)
    print(f"原始数据文件: {len(raw_files)}")
    print(f"AI 增强文件: {len(enhanced_files)}")
    print(f"已记录完成: {len(completed)}")
    print(f"已记录失败: {len(failed)}")
    print(f"待处理: {len(raw_files) - len(enhanced_files)}")
    print("=" * 50)


def main():
    parser = argparse.ArgumentParser(
        description="批量对历史数据 JSONL 文件进行 AI 增强处理"
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="data/",
        help="数据目录路径"
    )
    parser.add_argument(
        "--max-workers",
        type=int,
        default=4,
        help="并发处理数"
    )
    parser.add_argument(
        "--language",
        type=str,
        default="Chinese",
        help="输出语言"
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="只显示将要处理的文件，不实际执行"
    )
    parser.add_argument(
        "--reset-progress",
        action="store_true",
        help="重置处理进度"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="显示统计信息"
    )
    parser.add_argument(
        "--reverse",
        action="store_true",
        help="从新到久处理（默认从久到新）"
    )
    parser.add_argument(
        "--limit",
        type=int,
        help="限制处理文件数量（用于测试）"
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        default=True,
        help="显示详细日志（默认开启）"
    )
    parser.add_argument(
        "--quiet",
        action="store_true",
        help="静默模式，只显示进度"
    )
    
    args = parser.parse_args()
    
    if args.reset_progress:
        reset_progress()
        return
    
    if args.stats:
        show_stats(args.data_dir, args.language)
        return
    
    # 检查环境变量（dry-run 不需要）
    if not args.dry_run and not os.environ.get("OPENAI_API_KEY"):
        print("错误: 未设置 OPENAI_API_KEY 环境变量")
        print("请设置后再运行: export OPENAI_API_KEY=your_key")
        return
    
    batch_process(
        data_dir=args.data_dir,
        max_workers=args.max_workers,
        language=args.language,
        dry_run=args.dry_run,
        reverse=args.reverse,
        limit=args.limit,
        verbose=not args.quiet
    )


if __name__ == "__main__":
    main()
