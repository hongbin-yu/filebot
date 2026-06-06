// 🌾 Department Import Tool — Bookmarklet
// Runs on canada.ca pages (same-origin, no CORS restrictions)
// Drag this bookmarklet into your bookmarks bar and click to run.
//
// Features:
//   - Sitemap-based bulk import of HTML pages
//   - Auto-collects same-domain images during crawl
//   - After sitemap crawl, imports all collected images

(function(){
  if (window.__DEPT_IMPORT_LOADED) return;
  window.__DEPT_IMPORT_LOADED = true;

  // ================================
  // Styles
  // ================================
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

  // ================================
  // HTML — built with DOM API (no innerHTML template literals)
  // This avoids all URL-encoding corruption issues
  // ================================
  var tool = document.createElement('div');
  tool.id = 'deptImportTool';

  // Header
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

  // Body
  var body = document.createElement('div');
  body.className = 'body';

  // Helper: create a labeled input
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

  // Helper: create a labeled select
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

  makeInput('d_sitemap', 'Sitemap URL', 'https://canada.ca/sitemap.xml');
  makeInput('d_api', 'FileBot API', 'http://localhost:8001/api/v1/import-page');
  makeInput('d_token', 'API Token (use Bearer prefix)', 'Bearer xxx');

  makeSelect('d_rate', 'Rate Limit', [
    { value: 2, text: '2 sec/page' },
    { value: 1, text: '1 sec/page' },
    { value: 3, text: '3 sec/page' },
    { value: 5, text: '5 sec/page' }
  ]);

  // Skip existing checkbox
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

  // Buttons row
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

  // Stats
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

  // Log box
  var logBox = document.createElement('div');
  logBox.id = 'd_log';
  logBox.className = 'logBox';
  body.appendChild(logBox);
  tool.appendChild(body);

  // Append to page
  document.body.appendChild(tool);

  // ================================
  // Logic
  // ================================
  var $ = function(id) { return tool.querySelector('#' + id); };
  var log = logBox;
  var running = false, done = 0, failed = 0, skipped = 0, updated = 0;

  // Image tracking: all (for display + dedup) and pending queue (for import)
  var allImages = {};
  var pendingImages = [];

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

  // Extract same-domain image URLs from HTML
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
      try {
        var u = new URL(absUrl);
        var pageU = new URL(pageUrl);
        if (u.hostname !== pageU.hostname) continue;
      } catch(e) { continue; }

      if (allImages[absUrl]) continue;
      allImages[absUrl] = true;
      pendingImages.push(absUrl);
      added++;
    }
    return added;
  }

  // Import a specific list of images (called by flushImages)
  async function importImageList(urls, api, delay, token) {
    if (urls.length === 0) return;

    addLog('Importing ' + urls.length + ' images...', 'img');
    var imgOk = 0, imgFail = 0;

    for (var i = 0; i < urls.length && running; i++) {
      var imgUrl = urls[i];
      addLog('Image [' + (i+1) + '/' + urls.length + '] ' + imgUrl, 'img');

      try {
        var imgResp = await fetch(imgUrl);
        if (!imgResp.ok) throw new Error('HTTP ' + imgResp.status);

        var blob = await imgResp.blob();
        var b64 = await blobToBase64(blob);
        var mimeType = blob.type || 'image/png';

        var headers = { 'Content-Type': 'application/json' };
        if (token) { headers['Authorization'] = token.startsWith('Bearer ') ? token : 'Bearer ' + token; }

        var resp = await fetch(api, {
          method: 'POST',
          headers: headers,
          body: JSON.stringify({
            url: imgUrl,
            html: '',
            title: '',
            is_image: true,
            image_data: 'data:' + mimeType + ';base64,' + b64
          })
        });

        if (!resp.ok) {
          throw new Error('HTTP ' + resp.status + ': ' + (await resp.text()).slice(0, 80));
        }

        imgOk++;
        addLog('Image saved', 'ok');
      } catch(e) {
        imgFail++;
        addLog('Image error: ' + e.message, 'err');
      }

      if (i < urls.length - 1 && running) {
        await new Promise(function(r) { setTimeout(r, Math.max(delay, 500)); });
      }
    }

    addLog('Images done: ' + imgOk + ' ok, ' + imgFail + ' err', imgFail === 0 ? 'ok' : 'info');
  }

  // Flush pending images (drain the pending queue)
  async function flushImages(api, delay, token) {
    if (pendingImages.length === 0) return;
    var batch = pendingImages.slice();
    pendingImages = [];
    await importImageList(batch, api, delay, token);
  }

  // Helper: Blob to base64
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

  // Close button
  closeBtn.onclick = function() {
    if (running) return addLog('Stop the import first', 'err');
    tool.remove();
    window.__DEPT_IMPORT_LOADED = false;
    document.head.removeChild(css);
  };

  // Start
  $('d_start').onclick = async function() {
    if (running) return;
    running = true;
    $('d_start').disabled = true;
    $('d_stop').disabled = false;

    allImages = {};
    pendingImages = [];

    addLog('Parsing sitemap...', 'info');

    try {
      var resp = await fetch($('d_sitemap').value.trim());
      var xml = await resp.text();
      var parser = new DOMParser();
      var doc = parser.parseFromString(xml, 'text/xml');
      var urls = [].slice.call(doc.querySelectorAll('loc')).map(function(el) { return el.textContent.trim(); });
      // Parse lastmod dates from sitemap
      var lastmods = {};
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

      var api = $('d_api').value.trim();
      var checkApi = api.replace('/import-page', '/check-urls');
      var delay = parseInt($('d_rate').value) * 1000;
      var skipExisting = $('d_skip').checked;

      // Build auth headers once
      var authHeaders = { 'Content-Type': 'application/json' };
      var tk = $('d_token').value.trim();
      if (tk) { authHeaders['Authorization'] = tk.startsWith('Bearer ') ? tk : 'Bearer ' + tk; }

      // Pre-fetch check cache — batch in chunks of 20 to avoid per-URL HTTP calls
      var checkCache = {};
      var CHECK_BATCH = 10;
      var ensureChecked = async function(url, idx) {
        if (!skipExisting) return null;
        if (checkCache[url] !== undefined) return checkCache[url];
        // Batch-fetch next 20 URLs
        var batch = [];
        for (var bi = idx; bi < Math.min(idx + CHECK_BATCH, urls.length); bi++) {
          if (checkCache[urls[bi]] === undefined) batch.push(urls[bi]);
        }
        if (batch.length === 0) return null;
        try {
          var cr = await fetch(checkApi, {
            method: 'POST', headers: authHeaders,
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
        // On failure, mark all as null so they get imported
        for (var bi = 0; bi < batch.length; bi++) {
          checkCache[batch[bi]] = null;
        }
        return null;
      }

      // Step 1: Crawl all HTML pages (no delay when skipping)
      for (var i = 0; i < urls.length && running; i++) {
        var url = urls[i];
        var shouldImport = true;

        // Instant check from cache (batch-fetches silently if needed)
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
            var pageResp = await fetch(url);
            var html = await pageResp.text();

            var imgFound = collectImages(html, url);
            if (imgFound > 0) {
              addLog('+' + imgFound + ' images collected', 'info');
              updateStats();
            }

            var uploadResp = await fetch(api, {
              method: 'POST',
              headers: authHeaders,
              body: JSON.stringify({ url: url, html: html, title: '' })
            });
            if (!uploadResp.ok) {
              throw new Error('HTTP ' + uploadResp.status + ': ' + (await uploadResp.text()).slice(0, 80));
            }
            done++;
            addLog('OK', 'ok');
          } catch(e) {
            failed++;
            addLog('Error: ' + e.message, 'err');
          }
          updateStats();
          // Flush images every 10 pages, on last page, or on stop
          if (pendingImages.length > 0 && ((done + updated) % 10 === 0 || i === urls.length - 1 || !running)) {
            await flushImages(api, delay, $('d_token').value.trim());
          }
          if (i < urls.length - 1 && running) {
            await new Promise(function(r) { setTimeout(r, delay); });
          }
        }
      }

      // Final flush: import any remaining images after loop exit (e.g. stopped midway)
      if (pendingImages.length > 0) {
        addLog('Importing remaining images...', 'info');
        await flushImages(api, delay, $('d_token').value.trim());
      }

      addLog(running ? 'Done!' : 'Stopped (all page images saved)', running ? 'ok' : 'info');
    } catch(e) {
      addLog('Error: ' + e.message, 'err');
    }

    running = false;
    $('d_start').disabled = false;
    $('d_stop').disabled = true;
  };

  // Stop
  $('d_stop').onclick = function() {
    running = false;
    addLog('Stopping...', 'info');
  };

  addLog('Ready', 'info');
})();
