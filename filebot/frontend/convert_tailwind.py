#!/usr/bin/env python3
"""Convert Tailwind CSS classes to WET/Bootstrap 3 + fb-* utility classes + inline styles."""

import re
import sys
import os

# ── Tailwind color → hex mapping ──
COLOR_HEX = {
    'red': {'50':'#fef2f2','100':'#fee2e2','200':'#fecaca','300':'#fca5a5','400':'#f87171',
            '500':'#ef4444','600':'#dc2626','700':'#b91c1c','800':'#991b1b','900':'#7f1d1d'},
    'blue': {'50':'#eff6ff','100':'#dbeafe','200':'#bfdbfe','300':'#93c5fd','400':'#60a5fa',
             '500':'#3b82f6','600':'#2563eb','700':'#1d4ed8','800':'#1e40af','900':'#1e3a8a'},
    'green': {'50':'#f0fdf4','100':'#dcfce7','200':'#bbf7d0','300':'#86efac','400':'#4ade80',
              '500':'#22c55e','600':'#16a34a','700':'#15803d','800':'#166534','900':'#14532d'},
    'yellow': {'50':'#fefce8','100':'#fef9c3','200':'#fef08a','300':'#fde047','400':'#facc15',
               '500':'#eab308','600':'#ca8a04','700':'#a16207','800':'#854d0e','900':'#713f12'},
    'gray': {'50':'#f9fafb','100':'#f3f4f6','200':'#e5e7eb','300':'#d1d5db','400':'#9ca3af',
             '500':'#6b7280','600':'#4b5563','700':'#374151','800':'#1f2937','900':'#111827'},
    'purple': {'50':'#faf5ff','100':'#f3e8ff','200':'#e9d5ff','300':'#d8b4fe','400':'#c084fc',
               '500':'#a855f7','600':'#9333ea','700':'#7e22ce','800':'#6b21a8','900':'#581c87'},
    'indigo': {'50':'#eef2ff','100':'#e0e7ff','200':'#c7d2fe','300':'#a5b4fc','400':'#818cf8',
               '500':'#6366f1','600':'#4f46e5','700':'#4338ca','800':'#3730a3','900':'#312e81'},
    'emerald': {'50':'#ecfdf5','100':'#d1fae5','200':'#a7f3d0','300':'#6ee7b7','400':'#34d399',
                '500':'#10b981','600':'#059669','700':'#047857','800':'#065f46','900':'#064e3b'},
    'pink': {'50':'#fdf2f8','100':'#fce7f3','200':'#fbcfe8','300':'#f9a8d4','400':'#f472b6',
             '500':'#ec4899','600':'#db2777','700':'#be185d','800':'#9d174d','900':'#831843'},
    'amber': {'50':'#fffbeb','100':'#fef3c7','200':'#fde68a','300':'#fcd34d','400':'#fbbf24',
              '500':'#f59e0b','600':'#d97706','700':'#b45309','800':'#92400e','900':'#78350f'},
    'teal': {'50':'#f0fdfa','100':'#ccfbf1','200':'#99f6e4','300':'#5eead4','400':'#2dd4bf',
             '500':'#14b8a6','600':'#0d9488','700':'#0f766e','800':'#115e59','900':'#134e4a'},
    'orange': {'50':'#fff7ed','100':'#ffedd5','200':'#fed7aa','300':'#fdba74','400':'#fb923c',
               '500':'#f97316','600':'#ea580c','700':'#c2410c','800':'#9a3412','900':'#7c2d12'},
    'cyan': {'50':'#ecfeff','100':'#cffafe','200':'#a5f3fc','300':'#67e8f9','400':'#22d3ee',
             '500':'#06b6d4','600':'#0891b2','700':'#0e7490','800':'#155e75','900':'#164e63'},
    'lime': {'50':'#f7fee7','100':'#ecfccb','200':'#d9f99d','300':'#bef264','400':'#a3e635',
             '500':'#84cc16','600':'#65a30d','700':'#4d7c0f','800':'#3f6212','900':'#365314'},
    'rose': {'50':'#fff1f2','100':'#ffe4e6','200':'#fecdd3','300':'#fda4af','400':'#fb7185',
             '500':'#f43f5e','600':'#e11d48','700':'#be123c','800':'#9f1239','900':'#881337'},
    'violet': {'50':'#f5f3ff','100':'#ede9fe','200':'#ddd6fe','300':'#c4b5fd','400':'#a78bfa',
               '500':'#8b5cf6','600':'#7c3aed','700':'#6d28d9','800':'#5b21b6','900':'#4c1d95'},
    'slate': {'50':'#f8fafc','100':'#f1f5f9','200':'#e2e8f0','300':'#cbd5e1','400':'#94a3b8',
              '500':'#64748b','600':'#475569','700':'#334155','800':'#1e293b','900':'#0f172a'},
    'zinc': {'50':'#fafafa','100':'#f4f4f5','200':'#e4e4e7','300':'#d4d4d8','400':'#a1a1aa',
             '500':'#71717a','600':'#52525b','700':'#3f3f46','800':'#27272a','900':'#18181b'},
    'neutral': {'50':'#fafafa','100':'#f5f5f5','200':'#e5e5e5','300':'#d4d4d4','400':'#a3a3a3',
                '500':'#737373','600':'#525252','700':'#404040','800':'#262626','900':'#171717'},
    'stone': {'50':'#fafaf9','100':'#f5f5f4','200':'#e7e5e4','300':'#d6d3d1','400':'#a8a29e',
              '500':'#78716c','600':'#57534e','700':'#44403c','800':'#292524','900':'#1c1917'},
}

