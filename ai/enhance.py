import os
import json
import sys
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import List, Dict, Optional
from queue import Queue
from threading import Lock

import dotenv
import argparse
from tqdm import tqdm
import yaml

import langchain_core.exceptions
from langchain_openai import ChatOpenAI
from langchain.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

# 全局配置变量
PROMPTS_CONFIG = None
OLD_TEMPLATE = None
OLD_SYSTEM = None


def load_prompts_config(config_path='prompts_config.yaml'):
    """
    加载提示词配置文件

    Args:
        config_path: 配置文件路径

    Returns:
        配置字典，如果文件不存在则返回 None
    """
    global PROMPTS_CONFIG
    if not os.path.exists(config_path):
        print(f'Warning: Prompts config file {config_path} not found, using legacy templates', file=sys.stderr)
        PROMPTS_CONFIG = None
        return None

    try:
        with open(config_path, 'r', encoding='utf-8') as f:
            PROMPTS_CONFIG = yaml.safe_load(f)
            print(f'Loaded prompts config from {config_path}', file=sys.stderr)
            return PROMPTS_CONFIG
    except Exception as e:
        print(f'Error loading prompts config: {e}, using legacy templates', file=sys.stderr)
        PROMPTS_CONFIG = None
        return None


def get_template_for_paper(prompts_config: Optional[Dict], paper_categories: List[str]) -> Dict:
    """
    根据论文分类选择合适的模板

    Args:
        prompts_config: 提示词配置字典
        paper_categories: 论文分类列表

    Returns:
        模板字典，包含 system_prompt 和 user_prompt
    """
    if not prompts_config:
        return None

    # 优先匹配第一个分类
    category_mapping = prompts_config.get('category_mapping', {})
    templates = prompts_config.get('templates', {})

    for category in paper_categories:
        if category in category_mapping:
            template_name = category_mapping[category]
            if template_name in templates:
                return templates[template_name]

    # 没有匹配则使用默认模板
    if 'default' in templates:
        return templates['default']

    return None


def load_legacy_templates():
    """
    加载旧的提示词文件（向后兼容）

    Returns:
        (template, system) 元组
    """
    global OLD_TEMPLATE, OLD_SYSTEM
    if OLD_TEMPLATE is None:
        try:
            OLD_TEMPLATE = open("template.txt", "r").read()
            OLD_SYSTEM = open("system.txt", "r").read()
        except Exception as e:
            print(f'Error loading legacy templates: {e}', file=sys.stderr)
            OLD_TEMPLATE = "Please analyze: {content}"
            OLD_SYSTEM = "You are a professional paper analyst. Your output should in {language}."

    return OLD_TEMPLATE, OLD_SYSTEM


def process_single_item(chain, item: Dict, language: str, prompts_config: Optional[Dict] = None) -> Dict:
    """
    处理单个数据项

    Args:
        chain: LangChain 处理链
        item: 论文数据
        language: 输出语言
        prompts_config: 提示词配置（可选）

    Returns:
        处理后的论文数据
    """
    try:
        # 尝试获取适合该论文的模板
        template_info = None
        if prompts_config:
            template_info = get_template_for_paper(prompts_config, item.get('categories', []))

        if template_info:
            # 使用配置的模板
            system_prompt = template_info['system_prompt'].format(language=language)
            user_prompt = template_info['user_prompt'].format(
                title=item.get('title', ''),
                authors=', '.join(item.get('authors', [])),
                content=item['summary']
            )

            # 构建完整的消息
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]

            response: Structure = chain.invoke(messages)
            item['AI'] = response.model_dump()
            item['AI']['_template_used'] = template_info['name']
            print(f"Processed {item['id']} using template: {template_info['name']}", file=sys.stderr)
        else:
            # 使用旧模板（向后兼容）
            response: Structure = chain.invoke({
                "language": language,
                "content": item['summary']
            })
            item['AI'] = response.model_dump()
            item['AI']['_template_used'] = 'legacy'

    except langchain_core.exceptions.OutputParserException as e:
        # 尝试从错误信息中提取 JSON 字符串并修复
        error_msg = str(e)
        if "Function Structure arguments:" in error_msg:
            try:
                # 提取 JSON 字符串
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
                # 预处理 LaTeX 数学符号 - 使用四个反斜杠来确保正确转义
                json_str = json_str.replace('\\', '\\\\')
                # 尝试解析修复后的 JSON
                fixed_data = json.loads(json_str)
                item['AI'] = fixed_data
                return item
            except Exception as json_e:
                print(f"Failed to fix JSON for {item['id']}: {json_e} {json_str}", file=sys.stderr)

        # 如果修复失败，返回错误状态
        item['AI'] = {
            "tldr": "Error",
            "motivation": "Error",
            "method": "Error",
            "result": "Error",
            "conclusion": "Error",
            "_template_used": "error"
        }
    except Exception as e:
        print(f"Error processing {item['id']}: {e}", file=sys.stderr)
        item['AI'] = {
            "tldr": "Error",
            "motivation": "Error",
            "method": "Error",
            "result": "Error",
            "conclusion": "Error",
            "_template_used": "error"
        }

    return item


def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int, prompts_config: Optional[Dict] = None) -> List[Dict]:
    """
    并行处理所有数据项

    Args:
        data: 论文数据列表
        model_name: 模型名称
        language: 输出语言
        max_workers: 最大并行数
        prompts_config: 提示词配置（可选）

    Returns:
        处理后的数据列表
    """
    llm = ChatOpenAI(model=model_name).with_structured_output(Structure, method="function_calling")
    print('Connect to:', model_name, file=sys.stderr)

    # 如果使用新模板系统，创建不同的处理链
    if prompts_config:
        # 新模板系统：直接传递消息
        chain = llm
    else:
        # 旧模板系统：使用 ChatPromptTemplate
        template, system = load_legacy_templates()
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system),
            HumanMessagePromptTemplate.from_template(template=template)
        ])
        chain = prompt_template | llm

    # 使用线程池并行处理
    processed_data = [None] * len(data)  # 预分配结果列表
    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        # 提交所有任务
        future_to_idx = {
            executor.submit(process_single_item, chain, item, language, prompts_config): idx
            for idx, item in enumerate(data)
        }

        # 使用tqdm显示进度
        for future in tqdm(
            as_completed(future_to_idx),
            total=len(data),
            desc="Processing items"
        ):
            idx = future_to_idx[future]
            try:
                result = future.result()
                processed_data[idx] = result
            except Exception as e:
                print(f"Item at index {idx} generated an exception: {e}", file=sys.stderr)
                # 保持原始数据
                processed_data[idx] = data[idx]

    return processed_data


def parse_args():
    """解析命令行参数"""
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    parser.add_argument("--prompts_config", type=str, default="prompts_config.yaml", help="Path to prompts config file")
    return parser.parse_args()


def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'deepseek-chat')
    language = os.environ.get("LANGUAGE", 'Chinese')

    # 加载提示词配置
    prompts_config = load_prompts_config(args.prompts_config)

    # 检查并删除目标文件
    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    if os.path.exists(target_file):
        os.remove(target_file)
        print(f'Removed existing file: {target_file}', file=sys.stderr)

    # 读取数据
    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    # 去重
    seen_ids = set()
    unique_data = []
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)

    data = unique_data
    print('Open:', args.data, file=sys.stderr)

    # 并行处理所有数据
    processed_data = process_all_items(
        data,
        model_name,
        language,
        args.max_workers,
        prompts_config
    )

    # 保存结果
    with open(target_file, "w") as f:
        for item in processed_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")


if __name__ == "__main__":
    main()
