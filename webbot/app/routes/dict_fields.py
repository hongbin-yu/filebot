"""字典映射通用工具（io/convert 与 mustache 渲染共用）。

数据行字段（如 status='O'、subjects='CM,EM'）→ 双语字典（{code: {en, fr}}）查表，
注入 compute fields（mustache 不支持 {{Status[status]}} 动态键，映射在数据层完成）：
  - 标量：{field}_obj = {code, en, fr}，{field}_label = 按 lang 选中的字符串
  - 逗号分隔：{field}_list = [{code, en, fr, last}, ...]，{field}_label = join(", ")，
    单数别名 {field[:-1]}_list（subjects → subject_list，老板指定 compute field 名）

调用方不传字典时完全无副作用 → io/convert 保持通用。
"""
from typing import Any, List


def _enrich_row(row: dict, mapping_name: str, mapping: dict, lang: str) -> None:
    """对单行应用单个字典（字典名与行字段大小写兼容：Status→status）。"""
    field_name = mapping_name if mapping_name in row else mapping_name.lower()
    if field_name not in row:
        return
    v = row[field_name]
    # 数组字段：含逗号（多值）或复数字段名（subjects 单值也应 split 成数组）
    is_list_field = (isinstance(v, str) and "," in v) or \
        (field_name.endswith("s") and len(field_name) > 1 and isinstance(v, (str, int)))
    if is_list_field:
        codes = [c.strip() for c in v.split(",") if c.strip()]
        if not codes:
            return
        items, labels = [], []
        for idx, c in enumerate(codes):
            mv = mapping.get(c)
            if isinstance(mv, dict):
                items.append({"code": c, "en": mv.get("en", c), "fr": mv.get("fr", c),
                              "last": idx == len(codes) - 1})
                labels.append(mv.get(lang) or mv.get("en") or c)
            else:
                items.append({"code": c, "en": c, "fr": c, "last": idx == len(codes) - 1})
                labels.append(str(mv) if mv is not None else c)
        row[f"{field_name}_list"] = items
        if field_name.endswith("s") and len(field_name) > 1:
            row[f"{field_name[:-1]}_list"] = items
        row[f"{field_name}_label"] = ", ".join(labels)
    elif isinstance(v, (str, int)):
        mv = mapping.get(str(v))
        if isinstance(mv, dict):
            row[f"{field_name}_obj"] = {"code": v, "en": mv.get("en", v), "fr": mv.get("fr", v)}
            row[f"{field_name}_label"] = mv.get(lang) or mv.get("en") or v
        elif mv is not None:
            row[f"{field_name}_label"] = mv


def enrich_dictionary_fields(ctx: dict, lang: str = "en") -> None:
    """mustache 渲染上下文版：ctx 顶层含字典（值含 dict 的），作用于 ctx['data'] 行列表。

    跳过 data/query/labels/items/datasource_* 等非字典字段。
    """
    data = ctx.get("data")
    if not isinstance(data, list):
        return
    skip = {"data", "query", "labels", "items", "datasource_raw",
            "datasource_loaded", "datasource_error"}
    for mapping_name, mapping in list(ctx.items()):
        if mapping_name in skip or not isinstance(mapping, dict) or not mapping:
            continue
        # 只处理"字典条目值"型映射（值含 dict 如 {en, fr}）；labels 由 _enrich_label_fields 处理
        if not any(isinstance(v, dict) for v in mapping.values()):
            continue
        for row in data:
            if isinstance(row, dict):
                _enrich_row(row, mapping_name, mapping, lang)


def apply_dictionary_to_rows(rows: List[dict], dictionary: dict, lang: str = "en") -> List[str]:
    """io/convert 版：对行列表应用传入的字典，返回实际应用的字典名列表。

    dictionary 形如 {"Status": {"O": {"en": "...", "fr": "..."}}, "Subjects": {...}}
    """
    applied: List[str] = []
    if not isinstance(rows, list) or not isinstance(dictionary, dict):
        return applied
    for mapping_name, mapping in dictionary.items():
        if not isinstance(mapping, dict) or not mapping:
            continue
        if not any(isinstance(v, dict) for v in mapping.values()):
            continue
        for row in rows:
            if isinstance(row, dict):
                _enrich_row(row, mapping_name, mapping, lang)
        applied.append(mapping_name)
    return applied
