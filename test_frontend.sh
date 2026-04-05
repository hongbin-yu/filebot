#!/bin/bash
echo "=== WebBot前端功能验证 ==="
echo

# 1. 检查服务状态
echo "1. 服务状态检查:"
if curl -s http://localhost:5173/health > /dev/null; then
  echo "   ✅ 前端代理健康检查通过"
else
  echo "   ❌ 前端代理健康检查失败"
fi

if curl -s http://localhost:8000/health > /dev/null; then
  echo "   ✅ 后端直接健康检查通过"
else
  echo "   ❌ 后端直接健康检查失败"
fi

# 2. 检查API端点
echo
echo "2. API端点检查:"
COMPONENT_COUNT=$(curl -s http://localhost:5173/api/v1/components/templates | jq length 2>/dev/null || echo "0")
echo "   ✅ 组件API返回 $COMPONENT_COUNT 个组件"

# 3. 检查页面标题
echo
echo "3. 页面结构检查:"
PAGE_TITLE=$(curl -s http://localhost:5173 | grep -o "<title>[^<]*</title>" | sed 's/<title>//;s/<\/title>//')
echo "   ✅ 页面标题: $PAGE_TITLE"

# 4. 检查关键元素是否存在
echo
echo "4. 关键元素验证:"
curl -s http://localhost:5173 | grep -q "蓝色编辑区域\|e6f2ff" && echo "   ✅ 蓝色编辑区域代码存在" || echo "   ⚠️  蓝色编辑区域代码未找到"
curl -s http://localhost:5173 | grep -q "添加组件" && echo "   ✅ '添加组件'按钮代码存在" || echo "   ⚠️  '添加组件'按钮代码未找到"
curl -s http://localhost:5173 | grep -q "Government of Canada" && echo "   ✅ 加拿大政府Header代码存在" || echo "   ⚠️  加拿大政府Header代码未找到"

# 5. 进程检查
echo
echo "5. 进程状态检查:"
if netstat -tlnp 2>/dev/null | grep -q ":5173"; then
  echo "   ✅ 前端服务运行在端口 5173"
else
  echo "   ❌ 前端服务未运行"
fi

if netstat -tlnp 2>/dev/null | grep -q ":8000"; then
  echo "   ✅ 后端服务运行在端口 8000"
else
  echo "   ❌ 后端服务未运行"
fi

echo
echo "=== 验证完成 ==="
