#!/usr/bin/env python3
"""诊断 DeepSeek API 连接问题"""
import os
import sys
import time
from pathlib import Path

# 加载 .env
env_file = Path(__file__).parent.parent / "ai" / ".env"
if env_file.exists():
    import dotenv
    dotenv.load_dotenv(env_file)

print("=" * 60)
print("DeepSeek API 诊断工具")
print("=" * 60)

# 1. 检查环境变量
print("\n1. 环境变量检查:")
api_key = os.environ.get("OPENAI_API_KEY", "")
api_base = os.environ.get("OPENAI_API_BASE", "")

if api_key:
    print(f"   ✓ OPENAI_API_KEY: {api_key[:15]}...")
else:
    print("   ✗ OPENAI_API_KEY: 未设置!")
    sys.exit(1)

if api_base:
    print(f"   ✓ OPENAI_API_BASE: {api_base}")
else:
    print("   ⚠ OPENAI_API_BASE: 未设置，使用默认")

# 2. 测试 API 连接
print("\n2. API 连接测试:")
try:
    from langchain_openai import ChatOpenAI
    
    llm = ChatOpenAI(
        model="deepseek-chat",
        timeout=30,  # 30秒超时
        max_retries=1
    )
    
    start = time.time() if 'time' in dir() else None
    import time
    start = time.time()
    
    response = llm.invoke("Hello, reply in 1 word.")
    
    elapsed = time.time() - start
    print(f"   ✓ API 响应正常 ({elapsed:.2f}s)")
    print(f"   响应内容: {response.content[:50]}...")
    
except Exception as e:
    print(f"   ✗ API 连接失败: {e}")
    sys.exit(1)

# 3. Rate Limit 提示
print("\n3. DeepSeek Rate Limit 参考:")
print("   - Free Tier: 可能限制较严格")
print("   - Paid Tier: 通常 RPM=30-60, TPM=较高")
print("   - 建议 --max-workers 设为 2-4，根据实际限制调整")

print("\n" + "=" * 60)
print("✓ 诊断完成，API 连接正常")
print("=" * 60)