# ── Spacing scale (4px per unit) ──
SPACING = {str(n): n*4 for n in range(0, 97)}
SPACING['0.5'] = 2
SPACING['1.5'] = 6
SPACING['2.5'] = 10
SPACING['3.5'] = 14
SPACING['px'] = 1

# ── Font size scale ──
FONT_SIZES = {
    'xs': '0.75rem', 'sm': '0.875rem', 'base': '1rem',
    'lg': '1.125rem', 'xl': '1.25rem', '2xl': '1.5rem',
    '3xl': '1.875rem', '4xl': '2.25rem', '5xl': '3rem',
    '6xl': '3.75rem', '7xl': '4.5rem', '8xl': '6rem',
    '9xl': '8rem',
}

# ── Border radius scale ──
BORDER_RADIUS = {
    'none': 0, 'sm': 2, '': 4, 'md': 6,
    'lg': 8, 'xl': 12, '2xl': 16, '3xl': 24, 'full': '50%',
}

# ── Width/Height scale ──
SIZE = {
    '0': 0, '0.5': 2, '1': 4, '1.5': 6, '2': 8, '2.5': 10, '3': 12,
    '3.5': 14, '4': 16, '5': 20, '6': 24, '7': 28, '8': 32, '9': 36,
    '10': 40, '11': 44, '12': 48, '14': 56, '16': 64, '20': 80,
    '24': 96, '28': 112, '32': 128, '36': 144, '40': 160, '44': 176,
    '48': 192, '52': 208, '56': 224, '60': 240, '64': 256, '72': 288,
    '80': 320, '96': 384,
}

def get_color_hex(color_str):
    """Parse tailwind color like 'red-600' to hex like '#dc2626'"""
    parts = color_str.split('-')
    if len(parts) >= 2:
        color_name = parts[0]
        shade = parts[1]
        if color_name in COLOR_HEX and shade in COLOR_HEX[color_name]:
            return COLOR_HEX[color_name][shade]
    return None

