#!/bin/bash
echo "🔍 查找Smart iAdmin数据源..."
echo "1. 查找HSQLDB数据库文件:"
find /home /mnt -name "*.script" -o -name "*.properties" -o -name "*.data" 2>/dev/null | grep -i smarti | head -10

echo -e "\n2. 检查数据库配置:"
grep -r "jdbc:" /mnt/c/workspace/smarti-admin/ 2>/dev/null | grep -v ".class" | head -10

echo -e "\n3. 查看配置文件:"
cat /mnt/c/workspace/smarti-admin/conf/smarti-admin.properties 2>/dev/null | grep -A2 -B2 "jdbc.url\|jdbc.username\|DATABASE"

echo -e "\n4. 检查是否有数据备份:"
find /mnt/c/workspace/smarti-admin -name "*.backup" -o -name "*.dump" -o -name "*.export" 2>/dev/null | head -5
