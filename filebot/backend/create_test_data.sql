-- 创建测试数据用于TIFF提取功能测试

-- 1. 创建应用
INSERT INTO apps (id, name, description, owner_id, settings, created_by, created_at)
VALUES (
    '11111111-1111-1111-1111-111111111111',
    'TIFF测试应用',
    '用于TIFF页面提取功能测试',
    '590aba86-6038-4a72-911a-ce18ab7e0b75', -- admin用户ID
    '{}',
    'admin',
    datetime('now')
);

-- 2. 创建抽屉
INSERT INTO drawers (id, name, order_index, app_id, created_at)
VALUES (
    '22222222-2222-2222-2222-222222222222',
    'TIFF测试抽屉',
    1,
    '11111111-1111-1111-1111-111111111111',
    datetime('now')
);

-- 3. 创建文件夹
INSERT INTO folders (id, name, path, drawer_id, created_at)
VALUES (
    '33333333-3333-3333-3333-333333333333',
    'TIFF测试文件夹',
    '/tiff_test',
    '22222222-2222-2222-2222-222222222222',
    datetime('now')
);

-- 4. 创建文档记录（TIFF文件）
-- 首先，将TIFF文件复制到存储目录
-- 假设文件存储在: /mnt/c/workspace/tiff_input/fin00000.tif

-- 创建文档记录
INSERT INTO documents (
    id, folder_id, original_filename, stored_filename, 
    file_size, file_type, mime_type, uploaded_by,
    conversion_status, page_count, created_at
)
VALUES (
    '44444444-4444-4444-4444-444444444444',
    '33333333-3333-3333-3333-333333333333',
    'fin00000.tif',
    '44444444-4444-4444-4444-444444444444.tif', -- 使用UUID作为存储文件名
    10522, -- 实际文件大小
    'tiff',
    'image/tiff',
    '590aba86-6038-4a72-911a-ce18ab7e0b75', -- admin用户ID
    'completed',
    1,
    datetime('now')
);

-- 5. 确保文件存储目录存在并将文件复制到正确位置
-- 在shell中执行:
-- mkdir -p ./data/files/original
-- cp /mnt/c/workspace/tiff_input/fin00000.tif ./data/files/original/44444444-4444-4444-4444-444444444444.tif

SELECT '测试数据创建完成！' AS message;