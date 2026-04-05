#!/usr/bin/env python3
"""
创建标准WET-BOEW header和footer页面
"""

import sqlite3
import uuid
from datetime import datetime

DB_PATH = "/home/hongb/.openclaw/workspace/filebot/backend/filebot.db"

# WET-BOEW标准header HTML（简化版）
HEADER_HTML_EN = '''<header role="banner">
    <div id="wb-bnr" class="container">
        <div class="row">
            <div class="brand col-xs-5 col-md-4" property="publisher" typeof="GovernmentOrganization">
                <a href="https://www.canada.ca/en.html" property="url">
                    <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/sig-blk-en.svg" alt="Government of Canada" property="logo" />
                    <span class="wb-inv"> / <span lang="fr">Gouvernement du Canada</span></span>
                </a>
                <meta property="name" content="Government of Canada" />
                <meta property="areaServed" typeOf="Country" content="Canada" />
            </div>
            <section id="wb-srch" class="col-lg-8 text-right">
                <h2>Search</h2>
                <form action="https://recherche-search.gc.ca/rGs/s_r?#wb-land" method="get" role="search" class="form-inline">
                    <div class="form-group">
                        <label for="wb-srch-q" class="wb-inv">Search Canada.ca</label>
                        <input id="wb-srch-q" list="wb-srch-q-ac" class="wb-srch-q form-control" name="q" type="search" value="" size="27" maxlength="150" placeholder="Search Canada.ca" />
                        <datalist id="wb-srch-q-ac"></datalist>
                    </div>
                    <div class="form-group submit">
                        <button type="submit" id="wb-srch-sub" class="btn btn-primary btn-small" name="wb-srch-sub">
                            <span class="glyphicon-search glyphicon"></span>
                            <span class="wb-inv">Search</span>
                        </button>
                    </div>
                </form>
            </section>
        </div>
    </div>
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <nav class="gcweb-menu" typeof="SiteNavigationElement">
                    <div class="container">
                        <h2 class="wb-inv">Menu</h2>
                        <button type="button" aria-haspopup="true" aria-expanded="false">
                            <span class="wb-inv">Main </span>Menu <span class="expicon glyphicon glyphicon-chevron-down"></span>
                        </button>
                        <ul role="menu" aria-orientation="vertical" data-ajax-replace="https://www.canada.ca/content/dam/canada/sitemenu/sitemenu-v2-en.html">
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/jobs.html">Jobs and the workplace</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/immigration-citizenship.html">Immigration and citizenship</a></li>
                            <li role="presentation"><a role="menuitem" href="https://travel.gc.ca/">Travel and tourism</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/business.html">Business and industry</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/benefits.html">Benefits</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/health.html">Health</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/taxes.html">Taxes</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/environment.html">Environment and natural resources</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/defence.html">National security and defence</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/culture.html">Culture, history and sport</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/policing.html">Policing, justice and emergencies</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/transport.html">Transport and infrastructure</a></li>
                            <li role="presentation"><a role="menuitem" href="https://international.gc.ca/world-monde/index.aspx?lang=eng">Canada and the world</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/finance.html">Money and finance</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/en/services/science.html">Science and innovation</a></li>
                        </ul>
                    </div>
                </nav>
            </div>
        </div>
    </div>
</header>'''

# WET-BOEW标准footer HTML（简化版）
FOOTER_HTML_EN = '''<footer role="contentinfo" id="wb-info">
    <div class="brand">
        <div class="container">
            <div class="row">
                <nav class="col-md-10 ftr-urlt-lnk">
                    <h2 class="wb-inv">About this site</h2>
                    <ul>
                        <li><a href="https://www.canada.ca/en/social.html">Social media</a></li>
                        <li><a href="https://www.canada.ca/en/mobile.html">Mobile applications</a></li>
                        <li><a href="https://www1.canada.ca/en/newsite.html">About Canada.ca</a></li>
                        <li><a href="https://www.canada.ca/en/transparency/terms.html">Terms and conditions</a></li>
                        <li><a href="https://www.canada.ca/en/transparency/privacy.html">Privacy</a></li>
                    </ul>
                </nav>
                <div class="col-xs-6 col-sm-5 col-lg-2">
                    <a href="https://www.canada.ca/en/contact.html" class="btn btn-default btn-block">Contact us</a>
                </div>
            </div>
        </div>
    </div>
    <div class="container">
        <div class="row">
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <a href="https://www.canada.ca/en/government/about.html">
                    <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/wmms-blk.svg" alt="Symbol of the Government of Canada" />
                </a>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/en/transparency/terms.html">Terms and conditions</a><br />
                    <a href="https://www.canada.ca/en/transparency/privacy.html">Privacy</a>
                </p>
            </div>
            <div class="clearfix visible-xs"></div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/en/contact.html">Contact us</a><br />
                    <a href="https://www.canada.ca/en/government/dept.html">Departments and agencies</a><br />
                    <a href="https://www.canada.ca/en/government/publicservice.html">Public service and military</a>
                </p>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/en/news.html">News</a><br />
                    <a href="https://www.canada.ca/en/government/system/laws.html">Treaties, laws and regulations</a><br />
                    <a href="https://www.canada.ca/en/transparency/reporting.html">Government-wide reporting</a>
                </p>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://pm.gc.ca/eng">Prime Minister</a><br />
                    <a href="https://www.canada.ca/en/government/system.html">How government works</a><br />
                    <a href="https://open.canada.ca/en/">Open government</a>
                </p>
            </div>
        </div>
    </div>
</footer>'''