def convert_class(cls, collected_styles):
    """Convert a single Tailwind class. Returns (new_class_or_None, adds_to_styles)."""
    
    # ── Flex & layout ──
    if cls == 'flex':
        return 'fb-d-flex', None
    if cls == 'inline-flex':
        collected_styles.append(('display', 'inline-flex'))
        return None, None
    if cls == 'flex-col':
        collected_styles.append(('flexDirection', 'column'))
        return None, None
    if cls == 'flex-row':
        collected_styles.append(('flexDirection', 'row'))
        return None, None
    if cls == 'flex-wrap':
        collected_styles.append(('flexWrap', 'wrap'))
        return None, None
    if cls == 'flex-1':
        collected_styles.append(('flex', 1))
        return None, None
    if cls == 'flex-shrink-0':
        collected_styles.append(('flexShrink', 0))
        return None, None
    if cls == 'flex-grow':
        collected_styles.append(('flexGrow', 1))
        return None, None
    
    if cls == 'items-center':
        return 'fb-align-center', None
    if cls == 'items-start':
        return 'fb-align-start', None
    if cls == 'items-end':
        return 'fb-align-end', None
    if cls == 'items-baseline':
        collected_styles.append(('alignItems', 'baseline'))
        return None, None
    
    if cls == 'justify-between':
        return 'fb-justify-between', None
    if cls == 'justify-center':
        return 'fb-justify-center', None
    if cls == 'justify-end':
        return 'fb-justify-end', None
    if cls == 'justify-start':
        return 'fb-justify-start', None
    
    # ── Spacing ──
    for prefix, css_key in [('m-', 'margin'), ('mt-', 'marginTop'), ('mb-', 'marginBottom'),
                              ('ml-', 'marginLeft'), ('mr-', 'marginRight'),
                              ('mx-', 'marginLeft'),  # will be handled as pair
                              ('my-', 'marginTop'),   # will be handled as pair
                              ('p-', 'padding'), ('pt-', 'paddingTop'), ('pb-', 'paddingBottom'),
                              ('pl-', 'paddingLeft'), ('pr-', 'paddingRight'),
                              ('px-', 'paddingLeft'),  # will be handled as pair
                              ('py-', 'paddingTop')]:  # will be handled as pair
        if cls.startswith(prefix):
            val_key = cls[len(prefix):]
            # Handle negative margins like -m-2
            if val_key.startswith('-'):
                neg = True
                val_key = val_key[1:]
            else:
                neg = False
            if val_key in SPACING:
                val = SPACING[val_key]
                if neg:
                    val = -val
                if prefix in ('mx-',):
                    collected_styles.append(('marginLeft', val))
                    collected_styles.append(('marginRight', val))
                    return None, None
                if prefix in ('my-',):
                    collected_styles.append(('marginTop', val))
                    collected_styles.append(('marginBottom', val))
                    return None, None
                if prefix in ('px-',):
                    collected_styles.append(('paddingLeft', val))
                    collected_styles.append(('paddingRight', val))
                    return None, None
                if prefix in ('py-',):
                    collected_styles.append(('paddingTop', val))
                    collected_styles.append(('paddingBottom', val))
                    return None, None
                if prefix == 'm-':
                    collected_styles.append(('margin', val))
                    return None, None
                if prefix == 'p-':
                    collected_styles.append(('padding', val))
                    return None, None
                collected_styles.append((css_key, val))
                return None, None
    
    # ── Gap ──
    if cls.startswith('gap-'):
        val_key = cls[4:]
        if val_key in SPACING:
            collected_styles.append(('gap', SPACING[val_key]))
        return None, None
    
    # ── Space between ──
    if cls.startswith('space-x-'):
        val_key = cls[8:]
        if val_key in SPACING:
            collected_styles.append(('columnGap', SPACING[val_key]))
        return None, None
    if cls.startswith('space-y-'):
        val_key = cls[8:]
        if val_key in SPACING:
            collected_styles.append(('rowGap', SPACING[val_key]))
        return None, None
    
    # ── Width/Height ──
    if cls.startswith('w-'):
        val_key = cls[2:]
        if val_key in SIZE:
            collected_styles.append(('width', SIZE[val_key]))
        elif val_key == 'full':
            collected_styles.append(('width', '100%'))
        elif val_key == 'screen':
            collected_styles.append(('width', '100vw'))
        elif val_key == 'auto':
            collected_styles.append(('width', 'auto'))
        elif val_key == 'min':
            collected_styles.append(('width', 'min-content'))
        elif val_key == 'max':
            collected_styles.append(('width', 'max-content'))
        elif val_key == 'fit':
            collected_styles.append(('width', 'fit-content'))
        elif '/' in val_key:
            # Handle w-1/2, w-1/3, etc.
            parts = val_key.split('/')
            if len(parts) == 2:
                try:
                    pct = float(parts[0]) / float(parts[1]) * 100
                    collected_styles.append(('width', f'{pct}%'))
                except: pass
        return None, None
    
    if cls.startswith('h-'):
        val_key = cls[2:]
        if val_key in SIZE:
            collected_styles.append(('height', SIZE[val_key]))
        elif val_key == 'full':
            collected_styles.append(('height', '100%'))
        elif val_key == 'screen':
            collected_styles.append(('height', '100vh'))
        elif val_key == 'auto':
            collected_styles.append(('height', 'auto'))
        return None, None
    
    if cls.startswith('min-h-'):
        val_key = cls[6:]
        if val_key == 'screen':
            collected_styles.append(('minHeight', '100vh'))
        elif val_key in SIZE:
            collected_styles.append(('minHeight', SIZE[val_key]))
        return None, None
    
    if cls.startswith('max-w-'):
        val_key = cls[6:]
        if val_key in SIZE:
            collected_styles.append(('maxWidth', SIZE[val_key]))
        elif val_key == 'xs':
            collected_styles.append(('maxWidth', 320))
        elif val_key == 'sm':
            collected_styles.append(('maxWidth', 384))
        elif val_key == 'md':
            collected_styles.append(('maxWidth', 448))
        elif val_key == 'lg':
            collected_styles.append(('maxWidth', 512))
        elif val_key == 'xl':
            collected_styles.append(('maxWidth', 576))
        elif val_key == '2xl':
            collected_styles.append(('maxWidth', 672))
        elif val_key == '3xl':
            collected_styles.append(('maxWidth', 768))
        elif val_key == '4xl':
            collected_styles.append(('maxWidth', 896))
        elif val_key == '5xl':
            collected_styles.append(('maxWidth', 1024))
        elif val_key == '6xl':
            collected_styles.append(('maxWidth', 1152))
        elif val_key == '7xl':
            collected_styles.append(('maxWidth', 1280))
        return None, None
    
    if cls.startswith('max-h-'):
        val_key = cls[6:]
        if val_key in SIZE:
            collected_styles.append(('maxHeight', SIZE[val_key]))
        return None, None
    
    # ── Font size ──
    if cls in ('text-xs', 'text-sm', 'text-base', 'text-lg', 'text-xl', 'text-2xl', 'text-3xl',
               'text-4xl', 'text-5xl', 'text-6xl', 'text-7xl', 'text-8xl', 'text-9xl'):
        fs_key = cls[5:] if cls != 'text-base' else 'base'
        collected_styles.append(('fontSize', FONT_SIZES[fs_key]))
        return None, None
    
    # ── Font weight ──
    if cls == 'font-thin':
        collected_styles.append(('fontWeight', 100))
        return None, None
    if cls == 'font-extralight':
        collected_styles.append(('fontWeight', 200))
        return None, None
    if cls == 'font-light':
        collected_styles.append(('fontWeight', 300))
        return None, None
    if cls == 'font-normal':
        collected_styles.append(('fontWeight', 400))
        return None, None
    if cls == 'font-medium':
        # Will be combined with text-gray-* => fb-label
        # If standalone, just set fontWeight
        collected_styles.append(('fontWeight', 500))
        return None, None
    if cls == 'font-semibold':
        collected_styles.append(('fontWeight', 600))
        return None, None
    if cls == 'font-bold':
        collected_styles.append(('fontWeight', 700))
        return None, None
    if cls == 'font-extrabold':
        collected_styles.append(('fontWeight', 800))
        return None, None
    if cls == 'font-black':
        collected_styles.append(('fontWeight', 900))
        return None, None
    
    # ── Text decoration ──
    if cls == 'underline':
        collected_styles.append(('textDecoration', 'underline'))
        return None, None
    if cls == 'line-through':
        collected_styles.append(('textDecoration', 'line-through'))
        return None, None
    if cls == 'no-underline':
        collected_styles.append(('textDecoration', 'none'))
        return None, None
    
    # ── Text transform ──
    if cls == 'uppercase':
        collected_styles.append(('textTransform', 'uppercase'))
        return None, None
    if cls == 'lowercase':
        collected_styles.append(('textTransform', 'lowercase'))
        return None, None
    if cls == 'capitalize':
        collected_styles.append(('textTransform', 'capitalize'))
        return None, None
    
    # ── Text colors (standalone - combined patterns handled after class collection) ──
    # These will be processed further in post-processing
    if re.match(r'^text-(red|blue|green|yellow|gray|purple|indigo|emerald|pink|amber|teal|orange|cyan|lime|rose|violet|slate|zinc|neutral|stone)-\d+$', cls):
        hex_val = get_color_hex(cls[5:])
        if hex_val:
            collected_styles.append(('color', hex_val))
        return None, None
    
    if re.match(r'^text-(red|blue|green|yellow|gray|purple|white|black)$', cls):
        color = cls[5:]
        if color == 'white':
            collected_styles.append(('color', '#ffffff'))
        elif color == 'black':
            collected_styles.append(('color', '#000000'))
        return None, None
    
    # ── Background colors ──
    if re.match(r'^bg-(red|blue|green|yellow|gray|purple|indigo|emerald|pink|amber|teal|orange|cyan|lime|rose|violet|slate|zinc|neutral|stone)-\d+$', cls):
        hex_val = get_color_hex(cls[3:])
        if hex_val:
            collected_styles.append(('background', hex_val))
        return None, None
    
    if cls == 'bg-white':
        collected_styles.append(('background', '#ffffff'))
        return None, None
    if cls == 'bg-black':
        collected_styles.append(('background', '#000000'))
        return None, None
    if cls in ('bg-red', 'bg-blue', 'bg-green', 'bg-yellow', 'bg-purple', 'bg-indigo', 'bg-gray', 'bg-pink', 'bg-orange', 'bg-teal', 'bg-cyan', 'bg-amber', 'bg-lime', 'bg-rose', 'bg-violet', 'bg-slate', 'bg-zinc', 'bg-neutral', 'bg-stone'):
        # Usually means bg-{color}-500
        color_name = cls[3:]
        if color_name in COLOR_HEX:
            collected_styles.append(('background', COLOR_HEX[color_name]['500']))
        return None, None
    
    # ── Opacity ──
    if cls.startswith('bg-opacity-'):
        val = cls[11:]
        try:
            collected_styles.append(('opacity', float(val) / 100))
        except: pass
        return None, None
    
    # ── Border radius ──
    if cls.startswith('rounded'):
        suffix = cls[7:]
        if suffix in BORDER_RADIUS:
            collected_styles.append(('borderRadius', BORDER_RADIUS[suffix]))
        else:
            collected_styles.append(('borderRadius', 4))  # default rounded
        return None, None
    
    # ── Borders ──
    if cls == 'border':
        collected_styles.append(('border', '1px solid'))
        return None, None
    if cls == 'border-0':
        collected_styles.append(('border', 'none'))
        return None, None
    if re.match(r'^border-(red|blue|green|yellow|gray|purple|indigo)-\d+$', cls):
        hex_val = get_color_hex(cls[7:])
        if hex_val:
            collected_styles.append(('borderColor', hex_val))
        return None, None
    if cls == 'border-transparent':
        collected_styles.append(('borderColor', 'transparent'))
        return None, None
    
    if re.match(r'^border-[tblr]-', cls):
        # border-b, border-b-2, border-b-blue-600 etc.
        direction = cls[7]  # t, r, b, l
        dir_map = {'t': 'Top', 'r': 'Right', 'b': 'Bottom', 'l': 'Left'}
        rest = cls[9:] if len(cls) > 9 else ''
        if rest:
            if rest in SIZE:
                collected_styles.append((f'border{dir_map[direction]}Width', SIZE[rest]))
            else:
                hex_val = get_color_hex(rest)
                if hex_val:
                    collected_styles.append((f'border{dir_map[direction]}Color', hex_val))
        else:
            collected_styles.append((f'border{direction}', '1px solid'))
        return None, None
    
    if re.match(r'^border-[tblr]-\d$', cls):
        # border-b-2 etc.
        direction = cls[7]
        dir_map = {'t': 'Top', 'r': 'Right', 'b': 'Bottom', 'l': 'Left'}
        width = cls[9:]
        if width in SIZE:
            collected_styles.append((f'border{dir_map[direction]}Width', SIZE[width]))
        return None, None
    
    # ── Divide ──
    if cls == 'divide-y':
        return 'fb-divide-y', None
    if cls.startswith('divide-y-'):
        # divide-y-gray-200
        hex_val = get_color_hex(cls[9:])
        if hex_val:
            collected_styles.append(('--divide-color', hex_val))
        return 'fb-divide-y', None
    if cls.startswith('divide-x-'):
        hex_val = get_color_hex(cls[9:])
        if hex_val:
            collected_styles.append(('--divide-color', hex_val))
        return 'fb-divide-x', None
    
    # ── Shadow ──
    if cls == 'shadow':
        collected_styles.append(('boxShadow', '0 1px 3px 0 rgba(0,0,0,0.1)'))
        return None, None
    if cls == 'shadow-sm':
        collected_styles.append(('boxShadow', '0 1px 2px 0 rgba(0,0,0,0.05)'))
        return None, None
    if cls == 'shadow-md':
        collected_styles.append(('boxShadow', '0 4px 6px -1px rgba(0,0,0,0.1)'))
        return None, None
    if cls == 'shadow-lg':
        collected_styles.append(('boxShadow', '0 10px 15px -3px rgba(0,0,0,0.1)'))
        return None, None
    if cls == 'shadow-xl':
        collected_styles.append(('boxShadow', '0 20px 25px -5px rgba(0,0,0,0.1)'))
        return None, None
    if cls == 'shadow-none':
        collected_styles.append(('boxShadow', 'none'))
        return None, None
    
    # ── Display ──
    if cls == 'block':
        collected_styles.append(('display', 'block'))
        return None, None
    if cls == 'inline-block':
        collected_styles.append(('display', 'inline-block'))
        return None, None
    if cls == 'inline':
        collected_styles.append(('display', 'inline'))
        return None, None
    if cls == 'hidden':
        collected_styles.append(('display', 'none'))
        return None, None
    
    # ── Positioning ──
    if cls == 'relative':
        collected_styles.append(('position', 'relative'))
        return None, None
    if cls == 'absolute':
        collected_styles.append(('position', 'absolute'))
        return None, None
    if cls == 'fixed':
        collected_styles.append(('position', 'fixed'))
        return None, None
    if cls == 'sticky':
        collected_styles.append(('position', 'sticky'))
        return None, None
    if cls == 'static':
        collected_styles.append(('position', 'static'))
        return None, None
    
    if cls == 'inset-0':
        collected_styles.append(('top', 0))
        collected_styles.append(('right', 0))
        collected_styles.append(('bottom', 0))
        collected_styles.append(('left', 0))
        return None, None
    
    if cls.startswith('top-') or cls.startswith('right-') or cls.startswith('bottom-') or cls.startswith('left-'):
        parts = cls.split('-')
        prop = {'top': 'top', 'right': 'right', 'bottom': 'bottom', 'left': 'left'}[parts[0]]
        val = parts[1]
        if val in SPACING:
            collected_styles.append((prop, SPACING[val]))
        elif val == 'auto':
            collected_styles.append((prop, 'auto'))
        elif val == '0':
            collected_styles.append((prop, 0))
        return None, None
    
    if cls.startswith('z-'):
        val = cls[2:]
        try:
            collected_styles.append(('zIndex', int(val) * 10))
        except: pass
        return None, None
    
    # ── Overflow ──
    if cls == 'overflow-hidden':
        collected_styles.append(('overflow', 'hidden'))
        return None, None
    if cls == 'overflow-auto':
        collected_styles.append(('overflow', 'auto'))
        return None, None
    if cls == 'overflow-x-auto':
        collected_styles.append(('overflowX', 'auto'))
        return None, None
    if cls == 'overflow-y-auto':
        collected_styles.append(('overflowY', 'auto'))
        return None, None
    if cls == 'overflow-visible':
        collected_styles.append(('overflow', 'visible'))
        return None, None
    
    # ── Text alignment ──
    if cls == 'text-left':
        return 'text-left', None
    if cls == 'text-right':
        return 'text-right', None
    if cls == 'text-center':
        return 'text-center', None
    if cls == 'text-justify':
        collected_styles.append(('textAlign', 'justify'))
        return None, None
    
    # ── Whitespace ──
    if cls == 'whitespace-nowrap':
        collected_styles.append(('whiteSpace', 'nowrap'))
        return None, None
    if cls == 'whitespace-normal':
        collected_styles.append(('whiteSpace', 'normal'))
        return None, None
    if cls == 'whitespace-pre':
        collected_styles.append(('whiteSpace', 'pre'))
        return None, None
    
    # ── Truncate ──
    if cls == 'truncate':
        collected_styles.append(('overflow', 'hidden'))
        collected_styles.append(('textOverflow', 'ellipsis'))
        collected_styles.append(('whiteSpace', 'nowrap'))
        return None, None
    
    # ── Cursor ──
    if cls == 'cursor-pointer':
        collected_styles.append(('cursor', 'pointer'))
        return None, None
    if cls == 'cursor-not-allowed':
        collected_styles.append(('cursor', 'not-allowed'))
        return None, None
    
    # ── Tracking (letter-spacing) ──
    if cls == 'tracking-wider':
        collected_styles.append(('letterSpacing', '0.05em'))
        return None, None
    if cls == 'tracking-wide':
        collected_styles.append(('letterSpacing', '0.025em'))
        return None, None
    if cls == 'tracking-tight':
        collected_styles.append(('letterSpacing', '-0.025em'))
        return None, None
    
    # ── Font family ──
    if cls == 'font-mono':
        collected_styles.append(('fontFamily', 'monospace'))
        return None, None
    if cls == 'font-sans':
        collected_styles.append(('fontFamily', 'sans-serif'))
        return None, None
    
    # ── Visibility ──
    if cls == 'invisible':
        collected_styles.append(('visibility', 'hidden'))
        return None, None
    if cls == 'visible':
        collected_styles.append(('visibility', 'visible'))
        return None, None
    
    # ── Transition ──
    if cls == 'transition':
        collected_styles.append(('transition', 'all 0.2s ease'))
        return None, None
    if cls == 'transition-opacity':
        collected_styles.append(('transition', 'opacity 0.2s ease'))
        return None, None
    if cls == 'transition-colors':
        collected_styles.append(('transition', 'color, background-color, border-color 0.2s ease'))
        return None, None
    
    if cls.startswith('duration-'):
        val = cls[9:]
        try:
            collected_styles.append(('transitionDuration', f'{int(val)}ms'))
        except: pass
        return None, None
    
    # ── Opacity ──
    if cls.startswith('opacity-'):
        val = cls[8:]
        try:
            collected_styles.append(('opacity', int(val) / 100))
        except: pass
        return None, None
    
    # ── Box sizing ──
    if cls == 'box-border':
        collected_styles.append(('boxSizing', 'border-box'))
        return None, None
    if cls == 'box-content':
        collected_styles.append(('boxSizing', 'content-box'))
        return None, None
    
    # ── Object fit ──
    if cls == 'object-cover':
        collected_styles.append(('objectFit', 'cover'))
        return None, None
    if cls == 'object-contain':
        collected_styles.append(('objectFit', 'contain'))
        return None, None
    
    # ── List style ──
    if cls == 'list-none':
        collected_styles.append(('listStyle', 'none'))
        return None, None
    
    # ── Vertical align ──
    if cls == 'align-middle':
        collected_styles.append(('verticalAlign', 'middle'))
        return None, None
    if cls == 'align-top':
        collected_styles.append(('verticalAlign', 'top'))
        return None, None
    if cls == 'align-bottom':
        collected_styles.append(('verticalAlign', 'bottom'))
        return None, None
    
    # ── Pointer events ──
    if cls == 'pointer-events-none':
        collected_styles.append(('pointerEvents', 'none'))
        return None, None
    
    # ── User select ──
    if cls == 'select-none':
        collected_styles.append(('userSelect', 'none'))
        return None, None
    
    # ── Hover states (we keep as-is since hover requires CSS) ──
    if cls.startswith('hover:'):
        # These need :hover pseudo-class, keep as fb-hover-btn for common patterns
        rest = cls[6:]
        if rest == 'bg-gray-50':
            return 'fb-hover-btn', None
        if rest == 'bg-gray-100':
            return 'fb-hover-btn', None
        if rest == 'bg-blue-200':
            return 'fb-hover-btn', None
        if rest == 'bg-red-200':
            return 'fb-hover-btn', None
        if rest == 'bg-gray-200':
            return 'fb-hover-btn', None
        if rest == 'text-blue-600':
            return 'fb-link', None
        if rest == 'bg-green-200':
            return 'fb-hover-btn', None
        if rest == 'bg-purple-200':
            return 'fb-hover-btn', None
        # Other hover states - add inline with :hover handled by fb class
        return 'fb-hover-btn', None
    
    # ── Focus states ──
    if cls.startswith('focus:'):
        rest = cls[6:]
        if rest == 'outline-none':
            collected_styles.append(('outline', 'none'))
        elif rest.startswith('ring-'):
            ring_val = rest[5:]
            if ring_val in SIZE:
                collected_styles.append(('boxShadow', f'0 0 0 {SIZE[ring_val]}px rgba(59,130,246,0.5)'))
            elif ring_val in ('blue-500',):
                collected_styles.append(('boxShadow', '0 0 0 2px rgba(59,130,246,0.5)'))
            elif ring_val in ('red-300',):
                collected_styles.append(('boxShadow', '0 0 0 2px rgba(252,165,165,0.5)'))
            elif ring_val in ('gray-400',):
                collected_styles.append(('boxShadow', '0 0 0 2px rgba(156,163,175,0.5)'))
        elif rest == 'border-transparent':
            collected_styles.append(('borderColor', 'transparent'))
        elif rest.startswith('ring-offset-'):
            pass  # ring-offset is handled by ring
        return None, None
    
    # ── Disabled states ──
    if cls.startswith('disabled:'):
        rest = cls[9:]
        if rest == 'opacity-50':
            # This is applied via CSS, we'll add to style
            pass  # can't easily express disabled state in inline style
        if rest == 'cursor-not-allowed':
            pass
        return None, None
    
    # ── Responsive prefixes (sm:, md:, lg:, xl:) ──
    # We strip responsive prefixes since Bootstrap handles responsive breakpoints
    for bp in ['sm:', 'md:', 'lg:', 'xl:', '2xl:']:
        if cls.startswith(bp):
            inner = cls[len(bp):]
            # Recursively convert the inner class
            return convert_class(inner, collected_styles)
    
    # ── sr-only ──
    if cls == 'sr-only':
        return 'sr-only', None
    
    # ── Leading (line-height) ──
    if cls.startswith('leading-'):
        val = cls[8:]
        lh_map = {'3': '.75rem', '4': '1rem', '5': '1.25rem', '6': '1.5rem',
                  '7': '1.75rem', '8': '2rem', '9': '2.25rem', '10': '2.5rem',
                  'none': '1', 'tight': '1.25', 'snug': '1.375', 'normal': '1.5',
                  'relaxed': '1.625', 'loose': '2'}
        if val in lh_map:
            collected_styles.append(('lineHeight', lh_map[val]))
        return None, None
    
    # ── Grid ──
    if cls == 'grid':
        collected_styles.append(('display', 'grid'))
        return None, None
    if cls.startswith('grid-cols-'):
        val = cls[10:]
        try:
            collected_styles.append(('gridTemplateColumns', f'repeat({val}, minmax(0, 1fr))'))
        except: pass
        return None, None
    if cls.startswith('col-span-'):
        val = cls[9:]
        try:
            collected_styles.append(('gridColumn', f'span {val} / span {val}'))
        except: pass
        return None, None
    
    # ── Table display ──
    if cls == 'table':
        collected_styles.append(('display', 'table'))
        return None, None
    if cls == 'table-row':
        collected_styles.append(('display', 'table-row'))
        return None, None
    if cls == 'table-cell':
        collected_styles.append(('display', 'table-cell'))
        return None, None
    
    # ── Align self ──
    if cls == 'self-start':
        collected_styles.append(('alignSelf', 'flex-start'))
        return None, None
    if cls == 'self-center':
        collected_styles.append(('alignSelf', 'center'))
        return None, None
    if cls == 'self-end':
        collected_styles.append(('alignSelf', 'flex-end'))
        return None, None
    if cls == 'self-stretch':
        collected_styles.append(('alignSelf', 'stretch'))
        return None, None
    
    # ── Background transparent ──
    if cls == 'bg-transparent':
        collected_styles.append(('background', 'transparent'))
        return None, None
    
    # ── Justify self ──
    if cls == 'justify-self-start':
        collected_styles.append(('justifySelf', 'start'))
        return None, None
    if cls == 'justify-self-center':
        collected_styles.append(('justifySelf', 'center'))
        return None, None
    if cls == 'justify-self-end':
        collected_styles.append(('justifySelf', 'end'))
        return None, None
    
    # ── pt- (for already handled by general prefix above, but keeping here for pt-2, pt-4 etc) ──
    # Actually this is already handled by the general spacing prefix loop above
    
    # ── grid rows ──
    if cls.startswith('row-span-'):
        val = cls[9:]
        try:
            collected_styles.append(('gridRow', f'span {val} / span {val}'))
        except: pass
        return None, None
    
    # ── Anime (animate-*) ──
    if cls == 'animate-spin':
        return 'fb-spinner', None
    if cls == 'animate-pulse':
        return None, None  # keep as CSS animation
    if cls == 'animate-bounce':
        return None, None
    
    # ── Circular height/width ──
    if cls.startswith('h-') and cls[2:] in SIZE:
        collected_styles.append(('height', SIZE[cls[2:]]))
        return None, None
    
    # ── Miscellaneous that snuck through ──
    # handle number-based classes like "2", "0" that aren't Tailwind
    if cls.isdigit():
        return cls, None
    
    return cls, None


