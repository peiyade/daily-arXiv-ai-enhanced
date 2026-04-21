#!/usr/bin/env python3
"""
测试 Moonshot AI API (OpenAI 兼容)
需要 MOONSHOT_API_KEY 环境变量
"""

import os
import json
from openai import OpenAI

# Moonshot API 配置
MOONSHOT_BASE_URL = "https://api.moonshot.cn/v1"
MOONSHOT_MODEL = "moonshot-v1-32k"  # 或其他可用模型

def test_moonshot_translate():
    api_key = os.getenv("MOONSHOT_API_KEY")
    if not api_key:
        print("错误: 请设置 MOONSHOT_API_KEY 环境变量")
        print("获取方式: https://platform.moonshot.cn/")
        return
    
    client = OpenAI(
        api_key=api_key,
        base_url=MOONSHOT_BASE_URL
    )
    
    paper = {
        "title": "Lack of interior $L^q$ bounds for stable solutions to elliptic equations",
        "summary": "We consider stable solutions of semilinear elliptic equations of the form $-\\Delta u=f(u)$ in a bounded domain $\\Omega\\subset\\mathbb{R}^N$. We show that, for general nonlinearities $f\\in C^\\infty(\\mathbb{R})$, it is impossible, in any dimension $N\\geq 1$, to obtain an interior $L^q$ estimate in terms of the $L^p$-norm of $u$ whenever $1\\leq p<q\\leq \\infty$."
    }
    
    prompt = f"""你是一位专业的数学论文翻译专家。请将以下数学论文的标题和摘要翻译成中文，并提供结构化分析。

要求：
1. 标题翻译要准确、学术化
2. 摘要翻译要流畅，保留数学符号（用 $...$ 包裹）
3. 提供以下结构化信息：
   - tldr: 一句话核心贡献（中文）
   - motivation: 研究背景和动机（中文）
   - techniques: 主要数学技术/方法（中文）
   - main_theorems: 主要定理/结果（中文）
   - significance: 理论意义和影响（中文）

请严格按以下 JSON 格式返回（只返回 JSON，不要 markdown 代码块）：
{{"tldr": "...", "motivation": "...", "techniques": "...", "main_theorems": "...", "significance": "...", "title_zh": "...", "summary_zh": "..."}}

Title: {paper['title']}
Abstract: {paper['summary']}
"""
    
    try:
        response = client.chat.completions.create(
            model=MOONSHOT_MODEL,
            messages=[
                {"role": "system", "content": "你是数学论文翻译专家，只输出 JSON 格式结果。"},
                {"role": "user", "content": prompt}
            ],
            temperature=0.3,
            response_format={"type": "json_object"}
        )
        
        result = json.loads(response.choices[0].message.content)
        print("翻译成功!")
        print(json.dumps(result, indent=2, ensure_ascii=False))
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    test_moonshot_translate()
