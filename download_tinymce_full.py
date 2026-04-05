#!/usr/bin/env python3
import requests
import os
import zipfile
import shutil
import sys

API_KEY = '68matgqcnaoa96gx7x6cn8u8ur4thooph25rnufw2sa9oq8e'
VERSION = '6.8.2'
TINYMCE_DIR = '/home/hongb/.openclaw/workspace/webbot/static/external/tinymce'
ZIP_URL = f'https://cdn.tiny.cloud/1/{API_KEY}/tinymce/{VERSION}/tinymce.zip'
ZIP_PATH = os.path.join(TINYMCE_DIR, 'tinymce-full.zip')

print(f"Downloading TinyMCE {VERSION} full package from TinyMCE Cloud...")
print(f"URL: {ZIP_URL}")

try:
    # Create backup of existing tinymce directory
    backup_dir = TINYMCE_DIR + '.backup'
    if os.path.exists(TINYMCE_DIR) and not os.path.exists(backup_dir):
        shutil.copytree(TINYMCE_DIR, backup_dir)
        print(f"Created backup at: {backup_dir}")
    
    # Download the ZIP file
    response = requests.get(ZIP_URL, stream=True)
    response.raise_for_status()
    
    with open(ZIP_PATH, 'wb') as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
    
    print(f"Downloaded: {ZIP_PATH} ({os.path.getsize(ZIP_PATH)} bytes)")
    
    # Remove old tinymce directory
    tinymce_js_dir = os.path.join(TINYMCE_DIR, 'tinymce')
    if os.path.exists(tinymce_js_dir):
        shutil.rmtree(tinymce_js_dir)
        print(f"Removed old tinymce directory: {tinymce_js_dir}")
    
    # Extract the ZIP
    with zipfile.ZipFile(ZIP_PATH, 'r') as zf:
        zf.extractall(TINYMCE_DIR)
        print(f"Extracted to: {TINYMCE_DIR}")
    
    # Verify missing plugins now exist
    extracted_dir = os.path.join(TINYMCE_DIR, 'tinymce')
    missing_plugins = ['strikethrough', 'forecolor', 'backcolor', 'hr']
    
    print("\nVerifying plugins:")
    for plugin in missing_plugins:
        plugin_dir = os.path.join(extracted_dir, 'js', 'tinymce', 'plugins', plugin)
        if os.path.exists(plugin_dir):
            print(f"✓ Plugin '{plugin}' found at: {plugin_dir}")
        else:
            print(f"✗ Plugin '{plugin}' still missing!")
    
    # Check version
    package_json = os.path.join(extracted_dir, 'js', 'tinymce', 'package.json')
    if os.path.exists(package_json):
        import json
        with open(package_json, 'r') as f:
            data = json.load(f)
            print(f"\nTinyMCE version: {data.get('version', 'unknown')}")
    
    print(f"\n✅ TinyMCE full package downloaded and extracted successfully!")
    
except Exception as e:
    print(f"❌ Error: {e}")
    sys.exit(1)