# 法语版本
HEADER_HTML_FR = '''<header role="banner">
    <div id="wb-bnr" class="container">
        <div class="row">
            <div class="brand col-xs-5 col-md-4" property="publisher" typeof="GovernmentOrganization">
                <a href="https://www.canada.ca/fr.html" property="url">
                    <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/sig-blk-fr.svg" alt="Gouvernement du Canada" property="logo" />
                    <span class="wb-inv"> / <span lang="en">Government of Canada</span></span>
                </a>
                <meta property="name" content="Gouvernement du Canada" />
                <meta property="areaServed" typeOf="Country" content="Canada" />
            </div>
            <section id="wb-srch" class="col-lg-8 text-right">
                <h2>Recherche</h2>
                <form action="https://recherche-search.gc.ca/rGs/s_r?#wb-land" method="get" role="search" class="form-inline">
                    <div class="form-group">
                        <label for="wb-srch-q" class="wb-inv">Rechercher dans Canada.ca</label>
                        <input id="wb-srch-q" list="wb-srch-q-ac" class="wb-srch-q form-control" name="q" type="search" value="" size="27" maxlength="150" placeholder="Rechercher dans Canada.ca" />
                        <datalist id="wb-srch-q-ac"></datalist>
                    </div>
                    <div class="form-group submit">
                        <button type="submit" id="wb-srch-sub" class="btn btn-primary btn-small" name="wb-srch-sub">
                            <span class="glyphicon-search glyphicon"></span>
                            <span class="wb-inv">Recherche</span>
                        </button>
                    </div>
                </form>
            </section>
        </div>
    </div>
    <div class="container">
        <div class="row">
            <div class="col-md-12">
                <nav class="gcweb-menu" typeof="SiteNavigationElement">
                    <div class="container">
                        <h2 class="wb-inv">Menu</h2>
                        <button type="button" aria-haspopup="true" aria-expanded="false">
                            <span class="wb-inv">Menu </span>principal <span class="expicon glyphicon glyphicon-chevron-down"></span>
                        </button>
                        <ul role="menu" aria-orientation="vertical" data-ajax-replace="https://www.canada.ca/content/dam/canada/sitemenu/sitemenu-v2-fr.html">
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/emplois.html">Emplois et milieu de travail</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/immigration-citoyennete.html">Immigration et citoyenneté</a></li>
                            <li role="presentation"><a role="menuitem" href="https://voyage.gc.ca/">Voyage et tourisme</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/entreprises.html">Entreprises et industrie</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/prestations.html">Prestations</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/sante.html">Santé</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/impots.html">Impôts</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/environnement.html">Environnement et ressources naturelles</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/defense.html">Sécurité nationale et défense</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/culture.html">Culture, histoire et sport</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/police.html">Services de police, justice et urgences</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/transport.html">Transport et infrastructure</a></li>
                            <li role="presentation"><a role="menuitem" href="https://international.gc.ca/world-monde/index.aspx?lang=fra">Le Canada et le monde</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/finance.html">Argent et finances</a></li>
                            <li role="presentation"><a role="menuitem" href="https://www.canada.ca/fr/services/science.html">Science et innovation</a></li>
                        </ul>
                    </div>
                </nav>
            </div>
        </div>
    </div>
</header>'''

