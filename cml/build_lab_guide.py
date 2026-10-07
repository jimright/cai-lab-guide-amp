"""Build the lab guide (mkdocs or zensical) into a fixed output location.

Reads LAB_GUIDE_SRC_DIR and GUIDE_ENGINE, searches recursively under
LAB_GUIDE_SRC_DIR for the engine's config file (mkdocs.yml or
zensical.toml) rather than requiring it directly inside LAB_GUIDE_SRC_DIR
-- real course repos often nest it a few levels down (e.g.
instructor/mkdocs/mkdocs.yml, with content living elsewhere in the same
tree) -- builds the configured engine's site from wherever that config
file was found, and copies the result to a fixed path
(<project root>/lab_guide_site) so app/serve_lab_guide.py never has to
know which engine produced it or where its config lived. This is what
lets Path B (content uploaded after project creation) "just work": upload
content, rerun this job, and the already-running app picks up the new
build with no restart.
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


def find_config_matches(src_dir: pathlib.Path, config_filename: str) -> list[pathlib.Path]:
    """Find config_filename anywhere under src_dir, skipping dot-directories."""
    matches = []
    for dirpath, dirnames, filenames in os.walk(src_dir):
        dirnames[:] = [d for d in dirnames if not d.startswith(".")]
        if config_filename in filenames:
            matches.append(pathlib.Path(dirpath) / config_filename)
    return sorted(matches)


def resolve_config_path(src_dir_rel: str, engine: str) -> pathlib.Path:
    if engine not in ENGINE_CONFIG_FILENAMES:
        fail(
            f"Unrecognized GUIDE_ENGINE '{engine}'. Must be 'mkdocs' or "
            f"'zensical'. Set GUIDE_ENGINE to one of these values in the "
            f"project's environment variables and rerun this job."
        )

    config_filename = ENGINE_CONFIG_FILENAMES[engine]
    src_dir = PROJECT_ROOT / src_dir_rel

    if not src_dir.is_dir():
        fail(
            f"'{src_dir_rel}' does not exist under the project root.\n"
            f"This job is safe to rerun once the problem below is fixed:\n"
            f"  - Wrong setting: if your lab guide content lives in a "
            f"different folder, fix LAB_GUIDE_SRC_DIR in the project's "
            f"environment variables to match, then rerun this job.\n"
            f"  - Not uploaded yet: if you're following the manual-upload "
            f"path, upload your lab guide content (including a "
            f"'{config_filename}' somewhere underneath it) into "
            f"'{src_dir_rel}' via the Workbench Project Files UI (or scp / "
            f"CML CLI), then rerun this job from the Jobs page."
        )

    matches = find_config_matches(src_dir, config_filename)

    if not matches:
        fail(
            f"Could not find '{config_filename}' anywhere under "
            f"'{src_dir_rel}'.\n"
            f"This job is safe to rerun once the problem below is fixed:\n"
            f"  - Wrong setting: if your lab guide content lives in a "
            f"different folder, or uses the other engine, fix "
            f"LAB_GUIDE_SRC_DIR and/or GUIDE_ENGINE in the project's "
            f"environment variables to match, then rerun this job.\n"
            f"  - Not uploaded yet: if you're following the manual-upload "
            f"path, upload your markdown and '{config_filename}' anywhere "
            f"under '{src_dir_rel}' (e.g. "
            f"'{src_dir_rel}/instructor/mkdocs/{config_filename}', with the "
            f"content itself elsewhere under '{src_dir_rel}') via the "
            f"Workbench Project Files UI (or scp / CML CLI), then rerun "
            f"this job from the Jobs page."
        )

    if len(matches) > 1:
        listed = "\n".join(
            f"  - {m.relative_to(PROJECT_ROOT)}" for m in matches
        )
        fail(
            f"Found multiple '{config_filename}' files under "
            f"'{src_dir_rel}':\n{listed}\n"
            f"Narrow LAB_GUIDE_SRC_DIR to the one directory tree that "
            f"should be built, then rerun this job."
        )

    return matches[0]


class _MkdocsYamlLoader(yaml.SafeLoader):
    """SafeLoader that tolerates mkdocs.yml's Python-object tags.

    Material for MkDocs configs commonly reference Python objects (e.g.
    pymdownx.emoji's `emoji_index: !!python/name:material.extensions.emoji.twemoji`).
    We only need top-level scalar keys like site_dir here -- not to actually
    resolve those objects -- so each one is read as a harmless placeholder
    instead of making SafeLoader raise.
    """


_MkdocsYamlLoader.add_multi_constructor(
    "tag:yaml.org,2002:python/", lambda loader, suffix, node: None
)


def read_site_dir(config_path: pathlib.Path, engine: str) -> str:
    if engine == "mkdocs":
        with open(config_path, "r") as f:
            data = yaml.load(f, Loader=_MkdocsYamlLoader) or {}
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
