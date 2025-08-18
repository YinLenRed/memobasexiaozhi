import asyncio
from aiohttp import web
from config.logger import setup_logging
from core.api.ota_handler import OTAHandler
from core.api.vision_handler import VisionHandler
from core.api.greeting_handler import GreetingHandler

TAG = __name__


class SimpleHttpServer:
    def __init__(self, config: dict, mqtt_manager=None):
        self.config = config
        self.mqtt_manager = mqtt_manager
        self.logger = setup_logging()
        self.ota_handler = OTAHandler(config)
        self.vision_handler = VisionHandler(config)
        self.greeting_handler = GreetingHandler(config, mqtt_manager)

    def _get_websocket_url(self, local_ip: str, port: int) -> str:
        """获取websocket地址

        Args:
            local_ip: 本地IP地址
            port: 端口号

        Returns:
            str: websocket地址
        """
        server_config = self.config["server"]
        websocket_config = server_config.get("websocket")

        if websocket_config and "你" not in websocket_config:
            return websocket_config
        else:
            return f"ws://{local_ip}:{port}/xiaozhi/v1/"

    async def start(self):
        server_config = self.config["server"]
        host = server_config.get("ip", "0.0.0.0")
        port = int(server_config.get("http_port", 8003))

        if port:
            app = web.Application()

            read_config_from_api = server_config.get("read_config_from_api", False)

            if not read_config_from_api:
                # 如果没有开启智控台，只是单模块运行，就需要再添加简单OTA接口，用于下发websocket接口
                app.add_routes(
                    [
                        web.get("/xiaozhi/ota/", self.ota_handler.handle_get),
                        web.post("/xiaozhi/ota/", self.ota_handler.handle_post),
                        web.options("/xiaozhi/ota/", self.ota_handler.handle_post),
                    ]
                )
            # 添加路由
            app.add_routes(
                [
                    web.get("/mcp/vision/explain", self.vision_handler.handle_get),
                    web.post("/mcp/vision/explain", self.vision_handler.handle_post),
                    web.options("/mcp/vision/explain", self.vision_handler.handle_post),
                ]
            )
            
            # 添加主动问候API路由
            if self.mqtt_manager:
                app.add_routes(
                    [
                        web.post("/xiaozhi/greeting/send", self.greeting_handler.handle_post),
                        web.get("/xiaozhi/greeting/status", self.greeting_handler.handle_get),
                        web.options("/xiaozhi/greeting/send", self.greeting_handler.handle_options),
                        web.options("/xiaozhi/greeting/status", self.greeting_handler.handle_options),
                        web.post("/xiaozhi/user/profile", self.greeting_handler.handle_user_profile),
                        web.get("/xiaozhi/user/profile", self.greeting_handler.handle_user_profile),
                        web.options("/xiaozhi/user/profile", self.greeting_handler.handle_options),
                    ]
                )

            # 运行服务
            runner = web.AppRunner(app)
            await runner.setup()
            site = web.TCPSite(runner, host, port)
            await site.start()

            # 保持服务运行
            while True:
                await asyncio.sleep(3600)  # 每隔 1 小时检查一次
