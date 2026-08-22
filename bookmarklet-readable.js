(function(){
  if (window.__DEPT_IMPORT_LOADED) return;
  window.__DEPT_IMPORT_LOADED = true;

  var BOOKMARKLET_VERSION = '2026-08-21-v11';



  var css = document.createElement('style');
  css.textContent = `
#deptImportTool * { box-sizing:border-box; margin:0; padding:0; font-family:system-ui,sans-serif; }
#deptImportTool {
  position:fixed; top:20px; right:20px; z-index:999999;
  width:480px; max-height:90vh;
  background:#fff; border-radius:10px;
  box-shadow:0 8px 32px rgba(0,0,0,.25);
  display:flex; flex-direction:column;
  font-size:14px; color:#222;
}
#deptImportTool .header {
  background:linear-gradient(135deg,#1a6b3c,#2d8f56); color:#fff;
  padding:12px 16px; border-radius:10px 10px 0 0;
  display:flex; justify-content:space-between; align-items:center;
}
#deptImportTool .header h2 { font-size:14px; }
#deptImportTool .closeBtn {
  background:none; border:none; color:#fff; font-size:18px; cursor:pointer; padding:0 4px;
}
#deptImportTool .body { padding:12px 16px; overflow-y:auto; flex:1; }
#deptImportTool label {
  display:block; font-size:12px; font-weight:600; color:#555;
  margin-top:8px; margin-bottom:2px;
}
#deptImportTool label:first-child { margin-top:0; }
#deptImportTool input[type="text"] {
  width:100%; padding:6px 8px; border:1px solid #ccc; border-radius:5px; font-size:13px;
}
#deptImportTool input:focus { border-color:#2d8f56; outline:none; box-shadow:0 0 0 2px rgba(45,143,86,.2); }
#deptImportTool .row { display:flex; gap:6px; margin-top:8px; flex-wrap:wrap; }
#deptImportTool button {
  padding:6px 14px; border:none; border-radius:5px; font-size:13px; cursor:pointer; font-weight:600;
}
#deptImportTool button:disabled { opacity:.5; cursor:not-allowed; }
#deptImportTool .btnStart { background:#1a6b3c; color:#fff; }
#deptImportTool .btnStart:hover:not(:disabled) { background:#15582f; }
#deptImportTool .btnStop { background:#c0392b; color:#fff; }
#deptImportTool .btnStop:hover:not(:disabled) { background:#a93226; }
#deptImportTool .stats {
  display:flex; gap:8px; margin-top:8px; font-size:12px;
}
#deptImportTool .stats span {
  background:#f0f0f0; padding:2px 8px; border-radius:4px;
}
#deptImportTool .stats .ok { background:#d4edda; color:#155724; }
#deptImportTool .stats .err { background:#f8d7da; color:#721c24; }
#deptImportTool .stats .img { background:#cce5ff; color:#004085; }
#deptImportTool .logBox {
  background:#1e1e1e; color:#d4d4d4; border-radius:5px;
  padding:8px; margin-top:8px; height:200px; overflow-y:auto;
  font-family:'Cascadia Code','Fira Code',monospace; font-size:12px; line-height:1.4;
}
#deptImportTool .logBox .ok { color:#6fcf97; }
#deptImportTool .logBox .err { color:#eb5757; }
#deptImportTool .logBox .info { color:#888; }
#deptImportTool .logBox .img { color:#6bb9f0; }
  `;
  document.head.appendChild(css);




  var tool = document.createElement('div');
  tool.id = 'deptImportTool';

  var header = document.createElement('div');
  header.className = 'header';
  var title = document.createElement('h2');
  title.textContent = 'Site Import';
  var closeBtn = document.createElement('button');
  closeBtn.className = 'closeBtn';
  closeBtn.textContent = 'X';
  header.appendChild(title);
  header.appendChild(closeBtn);
  tool.appendChild(header);

  var body = document.createElement('div');
  body.className = 'body';

  function makeInput(id, labelText, placeholder) {
    var label = document.createElement('label');
    label.textContent = labelText;
    body.appendChild(label);
    var input = document.createElement('input');
    input.id = id;
    input.type = 'text';
    input.placeholder = placeholder;
    input.style.fontFamily = 'monospace';
    body.appendChild(input);
    return input;
  }

  function makeSelect(id, labelText, options) {
    var label = document.createElement('label');
    label.textContent = labelText;
    body.appendChild(label);
    var select = document.createElement('select');
    select.id = id;
    select.style.cssText = 'width:100%;padding:6px;border:1px solid #ccc;border-radius:5px;';
    options.forEach(function(opt) {
      var el = document.createElement('option');
      el.value = opt.value;
      el.textContent = opt.text;
      select.appendChild(el);
    });
    body.appendChild(select);
    return select;
  }

  makeInput('d_url', 'Page URL (single page)', 'https://www.canada.ca/en/services.html');
  makeInput('d_sitemap', 'Sitemap URL', 'https://canada.ca/sitemap.xml');
  makeInput('d_api', 'FileBot API', 'https://prod.webfilebot.com/api/v1/import-page');
  makeInput('d_token', 'API Token (use Bearer prefix)', 'Bearer xxx');
  makeInput('d_root', 'Image Root Dir', '/boarding/canadasite/content/dam/cwa-ace');

  makeSelect('d_rate', 'Rate Limit', [
    { value: 2, text: '2 sec/page' },
    { value: 1, text: '1 sec/page' },
    { value: 3, text: '3 sec/page' },
    { value: 5, text: '5 sec/page' }
  ]);

  makeInput('d_since', 'Only pages modified after', '2026-01-01T00:00 or leave empty for all');

  var skipRow = document.createElement('div');
  skipRow.style.cssText = 'display:flex;align-items:center;gap:6px;margin-top:8px;';
  var skipCheckbox = document.createElement('input');
  skipCheckbox.id = 'd_skip';
  skipCheckbox.type = 'checkbox';
  skipCheckbox.checked = true;
  var skipLabel = document.createElement('label');
  skipLabel.textContent = 'Skip existing pages';
  skipLabel.style.cssText = 'font-size:12px;font-weight:400;margin:0;cursor:pointer;';
  skipRow.appendChild(skipCheckbox);
  skipRow.appendChild(skipLabel);
  body.appendChild(skipRow);

  var row = document.createElement('div');
  row.className = 'row';
  var startBtn = document.createElement('button');
  startBtn.id = 'd_start';
  startBtn.className = 'btnStart';
  startBtn.textContent = 'Start Import';
  var stopBtn = document.createElement('button');
  stopBtn.id = 'd_stop';
  stopBtn.className = 'btnStop';
  stopBtn.disabled = true;
  stopBtn.textContent = 'Stop';
  row.appendChild(startBtn);
  row.appendChild(stopBtn);
  body.appendChild(row);

  var stats = document.createElement('div');
  stats.className = 'stats';

  function makeSpan(id, cls, text) {
    var sp = document.createElement('span');
    sp.id = id;
    if (cls) sp.className = cls;
    sp.textContent = text;
    stats.appendChild(sp);
    return sp;
  }
  makeSpan('d_progress', '', '0 processed');
  makeSpan('d_ok', 'ok', '0 ok');
  makeSpan('d_updated', '', '0 updated');
  makeSpan('d_skipped', '', '0 skipped');
  makeSpan('d_err', 'err', '0 err');
  makeSpan('d_total', '', '0 pages');
  makeSpan('d_imgcnt', 'img', '0 images');
  body.appendChild(stats);

  var logBox = document.createElement('div');
  logBox.id = 'd_log';
  logBox.className = 'logBox';
  body.appendChild(logBox);
  tool.appendChild(body);

  document.body.appendChild(tool);



  var $ = function(id) { return tool.querySelector('#' + id); };
  var log = logBox;
  var running = false, done = 0, failed = 0, skipped = 0, updated = 0;

  var allImages = {};
  var pendingImages = [];
  var abortController = null;

  function addLog(text, cls) {
    var d = document.createElement('div');
    if (cls) d.className = cls;
    d.textContent = text;
    log.appendChild(d);
    log.scrollTop = log.scrollHeight;
  }

  function updateStats() {
    $('d_progress').textContent = (done + failed + skipped + updated) + ' processed';
    $('d_ok').textContent = done + ' ok';
    $('d_err').textContent = failed + ' err';
    $('d_skipped').textContent = skipped + ' skipped';
    $('d_updated').textContent = updated + ' updated';
    $('d_imgcnt').textContent = Object.keys(allImages).length + ' images';
  }

  function collectImages(html, pageUrl) {
    var parser = new DOMParser();
    var dom = parser.parseFromString(html, 'text/html');
    var baseUrl = pageUrl.replace(/\/[^/]*$/, '/');
    var imgs = dom.querySelectorAll('img[src]');
    var added = 0;
    for (var i = 0; i < imgs.length; i++) {
      var src = imgs[i].getAttribute('src');
      if (!src) continue;

      var absUrl;
      try {
        absUrl = new URL(src, baseUrl).href;
      } catch(e) { continue; }

      if (absUrl.startsWith('data:')) continue;

      if (src.indexOf('/etc/') !== -1 || absUrl.indexOf('/etc/') !== -1) continue;
      try {
        var u = new URL(absUrl);
        var pageU = new URL(pageUrl);
        if (u.hostname !== pageU.hostname) continue;
      } catch(e) { continue; }

      // Dedup on normalized URL (ignore query/fragment) so the same image
      // with different query params (e.g. ?w=800) is not uploaded twice.
      var normKey = absUrl.split('#')[0].split('?')[0];
      if (allImages[normKey]) continue;

      if (!/\.(jpe?g|png|gif|webp|bmp|svg)(\?|#|$)/i.test(absUrl)) continue;
      var alt = (imgs[i].getAttribute('alt') || '').trim();
      allImages[normKey] = { alt: alt };
      pendingImages.push({ url: absUrl, alt: alt });
      added++;
    }
    return added;
  }



  function computeImageFolderPath(imageUrl, rootDir) {
    if (!rootDir) return '';
    try {
      var parsed = new URL(imageUrl);
      var pathname = parsed.pathname;
      if (!pathname.startsWith('/content/dam/')) return '';  // server handles non-DAM
      var jcrIdx = pathname.indexOf('/_jcr_content');
      if (jcrIdx === -1) return '';
      var cleanPath = pathname.substring(0, jcrIdx);


      var rootParts = rootDir.split('/').filter(function(s){return s;});
      var lastSeg = rootParts[rootParts.length - 1]; // e.g. cwa-ace
      var stripPrefix = '/content/dam/' + lastSeg;

      var relPath = cleanPath.substring(stripPrefix.length);
      if (!relPath) return '';
      return rootDir.replace(/\/+$/, '') + relPath;
    } catch(e) {
      return '';
    }
  }


  /**
   * Transform canada.ca image paths to /boarding/canadasite/content/dam/... URLs.
   * This handles images that could not be uploaded, so they still render via proxy.
   */
    function transformCanadaCaImagePath(src) {
    // Handle absolute canada.ca / www.canada.ca URLs
    if (/^https?:\/\/(www\.)?canada\.ca/i.test(src)) {
      try {
        var u = new URL(src);
        src = u.pathname;
      } catch(e) { return src; }
    }

    // Skip non-path things
    if (!src.startsWith('/') || src.startsWith('data:')) return src;
    if (src.indexOf('/etc/') !== -1) return src;

    // If already a /boarding/ path without _jcr_content, it's clean
    if (src.startsWith('/boarding/') && src.indexOf('/_jcr_content') === -1) return src;

    // Save original filename from the full path
    var filename = src.substring(src.lastIndexOf('/') + 1);

    // Remove /content/canadasite prefix if present
    if (src.startsWith('/content/canadasite')) {
      src = src.substring('/content/canadasite'.length);
    }

    // For DAM URLs, strip the /content/dam/ prefix (mirror backend logic)
    // so we don't get /content/dam/content/dam/... in the proxy path.
    if (src.startsWith('/content/dam/')) {
      src = src.substring('/content/dam'.length);
    }

    // Strip /_jcr_content and everything after it
    var jcrIdx = src.indexOf('/_jcr_content');
    if (jcrIdx !== -1) {
      src = src.substring(0, jcrIdx);
    }

    // Re-attach filename if it was part of the _jcr_content path
    if (!src.endsWith('/' + filename)) {
      src = src + '/' + filename;
    }

    // Already /boarding/ ? Just clean _jcr_content, no prefix change
    if (src.startsWith('/boarding/')) {
      return src;
    }

    // Prepend the proxy prefix
    return '/boarding/canadasite/content/dam' + src;
  }

  async function importImageList(items, api, delay, token, signal) {
    var replaceMap = {};
    if (items.length === 0) return replaceMap;

    addLog('Importing ' + items.length + ' images...', 'img');
    var imgOk = 0, imgFail = 0;

    for (var i = 0; i < items.length && running; i++) {
      var item = items[i];
      var imgUrl = item.url;
      var imgTitle = item.alt || '';
      addLog('Image [' + (i+1) + '/' + items.length + '] ' + imgUrl, 'img');

      try {
        var headers = { 'Content-Type': 'application/json' };
        if (token) { headers['Authorization'] = token.startsWith('Bearer ') ? token : 'Bearer ' + token; }

        // Fetch image bytes through the backend proxy — direct browser fetches
        // of canada.ca assets fail on some networks (ERR_HTTP2_PROTOCOL_ERROR).
        var imgResp = await fetch(api.replace('/import-page', '/fetch-url'), {
          method: 'POST',
          headers: headers,
          signal: signal,
          body: JSON.stringify({ url: imgUrl })
        });
        if (!imgResp.ok) throw new Error('proxy HTTP ' + imgResp.status);
        var imgJson = await imgResp.json();
        if (imgJson.status !== 200 || !imgJson.image_data) {
          throw new Error('proxy status ' + imgJson.status + (imgJson.error ? ' (' + imgJson.error + ')' : ''));
        }
        var b64 = imgJson.image_data;
        var mimeType = (imgJson.content_type || 'image/png').split(';')[0];

        var folderPath = computeImageFolderPath(imgUrl, $('d_root').value.trim());
        var payload = { url: imgUrl, html: '', title: imgTitle, is_image: true, image_data: 'data:' + mimeType + ';base64,' + b64 };
        if (folderPath) { payload.folder_path = folderPath; }

        var resp = await fetch(api, {
          method: 'POST',
          headers: headers,
          signal: signal,
          body: JSON.stringify(payload)
        });

        if (!resp.ok) {
          throw new Error('HTTP ' + resp.status + ': ' + (await resp.text()).slice(0, 80));
        }

        var respJson = await resp.json();
        if (respJson.path) {
          // Use the full document path returned by the backend
          // (e.g. /boarding/canadasite/content/dam/.../photo.jpeg),
          // which preserves the original extension (.jpeg stays .jpeg)
          // instead of a root-level bare filename.
          replaceMap[imgUrl] = respJson.path;
        } else if (respJson.stored_filename) {
          // Fallback: strip _jcr_content from stored filename
          var sf = respJson.stored_filename;
          var jcrIdx = sf.indexOf('/_jcr_content');
          if (jcrIdx !== -1) {
            var filename = sf.substring(sf.lastIndexOf('/') + 1);
            var cleaned = sf.substring(0, jcrIdx);
            if (!cleaned.endsWith('/' + filename)) {
              cleaned = cleaned + '/' + filename;
            }
            sf = cleaned;
          }
          replaceMap[imgUrl] = '/' + sf;
        }

        imgOk++;
        addLog('Image saved → ' + (replaceMap[imgUrl] || '/?'), 'ok');
      } catch(e) {
        if (e.name === 'AbortError') throw e;
        imgFail++;
        addLog('Image error: ' + e.message, 'err');
      }

      if (i < items.length - 1 && running) {
        await new Promise(function(r) { setTimeout(r, Math.max(delay, 500)); });
      }
    }

    addLog('Images done: ' + imgOk + ' ok, ' + imgFail + ' err', imgFail === 0 ? 'ok' : 'info');
    return replaceMap;
  }

  async function flushImages(api, delay, token, signal) {
    if (pendingImages.length === 0) return {};
    var batch = pendingImages.slice();
    pendingImages = [];
    return await importImageList(batch, api, delay, token, signal);
  }

  function blobToBase64(blob) {
    return new Promise(function(resolve, reject) {
      var fr = new FileReader();
      fr.onload = function() {
        var s = fr.result;
        var idx = s.indexOf(';base64,');
        if (idx >= 0) {
          resolve(s.slice(idx + 8));
        } else {
          resolve(s);
        }
      };
      fr.onerror = reject;
      fr.readAsDataURL(blob);
    });
  }

  closeBtn.onclick = function() {
    if (running) return addLog('Stop the import first', 'err');
    tool.remove();
    window.__DEPT_IMPORT_LOADED = false;
    document.head.removeChild(css);
  };

  $('d_start').onclick = async function() {
    if (running) return;
    running = true;
    abortController = new AbortController();
    $('d_start').disabled = true;
    $('d_stop').disabled = false;

    allImages = {};
    pendingImages = [];

    var singleUrl = $('d_url').value.trim();
    var urls, lastmods;

    if (singleUrl) {
      // Single page import
      urls = [singleUrl];
      lastmods = {};
      $('d_total').textContent = '1 page';
      addLog('Importing single page: ' + singleUrl, 'info');
    } else {
      addLog('Parsing sitemap...', 'info');
      try {
        // Fetch the sitemap through the backend proxy — direct browser fetches
        // of canada.ca fail on some networks (ERR_HTTP2_PROTOCOL_ERROR).
        var smHeaders = { 'Content-Type': 'application/json' };
        var smToken = $('d_token').value.trim();
        if (smToken) { smHeaders['Authorization'] = smToken.startsWith('Bearer ') ? smToken : 'Bearer ' + smToken; }
        var smApi = $('d_api').value.trim();
        var resp = await fetch(smApi.replace('/import-page', '/fetch-url'), {
          method: 'POST',
          headers: smHeaders,
          signal: abortController.signal,
          body: JSON.stringify({ url: $('d_sitemap').value.trim() })
        });
        if (!resp.ok) throw new Error('proxy HTTP ' + resp.status);
        var smJson = await resp.json();
        if (smJson.status !== 200 || !smJson.html) {
          throw new Error('proxy status ' + smJson.status + (smJson.error ? ' (' + smJson.error + ')' : ''));
        }
        var xml = smJson.html;
        var parser = new DOMParser();
        var doc = parser.parseFromString(xml, 'text/xml');
        urls = [].slice.call(doc.querySelectorAll('loc')).map(function(el) { return el.textContent.trim(); });

        lastmods = {};
        [].slice.call(doc.querySelectorAll('url')).forEach(function(el) {
          var loc = el.querySelector('loc');
          var lm = el.querySelector('lastmod');
          if (loc && lm) {
            lastmods[loc.textContent.trim()] = lm.textContent.trim();
          }
        });
        $('d_total').textContent = urls.length + ' pages';
        addLog('Found ' + urls.length + ' pages', 'info');
        if (Object.keys(lastmods).length > 0) {
          addLog('Sitemap has lastmod dates for ' + Object.keys(lastmods).length + ' pages', 'info');
        }
      } catch(e) {
        addLog('Sitemap error: ' + e.message, 'err');
        $('d_start').disabled = false;
        $('d_stop').disabled = true;
        running = false;
        return;
      }
    }

      var api = $('d_api').value.trim();
      var checkApi = api.replace('/import-page', '/check-urls');
      var delay = parseInt($('d_rate').value) * 1000;
      var skipExisting = $('d_skip').checked;

      var authHeaders = { 'Content-Type': 'application/json' };
      var tk = $('d_token').value.trim();
      if (tk) { authHeaders['Authorization'] = tk.startsWith('Bearer ') ? tk : 'Bearer ' + tk; }

      var checkCache = {};
      var CHECK_BATCH = 10;
      var ensureChecked = async function(url, idx) {
        if (!skipExisting) return null;
        if (checkCache[url] !== undefined) return checkCache[url];

        var batch = [];
        for (var bi = idx; bi < Math.min(idx + CHECK_BATCH, urls.length); bi++) {
          if (checkCache[urls[bi]] === undefined) batch.push(urls[bi]);
        }
        if (batch.length === 0) return null;
        try {
          var cr = await fetch(checkApi, {
            method: 'POST', headers: authHeaders, signal: abortController.signal,
            body: JSON.stringify({ urls: batch })
          });
          if (cr.ok) {
            var cj = await cr.json();
            var ex = cj.existing || {};
            for (var bi = 0; bi < batch.length; bi++) {
              checkCache[batch[bi]] = ex[batch[bi]] !== undefined ? ex[batch[bi]] : null;
            }
            return checkCache[url];
          } else {
            addLog('Check failed (HTTP ' + cr.status + '), importing', 'err');
          }
        } catch(e) {
          addLog('Check error: ' + e.message, 'err');
        }

        for (var bi = 0; bi < batch.length; bi++) {
          checkCache[batch[bi]] = null;
        }
        return null;
      }

      for (var i = 0; i < urls.length && running; i++) {
        var url = urls[i];
        var shouldImport = true;

        // Filter by 'since' datetime FIRST (before API calls)
        var sinceVal = $('d_since').value.trim();
        if (sinceVal) {
          var sinceDate = new Date(sinceVal);
          if (!isNaN(sinceDate.getTime())) {
            var pageLastmod = lastmods[url];
            if (pageLastmod) {
              var modDate = new Date(pageLastmod);
              if (!isNaN(modDate.getTime()) && modDate <= sinceDate) {
                skipped++;
                addLog('[' + (i+1) + '/' + urls.length + '] Skipped (lastmod ' + pageLastmod + ' ≤ ' + sinceVal + '): ' + url, 'info');
                updateStats();
                continue;
              }
            } else {
              // d_since is set but page has no lastmod -> skip
              skipped++;
              addLog('[' + (i+1) + '/' + urls.length + '] Skipped (no lastmod, d_since set): ' + url, 'info');
              updateStats();
              continue;
            }
          }
        }

        if (skipExisting) {
          var importedAt = await ensureChecked(url, i);
          if (importedAt !== null) {
            var sitemapLastmod = lastmods[url];
            if (sitemapLastmod && new Date(sitemapLastmod) > new Date(importedAt)) {
              updated++;
              addLog('[' + (i+1) + '/' + urls.length + '] Updating (newer): ' + url, '');
            } else {
              skipped++;
              addLog('[' + (i+1) + '/' + urls.length + '] Skipped (up-to-date): ' + url, 'info');
              shouldImport = false;
            }
            updateStats();
          }
        }

        if (shouldImport) {
          addLog('[' + (i+1) + '/' + urls.length + '] ' + url, '');
          try {
            // Fetch page content through the backend proxy — direct browser
            // fetches of canada.ca fail on some networks (ERR_HTTP2_PROTOCOL_ERROR)
            // and cross-origin redirects (e.g., canada.ca → cbsa) throw CORS errors.
            var pageResp = await fetch(api.replace('/import-page', '/fetch-url'), {
              method: 'POST',
              headers: authHeaders,
              signal: abortController.signal,
              body: JSON.stringify({ url: url })
            });
            if (!pageResp.ok) throw new Error('proxy HTTP ' + pageResp.status);
            var pageJson = await pageResp.json();

            if (pageJson.status === 200 && pageJson.html) {
              // Server-side redirect detected (proxy followed it): record a stub,
              // same as the old resolve-redirect flow.
              if (pageJson.final_url && pageJson.final_url !== url) {
                var uploadResp = await fetch(api, {
                  method: 'POST',
                  headers: authHeaders,
                  signal: abortController.signal,
                  body: JSON.stringify({ url: url, html: '<html><head><title>Redirect</title></head><body></body></html>', title: 'Redirect: ' + url, redirect_to: pageJson.final_url })
                });
                if (!uploadResp.ok) {
                  throw new Error('HTTP ' + uploadResp.status + ': ' + (await uploadResp.text()).slice(0, 80));
                }
                done++;
                addLog('Redirect recorded → ' + pageJson.final_url, 'ok');
              } else {
                var html = pageJson.html;

                var imgFound = collectImages(html, url);
                if (imgFound > 0) {
                  addLog('+' + imgFound + ' images collected', 'info');
                  updateStats();

                  var replaceMap = await flushImages(api, delay, $('d_token').value.trim(), abortController.signal);
                  for (var oldUrl in replaceMap) {
                    html = html.split(oldUrl).join(replaceMap[oldUrl]);
                    addLog('Replaced: ' + oldUrl.slice(-40) + ' → ' + replaceMap[oldUrl], 'info');
                  }
                  // AEM pattern pass: AEM publish expands one image into several URL
                  // variants (src, srcset renditions, data-cmp-src {.width} template),
                  // all under /_jcr_content/... and all ending in the same filename.
                  // The exact-string pass above only hits the exact src, so rewrite
                  // every remaining _jcr_content variant of an uploaded image too.
                  for (var oldUrl in replaceMap) {
                    var fn = oldUrl.slice(oldUrl.lastIndexOf('/') + 1);
                    if (!fn) continue;
                    var esc = fn.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
                    var aemRe = new RegExp('(["\'>\\s])([^"\'>\\s]*?_jcr_content[^"\'>\\s]*?' + esc + ')(?=["\'\\s>])', 'g');
                    html = html.replace(aemRe, function(m, delim, url) { return delim + replaceMap[oldUrl]; });
                  }
                }

                // Transform any remaining canada.ca image URLs that weren't uploaded
                var transformedCount = 0;
                html = html.replace(/(<img[^>]+src=["'])([^"']+)(["'])/gi, function(m, pre, imgSrc, post) {
                  var result = transformCanadaCaImagePath(imgSrc);
                  if (result && result !== imgSrc) {
                    transformedCount++;
                    addLog('Transform: ' + imgSrc.slice(-40) + ' → ' + result, 'img');
                  }
                  // Never emit a dangling arrow or blank src: keep original when result is empty
                  return pre + (result || imgSrc) + post;
                });
                if (transformedCount > 0) {
                  addLog('Transformed ' + transformedCount + ' remaining image paths', 'info');
                }

                var uploadResp = await fetch(api, {
                  method: 'POST',
                  headers: authHeaders,
                  signal: abortController.signal,
                  body: JSON.stringify({ url: url, html: html, title: '' })
                });
                if (!uploadResp.ok) {
                  throw new Error('HTTP ' + uploadResp.status + ': ' + (await uploadResp.text()).slice(0, 80));
                }
                done++;
                addLog('OK', 'ok');
              }
            } else {
              addLog('Unexpected status ' + pageJson.status + ': ' + url, 'err');
              failed++;
            }
          } catch(e) {
            if (e.name === 'AbortError') throw e;
            // Honest error: the old resolve-redirect fallback was misleading — it
            // returns null on its own fetch failures too, so "Could not resolve
            // redirect" was shown for plain proxy errors (e.g. a missing
            // /api/v1/fetch-url route). Real redirects are already handled above
            // via final_url != url, so surface the real error instead.
            failed++;
            addLog('Error: ' + e.message, 'err');
            if (e.message.indexOf('proxy HTTP 404') !== -1 || e.message.indexOf('proxy status 404') !== -1) {
              addLog('Hint: /api/v1/fetch-url may be missing on the server (check nginx routes)', 'warn');
            }
          }
          updateStats();
          if (i < urls.length - 1 && running) {
            await new Promise(function(r) { setTimeout(r, delay); });
          }
        }
      }

      if (pendingImages.length > 0) {
        addLog('Importing remaining images...', 'info');
        await flushImages(api, delay, $('d_token').value.trim(), abortController.signal);
      }

      addLog(running ? 'Done!' : 'Stopped (all page images saved)', running ? 'ok' : 'info');

    running = false;
    $('d_start').disabled = false;
    $('d_stop').disabled = true;
  };

  $('d_stop').onclick = function() {
    running = false;
    if (abortController) abortController.abort();
    addLog('Stopping...', 'info');
  };

  addLog('🌾 Import v' + BOOKMARKLET_VERSION + ' ready', 'info');
})();