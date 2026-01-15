import subprocess
import os
import sys

# Define Blender execution paths
# You can add your local blender paths here. 
# The script will automatically skip missing ones.
BLENDER_PATHS = [
    r"C:\Program Files\Blender Foundation\Blender 3.6\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 4.2\blender.exe",
    r"C:\Program Files\Blender Foundation\Blender 5.0\blender.exe",
    r"D:\Program Files\Blender-3.6\blender.exe",
    r"D:\Program Files\Blender-4.2\blender.exe",
    r"D:\Program Files\Blender-4.5\blender.exe",
    r"D:\Program Files\Blender-5.0\blender.exe",
]

current_dir = os.path.dirname(os.path.realpath(__file__))
runner_script = os.path.join(current_dir, "headless_runner.py")

def get_blender_version(path):
    try:
        res = subprocess.run([path, "--version"], capture_output=True, text=True, check=True)
        return res.stdout.splitlines()[0]
    except:
        return "Unknown Version"

def main():
    results = []
    
    print("\n" + "="*80)
    print("      BAKETOOL CROSS-VERSION TEST SUITE")
    print("="*80)
    print(f"{'Blender Path/Version':<45} | {'Status':<10} | {'Details'}")
    print("-" * 80)

    # Force UTF-8 environment variables to prevent encoding issues on Windows
    test_env = os.environ.copy()
    test_env["PYTHONIOENCODING"] = "utf-8"
    test_env["LANG"] = "en_US.UTF-8"

    valid_paths = [p for p in BLENDER_PATHS if os.path.exists(p)]
    
    if not valid_paths:
        print("\033[91mERROR: No valid Blender executables found in BLENDER_PATHS.\033[0m")
        return

    for path in valid_paths:
        full_ver = get_blender_version(path)
        ver_display = full_ver[:40] if len(full_ver) > 40 else full_ver
        
        # Run command
        cmd = [path, "--background", "--factory-startup", "--python", runner_script]
        
        try:
            process = subprocess.run(
                cmd, 
                capture_output=True, 
                env=test_env,
                check=False
            )
            
            stdout = process.stdout.decode('utf-8', errors='replace')
            stderr = process.stderr.decode('utf-8', errors='replace')
            
            if process.returncode == 0:
                print(f"{ver_display:<45} | \033[92mPASS\033[0m       | All tests cleared")
                results.append((ver_display, "PASS", ""))
            else:
                print(f"{ver_display:<45} | \033[91mFAIL\033[0m       | Check logs")
                results.append((ver_display, "FAIL", stdout[-1000:] + "\n" + stderr))
                
        except Exception as e:
            print(f"{ver_display:<45} | \033[91mERROR\033[0m      | {str(e)}")
            results.append((ver_display, "ERROR", str(e)))

    print("-" * 80)
    print("      FINAL SUMMARY")
    print("-" * 80)
    for ver, status, detail in results:
        status_color = "\033[92m" if status == "PASS" else "\033[91m"
        print(f" > {ver:<43} : {status_color}[{status}]\033[0m")
        if status != "PASS":
            print(f"   \033[90m{detail.splitlines()[-1] if detail.splitlines() else 'Unknown error'}\033[0m")
    print("="*80 + "\n")

if __name__ == "__main__":
    main()