FOOTER_HTML_FR = '''<footer role="contentinfo" id="wb-info">
    <div class="brand">
        <div class="container">
            <div class="row">
                <nav class="col-md-10 ftr-urlt-lnk">
                    <h2 class="wb-inv">À propos de ce site</h2>
                    <ul>
                        <li><a href="https://www.canada.ca/fr/sociaux.html">Médias sociaux</a></li>
                        <li><a href="https://www.canada.ca/fr/mobile.html">Applications mobiles</a></li>
                        <li><a href="https://www1.canada.ca/fr/nouveausite.html">À propos de Canada.ca</a></li>
                        <li><a href="https://www.canada.ca/fr/transparence/avis.html">Avis</a></li>
                        <li><a href="https://www.canada.ca/fr/transparence/confidentialite.html">Confidentialité</a></li>
                    </ul>
                </nav>
                <div class="col-xs-6 col-sm-5 col-lg-2">
                    <a href="https://www.canada.ca/fr/contact.html" class="btn btn-default btn-block">Nous joindre</a>
                </div>
            </div>
        </div>
    </div>
    <div class="container">
        <div class="row">
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <a href="https://www.canada.ca/fr/gouvernement/a-propos.html">
                    <img src="https://wet-boew.github.io/themes-dist/GCWeb/GCWeb/assets/wmms-blk.svg" alt="Symbole du gouvernement du Canada" />
                </a>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/fr/transparence/avis.html">Avis</a><br />
                    <a href="https://www.canada.ca/fr/transparence/confidentialite.html">Confidentialité</a>
                </p>
            </div>
            <div class="clearfix visible-xs"></div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/fr/contact.html">Nous joindre</a><br />
                    <a href="https://www.canada.ca/fr/gouvernement/min.html">Ministères et organismes</a><br />
                    <a href="https://www.canada.ca/fr/gouvernement/fonctionpublique.html">Fonction publique et force militaire</a>
                </p>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://www.canada.ca/fr/nouvelles.html">Nouvelles</a><br />
                    <a href="https://www.canada.ca/fr/gouvernement/systeme/lois.html">Traités, lois et règlements</a><br />
                    <a href="https://www.canada.ca/fr/transparence/rapports.html">Rapports à l'échelle du gouvernement</a>
                </p>
            </div>
            <div class="col-xs-6 col-sm-3 col-md-3 col-lg-2">
                <p class="text-left">
                    <a href="https://pm.gc.ca/fr">Premier ministre</a><br />
                    <a href="https://www.canada.ca/fr/gouvernement/systeme.html">Comment le gouvernement fonctionne</a><br />
                    <a href="https://ouvert.canada.ca/fr/">Gouvernement ouvert</a>
                </p>
            </div>
        </div>
    </div>
</footer>'''

def create_header_footer_pages():
    """创建header和footer页面"""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # 检查表是否存在
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table' AND name='webbot_page'")
    if not cursor.fetchone():
        print("错误: webbot_page 表不存在")
        return False
    
    # 页面定义
    pages_to_create = [
        # 英语页面
        {
            "id": "/canadasite/header",
            "title": "Canada.ca Header (English)",
            "content": HEADER_HTML_EN,
            "language": "en",
            "status": "published",
            "description": "Standard Canada.ca header for English pages"
        },
        {
            "id": "/canadasite/footer",
            "title": "Canada.ca Footer (English)",
            "content": FOOTER_HTML_EN,
            "language": "en",
            "status": "published",
            "description": "Standard Canada.ca footer for English pages"
        },
        {
            "id": "/canadasite/en/header",
            "title": "Canada.ca Header (English - Language Specific)",
            "content": HEADER_HTML_EN,
            "language": "en",
            "status": "published",
            "description": "Language-specific Canada.ca header for English pages"
        },
        {
            "id": "/canadasite/en/footer",
            "title": "Canada.ca Footer (English - Language Specific)",
            "content": FOOTER_HTML_EN,
            "language": "en",
            "status": "published",
            "description": "Language-specific Canada.ca footer for English pages"
        },
        # 法语页面
        {
            "id": "/canadasite/fr/header",
            "title": "Canada.ca Entête (Français)",
            "content": HEADER_HTML_FR,
            "language": "fr",
            "status": "published",
            "description": "Entête standard Canada.ca pour les pages françaises"
        },
        {
            "id": "/canadasite/fr/footer",
            "title": "Canada.ca Pied de page (Français)",
            "content": FOOTER_HTML_FR,
            "language": "fr",
            "status": "published",
            "description": "Pied de page standard Canada.ca pour les pages françaises"
        }
    ]
    
    created_count = 0
    updated_count = 0
    
    for page_data in pages_to_create:
        page_id = page_data["id"]
        
        # 检查页面是否已存在
        cursor.execute("SELECT id FROM webbot_page WHERE id = ?", (page_id,))
        existing = cursor.fetchone()
        
        current_time = datetime.now().isoformat()
        
        if existing:
            # 更新现有页面
            cursor.execute("""
                UPDATE webbot_page 
                SET title = ?, content = ?, language = ?, status = ?, last_modified = ?
                WHERE id = ?
            """, (
                page_data["title"],
                page_data["content"],
                page_data["language"],
                page_data["status"],
                current_time,
                page_id
            ))
            updated_count += 1
            print(f"✓ 更新页面: {page_id}")
        else:
            # 创建新页面
            cursor.execute("""
                INSERT INTO webbot_page (
                    id, title, content, language, status,
                    created_at, last_modified, metadata
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                page_id,
                page_data["title"],
                page_data["content"],
                page_data["language"],
                page_data["status"],
                current_time,
                current_time,
                json.dumps({"description": page_data["description"]})
            ))
            created_count += 1
            print(f"✓ 创建页面: {page_id}")
    
    conn.commit()
    conn.close()
    
    print(f"\n✅ 完成: 创建了 {created_count} 个新页面，更新了 {updated_count} 个现有页面")
    return True

if __name__ == "__main__":
    import json
    create_header_footer_pages()