#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

response = requests.get("http://localhost:8000/api/v1/pages/avis")
data = response.json()
content = data.get('content', '')

soup = BeautifulSoup(content, 'html.parser')

# Look for common Canada.ca content containers
containers = [
    '.mwstext.section',
    '.mwstext',
    '.section',
    '.row.profile',
    '.col-md-12',
    '.gc-srvinfo',
    '.wb-eqht-grd',
    'section',
    'div.container',
    '#wb-main'
]

print("Checking for content containers:")
for selector in containers:
    elements = soup.select(selector)
    if elements:
        print(f"  {selector}: found {len(elements)} element(s)")
        for i, elem in enumerate(elements[:2]):  # Show first 2
            text = elem.get_text(strip=True)[:100]
            print(f"    Element {i}: {elem.name}, text preview: {text}")
            # Check if it has meaningful content
            child_count = len(list(elem.children))
            text_length = len(elem.get_text(strip=True))
            print(f"      Children: {child_count}, Text length: {text_length}")
    else:
        print(f"  {selector}: not found")

# Check the structure around #wb-cont
print("\nStructure around #wb-cont:")
wb_cont = soup.select_one('#wb-cont')
if wb_cont:
    # Go up the tree to find containing section
    parent = wb_cont.parent
    depth = 0
    while parent and depth < 5:
        print(f"  Level {depth}: {parent.name}, class={parent.get('class')}, id={parent.get('id')}")
        parent = parent.parent
        depth += 1

# Look for text content sections
print("\nText content analysis:")
all_text = soup.get_text()
lines = [line.strip() for line in all_text.split('\n') if line.strip()]
print(f"Total non-empty lines: {len(lines)}")
print("First 20 lines:")
for i, line in enumerate(lines[:20]):
    print(f"  {i}: {line[:100]}")