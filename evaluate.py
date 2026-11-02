import json
import re
import pandas as pd
from collections import defaultdict, Counter

# ===== 配置 =====
INPUT_JSONL = "dataset/BREX.jsonl"
STAGE1_XLSX = "business_rules_results.xlsx"
STAGE2_XLSX = "dependency_results.xlsx"

# ===== 依赖类型映射：中文 -> 英文 =====
DEP_MAP = {
    "选择关系": "Conditional",
    "顺序关系": "Sequential",
    "并行关系": "Parallel",
}

# ===== 槽位名归一化 =====
def normalize_slot(slot):
    if slot is None:
        return None
    s = slot.strip()
    # 去除常见后缀
    for suffix in ["类型", "种类", "方式", "名称", "信息"]:
        if s.endswith(suffix) and len(s) > len(suffix):
            s = s[:-len(suffix)]
            break
    return s

def slots_match(s1, s2):
    """判断两个槽位名是否匹配（归一化后相等，或互相包含）"""
    if s1 is None or s2 is None:
        return False
    n1 = normalize_slot(s1)
    n2 = normalize_slot(s2)
    if n1 == n2:
        return True
    # 互相包含
    if n1 in n2 or n2 in n1:
        return True
    return False

# ===== 解析单条规则 =====
def parse_rule(rule_str):
    """从 <<Slot, Operator, Value>, Action> 中提取 (slot, action)"""
    rule_str = rule_str.strip()
    # 去掉开头的 << 或 <
    rule_str = re.sub(r'^<+', '', rule_str)
    # 去掉结尾的 >
    rule_str = re.sub(r'>+$', '', rule_str)
    # 按第一个逗号分割，但要注意槽位内部可能没有逗号
    # 更稳妥的方式：找最后一个 '>, ' 来分割 condition 和 action
    m = re.match(r'^(.*?)>\s*,\s*(.+)$', rule_str)
    if not m:
        return None, None
    condition_part = m.group(1)
    action = m.group(2).strip()
    # condition_part 形如 "Slot, Operator, Value"
    parts = [p.strip() for p in condition_part.split(',')]
    if len(parts) < 3:
        return None, None
    slot = parts[0].strip()
    return slot, action


# ===== 解析模型输出的依赖行 =====
def parse_model_dep(line):
    """解析 <Rule1> - <Rule2>: Type"""
    m = re.match(r'^(.*?)\s*-\s*(.*?)\s*:\s*(\w+)\s*$', line.strip())
    if not m:
        return None
    rule1_str, rule2_str, dep_type = m.group(1), m.group(2), m.group(3)
    slot1, _ = parse_rule(rule1_str)
    slot2, _ = parse_rule(rule2_str)
    if slot1 is None or slot2 is None:
        return None
    return (slot1, slot2, dep_type)


# ===== 解析黄金标准的依赖行 =====
def parse_gold_dep(line):
    """解析 规则A -> 规则B：类型"""
    m = re.match(r'^(.*?)\s*->\s*(.*?)\s*[：:]\s*(.+?)\s*$', line.strip())
    if not m:
        return None
    rule1_str, rule2_str, dep_type_cn = m.group(1), m.group(2), m.group(3)
    dep_type = DEP_MAP.get(dep_type_cn, dep_type_cn)
    slot1, _ = parse_rule(rule1_str)
    slot2, _ = parse_rule(rule2_str)
    if slot1 is None or slot2 is None:
        return None
    return (slot1, slot2, dep_type)


# ===== 读取黄金标准 =====
gold_data = {}
with open(INPUT_JSONL, "r", encoding="utf-8") as f:
    for i, line in enumerate(f):
        data = json.loads(line)
        gold_data[i + 1] = {
            "rules": data["业务规则二元组"],
            "deps": data["依赖关系"],
        }

# ===== 读取模型 Stage I 输出 =====
df_s1 = pd.read_excel(STAGE1_XLSX)

# ===== 读取模型 Stage II 输出 =====
df_s2 = pd.read_excel(STAGE2_XLSX)

# ===== 评测 Stage I：规则数量对比 =====
print("=" * 60)
print("Stage I 评测：规则数量对比")
print("=" * 60)

s1_results = []
for _, row in df_s1.iterrows():
    idx = row.iloc[0]
    model_output = str(row.iloc[2])
    model_rules = [l.strip() for l in model_output.strip().split("\n") if l.strip()]
    model_rule_count = len(model_rules)
    
    gold_rules = [l.strip() for l in gold_data[idx]["rules"].strip().split("\n") if l.strip()]
    gold_rule_count = len(gold_rules)
    
    s1_results.append({
        "Index": idx,
        "model_rules": model_rule_count,
        "gold_rules": gold_rule_count,
        "diff": model_rule_count - gold_rule_count,
    })

df_s1_eval = pd.DataFrame(s1_results)
print(f"已评测: {len(df_s1_eval)} 篇")
print(f"模型平均规则数: {df_s1_eval['model_rules'].mean():.2f}")
print(f"黄金平均规则数: {df_s1_eval['gold_rules'].mean():.2f}")
print(f"平均差异: {df_s1_eval['diff'].mean():.2f}")
print()

