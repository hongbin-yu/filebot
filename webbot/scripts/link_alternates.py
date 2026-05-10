#!/usr/bin/env python3
"""
配对 webbot_page 中的 EN/FR 页面。
从 FileBot documents 的 document_metadata 中读取 alternate_fr_url，
与 webbot_page 中的 FR 路径进行匹配，建立双向 other_language_path 关联。
"""

import json
import sqlite3
import sys
from urllib.parse import urlparse

DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"


def main():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()

    # 读取所有 boarding HTML 文档
    cur.execute("""
        SELECT id, path, document_metadata
        FROM documents
        WHERE path LIKE '/boarding/%'
          AND (file_type = 'HTML' OR mime_type = 'text/html')
          AND document_metadata IS NOT NULL
          AND document_metadata != ''
    """)
    docs = cur.fetchall()
    print(f"📄 检查 {len(docs)} 个文档的 alternate URLs")

    paired = 0
    errors = 0
    skipped = 0

    for doc in docs:
        doc_id = doc['id']
        doc_path = doc['path'] or ''
        raw = doc['document_metadata']

        meta = {}
        if raw:
            try:
                meta = json.loads(raw) if isinstance(raw, str) else raw
            except (json.JSONDecodeError, TypeError):
                continue

        # 判断语言
        lang = 'fr' if '/fr/' in doc_path else 'en'

        # 提取 alternate URL（EN 找 alternate_fr_url，FR 找 alternate_en_url）
        alt_field = 'alternate_fr_url' if lang == 'en' else 'alternate_en_url'
        alt_url = meta.get(alt_field)

        if not alt_url:
            continue

        # 从 alternate URL 解析路径
        try:
            alt_path = urlparse(alt_url).path  # e.g. /fr/gouvernement/min.html
        except Exception:
            continue

        # 去除 .html 后缀（dedup 后页面不含 .html）
        alt_base = alt_path[:-5] if alt_path.endswith('.html') else alt_path

        # 尝试多个候选路径（含/不含 .html、含/不含 /canadasite 前缀）
        candidates = [
            f'/boarding/canadasite{alt_path}',
            f'/canadasite{alt_path}',
            f'/canadasite{alt_base}',
            f'{alt_path}',
            f'{alt_base}',
        ]

        # 查找 webbot_page 中的对应页面
        alt_row = None
        for c in candidates:
            alt_row = cur.execute('SELECT id, path, language FROM webbot_page WHERE path = ?', (c,)).fetchone()
            if alt_row:
                break

        if not alt_row:
            skipped += 1
            continue

        # 获取 webbot_page 中当前文档对应的页面
        # 文档 ID 即为 webbot_page ID（导入时使用了相同的 ID）
        cur.execute('SELECT id, path, language, other_language_path FROM webbot_page WHERE id = ?', (doc_id,))
        my_row = cur.fetchone()
        if not my_row:
            skipped += 1
            continue

        alt_id = alt_row['id']
        alt_path = alt_row['path']
        my_id = my_row['id']
        my_path = my_row['path']

        # 确认语言匹配
        expected_lang = 'fr' if lang == 'en' else 'en'
        if alt_row['language'] != expected_lang:
            print(f"  ⚠️  语言不匹配: {doc_path} → {alt_row['path']} (期望 {expected_lang}, 实际 {alt_row['language']})")

        if not doc_id or not alt_id:
            errors += 1
            continue

        # 已配对则跳过
        if my_row['other_language_path'] == alt_id:
            continue

        # 写入双向配对（存储 PATH 而非 ID）
        cur.execute("UPDATE webbot_page SET other_language_path = ? WHERE id = ?", (alt_path, my_id))
        cur.execute("UPDATE webbot_page SET other_language_path = ? WHERE id = ?", (my_path, alt_id))
        paired += 1

        if paired % 50 == 0:
            print(f"  进度: 已配对 {paired} 对...")

    conn.commit()
    conn.close()

    print(f"\n✅ 完成!")
    print(f"  已配对: {paired} 对")
    print(f"  无匹配: {skipped}")
    print(f"  错误: {errors}")


if __name__ == '__main__':
    main()
