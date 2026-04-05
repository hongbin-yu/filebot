#!/usr/bin/env python3
import zipfile
import sys

zip_path = '/home/hongb/.openclaw/workspace/webbot/static/external/tinymce/tinymce.zip'
missing_plugins = ['strikethrough', 'forecolor', 'backcolor', 'hr']

try:
    with zipfile.ZipFile(zip_path, 'r') as zf:
        files = zf.namelist()
        print(f"Total files in ZIP: {len(files)}")
        
        for plugin in missing_plugins:
            plugin_files = [f for f in files if f'plugins/{plugin}/' in f]
            if plugin_files:
                print(f"✓ Plugin '{plugin}' found: {len(plugin_files)} files")
                for f in plugin_files[:3]:
                    print(f"  - {f}")
            else:
                print(f"✗ Plugin '{plugin}' NOT found in ZIP")
                
        # Check TinyMCE version
        version_file = [f for f in files if 'tinymce/js/tinymce/package.json' in f]
        if version_file:
            with zf.open(version_file[0]) as f:
                import json
                data = json.load(f)
                print(f"\nTinyMCE version: {data.get('version', 'unknown')}")
                
except Exception as e:
    print(f"Error reading ZIP file: {e}")
    sys.exit(1)