def process_jsx_line(line, in_template_literal=False):
    """Process a single JSX line, converting Tailwind classes."""
    
    # Handle className="..." patterns
    # We need to find all className="..." in the line (but not inside template literals)
    
    def replace_classname(match):
        full_match = match.group(0)
        quote_char = match.group(1)  # " or '
        class_str = match.group(2)
        
        # Split into individual classes
        classes = [c for c in class_str.split() if c]
        
        new_classes = []
        styles = []
        
        for cls in classes:
            new_cls, style_extra = convert_class(cls, styles)
            if new_cls and new_cls not in new_classes:
                new_classes.append(new_cls)
        
        # Post-process: check for fb-label pattern (font-medium + text-gray-700/900)
        has_font_medium = any('fontWeight' in str(s) for s in styles)
        # Remove fontWeight:500 entries if we have a text color entry
        has_color = any(s[0] == 'color' for s in styles)
        
        # Build result
        rebuilt = ' '.join(new_classes) if new_classes else ''
        
        if styles:
            style_parts = []
            for key, val in styles:
                if isinstance(val, str) and not val.startswith(("'", '"')):
                    style_parts.append(f'{key}:"{val}"')
                else:
                    style_parts.append(f'{key}:{val}')
            style_str = '{{' + ','.join(style_parts) + '}}'
            
            if rebuilt:
                return f'className="{rebuilt}" style={style_str}'
            else:
                return f'style={style_str}'
        else:
            if rebuilt:
                return f'className="{rebuilt}"'
            else:
                return ''  # Remove empty className
    
    # Find className="..." or className='...' patterns
    # Be careful not to match inside style objects or other attributes
    pattern = r'className=(["\'])((?:[^\\\1]|\\.)*?)\1'
    result = re.sub(pattern, replace_classname, line)
    
    return result


