"""Install dependencies for the Lab Guide AMP.

Both supported engines (mkdocs-material and zensical) are installed
unconditionally, so switching GUIDE_ENGINE later and rerunning only the
build job always works without rerunning this one.
"""
import subprocess
import sys


def main():
    cmd = [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"]
    print(f"Running: {' '.join(cmd)}")
    result = subprocess.run(cmd)
    if result.returncode != 0:
        sys.exit(result.returncode)
    print("Dependencies installed successfully.")


if __name__ == "__main__":
    main()