# ===== Stage II 评测：依赖识别 F1（修正版）=====
print("=" * 60)
print("Stage II 评测：依赖识别 F1（修正版）")
print("=" * 60)

all_tp = defaultdict(int)
all_fp = defaultdict(int)
all_fn = defaultdict(int)
# 混淆矩阵：gold -> {pred -> count}
confusion = defaultdict(lambda: defaultdict(int))
aligned_pairs = 0
total_gold_pairs = 0
total_none_tn = 0

for _, row in df_s2.iterrows():
    idx = row.iloc[0]
    if idx not in gold_data:
        continue

    model_output = str(row.iloc[2])

    # 解析模型预测，按槽位对聚合
    model_raw = []
    for line in model_output.strip().split("\n"):
        parsed = parse_model_dep(line)
        if parsed:
            s1, s2, dep = parsed
            model_raw.append((normalize_slot(s1), normalize_slot(s2), dep))

    model_agg = defaultdict(list)
    for s1, s2, dep in model_raw:
        key = tuple(sorted([s1, s2]))
        model_agg[key].append(dep)
    model_preds = {}
    for key, deps in model_agg.items():
        most_common = Counter(deps).most_common(1)[0][0]
        model_preds[key] = most_common

    # 解析黄金标准（黄金标准只标注有依赖的规则对）
    gold_raw = []
    for line in gold_data[idx]["deps"].strip().split("\n"):
        parsed = parse_gold_dep(line)
        if parsed:
            s1, s2, dep = parsed
            gold_raw.append((normalize_slot(s1), normalize_slot(s2), dep))

    gold_preds = {}
    for s1, s2, dep in gold_raw:
        key = tuple(sorted([s1, s2]))
        gold_preds[key] = dep

    # 对比：遍历黄金标准里有的规则对
    for key, gold_dep in gold_preds.items():
        total_gold_pairs += 1
        model_dep = model_preds.get(key)
        if model_dep is None:
            all_fn[gold_dep] += 1
            confusion[gold_dep]["__missing__"] += 1
            continue
        aligned_pairs += 1
        confusion[gold_dep][model_dep] += 1
        if model_dep == gold_dep:
            all_tp[gold_dep] += 1
        else:
            all_fp[model_dep] += 1
            all_fn[gold_dep] += 1

    # 处理 None：黄金标准里没标注的规则对，模型判 None 算 TN
    for key, model_dep in model_preds.items():
        if key not in gold_preds:
            if model_dep == "None":
                total_none_tn += 1
            else:
                all_fp[model_dep] += 1

# 计算每类的 F1
print(f"已评测: {len(df_s2)} 篇")
print(f"黄金标准总规则对: {total_gold_pairs}")
print(f"能对齐的规则对: {aligned_pairs} ({aligned_pairs/total_gold_pairs:.2%})")
print(f"None 判对（TN）: {total_none_tn}")
print()

# 手动设置 None 的 TP/FP/FN
none_tp = total_none_tn
none_fp = all_fp.get("None", 0)
none_fn = all_fn.get("None", 0)

for dep_type in ["Sequential", "Conditional", "Parallel"]:
    tp = all_tp.get(dep_type, 0)
    fp = all_fp.get(dep_type, 0)
    fn = all_fn.get(dep_type, 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    print(f"{dep_type}: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}, (TP={tp}, FP={fp}, FN={fn})")

precision = none_tp / (none_tp + none_fp) if (none_tp + none_fp) > 0 else 0
recall = none_tp / (none_tp + none_fn) if (none_tp + none_fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
print(f"None: P={precision:.3f}, R={recall:.3f}, F1={f1:.3f}, (TP={none_tp}, FP={none_fp}, FN={none_fn})")

# 宏平均
f1s = []
for dep_type in ["Sequential", "Conditional", "Parallel"]:
    tp = all_tp.get(dep_type, 0)
    fp = all_fp.get(dep_type, 0)
    fn = all_fn.get(dep_type, 0)
    precision = tp / (tp + fp) if (tp + fp) > 0 else 0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0
    f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
    f1s.append(f1)

precision = none_tp / (none_tp + none_fp) if (none_tp + none_fp) > 0 else 0
recall = none_tp / (none_tp + none_fn) if (none_tp + none_fn) > 0 else 0
f1 = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
f1s.append(f1)

print()
print(f"Macro F1: {sum(f1s) / len(f1s):.3f}")

# ===== 混淆矩阵 =====
print()
print("=" * 60)
print("混淆矩阵（行=黄金标准，列=模型预测）")
print("=" * 60)
print(f"{'':>15} {'Sequential':>12} {'Conditional':>12} {'Parallel':>12} {'None':>12} {'__missing__':>12}")
for gold_type in ["Sequential", "Conditional", "Parallel"]:
    row_str = f"{gold_type:>15}"
    for pred_type in ["Sequential", "Conditional", "Parallel", "None", "__missing__"]:
        count = confusion[gold_type].get(pred_type, 0)
        row_str += f" {count:>12}"
    print(row_str)