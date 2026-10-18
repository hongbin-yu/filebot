/* 拼写检查模块（独立叠加层）
 * 依赖：typo.js（全局 Typo）、TinyMCE editor 实例
 * 词典：/static/dicts/{en_CA|fr_CA}.{aff,dic}（离线 Hunspell 词典）
 * 设计：高亮只是临时 UI 层，序列化/取内容前自动清理，HTML 不残留标记
 */
(function () {
  'use strict';
  if (typeof Typo === 'undefined') {
    console.warn('[spellcheck] typo.js not loaded, spell check unavailable');
    return;
  }

  var dict = null;
  var dictLang = null;
  var popupEl = null;

  // ---- 语言 ----
  function getPageLanguage() {
    if (window.currentPageData && window.currentPageData.language) {
      var l = String(window.currentPageData.language).toLowerCase();
      if (l === 'fr' || l === 'fr_ca') return 'fr_CA';
      return 'en_CA';
    }
    var m = (location.pathname || '').match(/^\/(en|fr)(\/|$)/);
    return (m && m[1] === 'fr') ? 'fr_CA' : 'en_CA';
  }

  // ---- 词典加载（带缓存）----
  function loadDict(lang) {
    if (dict && dictLang === lang) return Promise.resolve(dict);
    return Promise.all([
      fetch('/static/dicts/' + lang + '.aff').then(function (r) { return r.text(); }),
      fetch('/static/dicts/' + lang + '.dic').then(function (r) { return r.text(); })
    ]).then(function (d) {
      dict = new Typo(lang, d[0], d[1]);
      dictLang = lang;
      return dict;
    });
  }

  // ---- 标记清理 ----
  function clearMarks(body) {
    if (!body) return;
    var els = body.querySelectorAll('.spell-err, .spell-fixed');
    for (var i = 0; i < els.length; i++) {
      var el = els[i];
      var t = body.ownerDocument.createTextNode(el.textContent);
      el.parentNode.replaceChild(t, el);
    }
    body.normalize();
  }

  // ---- 单词检查（含法语 elision 处理）----
  function checkWord(word) {
    if (dict.check(word)) return true;
    // 法语 elision：l'heure -> heure, d'accord -> accord
    var m = word.match(/^[a-zà-ÿ]'/i);
    if (m && word.length > m[0].length) {
      if (dict.check(word.slice(m[0].length))) return true;
    }
    return false;
  }

  // ---- 建议弹窗 ----
  function ensurePopup() {
    if (!popupEl) {
      popupEl = document.createElement('div');
      popupEl.id = 'spellcheck-popup';
      popupEl.style.cssText = 'position:fixed;display:none;background:#fff;border:1px solid #d0d5dd;border-radius:8px;box-shadow:0 6px 24px rgba(0,0,0,.16);min-width:160px;max-width:280px;z-index:2147483647;overflow:hidden;font-family:-apple-system,Segoe UI,Roboto,Arial,sans-serif;';
      document.body.appendChild(popupEl);
    }
    return popupEl;
  }
  function hidePopup() {
    if (popupEl) popupEl.style.display = 'none';
  }

  function getIframeRect(editor) {
    var iframe = editor.iframeElement ||
      (editor.getWin && editor.getWin().frameElement) || null;
    return iframe ? iframe.getBoundingClientRect() : null;
  }

  function showSuggest(editor, span) {
    var word = span.textContent;
    var sugs = dict ? dict.suggest(word) : [];
    var ifr = getIframeRect(editor);
    var sr = span.getBoundingClientRect();
    var popup = ensurePopup();
    popup.innerHTML = '';

    var title = document.createElement('div');
    title.style.cssText = 'padding:6px 10px;font-size:12px;color:#888;border-bottom:1px solid #eee;';
    title.textContent = word;
    popup.appendChild(title);

    if (!sugs || sugs.length === 0) {
      var no = document.createElement('div');
      no.style.cssText = 'padding:8px 12px;font-size:13px;color:#999;';
      no.textContent = 'No suggestions';
      popup.appendChild(no);
    } else {
      sugs.slice(0, 10).forEach(function (s) {
        var d = document.createElement('div');
        d.style.cssText = 'padding:7px 12px;font-size:14px;cursor:pointer;';
        d.textContent = s;
        d.onmouseenter = function () { d.style.background = '#eef4ff'; };
        d.onmouseleave = function () { d.style.background = ''; };
        d.onclick = function () {
          span.textContent = s;
          span.className = 'spell-fixed';
          hidePopup();
        };
        popup.appendChild(d);
      });
    }

    var left = (ifr ? ifr.left : 0) + sr.left;
    var top = (ifr ? ifr.top : 0) + sr.bottom + 5;
    popup.style.left = left + 'px';
    popup.style.top = top + 'px';
    popup.style.display = 'block';
  }

  // ---- 主检查 ----
  function runCheck(editor) {
    var lang = getPageLanguage();
    editor.notificationManager.open({
      text: 'Loading dictionary ' + lang + ' ...',
      type: 'info',
      timeout: 1500
    });
    loadDict(lang).then(function () {
      var body = editor.getBody();
      var doc = body.ownerDocument;
      clearMarks(body);
      hidePopup();

      var walker = doc.createTreeWalker(body, NodeFilter.SHOW_TEXT, null);
      var nodes = [];
      while (walker.nextNode()) nodes.push(walker.currentNode);

      var re = /[\p{L}\p{M}'’\-]+/gu;
      var total = 0, errors = 0;

      nodes.forEach(function (node) {
        var text = node.nodeValue;
        var m, last = 0;
        var frag = doc.createDocumentFragment();
        re.lastIndex = 0;
        while ((m = re.exec(text))) {
          var word = m[0];
          if (m.index > last) frag.appendChild(doc.createTextNode(text.slice(last, m.index)));
          total++;
          if (checkWord(word)) {
            frag.appendChild(doc.createTextNode(word));
          } else {
            errors++;
            var span = doc.createElement('span');
            span.className = 'spell-err';
            span.textContent = word;
            frag.appendChild(span);
          }
          last = m.index + word.length;
        }
        if (last < text.length) frag.appendChild(doc.createTextNode(text.slice(last)));
        node.parentNode.replaceChild(frag, node);
      });

      editor.notificationManager.open({
        text: 'Spell check complete: ' + total + ' words, ' + errors + ' possible errors',
        type: errors > 0 ? 'warning' : 'success',
        timeout: 6000
      });
    }).catch(function (e) {
      editor.notificationManager.open({
        text: 'Dictionary load failed: ' + e,
        type: 'error',
        timeout: 5000
      });
    });
  }

  // ---- 注入 iframe 内高亮样式 ----
  function injectStyles(editor) {
    var doc = editor.getDoc();
    if (!doc) return;
    var head = doc.head || doc.getElementsByTagName('head')[0];
    if (!head) return;
    var style = doc.createElement('style');
    style.textContent = '.spell-err{text-decoration:underline wavy #e11d48;text-decoration-skip-ink:none;background-color:rgba(225,29,72,.06);cursor:pointer;}' +
      '.spell-fixed{text-decoration:none;background:none;} .spell-err:hover{background-color:rgba(225,29,72,.12);}';
    head.appendChild(style);
  }

  // ---- 绑定编辑器事件（幂等）----
  function attach(editor) {
    if (editor.__spellAttached) return;
    editor.__spellAttached = true;

    injectStyles(editor);

    editor.on('click', function (e) {
      if (e.target && e.target.nodeType === 1 && e.target.classList && e.target.classList.contains('spell-err')) {
        showSuggest(editor, e.target);
        e.preventDefault();
      } else if (popupEl && !popupEl.contains(e.target)) {
        hidePopup();
      }
    });

    // 序列化时剥离高亮标记（node filter）：取出的 HTML 不残留，且不影响编辑器内正在显示的标记
    editor.serializer.addNodeFilter('span', function (nodes) {
      for (var i = 0; i < nodes.length; i++) {
        var cls = nodes[i].attr('class') || '';
        if (cls.indexOf('spell-err') !== -1 || cls.indexOf('spell-fixed') !== -1) {
          nodes[i].unwrap();
        }
      }
    });
  }

  // ---- 导出 ----
  window.runSpellCheck = function (editor) {
    if (!editor) return;
    attach(editor);
    runCheck(editor);
  };
  window.clearSpellCheckMarks = function (editor) {
    if (editor) clearMarks(editor.getBody());
    hidePopup();
  };
})();
