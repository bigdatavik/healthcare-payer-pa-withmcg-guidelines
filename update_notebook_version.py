#!/usr/bin/env python3
"""
Update notebook version and timestamp automatically before deployment.

This script:
1. Reads the current version from notebooks/01_pa_agent.py
2. Increments the version (or uses git info)
3. Updates the date to current date
4. Updates the notebook file

Usage:
    python update_notebook_version.py [--bump-version] [--use-git]
"""

import re
import sys
from datetime import datetime
from pathlib import Path
import subprocess

def get_git_commit_date():
    """Get the last commit date from git"""
    try:
        result = subprocess.run(
            ['git', 'log', '-1', '--format=%cd', '--date=format:%B %d, %Y'],
            capture_output=True,
            text=True,
            check=True
        )
        return result.stdout.strip()
    except:
        return None

def get_current_date():
    """Get current date in format: December 19, 2024"""
    return datetime.now().strftime("%B %d, %Y")

def increment_version(version_str):
    """Increment version number: 1.0 -> 1.1"""
    match = re.match(r'(\d+)\.(\d+)', version_str)
    if match:
        major, minor = int(match.group(1)), int(match.group(2))
        return f"{major}.{minor + 1}"
    return version_str

def update_notebook_version(notebook_path, bump_version=False, use_git=False):
    """Update version and date in the notebook"""
    
    notebook_file = Path(notebook_path)
    if not notebook_file.exists():
        print(f"❌ Error: Notebook not found at {notebook_path}")
        return False
    
    # Read notebook content
    content = notebook_file.read_text()
    
    # Get current date
    if use_git:
        new_date = get_git_commit_date() or get_current_date()
    else:
        new_date = get_current_date()
    
    # Extract current version
    version_pattern = r'# MAGIC # ✨✨✨ VERSION ([\d.]+) - CREATED ([^✨]+)✨✨✨'
    match = re.search(version_pattern, content)
    
    if not match:
        print("⚠️  Warning: Could not find version pattern in notebook")
        print("   Notebook may not have version header yet")
        return True  # Don't fail, just skip
    
    current_version = match.group(1)
    current_date = match.group(2).strip()
    
    # Determine new version
    if bump_version:
        new_version = increment_version(current_version)
    else:
        new_version = current_version
    
    # Update the version header
    old_header = f"# MAGIC # ✨✨✨ VERSION {current_version} - CREATED {current_date} ✨✨✨"
    new_header = f"# MAGIC # ✨✨✨ VERSION {new_version} - CREATED {new_date} ✨✨✨"
    
    content = content.replace(old_header, new_header)
    
    # Update the "Last Updated" field
    last_updated_pattern = r'# MAGIC \*\*📅 Last Updated:\*\* [^\n]+'
    new_last_updated = f'# MAGIC **📅 Last Updated:** {new_date}'
    content = re.sub(last_updated_pattern, new_last_updated, content)
    
    # Update the version field
    version_field_pattern = r'# MAGIC \*\*🔧 Version:\*\* [^\n]+'
    new_version_field = f'# MAGIC **🔧 Version:** {new_version}'
    content = re.sub(version_field_pattern, new_version_field, content)
    
    # Write updated content
    notebook_file.write_text(content)
    
    print("=" * 70)
    print("✅ NOTEBOOK VERSION UPDATED")
    print("=" * 70)
    print(f"Notebook: {notebook_path}")
    print(f"Version:  {current_version} → {new_version}")
    print(f"Date:     {current_date} → {new_date}")
    print("=" * 70)
    
    return True

def main():
    """Main function"""
    bump_version = '--bump-version' in sys.argv
    use_git = '--use-git' in sys.argv
    
    notebooks_to_update = [
        'notebooks/01_pa_agent.py',
        # Add more notebooks here as you create them
    ]
    
    all_success = True
    for notebook_path in notebooks_to_update:
        if Path(notebook_path).exists():
            success = update_notebook_version(notebook_path, bump_version, use_git)
            if not success:
                all_success = False
        else:
            print(f"⚠️  Skipping {notebook_path} (not found)")
    
    if all_success:
        print("\n✅ All notebooks updated successfully")
        return 0
    else:
        print("\n⚠️  Some notebooks could not be updated")
        return 1

if __name__ == '__main__':
    sys.exit(main())



