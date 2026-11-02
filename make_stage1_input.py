import json
import pandas as pd

# ===== 配置 =====
INPUT_JSONL = "dataset/BREX.jsonl"
OUTPUT_XLSX = "business_rules.xlsx"
# LIMIT = 2  # 只跑前 2 篇，验证流程
LIMIT = 409

# ===== Prompt 模板（简化版 Prompt 5：Executable Grounding）=====
# PROMPT_TEMPLATE = """You are a professor of logical reasoning. Extract business rules from the text below.

# Definition:
# - Condition = <Slot Type, Logical Operator, Reference Value>
# - Logical Operator can be: contains, equal to, less than, greater than, less than or equal to, greater than or equal to
# - Action = the operation triggered when the condition is met
# - If the process terminates, Action = None

# Output format (one rule per line):
# <<Slot Type, Logical Operator, Reference Value>, Action>

# Business Text:
# {text}

# Output:
# """

PROMPT_TEMPLATE = """You are a professor of logical reasoning. Extract ALL business rules from the text below.

Definition:
- Condition = <Slot Type, Logical Operator, Reference Value>
- Logical Operator can be: contains, equal to, less than, greater than, less than or equal to, greater than or equal to
- Action = the operation triggered when the condition is met
- If the process terminates, Action = None

IMPORTANT REQUIREMENTS:
1. You MUST extract ALL business rules from the text, including:
   - Every condition and its corresponding action
   - Nested conditions (conditions that depend on previous selections)
   - All branches and options mentioned
2. Do NOT skip rules even if the text is short.
3. Every slot type mentioned in the text should appear in at least one rule.
4. Use "contains" when the reference value is a list of options, and "equal to" for a single specific value.

Output format (one rule per line):
<<Slot Type, Logical Operator, Reference Value>, Action>

Business Text:
{text}

Output:
"""

# ===== 读取 jsonl =====
rows = []
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        if i >= LIMIT:
            break
        data = json.loads(line)
        text = data["文本"]
        prompt = PROMPT_TEMPLATE.format(text=text)
        rows.append({
            "Index": i + 1,
            "Domain": data["领域"],
            "Intent": data["意图"],
            "Text": text,
            "prompt": prompt,
        })

# ===== 写出 Excel =====
df = pd.DataFrame(rows)
df.to_excel(OUTPUT_XLSX, index=False)
print(f"Generated {OUTPUT_XLSX} with {len(df)} rows")
print(f"Columns: {list(df.columns)}")

# # 新promt:跑小文本，提高匹配度
# You are a professor of logical reasoning. Extract ALL business rules from the text below.

# Definition:
# - Condition = <Slot Type, Logical Operator, Reference Value>
# - Logical Operator can be: contains, equal to, less than, greater than, less than or equal to, greater than or equal to
# - Action = the operation triggered when the condition is met
# - If the process terminates, Action = None

# IMPORTANT REQUIREMENTS:
# 1. You MUST extract ALL business rules from the text, including:
#    - Every condition and its corresponding action
#    - Nested conditions (conditions that depend on previous selections)
#    - All branches and options mentioned
# 2. Do NOT skip rules even if the text is short.
# 3. Every slot type mentioned in the text should appear in at least one rule.
# 4. Use "contains" when the reference value is a list of options, and "equal to" for a single specific value.

# Output format (one rule per line):
# <<Slot Type, Logical Operator, Reference Value>, Action>

# Business Text:
# {text}

# Output:
