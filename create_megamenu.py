#!/usr/bin/env python3
import sqlite3
import json
from datetime import datetime

def get_db_connection():
    """获取数据库连接（从 pages.py 复制）"""
    import os
    db_path = os.path.join(os.path.dirname(__file__), "webbot", "filebot", "backend", "filebot.db")
    # 备用路径
    if not os.path.exists(db_path):
        db_path = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"
    if not os.path.exists(db_path):
        db_path = "/home/hongb/.openclaw/workspace/webbot/filebot/backend/filebot.db"
    
    print(f"数据库路径: {db_path}")
    conn = sqlite3.connect(db_path)
    conn.row_factory = sqlite3.Row
    return conn

def create_megamenu():
    conn = get_db_connection()
    cursor = conn.cursor()
    
    now = datetime.now().isoformat()
    
    # 英文 megamenu
    english_data = {
        "id": "/canadasite/en/megamenu",
        "title": "Megamenu",
        "content": """<div class="megamenu">
<nav>
  <ul>
    <li><a href="/canadasite/en">Home</a></li>
    <li>
      <a href="/canadasite/en/services">Services <span>▼</span></a>
      <div class="dropdown">
        <a href="/canadasite/en/web">Web Development</a>
        <a href="/canadasite/en/mobile">Mobile Apps</a>
        <a href="/canadasite/en/cloud">Cloud Solutions</a>
      </div>
    </li>
    <li>
      <a href="/canadasite/en/products">Products <span>▼</span></a>
      <div class="dropdown">
        <a href="/canadasite/en/software">Software</a>
        <a href="/canadasite/en/hardware">Hardware</a>
        <a href="/canadasite/en/support">Support</a>
      </div>
    </li>
    <li><a href="/canadasite/en/about">About Us</a></li>
    <li><a href="/canadasite/en/contact">Contact</a></li>
  </ul>
</nav>
</div>""",
        "language": "en",
        "parent_id": "/canadasite/en",
        "other_lang_page_id": "/canadasite/fr/megamenu",
        "status": "published",
        "metadata": json.dumps({"component_type": "megamenu", "is_structural": True}),
        "created_at": now,
        "last_modified": now
    }
    
    # 法文 megamenu
    french_data = {
        "id": "/canadasite/fr/megamenu",
        "title": "Mégamenu",
        "content": """<div class="megamenu">
<nav>
  <ul>
    <li><a href="/canadasite/fr">Accueil</a></li>
    <li>
      <a href="/canadasite/fr/services">Services <span>▼</span></a>
      <div class="dropdown">
        <a href="/canadasite/fr/web">Développement Web</a>
        <a href="/canadasite/fr/mobile">Applications Mobiles</a>
        <a href="/canadasite/fr/cloud">Solutions Cloud</a>
      </div>
    </li>
    <li>
      <a href="/canadasite/fr/products">Produits <span>▼</span></a>
      <div class="dropdown">
        <a href="/canadasite/fr/software">Logiciels</a>
        <a href="/canadasite/fr/hardware">Matériel</a>
        <a href="/canadasite/fr/support">Support</a>
      </div>
    </li>
    <li><a href="/canadasite/fr/a-propos">À propos</a></li>
    <li><a href="/canadasite/fr/contact">Contact</a></li>
  </ul>
</nav>
</div>""",
        "language": "fr",
        "parent_id": "/canadasite/fr",
        "other_lang_page_id": "/canadasite/en/megamenu",
        "status": "published",
        "metadata": json.dumps({"component_type": "megamenu", "is_structural": True}),
        "created_at": now,
        "last_modified": now
    }
    
    try:
        # 检查是否已存在
        cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (english_data["id"],))
        if cursor.fetchone():
            print(f"页面已存在: {english_data['id']}")
        else:
            cursor.execute("""
                INSERT INTO webbot_page 
                (id, title, content, language, parent_id, other_lang_page_id, status, metadata, created_at, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                english_data["id"],
                english_data["title"],
                english_data["content"],
                english_data["language"],
                english_data["parent_id"],
                english_data["other_lang_page_id"],
                english_data["status"],
                english_data["metadata"],
                english_data["created_at"],
                english_data["last_modified"]
            ))
            print(f"创建英文 megamenu: {english_data['id']}")
        
        cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (french_data["id"],))
        if cursor.fetchone():
            print(f"页面已存在: {french_data['id']}")
        else:
            cursor.execute("""
                INSERT INTO webbot_page 
                (id, title, content, language, parent_id, other_lang_page_id, status, metadata, created_at, last_modified)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                french_data["id"],
                french_data["title"],
                french_data["content"],
                french_data["language"],
                french_data["parent_id"],
                french_data["other_lang_page_id"],
                french_data["status"],
                french_data["metadata"],
                french_data["created_at"],
                french_data["last_modified"]
            ))
            print(f"创建法文 megamenu: {french_data['id']}")
        
        conn.commit()
        print("✅ 两个 megamenu 页面创建成功")
        
    except Exception as e:
        conn.rollback()
        print(f"❌ 创建失败: {e}")
        raise
    finally:
        conn.close()

if __name__ == "__main__":
    create_megamenu()