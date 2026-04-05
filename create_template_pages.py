#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime

# Connect to database
db_path = '/home/hongb/.openclaw/workspace/filebot/backend/filebot.db'
conn = sqlite3.connect(db_path)
cursor = conn.cursor()

# Basic templates to create
templates = [
    {
        'id': 'template-button-primary',
        'title': 'Primary Button Template',
        'content': '<button type="button" class="btn btn-primary webbot-component">${buttonText}</button>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-button-success',
        'title': 'Success Button Template',
        'content': '<button type="button" class="btn btn-success webbot-component">${buttonText}</button>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-button-info',
        'title': 'Info Button Template',
        'content': '<button type="button" class="btn btn-info webbot-component">${buttonText}</button>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-button-warning',
        'title': 'Warning Button Template',
        'content': '<button type="button" class="btn btn-warning webbot-component">${buttonText}</button>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-button-danger',
        'title': 'Danger Button Template',
        'content': '<button type="button" class="btn btn-danger webbot-component">${buttonText}</button>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-alert-info',
        'title': 'Info Alert Template',
        'content': '<div class="alert alert-info webbot-component">\n  <h3>Information</h3>\n  <p>This is an alert box.</p>\n</div>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-alert-danger',
        'title': 'Danger Alert Template',
        'content': '<section class="alert alert-danger webbot-component">\n  <h3>Danger alert</h3>\n  <p>Alert details.</p>\n</section>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-alert-warning',
        'title': 'Warning Alert Template',
        'content': '<section class="alert alert-warning webbot-component">\n  <h3>Warning alert</h3>\n  <p>Alert details.</p>\n</section>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-alert-success',
        'title': 'Success Alert Template',
        'content': '<section class="alert alert-success webbot-component">\n  <h3>Success alert</h3>\n  <p>Alert details.</p>\n</section>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-table-basic',
        'title': 'Basic Table Template',
        'content': '<table class="table table-striped webbot-component">\n  <thead>\n    <tr>\n      <th scope="col">#</th>\n      <th scope="col">Header 1</th>\n      <th scope="col">Header 2</th>\n    </tr>\n  </thead>\n  <tbody>\n    <tr>\n      <th scope="row">1</th>\n      <td>Data 1</td>\n      <td>Data 2</td>\n    </tr>\n  </tbody>\n</table>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-introduction-basic',
        'title': 'Basic Introduction Template',
        'content': '<div class="webbot-component">\n  <h1 property="name" id="wb-cont">Introduction block</h1>\n  <p>The introduction block pattern introduces the content of a landing page.</p>\n  <p><a class="btn btn-call-to-action" href="#">Super task button</a></p>\n</div>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-services-info-2col',
        'title': 'Services and Information (2 Columns)',
        'content': '<section class="gc-srvinfo webbot-component">\n  <h2>Services and information</h2>\n  <div class="wb-eqht row">\n    <div class="col-md-6">\n      <h3><a href="#">[Hyperlink text]</a></h3>\n      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n    </div>\n    <div class="col-md-6">\n      <h3><a href="#">[Hyperlink text]</a></h3>\n      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n    </div>\n    <div class="col-md-6">\n      <h3><a href="#">[Hyperlink text]</a></h3>\n      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n    </div>\n    <div class="col-md-6">\n      <h3><a href="#">[Hyperlink text]</a></h3>\n      <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n    </div>\n  </div>\n</section>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    },
    {
        'id': 'template-services-info-list',
        'title': 'Services and Information (List)',
        'content': '<section class="gc-srvinfo webbot-component">\n  <h2>Services and information</h2>\n  <h3><a href="#">[Hyperlink text]</a></h3>\n  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n  <h3><a href="#">[Hyperlink text]</a></h3>\n  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n  <h3><a href="#">[Hyperlink text]</a></h3>\n  <p>Use action verbs, or simply list keywords to summarize the information or tasks that can be accomplished on the page it links to</p>\n</section>',
        'language': 'en',
        'parent_id': 'template-container',
        'status': 'published'
    }
]

# First, check if template-container page exists
cursor.execute("SELECT id FROM webbot_page WHERE id = ?", ('template-container',))
template_parent = cursor.fetchone()

if not template_parent:
    # Create template-container parent page
    now = datetime.now().isoformat()
    cursor.execute("""
        INSERT INTO webbot_page (
            id, title, content, language, parent_id, other_lang_page_id, 
            status, created_by, created_at, last_modified, last_published, metadata
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
    """, (
        'template-container',
        'Component Templates',
        'Container for component templates',
        'en',
        None,
        None,
        'published',
        'system',
        now,
        now,
        now,
        json.dumps({'template_container': True})
    ))
    print("Created template-container parent page")

# Create template pages
for template in templates:
    # Check if template already exists
    cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (template['id'],))
    existing = cursor.fetchone()
    
    if existing:
        print(f"Template {template['id']} already exists, updating...")
        # Update existing
        now = datetime.now().isoformat()
        cursor.execute("""
            UPDATE webbot_page SET
                title = ?,
                content = ?,
                last_modified = ?
            WHERE id = ?
        """, (
            template['title'],
            template['content'],
            now,
            template['id']
        ))
    else:
        # Insert new
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO webbot_page (
                id, title, content, language, parent_id, other_lang_page_id, 
                status, created_by, created_at, last_modified, last_published, metadata
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            template['id'],
            template['title'],
            template['content'],
            template['language'],
            template['parent_id'],
            None,
            template['status'],
            'system',
            now,
            now,
            now,
            json.dumps({'is_template': True, 'component_type': template['id'].split('/')[-1]})
        ))
        print(f"Created template: {template['id']}")

# Commit changes
conn.commit()
conn.close()

print(f"Created/updated {len(templates)} template pages")