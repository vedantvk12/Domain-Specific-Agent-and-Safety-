"""
package_deliverables.py
-----------------------
Packages the complete working SecureCode AI implementation, sample data, tests,
actual execution logs, and architecture diagrams into securecode-ai-source-code.zip.
"""

import os
import zipfile


def create_zip_archive():
    root_dir = os.path.dirname(os.path.abspath(__file__))
    source_dir = os.path.join(root_dir, "securecode-ai")
    zip_path = os.path.join(root_dir, "securecode-ai-source-code.zip")

    if os.path.exists(zip_path):
        os.remove(zip_path)

    print(f"[*] Packaging {source_dir} into {zip_path}...")
    file_count = 0

    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zipf:
        for root, dirs, files in os.walk(source_dir):
            # Skip python cache directories
            if "__pycache__" in root or ".pytest_cache" in root or ".mplcache" in root:
                continue

            for file in files:
                full_path = os.path.join(root, file)
                rel_path = os.path.relpath(full_path, root_dir)
                zipf.write(full_path, rel_path)
                file_count += 1
                print(f"  + Added: {rel_path}")

    size_kb = os.path.getsize(zip_path) / 1024
    print(f"[+] Successfully generated {zip_path} ({file_count} files, {size_kb:.1f} KB)")


if __name__ == "__main__":
    create_zip_archive()

