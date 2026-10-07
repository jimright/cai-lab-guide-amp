"""Build the lab guide (mkdocs or zensical) into a fixed output location.

Reads LAB_GUIDE_SRC_DIR and GUIDE_ENGINE, builds the configured engine's
site, and copies the result to a fixed path (<project root>/lab_guide_site)
so app/serve_lab_guide.py never has to know which engine produced it. This
is what lets Path B (content uploaded after project creation) "just work":
upload content, rerun this job, and the already-running app picks up the
new build with no restart.
"""
import os
import pathlib
import shutil
import subprocess
import sys
import tomllib

import yaml

# CDSW_PROJECT_ROOT is not a real CML env var; it exists only so this
# script can be smoke-tested locally against this repo's actual path.
# In CML the default /home/cdsw is always correct.
PROJECT_ROOT = pathlib.Path(os.environ.get("CDSW_PROJECT_ROOT", "/home/cdsw"))
FIXED_OUTPUT_DIR = PROJECT_ROOT / "lab_guide_site"

ENGINE_CONFIG_FILENAMES = {
    "mkdocs": "mkdocs.yml",
    "zensical": "zensical.toml",
}


def fail(message: str) -> None:
    print(f"ERROR: {message}", file=sys.stderr)
    sys.exit(1)


def get_env():
    src_dir_rel = os.environ.get("LAB_GUIDE_SRC_DIR", "lab_guide")
    engine = os.environ.get("GUIDE_ENGINE", "mkdocs").strip().lower()
    return src_dir_rel, engine


def resolve_config_path(src_dir_rel: str, engine: str) -> pathlib.Path:
    if engine not in ENGINE_CONFIG_FILENAMES:
        fail(
            f"Unrecognized GUIDE_ENGINE '{engine}'. Must be 'mkdocs' or "
            f"'zensical'. Set GUIDE_ENGINE to one of these values in the "
            f"project's environment variables and rerun this job."
        )

    config_filename = ENGINE_CONFIG_FILENAMES[engine]
    src_dir = PROJECT_ROOT / src_dir_rel
    config_path = src_dir / config_filename

    if not src_dir.is_dir() or not config_path.is_file():
        fail(
            f"Could not find '{config_filename}' in '{src_dir_rel}'.\n"
            f"This job is safe to rerun once the problem below is fixed:\n"
            f"  - Wrong setting: if your lab guide content lives in a "
            f"different folder, or uses the other engine, fix "
            f"LAB_GUIDE_SRC_DIR and/or GUIDE_ENGINE in the project's "
            f"environment variables to match, then rerun this job.\n"
            f"  - Not uploaded yet: if you're following the manual-upload "
            f"path, upload your markdown and '{config_filename}' into "
            f"'{src_dir_rel}' via the Workbench Project Files UI (or scp / "
            f"CML CLI), then rerun this job from the Jobs page."
        )

    return config_path


def read_site_dir(config_path: pathlib.Path, engine: str) -> str:
    if engine == "mkdocs":
        with open(config_path, "r") as f:
            data = yaml.safe_load(f) or {}
        return data.get("site_dir") or "site"
    else:  # zensical
        with open(config_path, "rb") as f:
            data = tomllib.load(f)
        project_table = data.get("project", {})
        return project_table.get("site_dir") or "site"


def run_build(config_path: pathlib.Path, engine: str) -> None:
    config_dir = config_path.parent
    if engine == "mkdocs":
        cmd = ["mkdocs", "build", "-f", config_path.name]
    else:
        cmd = ["zensical", "build", "-f", config_path.name]

    print(f"Running '{' '.join(cmd)}' in {config_dir}")
    result = subprocess.run(cmd, cwd=config_dir)
    if result.returncode != 0:
        fail(
            f"'{' '.join(cmd)}' failed with exit code {result.returncode}. "
            f"See the build output above for details, fix the lab guide "
            f"content/config, and rerun this job."
        )


def copy_to_fixed_output(config_path: pathlib.Path, site_dir_name: str) -> None:
    built_site_dir = config_path.parent / site_dir_name
    if not built_site_dir.is_dir():
        fail(
            f"Build reported success but expected output directory "
            f"'{built_site_dir}' was not found. Check the configured "
            f"site_dir in '{config_path.name}'."
        )

    if FIXED_OUTPUT_DIR.exists():
        shutil.rmtree(FIXED_OUTPUT_DIR)
    shutil.copytree(built_site_dir, FIXED_OUTPUT_DIR)
    print(f"Copied built site from '{built_site_dir}' to '{FIXED_OUTPUT_DIR}'.")


def main():
    src_dir_rel, engine = get_env()
    config_path = resolve_config_path(src_dir_rel, engine)
    site_dir_name = read_site_dir(config_path, engine)
    run_build(config_path, engine)
    copy_to_fixed_output(config_path, site_dir_name)
    print("Lab guide build complete.")


if __name__ == "__main__":
    main()