def has_tailwind(content):
    """Check if content still has Tailwind patterns."""
    tailwind_patterns = [
        r'\bflex\s', r'\bflex\b', r'items-center', r'items-start', r'items-end',
        r'justify-between', r'justify-center', r'justify-end',
        r'\bspace-x-', r'\bspace-y-', r'\bgap-\d', r'\bgrid-cols-',
        r'text-(xs|sm|base|lg|xl|2xl|3xl|4xl|5xl|6xl)\b',
        r'font-(thin|extralight|light|normal|medium|semibold|bold|extrabold|black)',
        r'\bm[tblrxy]?-\d', r'\bp[tblrxy]?-\d',
        r'w-\d', r'h-\d', r'min-h-', r'max-w-', r'max-h-',
        r'\bbg-(red|blue|green|yellow|gray|purple|indigo|emerald|slate)-\d',
        r'text-(red|blue|green|yellow|gray|purple|indigo|emerald|slate)-\d',
        r'\bbg-white\b', r'\bbg-black\b',
        r'rounded-(sm|md|lg|xl|2xl|3xl|full)',
        r'\bshadow(-sm|-md|-lg|-xl)?\b',
        r'\btruncate\b', r'whitespace-nowrap',
        r'hover:', r'focus:', r'disabled:',
        r'animate-(spin|pulse|bounce)',
        r'border-b\b', r'border-t\b', r'border-l\b', r'border-r\b',
        r'\bdivided?-[xy]',
        r'w-\[', r'h-\[',  # arbitrary values
    ]
    return bool(re.search('|'.join(tailwind_patterns), content))


