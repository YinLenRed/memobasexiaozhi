#!/bin/bash
# Python主动天气播报测试脚本

echo "🌤️ Python主动天气播报测试"
echo "========================================"

# 配置信息
API_URL="http://47.98.51.180:8003/xiaozhi/greeting/send"
DEVICE_ID="f0:9e:9e:04:8a:44"

echo "📋 API端点: $API_URL"
echo "🎯 目标设备: $DEVICE_ID"
echo ""

# 测试1: 日常天气播报
echo "🌞 测试1: 日常天气播报"
echo "--------------------------------"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": \"$DEVICE_ID\",
    \"category\": \"weather\",
    \"initial_content\": \"北京今天晴天，温度18-25度，微风，空气质量良好，适合外出活动\",
    \"user_info\": {
      \"custom_prompt\": \"请用轻松友好的语调播报今日天气，让用户了解出行注意事项\"
    }
  }"

echo -e "\n\n"

# 测试2: 天气预警
echo "⚠️ 测试2: 天气预警播报"
echo "--------------------------------"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": \"$DEVICE_ID\",
    \"category\": \"weather\",
    \"initial_content\": \"北京发布大风蓝色预警，阵风可达6-7级，请注意防范，避免户外活动\",
    \"user_info\": {
      \"custom_prompt\": \"这是天气预警信息，请用清晰严肃的语调播报，提醒用户注意安全\"
    }
  }"

echo -e "\n\n"

# 测试3: 简单天气播报
echo "☀️ 测试3: 简单天气播报"
echo "--------------------------------"

curl -X POST "$API_URL" \
  -H "Content-Type: application/json" \
  -d "{
    \"device_id\": \"$DEVICE_ID\",
    \"category\": \"weather\",
    \"initial_content\": \"测试天气播报：现在天气晴朗，温度20度，适合外出\"
  }"

echo -e "\n\n"
echo "✅ 天气播报测试完成！"
echo "💡 如果API调用成功，硬件应该会播放语音"
echo "📊 检查返回的JSON响应确认状态"
