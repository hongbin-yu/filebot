#!/bin/bash

echo "🔍 Smart iAdmin数据源定位工具"
echo "=============================="
echo ""

# 1. 检查Java环境
echo "1. Java环境检查:"
java -version 2>&1 | head -1
echo ""

# 2. 查找HSQLDB数据库文件
echo "2. 查找HSQLDB数据库文件 (*.script, *.properties, *.data):"
find /mnt/c/workspace/smarti-admin -type f \( -name "*.script" -o -name "*.properties" -o -name "*.data" -o -name "*.backup" \) 2>/dev/null | head -10
if [ $? -ne 0 ]; then
    echo "   未找到HSQLDB数据库文件"
fi
echo ""

# 3. 检查数据库连接配置
echo "3. 数据库连接配置检查:"
echo "   3.1 主配置文件:"
if [ -f "/mnt/c/workspace/smarti-admin/conf/smarti-admin.properties" ]; then
    grep -A5 -B2 "jdbc\." /mnt/c/workspace/smarti-admin/conf/smarti-admin.properties 2>/dev/null || echo "   无法读取配置文件"
else
    echo "   配置文件不存在: conf/smarti-admin.properties"
fi

echo ""
echo "   3.2 Hibernate配置文件:"
find /mnt/c/workspace/smarti-admin -name "hibernate*.properties" -o -name "hibernate*.cfg.xml" 2>/dev/null | head -5
echo ""

# 4. 检查data目录
echo "4. 检查data目录结构:"
if [ -d "/mnt/c/workspace/smarti-admin/data" ]; then
    ls -la /mnt/c/workspace/smarti-admin/data/
else
    echo "   没有data目录"
fi
echo ""

# 5. 检查war文件中是否包含数据库
echo "5. 检查WAR文件中是否包含数据库:"
find /mnt/c/workspace/smarti-admin -name "*.war" 2>/dev/null | head -3
if [ $? -eq 0 ]; then
    echo "   发现WAR文件，可能包含嵌入式数据库"
fi
echo ""

# 6. 检查其他可能的数据文件
echo "6. 检查其他数据文件 (*.sql, *.csv, *.txt, *.xml):"
find /mnt/c/workspace/smarti-admin -type f \( -name "*.sql" -o -name "*.csv" -o -name "*.txt" -o -name "*.xml" \) 2>/dev/null | grep -v target | grep -v ".git" | head -10
echo ""

# 7. 检查运行中的HSQLDB服务
echo "7. 检查运行中的HSQLDB服务:"
netstat -tlnp 2>/dev/null | grep :9001 || echo "   端口9001未监听 (HSQLDB默认端口)"
ps aux 2>/dev/null | grep -i hsqldb | grep -v grep || echo "   未发现HSQLDB进程"
echo ""

# 8. 检查系统级数据库文件
echo "8. 检查系统级数据库文件 (可能在其他位置):"
find /home -name "*.script" 2>/dev/null | head -5
find /tmp -name "*.script" 2>/dev/null | head -3
echo ""

echo "=============================="
echo "🔧 总结和建议"
echo ""

# 分析结果并提供建议
if [ -f "/mnt/c/workspace/smarti-admin/conf/smarti-admin.properties" ]; then
    echo "✅ 发现主配置文件"
    DB_TYPE=$(grep "jdbc.url" /mnt/c/workspace/smarti-admin/conf/smarti-admin.properties 2>/dev/null | head -1)
    if [ ! -z "$DB_TYPE" ]; then
        echo "   数据库类型: $DB_TYPE"
        
        if [[ "$DB_TYPE" == *"hsqldb"* ]]; then
            echo "   建议: 使用HSQLDB导出脚本，可能需要启动数据库服务"
        elif [[ "$DB_TYPE" == *"sybase"* ]]; then
            echo "   建议: 需要Sybase客户端工具或JDBC连接"
        elif [[ "$DB_TYPE" == *"oracle"* ]]; then
            echo "   建议: 需要Oracle客户端工具或JDBC连接"
        elif [[ "$DB_TYPE" == *"mysql"* ]]; then
            echo "   建议: 可以使用mysql命令行工具导出"
        else
            echo "   建议: 需要针对特定数据库类型的导出工具"
        fi
    fi
else
    echo "⚠️  未找到主配置文件"
fi

echo ""
echo "🎯 下一步行动建议:"
echo "1. 如果找到.script文件: 运行 export_hsqldb_simple.py"
echo "2. 如果找到其他数据库配置: 告诉我类型，我提供对应导出工具"
echo "3. 如果都找不到: 使用演示数据验证流程，再寻找实际数据源"
echo ""

echo "📋 推荐执行的命令:"
echo "   # 如果上述检查发现.script文件:"
echo "   python3 export_hsqldb_simple.py --db-file <路径> --download-jar"
echo ""
echo "   # 如果都没找到，验证转换流程:"
echo "   python3 filebot_coldreport_integration_demo.py"
echo ""

echo "💡 需要更多帮助? 请告诉我具体发现了什么文件或配置。"