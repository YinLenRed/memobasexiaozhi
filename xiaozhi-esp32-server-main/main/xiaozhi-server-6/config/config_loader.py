import os
import yaml
from collections.abc import Mapping
from config.manage_api_client import init_service, get_server_config, get_agent_models


def get_project_dir():
    """获取项目根目录"""
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__))) + "/"


def read_config(config_path):
    with open(config_path, "r", encoding="utf-8") as file:
        config = yaml.safe_load(file)
    return config


def load_config():
    """加载配置文件"""
    from core.utils.cache.manager import cache_manager, CacheType

    # 检查缓存
    cached_config = cache_manager.get(CacheType.CONFIG, "main_config")
    if cached_config is not None:
        return cached_config

    default_config_path = get_project_dir() + "config.yaml"
    custom_config_path = get_project_dir() + "data/.config.yaml"

    # 加载默认配置
    default_config = read_config(default_config_path)
    custom_config = read_config(custom_config_path)

    if custom_config.get("manager-api", {}).get("url"):
        config = get_config_from_api(custom_config)
    else:
        # 合并配置
        config = merge_configs(default_config, custom_config)
    # 初始化目录
    ensure_directories(config)

    # 缓存配置
    cache_manager.set(CacheType.CONFIG, "main_config", config)
    return config


def get_config_from_api(config):
    """从Java API获取配置"""
    # 初始化API客户端
    init_service(config)

    # 获取服务器配置（Java返回的原始响应）
    java_response = get_server_config()
    if java_response is None:
        raise Exception("Failed to fetch server config from API")

    # 适配Java API返回的结构
    config_data = adapt_java_config_response(java_response)
    if config_data is None:
        raise Exception("Failed to adapt Java config response")

    config_data["read_config_from_api"] = True
    config_data["manager-api"] = {
        "url": config["manager-api"].get("url", ""),
        "secret": config["manager-api"].get("secret", ""),
    }
    # server的配置以本地为准
    if config.get("server"):
        config_data["server"] = {
            "ip": config["server"].get("ip", ""),
            "port": config["server"].get("port", ""),
            "http_port": config["server"].get("http_port", ""),
            "vision_explain": config["server"].get("vision_explain", ""),
            "auth_key": config["server"].get("auth_key", ""),
        }
    return config_data


def adapt_java_config_response(java_response):
    """
    适配Java API返回的配置格式
    
    支持多种Java响应格式
    """
    if not java_response:
        print("⚠️ Java响应为空")
        return None
    
    print(f"🔍 调试：Java原始响应类型: {type(java_response)}")
    print(f"🔍 调试：Java响应内容: {java_response}")
    
    # 处理不同的响应格式
    config_data = None
    
    # 格式1: 标准API响应 {code, msg, data}
    if isinstance(java_response, dict) and 'data' in java_response:
        print("📋 检测到标准API响应格式")
        config_data = java_response['data']
    
    # 格式2: 直接配置对象 (没有包装)
    elif isinstance(java_response, dict):
        print("📋 检测到直接配置格式")
        config_data = java_response
    
    # 格式3: 字符串响应 (如"Server is running")
    elif isinstance(java_response, str):
        print(f"⚠️ Java返回字符串而不是JSON: {java_response}")
        return None
    
    else:
        print(f"❌ 不支持的响应格式: {type(java_response)}")
        return None
    
    if not config_data:
        print("❌ 无法提取配置数据")
        return None
    
    # 使用提取的配置数据
    config = config_data.copy()
    
    print(f"🔍 配置数据内容: {list(config.keys())}")
    
    # 处理嵌套的mqtt配置
    if 'mqtt' in config and isinstance(config['mqtt'], dict):
        print("📋 发现mqtt配置段，开始处理...")
        mqtt_config = config.pop('mqtt')
        
        # 创建mqtt配置结构
        mqtt_section = {}
        proactive_greeting_section = {}
        
        print(f"🔍 MQTT配置项: {list(mqtt_config.keys())}")
        
        for key, value in mqtt_config.items():
            # 处理类型转换
            if value == 'true':
                converted_value = True
            elif value == 'false':
                converted_value = False
            elif isinstance(value, str) and value.isdigit():
                converted_value = int(value)
            else:
                converted_value = value
            
            # 按配置类型分组
            if key.startswith('mqtt.'):
                # 去掉mqtt.前缀，构建嵌套结构
                sub_key = key[5:]  # 去掉 "mqtt."
                if '.' in sub_key:
                    # 处理嵌套配置如 topics.command
                    parts = sub_key.split('.')
                    current = mqtt_section
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = converted_value
                else:
                    mqtt_section[sub_key] = converted_value
            elif key.startswith('proactive_greeting.'):
                # 处理主动问候配置
                sub_key = key[19:]  # 去掉 "proactive_greeting."
                if '.' in sub_key:
                    parts = sub_key.split('.')
                    current = proactive_greeting_section
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = converted_value
                else:
                    proactive_greeting_section[sub_key] = converted_value
        
        # 添加到主配置中
        if mqtt_section:
            config['mqtt'] = mqtt_section
            print(f"✅ 已处理MQTT配置: {list(mqtt_section.keys())}")
        if proactive_greeting_section:
            config['proactive_greeting'] = proactive_greeting_section
            print(f"✅ 已处理主动问候配置: {list(proactive_greeting_section.keys())}")
    
    else:
        print("⚠️ 未找到mqtt配置段，或配置格式不正确")
        # 兜底策略：直接查找mqtt.*配置项
        mqtt_section = {}
        proactive_greeting_section = {}
        
        for key, value in config.items():
            if key.startswith('mqtt.'):
                # 处理类型转换
                if value == 'true':
                    converted_value = True
                elif value == 'false':
                    converted_value = False
                elif isinstance(value, str) and value.isdigit():
                    converted_value = int(value)
                else:
                    converted_value = value
                
                # 构建嵌套结构
                sub_key = key[5:]  # 去掉 "mqtt."
                if '.' in sub_key:
                    parts = sub_key.split('.')
                    current = mqtt_section
                    for part in parts[:-1]:
                        if part not in current:
                            current[part] = {}
                        current = current[part]
                    current[parts[-1]] = converted_value
                else:
                    mqtt_section[sub_key] = converted_value
        
        if mqtt_section:
            config['mqtt'] = mqtt_section
            print(f"✅ 兜底处理MQTT配置: {list(mqtt_section.keys())}")
    
    print(f"🎯 最终配置结构: {list(config.keys())}")
    
    # 确保LLM和TTS配置存在，如果从Java API获取的配置中没有，则使用默认配置
    _ensure_llm_tts_config(config)
    
    return config


