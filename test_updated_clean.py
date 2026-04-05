#!/usr/bin/env python3
import requests
from bs4 import BeautifulSoup
import re

def clean_content_updated(content, page_id):
    """Simulate UPDATED JavaScript cleanContent function"""
    print(f"cleanContent called for page: {page_id}, content length: {len(content)}")
    
    if not content or not isinstance(content, str):
        print(f"cleanContent: invalid content, returning: {content}")
        return content
    
    cleaned = content
    
    # Try to extract main content if it's HTML
    if '<' in content and '>' in content:
        # It's HTML content
        try:
            soup = BeautifulSoup(content, 'html.parser')
            
            # Remove Canada.ca header and footer elements before extracting main
            header_footer_selectors = [
                '#wb-bnr', '#wb-sm', '#wb-info', '#wb-srch', '#wb-lng',
                '#wb-sec', '#wb-dtmd', '#wb-glb-mn', '#wb-srch-frm',
                '.pagedetails', '.brand', '.subsite', '.gc-footer',
                '.gc-subway', '.gc-main-nav', '.gc-top-nav',
                'footer', 'header', '.footer', '.header',
                '#gcwu-sig', '#gcwu-sig-in', '#gcwu-tc', '#gcwu-date-mod',
                # Additional header/footer selectors
                '[role="banner"]', '[role="contentinfo"]',
                '.gcweb-menu', '.gc-web-menu', '.gc-web-header', '.gc-web-footer',
                '#gcweb-nav', '#gcweb-header', '#gcweb-footer',
                '.site-header', '.site-footer', '.global-header', '.global-footer',
                '.header-main', '.footer-main', '#header', '#footer',
                '.nav-main', '.navigation', '.main-nav', '.primary-nav'
            ]
            
            for selector in header_footer_selectors:
                for element in soup.select(selector):
                    element.decompose()
            
            # UPDATED mainSelectors array
            main_selectors = [
                'main[property="mainContentOfPage"]',
                'main',
                '.mwstext.section',           # Canada.ca content area
                '.row.profile',               # Canada.ca profile/content container
                '#main-content',
                'article',
                '.container.main',
                '.col-md-9',
                '.col-md-8',
                '.container',
                '#wb-cont'                    # Title element (last resort)
            ]
            
            main_element = None
            for selector in main_selectors:
                main_element = soup.select_one(selector)
                if main_element:
                    print(f"Found main element via selector: {selector}")
                    break
            
            # Special handling for #wb-cont if it's a heading
            if main_element and selector == '#wb-cont' and main_element.name in ['h1', 'h2', 'h3', 'h4', 'h5', 'h6']:
                print(f"#wb-cont is a heading element, looking for content container...")
                # Try to find a sibling or parent with actual content
                parent = main_element.parent
                if parent:
                    # Check if parent has meaningful content beyond the heading
                    parent_text = parent.get_text(strip=True)
                    heading_text = main_element.get_text(strip=True)
                    if len(parent_text) > len(heading_text) + 100:  # Parent has additional content
                        print(f"Using parent container instead of heading")
                        main_element = parent
                    else:
                        # Look for next sibling with content
                        next_sib = main_element.find_next_sibling()
                        while next_sib and len(next_sib.get_text(strip=True)) < 100:
                            next_sib = next_sib.find_next_sibling()
                        if next_sib and len(next_sib.get_text(strip=True)) >= 100:
                            print(f"Using next sibling with content")
                            main_element = next_sib
            
            # If found main element, use its innerHTML
            if main_element:
                print(f"cleanContent: found main element, innerHTML length: {len(str(main_element))}")
                cleaned = str(main_element)
            else:
                print("cleanContent: no main element found, falling back to body")
                # Fallback: use body content but keep the header/footer removal
                body = soup.body
                if body:
                    print(f"cleanContent: body found, innerHTML length: {len(str(body))}")
                    cleaned = str(body)
                else:
                    print("cleanContent: no body found")
            
            # Additional cleanup: remove any remaining date/modified sections
            date_selectors = [
                '.pagedetails',
                '.wb-inv',
                '.wb-tphp',
                '.date-modified',
                '.modified',
                '[class*="date"]',
                '[id*="date"]'
            ]
            
            for selector in date_selectors:
                for element in soup.select(selector):
                    text = element.get_text() or ''
                    if ('Date modified' in text or 'Page details' in text or 
                        'Modified' in text or re.search(r'\d{4}-\d{2}-\d{2}', text)):
                        element.decompose()
            
        except Exception as e:
            print(f"HTML parsing failed, falling back to text cleaning: {e}")
    
    # For plain text content or fallback, use pattern matching
    if '<' not in cleaned or cleaned == content:
        # Remove "Page details YYYY-MM-DD" footer
        cleaned = re.sub(r'Page details \d{4}-\d{2}-\d{2}$', '', cleaned, flags=re.IGNORECASE).strip()
        
        # Remove common Canada.ca footer patterns
        footer_patterns = [
            r'Date modified:.*$',
            r'Government of Canada.*$',
            r'©.*$',
            r'All rights reserved.*$',
            r'Report a problem.*$',
            r'Contact us.*$',
            r'Terms and conditions.*$',
            r'Privacy.*$',
            r'Canada\.ca.*$'
        ]
        
        for pattern in footer_patterns:
            cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE | re.MULTILINE).strip()
        
        # Remove duplicate title at beginning
        lines = cleaned.split('\n')
        if len(lines) > 1:
            first_line = lines[0].strip()
            if len(first_line) < 100 and cleaned.find(first_line, len(first_line)) != -1:
                lines.pop(0)
                cleaned = '\n'.join(lines).strip()
    
    print(f"cleanContent: returning cleaned content, length: {len(cleaned)}")
    print(f"First 500 chars: {cleaned[:500]}")
    return cleaned

def test_avis_page():
    """Test cleaning the avis page with updated logic"""
    print("Testing avis page cleaning with updated logic...")
    
    # Fetch the avis page from API
    response = requests.get("http://localhost:8000/api/v1/pages/avis")
    if response.status_code != 200:
        print(f"Failed to fetch avis page: {response.status_code}")
        return
    
    data = response.json()
    content = data.get('content', '')
    title = data.get('title', '')
    
    print(f"Original content length: {len(content)}")
    print(f"Title: {title}")
    
    # Test cleaning
    cleaned = clean_content_updated(content, 'avis')
    
    # Check if cleaned content has actual content beyond title
    soup = BeautifulSoup(cleaned, 'html.parser')
    text = soup.get_text().strip()
    
    print(f"\nCleaned text preview (first 1000 chars):")
    print(text[:1000])
    
    print(f"\nText length: {len(text)}")
    
    # Check for specific content sections
    if "Emploi de fichiers situés" in text:
        print("✓ Found French content section: 'Emploi de fichiers situés'")
    else:
        print("✗ Missing French content section: 'Emploi de fichiers situés'")
    
    if "Présentation d'un contenu dans les deux langues officielles" in text:
        print("✓ Found French content section: 'Présentation d'un contenu...'")
    else:
        print("✗ Missing French content section: 'Présentation d'un contenu...'")
    
    # Check HTML structure
    print(f"\nCleaned HTML tag analysis:")
    if soup.find():
        tags = {}
        for tag in soup.find_all():
            tags[tag.name] = tags.get(tag.name, 0) + 1
        print(f"  Tags found: {tags}")

if __name__ == "__main__":
    test_avis_page()