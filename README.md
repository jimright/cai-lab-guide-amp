# Lab Guide AMP

A Cloudera AI (CAI) AMP (Applied ML Prototype) that builds a Hands-on-Lab
guide — written as Material for MkDocs or Zensical markdown — and serves it as a running static site inside CAI, open to workshop attendees with no
login required.

## How it works

The AMP runs a short pipeline of CML Jobs, then starts an application:

1. **Install dependencies** — installs both `mkdocs-material` and `zensical`, so either engine is available.
2. **Build lab guide site** — reads `LAB_GUIDE_SRC_DIR` and `GUIDE_ENGINE`, searches recursively under `LAB_GUIDE_SRC_DIR` for the matching config file (`mkdocs.yml` or `zensical.toml` — it doesn't have to sit directly inside `LAB_GUIDE_SRC_DIR`, so a real course repo's `instructor/mkdocs/mkdocs.yml` works as-is), builds the engine's site from wherever that config file was found, and copies the result to a fixed path (`/home/cdsw/lab_guide_site`). This fixed path decouples the serving app from engine-specific output directories, so rerunning this job — after switching engines, or after uploading content — never requires restarting the app.
3. **Lab Guide** (application) — serves `/home/cdsw/lab_guide_site`. If nothing has been built yet, it shows a "guide not built yet" page instead of an error; once a build succeeds, the already-running app serves the real content immediately.

## Getting your content in

There are two supported ways to get your lab guide's markdown + config into the project.

### Path A: Fork and commit your content

1. Fork this repo.
2. Replace the contents of `lab_guide/` with your own markdown and your own `mkdocs.yml` and/or `zensical.toml`. The config doesn't need to sit at the top level of `lab_guide/` — it's found by recursive search — so you can keep whatever nesting your course repo already uses (the shipped example mirrors a real course repo's `instructor/mkdocs/mkdocs.yml` + sibling `content/` layout; see Repo layout below).
3. Commit and push.
4. Import your fork as a Custom AMP (see below). Your content is present the moment the project is cloned, so the build job succeeds on its first run.

Good for guides you're happy to publish/share as part of the AMP repo itself.

### Path B: Upload content after launch

Use this when your content lives somewhere Cloudera AI can't reach
directly — a Google Doc export, an internal-only repo, etc.

1. Import this AMP as-is (optionally setting `LAB_GUIDE_SRC_DIR` to a different folder name at launch).
2. The first run of the **Build lab guide site** job is *expected to fail* — this is normal, not a bug. It fails with a message telling you what to fix.
3. Get your content onto your machine, then upload it into `LAB_GUIDE_SRC_DIR` via the Workbench's Project Files UI (drag-and-drop), `scp`, the CML CLI, or a Session with filesystem access — including your `mkdocs.yml`/`zensical.toml` *somewhere* under `LAB_GUIDE_SRC_DIR` (it's found by recursive search, so e.g. uploading a whole repo whose config lives at `instructor/mkdocs/mkdocs.yml` works unmodified; just make sure only one matching config file ends up under `LAB_GUIDE_SRC_DIR`).
4. Rerun the **Build lab guide site** job from the Jobs page.
5. The already-running **Lab Guide** application starts serving your real content immediately — no restart needed.

## Choosing an engine

Set `GUIDE_ENGINE` to `mkdocs` (Material for MkDocs) or `zensical`. Both are fully supported. You can
switch engines at any time and just rerun the **Build lab guide site** job (no need to rerun **Install dependencies**, since both engines are always installed).

## Environment variables

| Variable            | Default     | Description |
| -------------------- | ----------- | ------------ |
| `LAB_GUIDE_SRC_DIR`  | `lab_guide` | Path, relative to the project root, to the folder containing your lab guide content. Its `mkdocs.yml`/`zensical.toml` can live directly inside this folder or in any subfolder beneath it (found by recursive search) — exactly one matching config file must exist under this path. |
| `GUIDE_ENGINE`       | `mkdocs`    | Which static site generator to build with — `mkdocs` or `zensical`. |

## Importing this repo as a Custom AMP in CAI

1. In the Cloudera AI ML Workspace, go to **AMPs**.
2. Choose **Add AMP from Git Repository** (admin access required to
   register a new AMP catalog source, or use your workspace's "Custom AMP" import flow if available).
3. Paste this repo's URL and select it.
4. Launch — you'll be prompted for `LAB_GUIDE_SRC_DIR` and `GUIDE_ENGINE` at launch time; the defaults match the shipped example content.

## Submitting to the AMP catalog

Once you've validated your fork, follow Cloudera's AMP catalog submission process (see `ml-amp-create-new-amp.html` in the Cloudera docs) — this generally means forking into the catalog's repo structure, adding catalog metadata, and opening a PR. Treat this as a later step once your content and config are settled.

## Local development / smoke-testing

`cml/build_lab_guide.py` and `app/serve_lab_guide.py` can be exercised outside CML in an isolated virtual environment — see
`adr/0001-lab-guide-amp-architecture.md`'s Verification section for the exact steps. `cml/build_lab_guide.py` honors an optional
`CDSW_PROJECT_ROOT` environment variable (defaulting to `/home/cdsw`, which is always correct inside CML) purely so it can be pointed at this repo's real path during local testing.

## Repo layout

```
.project-metadata.yaml
README.md
requirements.txt                  # mkdocs/mkdocs-material + common plugins + zensical, always installed
cml/
  install_deps.py                 # create_job/run_job: pip install -r requirements.txt
  build_lab_guide.py              # create_job/run_job: build the selected engine's site
app/
  serve_lab_guide.py              # start_application: serve the fixed build output dir
lab_guide/                        # shipped example content (Path A demo, both engines)
  instructor/                      # mirrors a real course repo's nesting (e.g. hol-004-telco-churn-data-lifecycle)
    mkdocs/
      mkdocs.yml                  # docs_dir: '../../content', site_dir: './build'
  zensical.toml                    # docs_dir = "content", site_dir = "./build" -- always top-level, see note below
  content/
    index.md
    module-1-setup.md
    module-2-exercise.md
adr/
  0001-lab-guide-amp-architecture.md
ref/
  serve_lab_guide.py              # untouched, left as original reference
```

Note: `mkdocs.yml` can live nested anywhere under `LAB_GUIDE_SRC_DIR` (it's
found by recursive search), but `zensical.toml` must always sit directly at
the top of `LAB_GUIDE_SRC_DIR` — Zensical always looks for its config
there, unlike MkDocs' `-f`-overridable path.