def _ensure_llm_tts_config(config):
    """确保LLM和TTS配置存在"""
    # 静默检查和补充配置，不输出日志
    
    # 检查是否有LLM配置
    if not config.get("LLM") or not config.get("selected_module", {}).get("LLM"):
        default_config = _get_default_llm_tts_config()
        
        if "LLM" not in config:
            config["LLM"] = default_config["LLM"]
        
        if "selected_module" not in config:
            config["selected_module"] = {}
        if "LLM" not in config["selected_module"]:
            config["selected_module"]["LLM"] = default_config["selected_module"]["LLM"]
    
    # 检查是否有TTS配置
    if not config.get("TTS") or not config.get("selected_module", {}).get("TTS"):
        default_config = _get_default_llm_tts_config()
        
        if "TTS" not in config:
            config["TTS"] = default_config["TTS"]
        
        if "selected_module" not in config:
            config["selected_module"] = {}
        if "TTS" not in config["selected_module"]:
            config["selected_module"]["TTS"] = default_config["selected_module"]["TTS"]


def _get_default_llm_tts_config():
    """获取默认的LLM和TTS配置"""
    # 从原始config.yaml文件加载默认配置
    default_config_path = get_project_dir() + "config.yaml"
    default_config = read_config(default_config_path)
    
    return {
        "LLM": default_config.get("LLM", {}),
        "TTS": default_config.get("TTS", {}),
        "selected_module": {
            "LLM": default_config.get("selected_module", {}).get("LLM", "ChatGLMLLM"),
            "TTS": default_config.get("selected_module", {}).get("TTS", "EdgeTTS")
        }
    }


def get_private_config_from_api(config, device_id, client_id):
    """从Java API获取私有配置"""
    return get_agent_models(device_id, client_id, config["selected_module"])


def ensure_directories(config):
    """确保所有配置路径存在"""
    dirs_to_create = set()
    project_dir = get_project_dir()  # 获取项目根目录
    # 日志文件目录
    log_dir = config.get("log", {}).get("log_dir", "tmp")
    dirs_to_create.add(os.path.join(project_dir, log_dir))

    # ASR/TTS模块输出目录
    for module in ["ASR", "TTS"]:
        if config.get(module) is None:
            continue
        for provider in config.get(module, {}).values():
            output_dir = provider.get("output_dir", "")
            if output_dir:
                dirs_to_create.add(output_dir)

    # 根据selected_module创建模型目录
    selected_modules = config.get("selected_module", {})
    for module_type in ["ASR", "LLM", "TTS"]:
        selected_provider = selected_modules.get(module_type)
        if not selected_provider:
            continue
        if config.get(module) is None:
            continue
        if config.get(selected_provider) is None:
            continue
        provider_config = config.get(module_type, {}).get(selected_provider, {})
        output_dir = provider_config.get("output_dir")
        if output_dir:
            full_model_dir = os.path.join(project_dir, output_dir)
            dirs_to_create.add(full_model_dir)

    # 统一创建目录（保留原data目录创建）
    for dir_path in dirs_to_create:
        try:
            os.makedirs(dir_path, exist_ok=True)
        except PermissionError:
            print(f"警告：无法创建目录 {dir_path}，请检查写入权限")


def merge_configs(default_config, custom_config):
    """
    递归合并配置，custom_config优先级更高

    Args:
        default_config: 默认配置
        custom_config: 用户自定义配置

    Returns:
        合并后的配置
    """
    if not isinstance(default_config, Mapping) or not isinstance(
        custom_config, Mapping
    ):
        return custom_config

    merged = dict(default_config)

    for key, value in custom_config.items():
        if (
            key in merged
            and isinstance(merged[key], Mapping)
            and isinstance(value, Mapping)
        ):
            merged[key] = merge_configs(merged[key], value)
        else:
            merged[key] = value

    return merged
