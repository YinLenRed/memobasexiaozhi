import os
import importlib.util
import asyncio

print("使用前请根据doc/performance_tester.md的说明准备配置。")


def list_performance_tester_modules():
    performance_tester_dir = os.path.join(
        os.path.dirname(__file__), "performance_tester"
    )
    modules = []
    
    # 检查目录是否存在
    if not os.path.exists(performance_tester_dir):
        print(f"错误：performance_tester 目录不存在：{performance_tester_dir}")
        print("请创建 performance_tester 目录并添加性能测试模块。")
        return modules
    
    try:
        for file in os.listdir(performance_tester_dir):
            if file.endswith(".py") and not file.startswith("__"):
                modules.append(file[:-3])
    except PermissionError:
        print(f"错误：没有权限访问目录：{performance_tester_dir}")
    except Exception as e:
        print(f"读取目录时出现错误：{e}")
    
    return modules


async def load_and_execute_module(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            print(f"错误：无法创建模块规范：{module_path}")
            return
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)

        if hasattr(module, "main"):
            main_func = module.main
            try:
                if asyncio.iscoroutinefunction(main_func):
                    await main_func()
                else:
                    main_func()
            except Exception as e:
                print(f"执行模块 {module_name} 的 main 函数时出错：{e}")
        else:
            print(f"模块 {module_name} 中没有找到 main 函数。")
    except FileNotFoundError:
        print(f"错误：找不到模块文件：{module_path}")
    except Exception as e:
        print(f"加载模块 {module_name} 时出错：{e}")


def get_module_description(module_name):
    module_path = os.path.join(
        os.path.dirname(__file__), "performance_tester", f"{module_name}.py"
    )
    
    try:
        spec = importlib.util.spec_from_file_location(module_name, module_path)
        if spec is None:
            return "无法加载模块描述"
            
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return getattr(module, "description", "暂无描述")
    except Exception as e:
        return f"获取描述时出错：{str(e)}"


def main():
    modules = list_performance_tester_modules()
    if not modules:
        print("performance_tester 目录中没有可用的性能测试工具。")
        return

    print("可用的性能测试工具：")
    for idx, module in enumerate(modules, 1):
        description = get_module_description(module)
        print(f"{idx}. {module} - {description}")

    try:
        choice = int(input("请选择要调用的性能测试工具编号：")) - 1
        if 0 <= choice < len(modules):
            asyncio.run(load_and_execute_module(modules[choice]))
        else:
            print("无效的选择。")
    except ValueError:
        print("请输入有效的数字。")


if __name__ == "__main__":
    main()
