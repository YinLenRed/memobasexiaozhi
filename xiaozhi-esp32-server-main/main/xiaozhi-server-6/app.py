import sys
import uuid
import signal
import asyncio
from aioconsole import ainput

# 首先设置UTF-8编码环境，确保中文字符处理正常
from core.utils.encoding_helper import setup_utf8_environment
setup_utf8_environment()

from config.settings import load_config
from config.logger import setup_logging
from core.utils.util import get_local_ip, validate_mcp_endpoint
from core.http_server import SimpleHttpServer
from core.websocket_server import WebSocketServer
from core.utils.util import check_ffmpeg_installed
from core.mqtt.mqtt_manager import MQTTManager
from core.utils.modules_initialize import initialize_modules

TAG = __name__
logger = setup_logging()


async def wait_for_exit() -> None:
    """
    阻塞直到收到 Ctrl‑C / SIGTERM。
    - Unix: 使用 add_signal_handler
    - Windows: 依赖 KeyboardInterrupt
    """
    loop = asyncio.get_running_loop()
    stop_event = asyncio.Event()

    if sys.platform != "win32":  # Unix / macOS
        for sig in (signal.SIGINT, signal.SIGTERM):
            loop.add_signal_handler(sig, stop_event.set)
        await stop_event.wait()
    else:
        # Windows：await一个永远pending的fut，
        # 让 KeyboardInterrupt 冒泡到 asyncio.run，以此消除遗留普通线程导致进程退出阻塞的问题
        try:
            await asyncio.Future()
        except KeyboardInterrupt:  # Ctrl‑C
            pass


async def monitor_stdin():
    """监控标准输入，消费回车键"""
    while True:
        await ainput()  # 异步等待输入，消费回车


async def main():
    check_ffmpeg_installed()
    config = load_config()

    # 默认使用manager-api的secret作为auth_key
    # 如果secret为空，则生成随机密钥
    # auth_key用于jwt认证，比如视觉分析接口的jwt认证
    auth_key = config.get("manager-api", {}).get("secret", "")
    if not auth_key or len(auth_key) == 0 or "你" in auth_key:
        auth_key = str(uuid.uuid4().hex)
    config["server"]["auth_key"] = auth_key

    # 添加 stdin 监控任务
    stdin_task = asyncio.create_task(monitor_stdin())

    # 初始化共享的TTS和LLM实例（与WebSocket服务共享）
    modules = initialize_modules(
        logger,
        config,
        init_vad=False,  # MQTT服务不需要VAD
        init_asr=False,  # MQTT服务不需要ASR
        init_llm="LLM" in config.get("selected_module", {}),
        init_tts="TTS" in config.get("selected_module", {}),
        init_memory=False,  # MQTT服务暂不需要Memory
        init_intent=False,  # MQTT服务不需要Intent
    )
    
    shared_llm = modules.get("llm")
    shared_tts = modules.get("tts")
    
    if shared_llm:
        logger.bind(tag=TAG).info("共享LLM实例初始化成功")
    if shared_tts:
        logger.bind(tag=TAG).info("共享TTS实例初始化成功")
    
    # 先启动 WebSocket 服务器
    ws_server = WebSocketServer(config)
    ws_task = asyncio.create_task(ws_server.start())
    
    # 启动 MQTT 管理器（如果启用），传入WebSocket服务器实例
    mqtt_manager = None
    mqtt_task = None
    if config.get("mqtt", {}).get("enabled", False):
        mqtt_manager = MQTTManager(config, shared_llm, shared_tts, ws_server)
        mqtt_task = asyncio.create_task(mqtt_manager.start())
        logger.bind(tag=TAG).info("MQTT主动问候功能已启用")
    # 启动 Simple http 服务器
    ota_server = SimpleHttpServer(config, mqtt_manager)
    ota_task = asyncio.create_task(ota_server.start())

    read_config_from_api = config.get("read_config_from_api", False)
    port = int(config["server"].get("http_port", 8003))
    if not read_config_from_api:
        logger.bind(tag=TAG).info(
            "OTA接口是\t\thttp://{}:{}/xiaozhi/ota/",
            get_local_ip(),
            port,
        )
    logger.bind(tag=TAG).info(
        "视觉分析接口是\thttp://{}:{}/mcp/vision/explain",
        get_local_ip(),
        port,
    )
    logger.bind(tag=TAG).info(
        "Cron生成接口是\thttp://{}:{}/api/cron/generate",
        get_local_ip(),
        port,
    )
    mcp_endpoint = config.get("mcp_endpoint", None)
    if mcp_endpoint is not None and "你" not in mcp_endpoint:
        # 校验MCP接入点格式
        if validate_mcp_endpoint(mcp_endpoint):
            logger.bind(tag=TAG).info("mcp接入点是\t{}", mcp_endpoint)
            # 将mcp计入点地址转成调用点
            mcp_endpoint = mcp_endpoint.replace("/mcp/", "/call/")
            config["mcp_endpoint"] = mcp_endpoint
        else:
            logger.bind(tag=TAG).error("mcp接入点不符合规范")
            config["mcp_endpoint"] = "你的接入点 websocket地址"

    # 获取WebSocket配置，使用安全的默认值
    websocket_port = 8000
    server_config = config.get("server", {})
    if isinstance(server_config, dict):
        websocket_port = int(server_config.get("port", 8000))

    logger.bind(tag=TAG).info(
        "Websocket地址是\tws://{}:{}/xiaozhi/v1/",
        get_local_ip(),
        websocket_port,
    )

    logger.bind(tag=TAG).info(
        "=======上面的地址是websocket协议地址，请勿用浏览器访问======="
    )
    logger.bind(tag=TAG).info(
        "如想测试websocket请用谷歌浏览器打开test目录下的test_page.html"
    )
    logger.bind(tag=TAG).info(
        "=============================================================\n"
    )

    try:
        await wait_for_exit()  # 阻塞直到收到退出信号
    except asyncio.CancelledError:
        print("任务被取消，清理资源中...")
    finally:
        # 取消所有任务（关键修复点）
        stdin_task.cancel()
        ws_task.cancel()
        if ota_task:
            ota_task.cancel()
        if mqtt_task:
            mqtt_task.cancel()

        # 等待任务终止（必须加超时）
        tasks_to_wait = [stdin_task, ws_task]
        if ota_task:
            tasks_to_wait.append(ota_task)
        if mqtt_task:
            tasks_to_wait.append(mqtt_task)
            
        await asyncio.wait(
            tasks_to_wait,
            timeout=3.0,
            return_when=asyncio.ALL_COMPLETED,
        )
        print("服务器已关闭，程序退出。")


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("手动中断，程序终止。")
