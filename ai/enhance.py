import os
import json
import sys
import time
from datetime import datetime
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
from langchain_core.prompts import (
    ChatPromptTemplate,
    SystemMessagePromptTemplate,
    HumanMessagePromptTemplate,
)
from structure import Structure

if os.path.exists('.env'):
    dotenv.load_dotenv()

PROMPTS_CONFIG = None
OLD_TEMPLATE = None
OLD_SYSTEM = None


def log(msg: str, level="INFO"):
    timestamp = datetime.now().strftime("%H:%M:%S.%f")[:-3]
    prefix = f"[{timestamp}] [{level}]"
    print(f"{prefix} {msg}", file=sys.stderr, flush=True)


def load_prompts_config(config_path='prompts_config.yaml'):
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
    if not prompts_config:
        return None

    category_mapping = prompts_config.get('category_mapping', {})
    templates = prompts_config.get('templates', {})

    for category in paper_categories:
        if category in category_mapping:
            template_name = category_mapping[category]
            if template_name in templates:
                return templates[template_name]

    if 'default' in templates:
        return templates['default']

    return None


def load_legacy_templates():
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


def process_single_item(chain, item: Dict, language: str, worker_id: int = 0, prompts_config: Optional[Dict] = None) -> Dict:
    paper_id = item.get('id', 'unknown')
    title = item.get('title', '')[:50]

    log(f"[Worker-{worker_id}] Processing: {paper_id} | {title}...", "PROCESS")

    try:
        template_info = None
        if prompts_config:
            template_info = get_template_for_paper(prompts_config, item.get('categories', []))

        if template_info:
            system_prompt = template_info['system_prompt'].format(language=language)
            user_prompt = template_info['user_prompt'].format(
                title=item.get('title', ''),
                authors=', '.join(item.get('authors', [])),
                content=item['summary']
            )
            messages = [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ]
            response: Structure = chain.invoke(messages)
            item['AI'] = response.model_dump()
            item['AI']['_template_used'] = template_info['name']
            log(f"[Worker-{worker_id}] Processed {paper_id} using template: {template_info['name']}", "SUCCESS")
        else:
            response: Structure = chain.invoke({
                "language": language,
                "content": item.get('summary', '')
            })
            item['AI'] = response.model_dump()
            item['AI']['_template_used'] = 'legacy'

    except langchain_core.exceptions.OutputParserException as e:
        log(f"[Worker-{worker_id}] Parse error, attempting fix: {paper_id}", "WARNING")
        error_msg = str(e)
        if "Function Structure arguments:" in error_msg:
            try:
                json_str = error_msg.split("Function Structure arguments:", 1)[1].strip().split('are not valid JSON')[0].strip()
                json_str = json_str.replace('\\', '\\\\')
                fixed_data = json.loads(json_str)
                item['AI'] = fixed_data
                log(f"[Worker-{worker_id}] Fix succeeded: {paper_id}", "SUCCESS")
                return item
            except Exception as json_e:
                log(f"[Worker-{worker_id}] Fix failed: {paper_id} - {json_e}", "ERROR")

        item['AI'] = {
            "tldr": "Error: Failed to parse response",
            "motivation": "Error",
            "method": "Error",
            "result": "Error",
            "conclusion": "Error",
            "msc_code": "Error",
            "_template_used": "error"
        }

    except Exception as e:
        log(f"[Worker-{worker_id}] Failed: {paper_id} - {str(e)[:100]}", "ERROR")
        item['AI'] = {
            "tldr": f"Error: {str(e)[:100]}",
            "motivation": "Error",
            "method": "Error",
            "result": "Error",
            "conclusion": "Error",
            "msc_code": "Error",
            "_template_used": "error"
        }

    return item


