-- 从页面 HTML 内容中提取 dcterms.modified 并回填 last_modified
-- 仅更新 last_modified 为空或近似导入时间的行（2026-05-12 之后）
-- 保留已手动编辑保存过的 last_modified（非导入时间戳）

-- Step 1: 预览要更新的行数
WITH parsed AS (
    SELECT 
        id,
        path,
        SUBSTR(
            content,
            INSTR(content, '<meta name="dcterms.modified" title="W3CDTF" content="') + 51,
            10
        ) AS meta_date,
        last_modified
    FROM webbot_page
    WHERE content LIKE '%dcterms.modified%'
      AND INSTR(content, '<meta name="dcterms.modified" title="W3CDTF" content="') > 0
)
SELECT 
    COUNT(*) AS total_match,
    COUNT(CASE WHEN meta_date BETWEEN '2025-01-01' AND '2027-12-31' THEN 1 END) AS valid_date,
    MIN(meta_date) AS earliest,
    MAX(meta_date) AS latest
FROM parsed;

-- Step 2: 执行更新
UPDATE webbot_page
SET last_modified = SUBSTR(
        content,
        INSTR(content, '<meta name="dcterms.modified" title="W3CDTF" content="') + 51,
        10
    )
WHERE content LIKE '%dcterms.modified%'
  AND INSTR(content, '<meta name="dcterms.modified" title="W3CDTF" content="') > 0
  AND SUBSTR(
        content,
        INSTR(content, '<meta name="dcterms.modified" title="W3CDTF" content="') + 51,
        10
  ) BETWEEN '2025-01-01' AND '2027-12-31';

-- Step 3: 确认结果
SELECT changes() AS rows_updated;
