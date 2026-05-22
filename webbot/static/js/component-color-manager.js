/**
 * CanadaColorManager - WET-BOEW Component Color Manager
 *
 * Manages color class changes for WET-BOEW components within the TinyMCE editor.
 * Supports: buttons, alerts, labels, badges, panels, wells, text, backgrounds.
 *
 * Usage (via AI assistant or editor.js):
 *   window.CanadaColorManager.describeCurrent()  → description string
 *   window.CanadaColorManager.getCurrentComponent() → { element, type, color } | null
 *   window.CanadaColorManager.changeColor(element, colorName) → result object
 *
 * @version 1.1.0
 */

(function () {
  'use strict';

  // ---- Color mappings for WET-BOEW ----
  // details is special — not a color component, but we recognise it for the "make it open" command
  var DETAILS_TYPE = 'details';

  var COLOR_MAP = {
    // WET buttons: <a class="btn btn-default">, <button class="btn btn-primary">
    btn: {
      base: 'btn',
      prefix: 'btn-',
      colors: ['default', 'primary', 'success', 'info', 'warning', 'danger', 'link']
    },
    // WET alerts: <div class="alert alert-success">
    alert: {
      base: 'alert',
      prefix: 'alert-',
      colors: ['success', 'info', 'warning', 'danger']
    },
    // WET labels: <span class="label label-primary">
    label: {
      base: 'label',
      prefix: 'label-',
      colors: ['default', 'primary', 'success', 'info', 'warning', 'danger']
    },
    // WET badges: <span class="badge">
    badge: {
      base: 'badge',
      prefix: 'badge-',
      colors: ['default', 'primary', 'success', 'info', 'warning', 'danger']
    },
    // WET panels: <div class="panel panel-default">
    panel: {
      base: 'panel',
      prefix: 'panel-',
      colors: ['default', 'primary', 'success', 'info', 'warning', 'danger']
    },
    // WET wells: <div class="well well-sm">
    well: {
      base: 'well',
      prefix: 'well-',
      colors: ['default', 'sm', 'lg']
    },
    // Text colors: <span class="text-danger">
    text: {
      base: '',
      prefix: 'text-',
      colors: ['muted', 'primary', 'success', 'info', 'warning', 'danger']
    },
    // Background colors: <div class="bg-primary">
    bg: {
      base: '',
      prefix: 'bg-',
      colors: ['primary', 'success', 'info', 'warning', 'danger']
    }
  };

  // Allow looking up typeKey by a base class
  COLOR_MAP[DETAILS_TYPE] = {
    base: 'details',
    prefix: '',
    colors: []
  };
  var BASE_TO_TYPE = {};
  for (var tk in COLOR_MAP) {
    if (COLOR_MAP[tk].base) {
      BASE_TO_TYPE[COLOR_MAP[tk].base] = tk;
    }
  }

  // Friendly color names → canonical WET color name
  var COLOR_ALIASES = {
    red: 'danger',
    green: 'success',
    blue: 'info',
    yellow: 'warning',
    orange: 'warning',
    gray: 'default',
    grey: 'default',
    dark: 'primary',
    light: 'default',
    // Chinese
    '红色': 'danger',
    '绿色': 'success',
    '蓝色': 'info',
    '黄色': 'warning',
    '橙色': 'warning',
    '灰色': 'default',
    '默认': 'default',
    '主要': 'primary'
  };

  /**
   * Get the active TinyMCE editor instance
   */
  function getEditor() {
    if (typeof tinymce !== 'undefined' && tinymce.activeEditor) {
      return tinymce.activeEditor;
    }
    return null;
  }

  /**
   * Check whether an element has a known WET component colour class.
   * Returns the first typeKey that matches, or null.
   */
  function hasRecognizedWetClass(el) {
    if (!el || !el.className) return null;
    var classes = el.className.split(/\s+/);
    for (var typeKey in COLOR_MAP) {
      var group = COLOR_MAP[typeKey];
      // Prefix match (e.g. btn-primary, panel-default)
      for (var i = 0; i < classes.length; i++) {
        var cls = classes[i];
        if (cls.indexOf(group.prefix) === 0) {
          var colorVal = cls.substring(group.prefix.length);
          if (group.colors.indexOf(colorVal) !== -1) {
            return typeKey;
          }
        }
      }
      // Base class match (e.g. just "btn" or "panel")
      if (group.base && classes.indexOf(group.base) !== -1) {
        return typeKey;
      }
    }
    // Check for label/badge element (special: class must be "label" or "badge")
    if (classes.indexOf('label') !== -1) return 'label';
    if (classes.indexOf('badge') !== -1) return 'badge';
    return null;
  }

  /**
   * Get the element currently under the cursor/selection in TinyMCE.
   * Strategy:
   *   1. Walk UP from cursor node to find a WET component ancestor.
   *   2. If not found, scan the parent container's children for a WET component.
   *   3. Fall back to the deepest element with a className.
   */
  function getElementAtCursor() {
    var editor = getEditor();
    if (!editor) return null;

    try {
      var node = editor.selection ? editor.selection.getNode() : null;
      if (!node) return null;

      // --- Strategy 1: Walk up from cursor ---
      var el = node;
      var maxDepth = 10;
      while (el && maxDepth-- > 0) {
        if (hasRecognizedWetClass(el)) return el;
        el = el.parentNode;
      }

      // --- Strategy 2: Scan nearest container's children ---
      // The component may be a child of the container rather than an ancestor.
      // Find the highest direct ancestor of the cursor node.
      var container = node;
      var upDepth = 3;
      while (container && upDepth-- > 0) {
        container = container.parentNode;
      }
      // Try a wider scan on the editor body
      if (container && container.querySelectorAll) {
        // Look for any known WET base class or colour class within the container
        var selectors = [];
        for (var typeKey in COLOR_MAP) {
          var group = COLOR_MAP[typeKey];
          if (group.base) {
            selectors.push('.' + group.base);
          }
          for (var ci = 0; ci < group.colors.length; ci++) {
            // Only add the first few common ones to keep the selector short
            selectors.push('.' + group.prefix + group.colors[ci]);
          }
        }
        try {
          var found = container.querySelector(selectors.join(','));
          if (found) return found;
        } catch (_e) {
          // selector might fail with unusual chars, skip
        }
      }

      // --- Strategy 3: Deepest element with a class ---
      var deepest = node;
      while (deepest && deepest.nodeType === 1 && !deepest.className) {
        deepest = deepest.parentNode;
      }
      if (deepest && deepest.nodeType === 1 && deepest.className) {
        return deepest;
      }

      return null;
    } catch (e) {
      console.debug('getElementAtCursor error:', e);
      return null;
    }
  }

  /**
   * Detect the component type and current color of a given element.
   */
  function identifyComponent(el) {
    if (!el || !el.className) return null;

    var classes = el.className.split(/\s+/);
    var result = { element: el, type: null, color: null, available: [] };

    for (var typeKey in COLOR_MAP) {
      var group = COLOR_MAP[typeKey];
      var hasBase = group.base ? classes.indexOf(group.base) !== -1 : false;
      var matchedColor = null;

      for (var i = 0; i < classes.length; i++) {
        var cls = classes[i];
        if (cls.indexOf(group.prefix) === 0) {
          var colorVal = cls.substring(group.prefix.length);
          if (group.colors.indexOf(colorVal) !== -1) {
            matchedColor = colorVal;
            break;
          }
        }
      }

      if (hasBase || matchedColor) {
        result.type = typeKey;
        result.color = matchedColor || 'default';
        result.available = group.colors.slice();
        return result;
      }
    }

    // Also check specifically for bare "label" / "badge" class
    if (classes.indexOf('label') !== -1) {
      var labelColors = COLOR_MAP.label.colors.slice();
      return { element: el, type: 'label', color: 'default', available: labelColors };
    }
    if (classes.indexOf('badge') !== -1) {
      var badgeColors = COLOR_MAP.badge.colors.slice();
      return { element: el, type: 'badge', color: 'default', available: badgeColors };
    }

    // Check for <details> element by tag name
    if (el.tagName && el.tagName.toLowerCase() === 'details') {
      var open = el.hasAttribute('open') ? 'open' : 'closed';
      return { element: el, type: DETAILS_TYPE, color: open, available: ['open', 'closed'] };
    }

    return null;
  }

  /**
   * Build a human-readable description of the component at cursor.
   */
  function describeCurrent() {
    var el = getElementAtCursor();
    if (!el) {
      return "No component detected. Click on a WET-BOEW component (button, alert, label, badge, panel, etc.) to see its details.";
    }

    var comp = identifyComponent(el);
    if (!comp) {
      var tag = el.tagName.toLowerCase();
      var cls = el.className || '(no classes)';
      return "Element: <" + tag + " class=\"" + cls + "\">. Not a recognized WET-BOEW color component. Try clicking a button, alert, label, or panel.";
    }

    var displayType = comp.type.charAt(0).toUpperCase() + comp.type.slice(1);
    var tag = el.tagName.toLowerCase();
    var cls = el.className;

    var desc = "**" + displayType + "** detected: <" + tag + " class=\"" + cls + "\">\n";
    desc += "Current color: *" + comp.color + "*\n";
    desc += "Available colors: " + comp.available.join(', ') + "\n";
    desc += "Say 'change to color' or '/color colorname' to change it.";

    return desc;
  }

  /**
   * Get the component currently under the cursor.
   */
  function getCurrentComponent() {
    var el = getElementAtCursor();
    if (!el) return null;
    var comp = identifyComponent(el);
    if (!comp) {
      // Return the element anyway even if we can't identify its type
      return { element: el, type: 'unknown', color: null };
    }
    return comp;
  }

  /**
   * Change the color of a WET component element.
   *
   * @param {Element} el - The DOM element to modify
   * @param {string} colorName - Target color (friendly name or canonical)
   * @returns {object} { success, display, error, available }
   */
  function changeColor(el, colorName) {
    if (!el) {
      return { success: false, error: 'No element provided.' };
    }

    var comp = identifyComponent(el);
    if (!comp) {
      // Last-ditch: maybe the element identified correctly after all?
      // Try describeCurrent to give a better error
      return {
        success: false,
        error: 'Element is not a recognized WET-BOEW color component.',
        available: []
      };
    }

    // Resolve color alias
    var targetColor = COLOR_ALIASES[colorName.toLowerCase()] || colorName.toLowerCase();

    // Validate target color
    if (comp.available.indexOf(targetColor) === -1) {
      return {
        success: false,
        error: 'Cannot change to "' + targetColor + '". Valid options: ' + comp.available.join(', '),
        available: comp.available.slice()
      };
    }

    // If already this color, no-op
    if (comp.color === targetColor) {
      return {
        success: true,
        display: comp.type + ' already uses "' + targetColor + '" color.'
      };
    }

    var group = COLOR_MAP[comp.type];
    if (!group) {
      return { success: false, error: 'Unknown component type: ' + comp.type };
    }

    // Remove old color class, add new one
    var oldClass = group.prefix + comp.color;
    var newClass = group.prefix + targetColor;

    el.classList.remove(oldClass);
    el.classList.add(newClass);

    // Special handling for 'default' — may need both bases
    if (targetColor === 'default' && comp.type === 'btn') {
      el.classList.add('btn-default');
    }
    if (targetColor === 'default' && comp.type === 'panel') {
      el.classList.add('panel-default');
    }
    if (targetColor === 'default' && comp.type === 'well') {
      // no specific well-default class needed; just remove the size class
    }

    // Also update any child <span class="label-xxx">, .panel-heading, .panel-body etc.
    var childSelectors = comp.type === 'panel'
      ? ['.panel-heading', '.panel-body', '.panel-footer']
      : ['.label-' + comp.color];
    for (var cs = 0; cs < childSelectors.length; cs++) {
      var sel = childSelectors[cs];
      var childEls = el.querySelectorAll(sel);
      for (var ce = 0; ce < childEls.length; ce++) {
        var oldChildClass = group.prefix + comp.color;
        var newChildClass = group.prefix + targetColor;
        childEls[ce].classList.remove(oldChildClass);
        childEls[ce].classList.add(newChildClass);
      }
    }

    // Update TinyMCE so the change is reflected in the editor content
    var editor = getEditor();
    if (editor) {
      try {
        editor.dispatch('Change', {});
        editor.nodeChanged();
      } catch (e) {
        // Non-critical
      }
    }

    return {
      success: true,
      display: comp.type + ' color changed from "' + comp.color + '" to "' + targetColor + '".'
    };
  }

  /**
   * Make a <details> element open by adding open="true".
   * If the element at cursor is not <details>, walks up to find one.
   * @returns {object} { success, display, error }
   */
  function makeOpen() {
    var editor = getEditor();
    if (!editor) {
      return { success: false, error: 'No editor found.' };
    }

    // Directly get cursor node from TinyMCE (doesn't require WET classes)
    var node = null;
    try {
      node = editor.selection ? editor.selection.getNode() : null;
    } catch (e) {
      return { success: false, error: 'Could not read cursor position.' };
    }
    if (!node) {
      return { success: false, error: 'No element at cursor. Click on a <details> element first.' };
    }

    // Walk up to find a <details> element
    var detailsEl = node;
    var maxDepth = 10;
    while (detailsEl && maxDepth-- > 0) {
      if (detailsEl.tagName && detailsEl.tagName.toLowerCase() === 'details') break;
      detailsEl = detailsEl.parentNode;
    }
    if (!detailsEl || detailsEl.tagName.toLowerCase() !== 'details') {
      return { success: false, error: 'No <details> element found near cursor.' };
    }

    if (detailsEl.hasAttribute('open') && detailsEl.getAttribute('open') !== 'false') {
      return { success: true, display: '✅ <details> is already open.' };
    }

    detailsEl.setAttribute('open', 'true');

    // Notify TinyMCE of the change
    try {
      editor.dispatch('Change', {});
      editor.nodeChanged();
    } catch (e) {
      // Non-critical
    }

    return { success: true, display: '✅ Added open="true" to <details>. Content is now visible and editable.' };
  }

  /**
   * Close a <details> element by removing open="true".
   * Uses the same cursor-node logic as makeOpen (without WET class dependency).
   * @returns {object} { success, display, error }
   */
  function makeClose() {
    var editor = getEditor();
    if (!editor) {
      return { success: false, error: 'No editor found.' };
    }

    var node = null;
    try {
      node = editor.selection ? editor.selection.getNode() : null;
    } catch (e) {
      return { success: false, error: 'Could not read cursor position.' };
    }
    if (!node) {
      return { success: false, error: 'No element at cursor. Click on a <details> element first.' };
    }

    // Walk up to find a <details> element
    var detailsEl = node;
    var maxDepth = 10;
    while (detailsEl && maxDepth-- > 0) {
      if (detailsEl.tagName && detailsEl.tagName.toLowerCase() === 'details') break;
      detailsEl = detailsEl.parentNode;
    }
    if (!detailsEl || detailsEl.tagName.toLowerCase() !== 'details') {
      return { success: false, error: 'No <details> element found near cursor.' };
    }

    if (!detailsEl.hasAttribute('open') || detailsEl.getAttribute('open') === 'false') {
      return { success: true, display: '✅ <details> is already closed.' };
    }

    detailsEl.removeAttribute('open');

    // Notify TinyMCE of the change
    try {
      editor.dispatch('Change', {});
      editor.nodeChanged();
    } catch (e) {
      // Non-critical
    }

    return { success: true, display: '🔒 Removed open="true" from <details>. Content is collapsed.' };
  }

  // ---- Export to window ----
  window.CanadaColorManager = {
    describeCurrent: describeCurrent,
    getCurrentComponent: getCurrentComponent,
    changeColor: changeColor,
    makeOpen: makeOpen,
    makeClose: makeClose
  };

  console.log('🎨 CanadaColorManager v1.1 loaded — btn/alert/label/badge/panel/well/text/bg supported.');

})();