def process_all_items(data: List[Dict], model_name: str, language: str, max_workers: int, prompts_config: Optional[Dict] = None) -> List[Dict]:
    log("=" * 70, "HEADER")
    log("Starting AI enhancement", "HEADER")
    log("=" * 70, "HEADER")

    log("Step 1/3: Initializing model...", "SETUP")
    log(f"  Model: {model_name}", "SETUP")
    log(f"  Workers: {max_workers}", "SETUP")

    llm = ChatOpenAI(
        model=model_name,
        timeout=60,
        max_retries=2
    ).with_structured_output(Structure, method="function_calling")

    if prompts_config:
        chain = llm
        log("  Using prompts_config template system", "SETUP")
    else:
        template, system = load_legacy_templates()
        prompt_template = ChatPromptTemplate.from_messages([
            SystemMessagePromptTemplate.from_template(system),
            HumanMessagePromptTemplate.from_template(template=template)
        ])
        chain = prompt_template | llm
        log("  Using legacy template system", "SETUP")

    log("Step 2/3: Processing papers...", "PROCESS")
    log(f"  Total: {len(data)}", "PROCESS")
    log(f"  Concurrency: {max_workers}", "PROCESS")
    log("-" * 70, "PROCESS")

    processed_data = [None] * len(data)
    completed_count = 0
    failed_count = 0

    with ThreadPoolExecutor(max_workers=max_workers) as executor:
        future_to_idx = {}
        for idx, item in enumerate(data):
            worker_id = idx % max_workers
            future = executor.submit(process_single_item, chain, item, language, worker_id, prompts_config)
            future_to_idx[future] = idx

        for future in tqdm(
            as_completed(future_to_idx),
            total=len(data),
            desc="Processing",
            file=sys.stderr
        ):
            idx = future_to_idx[future]
            try:
                result = future.result()
                processed_data[idx] = result
                completed_count += 1

                if completed_count % 10 == 0:
                    progress_pct = completed_count / len(data) * 100
                    log(f"Progress: {completed_count}/{len(data)} ({progress_pct:.1f}%)", "PROGRESS")

            except Exception as e:
                log(f"Item at index {idx} failed: {e}", "ERROR")
                processed_data[idx] = data[idx]
                failed_count += 1

    log("-" * 70, "PROCESS")
    log(f"Step 3/3: Done", "SUCCESS")
    log(f"  Success: {completed_count}", "SUCCESS")
    log(f"  Failed: {failed_count}", "SUCCESS")
    log("=" * 70, "HEADER")

    return processed_data


def parse_args():
    parser = argparse.ArgumentParser()
    parser.add_argument("--data", type=str, required=True, help="jsonline data file")
    parser.add_argument("--max_workers", type=int, default=1, help="Maximum number of parallel workers")
    parser.add_argument("--prompts_config", type=str, default="prompts_config.yaml", help="Path to prompts config file")
    return parser.parse_args()


def main():
    args = parse_args()
    model_name = os.environ.get("MODEL_NAME", 'deepseek-chat')
    language = os.environ.get("LANGUAGE", 'Chinese')

    log(f"Starting enhancement", "START")
    log(f"   Data: {args.data}", "START")
    log(f"   Model: {model_name}", "START")
    log(f"   Language: {language}", "START")
    log(f"   Workers: {args.max_workers}", "START")

    prompts_config = load_prompts_config(args.prompts_config)

    target_file = args.data.replace('.jsonl', f'_AI_enhanced_{language}.jsonl')
    if os.path.exists(target_file):
        os.remove(target_file)
        log(f'Removed old file: {target_file}', "SETUP")

    data = []
    with open(args.data, "r") as f:
        for line in f:
            data.append(json.loads(line))

    seen_ids = set()
    unique_data = []
    duplicates = 0
    for item in data:
        if item['id'] not in seen_ids:
            seen_ids.add(item['id'])
            unique_data.append(item)
        else:
            duplicates += 1

    data = unique_data
    if duplicates > 0:
        log(f"   Dedup: removed {duplicates} duplicates", "SETUP")
    log(f"   Processing: {len(data)} papers", "SETUP")

    processed_data = process_all_items(
        data,
        model_name,
        language,
        args.max_workers,
        prompts_config
    )

    log(f"Saving to: {target_file}", "SAVE")
    with open(target_file, "w") as f:
        for item in processed_data:
            f.write(json.dumps(item, ensure_ascii=False) + "\n")
    log(f"Done!", "SUCCESS")


if __name__ == "__main__":
    main()
