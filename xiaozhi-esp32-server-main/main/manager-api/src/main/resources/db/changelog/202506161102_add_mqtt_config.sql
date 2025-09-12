-- 添加MQTT配置参数
-- 此文件用于初始化MQTT相关的系统参数，无需手动执行，在项目启动时会自动执行

-- 删除可能已存在的MQTT配置参数（清理旧数据）
DELETE FROM sys_params WHERE id BETWEEN 500 AND 520;

-- 添加MQTT基础配置
INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date) VALUES 
(500, 'mqtt.enabled', 'true', 'boolean', 1, '是否启用MQTT功能', 1, NOW(), 1, NOW()),
(501, 'mqtt.host', '47.97.185.142', 'string', 1, 'MQTT代理服务器地址', 1, NOW(), 1, NOW()),
(502, 'mqtt.port', '1883', 'number', 1, 'MQTT代理服务器端口', 1, NOW(), 1, NOW()),
(503, 'mqtt.username', 'admin', 'string', 1, 'MQTT用户名', 1, NOW(), 1, NOW()),
(504, 'mqtt.password', 'Jyxd@2025', 'string', 1, 'MQTT密码', 1, NOW(), 1, NOW()),
(505, 'mqtt.client_id', '', 'string', 1, 'MQTT客户端ID，为空时自动生成', 1, NOW(), 1, NOW());

-- 添加MQTT主题配置
INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date) VALUES 
(510, 'mqtt.topics.command', 'device/{device_id}/cmd', 'string', 1, '设备命令主题模板', 1, NOW(), 1, NOW()),
(511, 'mqtt.topics.ack', 'device/{device_id}/ack', 'string', 1, '设备回复主题模板', 1, NOW(), 1, NOW()),
(512, 'mqtt.topics.event', 'device/{device_id}/event', 'string', 1, '设备事件主题模板', 1, NOW(), 1, NOW());

-- 添加主动问候配置
INSERT INTO sys_params (id, param_code, param_value, value_type, param_type, remark, creator, create_date, updater, update_date) VALUES 
(520, 'proactive_greeting.enabled', 'true', 'boolean', 1, '是否启用主动问候功能', 1, NOW(), 1, NOW()),
(521, 'proactive_greeting.content_generation.max_length', '100', 'number', 1, '主动问候内容最大字符数', 1, NOW(), 1, NOW()),
(522, 'proactive_greeting.content_generation.use_memory', 'true', 'boolean', 1, '是否使用记忆信息生成问候', 1, NOW(), 1, NOW()),
(523, 'proactive_greeting.content_generation.use_user_info', 'true', 'boolean', 1, '是否使用用户信息生成问候', 1, NOW(), 1, NOW());
