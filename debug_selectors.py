#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup

def debug_selectors():
    """Debug selector matching for avis page"""
    response = requests.get("http://localhost:8000/api/v1/pages/avis")
    data = response.json()
    content = data.get('content', '')
    
    soup = BeautifulSoup(content, 'html.parser')
    
    # Test each main selector
    main_selectors = [
        'main[property="mainContentOfPage"]',
        'main',
        '#wb-cont',
        '#main-content',
        'article',
        '.container.main',
        '.col-md-9',
        '.col-md-8',
        '.container'
    ]
    
    print("Testing selectors on original HTML:")
    for selector in main_selectors:
        element = soup.select_one(selector)
        if element:
            print(f"  ✓ {selector}: found, tag={element.name}, class={element.get('class')}, id={element.get('id')}")
            print(f"    Preview: {str(element)[:200]}...")
        else:
            print(f"  ✗ {selector}: not found")
    
    # Also check for the main element more carefully
    print("\nLooking for main element specifically:")
    main_elements = soup.find_all('main')
    for i, main in enumerate(main_elements):
        print(f"  Main element {i}:")
        print(f"    Attributes: {dict(main.attrs)}")
        print(f"    Class: {main.get('class')}")
        print(f"    First 200 chars: {str(main)[:200]}...")
    
    # Check what #wb-cont actually is
    wb_cont = soup.select_one('#wb-cont')
    if wb_cont:
        print(f"\n#wb-cont element details:")
        print(f"  Tag: {wb_cont.name}")
        print(f"  Class: {wb_cont.get('class')}")
        print(f"  Parent: {wb_cont.parent.name if wb_cont.parent else 'None'}")
        print(f"  Full element: {wb_cont}")
        
    # Check structure around #wb-cont
    print("\nChecking structure:")
    # Find all elements with id containing 'wb-cont'
    for elem in soup.find_all(id=lambda x: x and 'wb-cont' in x):
        print(f"  Element with id containing 'wb-cont': {elem.name}, id={elem.get('id')}")
        print(f"    Parent: {elem.parent.name if elem.parent else 'None'}")
        if elem.parent:
            print(f"    Parent class: {elem.parent.get('class')}")
            print(f"    Parent tag: {elem.parent.name}")

if __name__ == "__main__":
    debug_selectors()