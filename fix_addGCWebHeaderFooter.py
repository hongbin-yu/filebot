#!/usr/bin/env python3
import re
import os

# 读取 editor.html 文件
editor_path = "/home/hongb/.openclaw/workspace/webbot/static/editor.html"
with open(editor_path, 'r', encoding='utf-8') as f:
    content = f.read()

print(f"File size: {len(content)} chars")

# 查找 addGCWebHeaderFooter 函数
pattern = r'function addGCWebHeaderFooter\(content\) \{([\s\S]*?)\n\}\s*\n\s*// Clean content function'
match = re.search(pattern, content)

if match:
    print(f"Function found, length: {len(match.group(0))}")
    func_content = match.group(0)
    
    # 检查函数中的问题
    print("\n=== 问题分析 ===")
    
    # 1. 检查是否有嵌套的 cleanContent 函数
    if 'function cleanContent' in func_content:
        print("❌ 问题: addGCWebHeaderFooter 函数内部包含了 cleanContent 函数定义")
        print("    这会导致 cleanContent 函数被重新定义，而原本在外部定义的 cleanContent 函数会被覆盖")
    
    # 2. 检查 webBotHeader 和 webBotFooter 定义
    webBotHeader_match = re.search(r'const webBotHeader = \\([\s\S]*?);', func_content)
    webBotFooter_match = re.search(r'const webBotFooter = \\([\s\S]*?);', func_content)
    
    if webBotHeader_match:
        print(f"✅ webBotHeader 定义找到，长度: {len(webBotHeader_match.group(0))}")
        # 检查是否有转义问题
        header_content = webBotHeader_match.group(0)
        backslash_count = header_content.count('\\\\"')
        print(f"    转义引号 \\\" 的数量: {backslash_count}")
        
        # 检查是否有模板字符串
        backtick_count = header_content.count('`')
        print(f"    反引号 ` 的数量: {backtick_count}")
        
        if backtick_count > 0:
            print("    ⚠️  警告: 字符串中包含反引号，可能导致 JavaScript 语法错误")
    
    if webBotFooter_match:
        print(f"✅ webBotFooter 定义找到，长度: {len(webBotFooter_match.group(0))}")
    
    # 3. 检查函数返回值
    return_match = re.search(r'return ([^;]+);', func_content)
    if return_match:
        print(f"✅ 返回值: {return_match.group(1)[:50]}...")
    
    print("\n=== 修复方案 ===")
    print("1. 移除 addGCWebHeaderFooter 函数内部的 cleanContent 函数定义")
    print("2. 修复字符串中的转义问题")
    print("3. 确保函数只返回 gcwebHeader + mainContent + gcwebFooter")
    print("4. 移除 webBotHeader 和 webBotFooter 部分（这些不应该在 GCWeb 函数中）")
    
    # 生成修复后的函数
    print("\n=== 生成修复后的函数 ===")
    
    # 简单的修复：创建一个新的 addGCWebHeaderFooter 函数
    # 只包含 GCWeb 头部和尾部，不包含 WebBot 部分
    new_function = '''        function addGCWebHeaderFooter(content) {
            if (!content || typeof content !== 'string') return content;
            
            // Extract main content if needed
            let mainContent = extractMainContent(content);
            
            // GCWeb header (simplified version)
            const gcwebHeader = 
    "<header id=\\"gcweb-header\\">" +
    "<div id=\\"wb-bnr\\" class=\\"container\\">" +
    "<div class=\\"row\\">" +
    "<section id=\\"wb-lng\\" class=\\"col-xs-3 col-sm-12 pull-right text-right\\">" +
    "<h2 class=\\"wb-inv\\">Language selection</h2>" +
    "<div class=\\"row\\">" +
    "<div class=\\"col-md-12\\">" +
    "<ul class=\\"list-inline mrgn-bttm-0\\">" +
    "<li><a lang=\\"fr\\" href=\\"#\\">Français</a></li>" +
    "</ul>" +
    "</div>" +
    "</div>" +
    "</section>" +
    "<div class=\\"brand col-xs-9 col-sm-5 col-md-4\\" property=\\"publisher\\" typeof=\\"GovernmentOrganization\\">" +
    "<a href=\\"https://www.canada.ca/en.html\\">" +
    "<img src=\\"https://www.canada.ca/etc/designs/canada/wet-boew/assets/sig-blk-en.svg\\" alt=\\"Government of Canada\\" property=\\"logo\\">" +
    "<span class=\\"wb-inv\\">Government of Canada / <span lang=\\"fr\\">Gouvernement du Canada</span></span>" +
    "</a>" +
    "</div>" +
    "<section id=\\"wb-srch\\" class=\\"col-lg-8 text-right visible-md visible-lg\\">" +
    "<h2>Search</h2>" +
    "<form action=\\"/en/sr/srb.html\\" method=\\"get\\" name=\\"cse-search-box\\" role=\\"search\\">" +
    "<div class=\\"form-group wb-srch-qry\\">" +
    "<label for=\\"wb-srch-q\\" class=\\"wb-inv\\">Search Canada.ca</label>" +
    "<input id=\\"wb-srch-q\\" list=\\"wb-srch-q-ac\\" class=\\"wb-srch-q form-control\\" name=\\"q\\" type=\\"search\\" value=\\"\\" size=\\"27\\" maxlength=\\"150\\" placeholder=\\"Search Canada.ca\\">" +
    "<datalist id=\\"wb-srch-q-ac\\"></datalist>" +
    "</div>" +
    "<div class=\\"form-group submit\\">" +
    "<button type=\\"submit\\" id=\\"wb-srch-sub\\" class=\\"btn btn-primary btn-small\\">" +
    "<span class=\\"glyphicon-search glyphicon\\"></span>" +
    "<span class=\\"wb-inv\\">Search</span>" +
    "</button>" +
    "</div>" +
    "</form>" +
    "</section>" +
    "</div>" +
    "</div>" +
    "<nav class=\\"gcweb-menu\\" typeof=\\"SiteNavigationElement\\">" +
    "<div class=\\"container\\">" +
    "<h2 class=\\"wb-inv\\">Menu</h2>" +
    "<button type=\\"button\\" aria-haspopup=\\"true\\" aria-expanded=\\"false\\">Menu <span class=\\"expicon glyphicon glyphicon-chevron-down\\"></span></button>" +
    "<ul role=\\"menu\\" aria-orientation=\\"vertical\\" data-ajax-replace=\\"/etc/designs/canada/wet-boew/ajax/sitemenu-en.html\\">" +
    "<li role=\\"presentation\\"><a role=\\"menuitem\\" href=\\"/en/services/jobs.html\\">Jobs and the workplace</a></li>" +
    "<li role=\\"presentation\\"><a role=\\"menuitem\\" href=\\"/en/services/immigration-citizenship.html\\">Immigration and citizenship</a></li>" +
    "<li role=\\"presentation\\"><a role=\\"menuitem\\" href=\\"https://travel.gc.ca/\\">Travel and tourism</a></li>" +
    "</ul>" +
    "</div>" +
    "</nav>" +
    "</header>" +
    "<main property=\\"mainContentOfPage\\" resource=\\"#wb-main\\" typeof=\\"WebPageElement\\" class=\\"container\\">" +
    "<div class=\\"row mrgn-tp-lg\\">" +
    "<div class=\\"col-md-12\\">";
            
            // GCWeb footer (simplified version)
            const gcwebFooter = 
    "</div>" +
    "</div>" +
    "</main>" +
    "<footer id=\\"gcweb-footer\\">" +
    "<div id=\\"wb-info\\">" +
    "<div class=\\"gc-main-footer\\">" +
    "<div class=\\"container\\">" +
    "<nav>" +
    "<h3>Government of Canada</h3>" +
    "<ul class=\\"list-col-xs-1 list-col-sm-2 list-col-md-3\\">" +
    "<li><a href=\\"/en/contact.html\\">All contacts</a></li>" +
    "<li><a href=\\"/en/government/dept.html\\">Departments and agencies</a></li>" +
    "<li><a href=\\"/en/government/system.html\\">About government</a></li>" +
    "</ul>" +
    "<h4><span class=\\"wb-inv\\">Themes and topics</span></h4>" +
    "<ul class=\\"list-unstyled colcount-sm-2 colcount-md-3\\">" +
    "<li><a href=\\"/en/services/jobs.html\\">Jobs</a></li>" +
    "<li><a href=\\"/en/services/immigration-citizenship.html\\">Immigration and citizenship</a></li>" +
    "<li><a href=\\"https://travel.gc.ca/\\">Travel and tourism</a></li>" +
    "<li><a href=\\"/en/services/business.html\\">Business</a></li>" +
    "<li><a href=\\"/en/services/benefits.html\\">Benefits</a></li>" +
    "<li><a href=\\"/en/services/health.html\\">Health</a></li>" +
    "</ul>" +
    "</nav>" +
    "</div>" +
    "</div>" +
    "<div class=\\"brand\\">" +
    "<div class=\\"container\\">" +
    "<div class=\\"row\\">" +
    "<nav class=\\"col-md-9 col-lg-10 ftr-urlt-lnk\\">" +
    "<h2 class=\\"wb-inv\\">About this site</h2>" +
    "<ul>" +
    "<li><a href=\\"/en/contact.html\\">Contact us</a></li>" +
    "<li><a href=\\"/en/government/dept.html\\">Departments and agencies</a></li>" +
    "<li><a href=\\"/en/government/system.html\\">About government</a></li>" +
    "</ul>" +
    "</nav>" +
    "<div class=\\"col-xs-6 visible-sm visible-xs tofpg\\">" +
    "<a href=\\"#wb-cont\\">Top of Page <span class=\\"glyphicon glyphicon-chevron-up\\"></span></a>" +
    "</div>" +
    "<div class=\\"col-xs-6 col-md-3 col-lg-2 text-right\\">" +
    "<img src=\\"https://www.canada.ca/etc/designs/canada/wet-boew/assets/wmms-blk.svg\\" alt=\\"Symbol of the Government of Canada\\">" +
    "</div>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "</div>" +
    "</footer>";
            
            return gcwebHeader + mainContent + gcwebFooter;
        }'''
    
    print("修复函数已生成")
    print(f"新函数长度: {len(new_function)}")
    
    # 备份原文件
    backup_path = editor_path + '.backup_gcweb_fix'
    with open(backup_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"\n原文件已备份到: {backup_path}")
    
    # 替换原函数
    # 首先找到函数的结束位置
    func_end_pattern = r'function addGCWebHeaderFooter\(content\) \{[\s\S]*?\n\}\s*\n'
    new_content = re.sub(func_end_pattern, new_function + '\n\n', content, count=1)
    
    # 保存修改
    with open(editor_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    
    print(f"文件已更新: {editor_path}")
    
    # 验证修改
    with open(editor_path, 'r', encoding='utf-8') as f:
        updated_content = f.read()
    
    if 'function addGCWebHeaderFooter' in updated_content:
        print("✅ 修改成功验证: addGCWebHeaderFooter 函数存在")
    
    # 检查是否还有嵌套的 cleanContent 函数
    if 'function cleanContent(content)' in updated_content:
        # 计算 cleanContent 出现的次数
        cleanContent_count = updated_content.count('function cleanContent')
        print(f"⚠️  cleanContent 函数出现 {cleanContent_count} 次")
        
        # 如果是2次，可能有重复定义
        if cleanContent_count > 1:
            print("❌ 问题: cleanContent 函数有重复定义")
            print("    这可能导致 JavaScript 错误")
    
    print("\n=== 下一步 ===")
    print("1. 重新测试编辑器页面")
    print("2. 检查浏览器控制台是否有 JavaScript 错误")
    print("3. 验证预览功能是否正常工作")
    
else:
    print("❌ addGCWebHeaderFooter 函数未找到")
    
    # 尝试查找函数的不同格式
    alt_pattern = r'function addGCWebHeaderFooter[\s\S]*?\n\}\s*\n'
    alt_match = re.search(alt_pattern, content)
    if alt_match:
        print(f"备选模式找到函数，长度: {len(alt_match.group(0))}")
        print("前500字符:")
        print(alt_match.group(0)[:500])