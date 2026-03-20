import sys
import unittest
import argparse
import bpy
import os
from pathlib import Path

# 尝试直接导入或通过路径挂载后导入
try:
    from env_setup import setup_environment
except ImportError:
    # 强制挂载当前目录以查找 env_setup
    sys.path.append(os.path.dirname(__file__))
    from env_setup import setup_environment

def main():
    parser = argparse.ArgumentParser(description="BakeTool Unified CLI Test Runner")
    parser.add_argument("--suite", choices=['all', 'api', 'unit', 'workflow', 'preset'], default='all', 
                        help="Run a specific test suite or 'all' suites (suite_*.py)")
    parser.add_argument("--test", type=str, 
                        help="Run a specific test case (e.g. baketool.test_cases.suite_api.SuiteAPI)")
    parser.add_argument("--discover", action="store_true", 
                        help="Discover and run all test_*.py files")
    
    # 过滤掉 Blender 自身的命令行参数
    if "--" in sys.argv:
        args_idx = sys.argv.index("--") + 1
        cli_args = sys.argv[args_idx:]
    else:
        cli_args = []
    
    args = parser.parse_args(cli_args)

    # 1. 环境初始化
    addon_name, addon_root = setup_environment()
    parent_dir = str(addon_root.parent)
    test_dir = str(addon_root / "test_cases")

    try:
        # 2. 注册插件以启用属性定义
        import baketool
        try:
            baketool.unregister()
        except:
            pass
        baketool.register()
        print(">>> Addon registered successfully.")

        loader = unittest.TestLoader()
        suite = unittest.TestSuite()

        # 3. 决定加载逻辑
        if args.test:
            print(f">>> Loading specific test: {args.test}")
            suite = loader.loadTestsFromName(args.test)
        elif args.discover:
            print(">>> Discovering all test_*.py...")
            suite = loader.discover(start_dir=test_dir, pattern='test_*.py', top_level_dir=parent_dir)
        else:
            pattern = 'suite_*.py' if args.suite == 'all' else f'suite_{args.suite}.py'
            print(f">>> Loading suites matching pattern: {pattern}")
            suite = loader.discover(start_dir=test_dir, pattern=pattern, top_level_dir=parent_dir)

        # 4. 执行
        print(f">>> Running {suite.countTestCases()} tests...")
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite)

        # 5. 根据结果返回状态码
        if result.wasSuccessful():
            print("\n>>> CONSOLIDATED SUITES PASSED")
            print(">>> ALL TESTS PASSED")
            sys.exit(0)
        else:
            print("\n>>> TESTS FAILED")
            sys.exit(1)

    except Exception as e:
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
