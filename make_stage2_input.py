import json
import pandas as pd

# ===== 配置 =====
RESULTS_XLSX = "business_rules_results.xlsx"
INPUT_JSONL = "dataset/BREX.jsonl"
OUTPUT_XLSX = "results.xlsx"

# ===== 读取 Stage I 输出 =====
df_results = pd.read_excel(RESULTS_XLSX)
print(f"Stage I 已处理: {len(df_results)} 篇")

# ===== 读取原始 jsonl，取文本 =====
texts = []
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for line in f:
        data = json.loads(line)
        texts.append(data["文本"])

print(f"原始数据集: {len(texts)} 篇")

# ===== 构造 Stage II prompt =====
PROMPT_TEMPLATE = """You are a professor of logical reasoning. Given the business text and a list of business rules, determine the dependency relationship between each pair of rules.

Dependency types:
- Sequential: Rule A must be executed before Rule B.
- Conditional: Different reference values of Rule A trigger different subsequent rules.
- Parallel: Two or more rules must be executed simultaneously.
- None: No direct dependency.

Business Text:
{text}

Business Rules:
{rules}

Rule Pairs to Judge:
{pairs}

For each pair, output the dependency type in the format:
<Rule 1> - <Rule 2>: Dependency Type
"""

rows = []
for idx, row in df_results.iterrows():
    index_val = row.iloc[0]
    text = texts[index_val - 1]  # Index 从 1 开始
    model_output = str(row.iloc[2])
    
    # 解析规则：按行拆分，去掉空行
    rules = [line.strip() for line in model_output.strip().split("\n") if line.strip()]
    
    # 生成所有候选规则对
    pairs = []
    for i in range(len(rules)):
        for j in range(i + 1, len(rules)):
            pairs.append(f"{rules[i]} - {rules[j]}")
    
    pairs_text = "\n".join(pairs)
    rules_text = "\n".join(rules)
    
    prompt = PROMPT_TEMPLATE.format(
        text=text,
        rules=rules_text,
        pairs=pairs_text
    )
    
    rows.append({
        "Index": index_val,
        "prompt": prompt,
        "num_rules": len(rules),
        "num_pairs": len(pairs),
    })

# ===== 写出 Excel =====
df_out = pd.DataFrame(rows)
df_out.to_excel(OUTPUT_XLSX, index=False)
print(f"Generated {OUTPUT_XLSX} with {len(df_out)} rows")
print(f"Columns: {list(df_out.columns)}")
print()
print("规则数分布:")
print(df_out["num_rules"].describe())
print()
print("候选对数量分布:")
print(df_out["num_pairs"].describe())