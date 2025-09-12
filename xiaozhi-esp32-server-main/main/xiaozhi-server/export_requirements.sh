#!/bin/bash

echo "🔍 导出当前环境的所有已安装包 (UV版本)"
echo "=================================="

# 检查虚拟环境
if [[ "$VIRTUAL_ENV" != "" ]]; then
    echo "✅ 当前虚拟环境: $VIRTUAL_ENV"
else
    echo "⚠️  未检测到虚拟环境"
fi

# 检查使用的包管理器
if command -v uv &> /dev/null; then
    PIP_CMD="uv pip"
    echo "✅ 使用UV包管理器"
elif command -v pip &> /dev/null; then
    PIP_CMD="pip"
    echo "✅ 使用标准pip"
else
    echo "❌ 未找到pip或uv命令"
    exit 1
fi

echo ""
echo "📦 方法1: 导出所有包（包含版本号）"
$PIP_CMD freeze > requirements_full.txt
echo "✅ 已导出到: requirements_full.txt"

echo ""
echo "📦 方法2: 导出项目直接依赖"
$PIP_CMD list --format=freeze > requirements_direct.txt
echo "✅ 已导出到: requirements_direct.txt"

echo ""
echo "📦 方法3: 使用uv专用导出"
if command -v uv &> /dev/null; then
    uv pip freeze > requirements_uv.txt
    echo "✅ 已导出到: requirements_uv.txt"
fi

echo ""
echo "📊 统计信息："
echo "- 总包数量: $($PIP_CMD list | wc -l)"
echo "- freeze包数量: $($PIP_CMD freeze | wc -l)"

echo ""
echo "📋 生成的文件："
ls -la requirements_*.txt

echo ""
echo "🚀 使用方法："
echo "在新服务器上运行:"
echo "  - 使用uv: uv pip install -r requirements_full.txt"
echo "  - 使用pip: pip install -r requirements_full.txt"
