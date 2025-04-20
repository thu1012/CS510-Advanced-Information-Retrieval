import argparse
import json
import os
import re
from typing import Tuple, Optional


def extract_code(markdown_block: str) -> Optional[Tuple[str, str]]:
    match = re.search(r"```json\s*([\s\S]+?)\s*```", markdown_block)
    if not match:
        return None

    try:
        payload = json.loads(match.group(1))
        first_item = payload[0]
        version = first_item.get("version", "python3")
        target = first_item.get("target code", "")
        return version, target
    except Exception:
        return None


def gather_candidates(item: dict) -> list:
    candidates = []
    
    for idx in range(6):
        key = f"program_synthesis_{idx}"
        if key in item and item[key]:
            res = extract_code(item[key])
            if res:
                candidates.append(res)
    
    if not candidates and "program_synthesis" in item:
        for blob in item["program_synthesis"]:
            if not blob:
                continue
            res = extract_code(blob)
            if res:
                candidates.append(res)

    return candidates


def transform_record(raw: dict) -> Optional[dict]:
    candidates = gather_candidates(raw)
    if not candidates:
        return None

    transformed = {
        "lang_cluster": raw.get("lang_cluster", "python"),
        "src_uid": raw.get("src_uid"),
        "difficulty": raw.get("difficulty", 0),
        "testcases": raw.get("testcases", "[]"),
        "lang": candidates[0][0],
    }

    for i in range(min(len(candidates), 6)):
        version, code = candidates[i]
        wrapped = f"```json\n[{json.dumps({'version': version, 'target code': code}, ensure_ascii=False)}]\n```"
        transformed[f"program_synthesis_{i}"] = wrapped

    return transformed


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", default="./inference/results/program_synthesis_run_gemini.jsonl")
    parser.add_argument("--output", default="./inference/results/program_synthesis_eval_gemini.jsonl")
    args = parser.parse_args()

    os.makedirs(os.path.dirname(args.output), exist_ok=True)

    converted, skipped = 0, 0
    with open(args.input, "r", encoding="utf-8") as fin, \
            open(args.output, "w", encoding="utf-8") as fout:
        for line in fin:
            line = line.strip()
            if not line:
                continue
            try:
                raw_obj = json.loads(line)
            except Exception:
                skipped += 1
                continue

            new_obj = transform_record(raw_obj)
            if new_obj is None:
                skipped += 1
                continue

            fout.write(json.dumps(new_obj, ensure_ascii=False) + "\n")
            converted += 1

    print(f"Converted {converted} records → {args.output}")
    if skipped:
        print(f"Skipped {skipped} records due to missing/invalid code blocks.")


if __name__ == "__main__":
    main()
