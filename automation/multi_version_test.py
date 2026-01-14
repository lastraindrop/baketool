import subprocess
import os
import sys

# Define Blender execution paths
BLENDER_PATHS = [
    r"D:\Program Files\Blender-3.6\blender.exe",
    r"D:\Program Files\Blender-4.2\blender.exe",
    r"D:\Program Files\Blender-4.5\blender.exe",
    r"D:\Program Files\Blender-5.0\blender.exe",
]

current_dir = os.path.dirname(os.path.realpath(__file__))
runner_script = os.path.join(current_dir, "headless_runner.py")

def main():
    results = []
    
    print("\n" + "="*70)
    print("      BAKETOOL CROSS-VERSION TEST SUITE")
    print("="*70)
    print(f"{'Blender Version':<20} | {'Status':<10} | {'Details'}")
    print("-" * 70)

    # Force UTF-8 environment variables to prevent encoding issues on Windows
    test_env = os.environ.copy()
    test_env["PYTHONIOENCODING"] = "utf-8"
    test_env["LANG"] = "en_US.UTF-8"

    for path in BLENDER_PATHS:
        ver_name = path.split("\\")[-2]
        
        if not os.path.exists(path):
            print(f"{ver_name:<20} | \033[93mSKIP\033[0m       | Executable not found")
            results.append((ver_name, "SKIP"))
            continue

        # Run command
        cmd = [path, "--background", "--factory-startup", "--python", runner_script]
        
        try:
            # We capture output and decode it manually to handle potential encoding quirks
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                env=test_env,
                check=False
            )
            
            # Use 'replace' to handle any stray bytes that aren't valid UTF-8
            stdout = process.stdout.decode('utf-8', errors='replace')
            stderr = process.stderr.decode('utf-8', errors='replace')
            
            if process.returncode == 0:
                print(f"{ver_name:<20} | \033[92mPASS\033[0m       | All tests cleared")
                results.append((ver_name, "PASS"))
            else:
                print(f"{ver_name:<20} | \033[91mFAIL\033[0m       | Check logs below")
                results.append((ver_name, "FAIL"))
                
                # Show error summary if failed
                print("\n" + "!"*20 + f" {ver_name} ERROR LOG " + "!"*20)
                # Just show the last part of stdout which contains unittest results
                print(stdout[-1500:] if len(stdout) > 1500 else stdout)
                if stderr.strip():
                    print("\nSTDERR:")
                    print(stderr)
                print("!"*55 + "\n")
                
        except Exception as e:
            print(f"{ver_name:<20} | \033[91mERROR\033[0m      | {str(e)}")
            results.append((ver_name, "ERROR"))

    print("-" * 70)
    print("      FINAL SUMMARY")
    print("-" * 70)
    for ver, status in results:
        status_str = f"[{status}]"
        print(f" > {ver:<18} : {status_str}")
    print("="*70 + "\n")

if __name__ == "__main__":
    main()