def convert_file(filepath):
    """Convert Tailwind classes in a single file."""
    print(f"Processing {filepath}...")
    
    with open(filepath, 'r') as f:
        content = f.read()
    
    # Process line by line for className attributes
    lines = content.split('\n')
    converted_lines = []
    modified = False
    
    for line in lines:
        if 'className=' in line:
            new_line = process_jsx_line(line)
            if new_line != line:
                modified = True
            converted_lines.append(new_line)
        else:
            converted_lines.append(line)
    
    converted = '\n'.join(converted_lines)
    
    # Clean up empty className="" 
    converted = re.sub(r'\bclassName=""\s*', '', converted)
    # Clean up empty className='' 
    converted = re.sub(r"\bclassName=''\s*", '', converted)
    # Clean up duplicates: className="foo" style={..} className="bar" -> className="foo bar"
    
    if modified:
        with open(filepath, 'w') as f:
            f.write(converted)
        print(f"  ✅ Converted {filepath}")
    else:
        print(f"  ⚠️ No changes in {filepath}")
    
    # Check for remaining tailwind
    remaining = has_tailwind(converted)
    if remaining:
        print(f"  ⚠️ Some Tailwind patterns may remain - check manually")
    
    return converted


if __name__ == '__main__':
    files = [
        'src/pages/admin/AdminAppFolders.tsx',
        'src/pages/admin/AdminPathView.tsx',
        'src/pages/admin/AdminDocuments.tsx',
        'src/pages/admin/AdminAppsDashboard.tsx',
        'src/pages/admin/AdminInstitutions.tsx',
        'src/pages/admin/AdminTasks.tsx',
        'src/pages/admin/AdminUpload.tsx',
        'src/pages/admin/AdminUsers.tsx',
    ]
    
    for f in files:
        full_path = os.path.join(os.getcwd(), f)
        if os.path.exists(full_path):
            convert_file(full_path)
        else:
            print(f"  ❌ File not found: {full_path}")
    
    print("\nDone! Now check for remaining Tailwind patterns...")
