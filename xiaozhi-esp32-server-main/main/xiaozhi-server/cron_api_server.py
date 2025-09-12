#!/usr/bin/env python3
"""
Cron表达式生成HTTP API服务器
为Java后端提供HTTP接口调用cron生成功能
"""

import sys
import os
from datetime import datetime
import json
from http.server import HTTPServer, BaseHTTPRequestHandler
import urllib.parse as urlparse

sys.path.append('.')
from api_cron_generator import CronAPI


class CronAPIHandler(BaseHTTPRequestHandler):
    """HTTP请求处理器"""
    
    def _send_response(self, status_code, data, content_type='application/json'):
        """发送响应"""
        self.send_response(status_code)
        self.send_header('Content-Type', f'{content_type}; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.end_headers()
        
        if isinstance(data, dict) or isinstance(data, list):
            response_data = json.dumps(data, ensure_ascii=False, indent=2)
        else:
            response_data = str(data)
            
        self.wfile.write(response_data.encode('utf-8'))
    
    def _send_error_response(self, status_code, message):
        """发送错误响应"""
        error_data = {
            "success": False,
            "error": message,
            "timestamp": datetime.now().isoformat(),
            "status_code": status_code
        }
        self._send_response(status_code, error_data)
    
    def do_OPTIONS(self):
        """处理预检请求"""
        self._send_response(200, {"message": "OK"})
    
    def do_GET(self):
        """处理GET请求"""
        parsed_path = urlparse.urlparse(self.path)
        path = parsed_path.path
        
        if path == '/':
            # 首页 - 显示API文档
            self._handle_home()
        elif path == '/health':
            # 健康检查
            self._handle_health()
        elif path == '/api/cron/generate':
            # GET方式生成cron表达式
            self._handle_get_generate(parsed_path.query)
        else:
            self._send_error_response(404, "API端点不存在")
    
    def do_POST(self):
        """处理POST请求"""
        if self.path == '/api/cron/generate':
            self._handle_post_generate()
        elif self.path == '/api/cron/batch-generate':
            self._handle_batch_generate()
        elif self.path == '/api/cron/validate':
            self._handle_validate()
        else:
            self._send_error_response(404, "API端点不存在")
    
    def _handle_home(self):
        """处理首页请求"""
        html_content = """
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="utf-8">
            <title>Cron表达式生成API</title>
            <style>
                body { font-family: Arial, sans-serif; margin: 40px; }
                .endpoint { background: #f5f5f5; padding: 15px; margin: 10px 0; border-radius: 5px; }
                .method { font-weight: bold; color: #2196F3; }
                .example { background: #e8f5e8; padding: 10px; margin: 10px 0; border-radius: 3px; }
                pre { background: #f0f0f0; padding: 10px; border-radius: 3px; overflow-x: auto; }
            </style>
        </head>
        <body>
            <h1>⏰ Cron表达式生成API</h1>
            <p>中文自然语言到Java Quartz兼容cron表达式的转换服务</p>
            
            <h2>🚀 API端点</h2>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /api/cron/generate</h3>
                <p>通过URL参数生成单个cron表达式</p>
                <div class="example">
                    <strong>示例:</strong><br>
                    <code>/api/cron/generate?time_description=每天早上8点13分</code>
                </div>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/cron/generate</h3>
                <p>通过JSON请求体生成单个cron表达式</p>
                <div class="example">
                    <strong>请求体:</strong>
                    <pre>{"time_description": "每天早上8点13分", "timezone": "Asia/Shanghai"}</pre>
                    <strong>响应:</strong>
                    <pre>{"success": true, "cron_expression": "0 13 8 * * ?"}</pre>
                </div>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">POST</span> /api/cron/batch-generate</h3>
                <p>批量生成cron表达式</p>
                <div class="example">
                    <strong>请求体:</strong>
                    <pre>{"time_descriptions": ["每天早上8点13分", "每周一上午9点"]}</pre>
                </div>
            </div>
            
            <div class="endpoint">
                <h3><span class="method">GET</span> /health</h3>
                <p>健康检查端点</p>
            </div>
            
            <h2>📋 支持的时间格式</h2>
            <ul>
                <li><strong>每天:</strong> 每天早上8点13分 → 0 13 8 * * ?</li>
                <li><strong>每周:</strong> 每周一上午9点 → 0 0 9 ? * 1</li>
                <li><strong>每月:</strong> 每月15号下午2点 → 0 0 14 15 * ?</li>
                <li><strong>每年:</strong> 每年1月1日上午8点 → 0 0 8 1 1 ?</li>
            </ul>
            
            <h2>🧪 快速测试</h2>
            <p>在浏览器中访问: 
                <a href="/api/cron/generate?time_description=每天早上8点13分" target="_blank">
                    /api/cron/generate?time_description=每天早上8点13分
                </a>
            </p>
        </body>
        </html>
        """
        self._send_response(200, html_content, 'text/html')
    
    def _handle_health(self):
        """处理健康检查"""
        health_data = {
            "status": "healthy",
            "service": "cron-generator-api",
            "version": "1.0.0",
            "timestamp": datetime.now().isoformat(),
            "uptime": "运行正常"
        }
        self._send_response(200, health_data)
    
    def _handle_get_generate(self, query_string):
        """处理GET方式的生成请求"""
        try:
            params = urlparse.parse_qs(query_string)
            time_description = params.get('time_description', [''])[0]
            timezone = params.get('timezone', ['Asia/Shanghai'])[0]
            
            if not time_description:
                self._send_error_response(400, "缺少time_description参数")
                return
            
            result = CronAPI.generate_cron_expression(time_description, timezone)
            self._send_response(200, result)
            
        except Exception as e:
            self._send_error_response(500, f"处理请求时出错: {str(e)}")
    
    def _handle_post_generate(self):
        """处理POST方式的生成请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            time_description = data.get('time_description')
            timezone = data.get('timezone', 'Asia/Shanghai')
            
            if not time_description:
                self._send_error_response(400, "缺少time_description字段")
                return
            
            result = CronAPI.generate_cron_expression(time_description, timezone)
            self._send_response(200, result)
            
        except json.JSONDecodeError:
            self._send_error_response(400, "无效的JSON格式")
        except Exception as e:
            self._send_error_response(500, f"处理请求时出错: {str(e)}")
    
    def _handle_batch_generate(self):
        """处理批量生成请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            time_descriptions = data.get('time_descriptions', [])
            timezone = data.get('timezone', 'Asia/Shanghai')
            
            if not time_descriptions or not isinstance(time_descriptions, list):
                self._send_error_response(400, "time_descriptions必须是非空数组")
                return
            
            result = CronAPI.batch_generate(time_descriptions, timezone)
            self._send_response(200, result)
            
        except json.JSONDecodeError:
            self._send_error_response(400, "无效的JSON格式")
        except Exception as e:
            self._send_error_response(500, f"处理请求时出错: {str(e)}")
    
    def _handle_validate(self):
        """处理验证请求"""
        try:
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length).decode('utf-8')
            data = json.loads(post_data)
            
            cron_expression = data.get('cron_expression')
            
            if not cron_expression:
                self._send_error_response(400, "缺少cron_expression字段")
                return
            
            is_valid = CronAPI.validate_cron_expression(cron_expression)
            
            result = {
                "success": True,
                "cron_expression": cron_expression,
                "is_valid": is_valid,
                "message": "验证完成",
                "timestamp": datetime.now().isoformat()
            }
            
            self._send_response(200, result)
            
        except json.JSONDecodeError:
            self._send_error_response(400, "无效的JSON格式")
        except Exception as e:
            self._send_error_response(500, f"处理请求时出错: {str(e)}")
    
    def log_message(self, format, *args):
        """自定义日志格式"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        print(f"[{timestamp}] {format % args}")


def main():
    """启动HTTP API服务器"""
    host = os.environ.get('HOST', '0.0.0.0')
    port = int(os.environ.get('PORT', 5001))
    
    print("⏰ 启动Cron表达式生成API服务器")
    print("=" * 50)
    print(f"🌐 服务地址: http://{host}:{port}")
    print(f"📖 API文档: http://{host}:{port}/")
    print(f"❤️  健康检查: http://{host}:{port}/health")
    print(f"🧪 快速测试: http://{host}:{port}/api/cron/generate?time_description=每天早上8点13分")
    print("=" * 50)
    print(f"🔄 按Ctrl+C停止服务")
    print()
    
    try:
        server = HTTPServer((host, port), CronAPIHandler)
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n👋 服务已停止")
    except Exception as e:
        print(f"❌ 服务启动失败: {e}")


if __name__ == "__main__":
    main()
