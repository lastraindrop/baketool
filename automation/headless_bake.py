"""
BakeNexus Headless CLI Entry Point
Usage: blender -b scene.blend -P headless_bake.py -- --job "JobName" --output "C:/path"
"""
import sys
import bpy
import argparse
from pathlib import Path

addon_dir = str(Path(__file__).resolve().parent.parent)
addon_parent = str(Path(__file__).resolve().parent.parent.parent)
for path in (addon_parent, addon_dir):
    if path not in sys.path:
        sys.path.append(path)

try:
    import baketool
    from baketool.core.engine import JobPreparer, BakeStepRunner
except ImportError:
    print("Error: Could not import BakeNexus core. Ensure the script is inside the addon or path is correct.")
    sys.exit(1)


def ensure_addon_registered():
    """Register BakeNexus when running from a clean background session."""
    scene = bpy.context.scene
    if hasattr(scene, "BakeJobs"):
        return True

    try:
        baketool.register()
    except ValueError:
        # Already registered but Blender state was partially initialized.
        pass
    except (ValueError, RuntimeError) as exc:
        print(f"Error: Failed to register BakeNexus addon: {exc}")
        return False

    return hasattr(bpy.context.scene, "BakeJobs")

def main():
    """Entry point: register addon, parse args, run headless bake jobs."""
    # Parse CLI arguments after '--'
    if "--" in sys.argv:
        args_idx = sys.argv.index("--") + 1
        cli_args = sys.argv[args_idx:]
    else:
        cli_args = []

    parser = argparse.ArgumentParser(description="BakeNexus Headless CLI")
    parser.add_argument("--job", type=str, help="Name of the job to bake (if empty, bakes all enabled)")
    parser.add_argument("--output", type=str, help="Override output directory")
    args = parser.parse_args(cli_args)

    if not ensure_addon_registered():
        print("Error: BakeNexus properties could not be initialized.")
        return False

    scene = bpy.context.scene
    bj_prop = getattr(scene, "BakeJobs", None)
    if not bj_prop:
        print("Error: BakeNexus properties not found in scene.")
        return False

    # Filter jobs
    jobs_to_run = []
    if args.job:
        job = next((j for j in bj_prop.jobs if j.name == args.job), None)
        if job:
            jobs_to_run = [job]
        else:
            print(f"Error: Job '{args.job}' not found.")
    else:
        jobs_to_run = [j for j in bj_prop.jobs if j.enabled]

    if not jobs_to_run:
        print("No jobs to run. Exiting.")
        return False

    # Override output if provided
    if args.output:
        for job in jobs_to_run:
            job.setting.external_save_path = args.output
            job.setting.use_external_save = True

    print(f"BakeNexus CLI: Starting {len(jobs_to_run)} jobs...")

    # Execution Queue using standard preparer
    queue = JobPreparer.prepare_execution_queue(bpy.context, jobs_to_run)

    if not queue:
        print("Preparation failed. Check logs.")
        return False

    # Run steps without modal operator (synchronous)
    runner = BakeStepRunner(bpy.context)
    failed_steps = 0
    for i, step in enumerate(queue):
        base_name = getattr(getattr(step, "task", None), "base_name", f"Step {i+1}")
        print(f"[{i+1}/{len(queue)}] Baking: {base_name}")
        try:
            runner.run(step, queue_idx=i)
        except (RuntimeError, AttributeError) as exc:
            failed_steps += 1
            print(f"[{i+1}/{len(queue)}] FAILED: {exc}")

    if failed_steps:
        print(f"BakeNexus CLI: Finished with {failed_steps}/{len(queue)} failures.")
        return False

    print("BakeNexus CLI: Finished.")
    return True

if __name__ == "__main__":
    sys.exit(0 if main() else 1)
