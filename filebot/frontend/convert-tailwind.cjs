#!/usr/bin/env node
/**
 * Tailwind CSS → Bootstrap 3 + fb-* + inline style converter v2
 */
const fs = require('fs');

// ============ COMPOSITE PATTERNS (match full className string) ============
// These are matched BEFORE token-by-token conversion
const COMPOSITE_PATTERNS = [
  // Buttons: bg-{color}-600 text-white px-{x} py-{y} rounded{?} hover:bg-{color}-700
  {
    match: /^bg-blue-600 text-white px-\d+ py-\d+ rounded(?:-md)?(?: hover:bg-blue-700)?(?: focus:outline-none focus:ring-2 focus:ring-blue-500)?(?: disabled:opacity-50 disabled:cursor-not-allowed)?$/,
    result: { classes: ['btn', 'btn-primary'], style: {} }
  },
  {
    match: /^bg-green-600 text-white px-\d+ py-\d+ rounded(?:-md)?(?: hover:bg-green-700)?(?: focus:outline-none focus:ring-2 focus:ring-green-500)?(?: disabled:opacity-50 disabled:cursor-not-allowed)?$/,
    result: { classes: ['btn', 'btn-success'], style: {} }
  },
  {
    match: /^bg-red-600 text-white px-\d+ py-\d+ rounded(?:-md)?(?: hover:bg-red-700)?(?: focus:outline-none focus:ring-2 focus:ring-red-500)?(?: disabled:opacity-50 disabled:cursor-not-allowed)?$/,
    result: { classes: ['btn', 'btn-danger'], style: {} }
  },
  {
    match: /^bg-yellow-500 text-white px-\d+ py-\d+ rounded(?:-md)?(?: hover:bg-yellow-600)?$/,
    result: { classes: ['btn', 'btn-warning'], style: {} }
  },
  {
    match: /^border border-gray-300 text-gray-700 px-\d+ py-\d+ rounded(?:-md)?(?: hover:bg-gray-50)?$/,
    result: { classes: ['btn', 'btn-default'], style: {} }
  },
  // Form controls
  {
    match: /^w-full px-3 py-2 border border-gray-300 rounded(?: focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent)?$/,
    result: { classes: ['form-control'], style: {} }
  },
  {
    match: /^w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent$/,
    result: { classes: ['form-control'], style: {} }
  },
  // Textarea form-control
  {
    match: /^flex-1 border border-gray-300 rounded(?:-lg)? px-\d+ py-\d+ focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent resize-none$/,
    result: { classes: ['form-control'], style: { flex: 1, resize: 'none', borderRadius: 8 } }
  },
  // Select form-control
  {
    match: /^w-full px-3 py-2 border border-gray-300 rounded(?:-md)?(?: bg-white)?(?: focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent)?$/,
    result: { classes: ['form-control'], style: {} }
  },
  // Modal backdrop
  {
    match: /^fixed inset-0 bg-black bg-opacity-50 flex items-center justify-center z-50(?: p-4)?$/,
    result: { classes: ['fb-modal-backdrop', 'fb-d-flex', 'fb-align-center'], style: { justifyContent: 'center', zIndex: 50 } }
  },
  // Page background
  {
    match: /^min-h-screen bg-gray-50 p-4$/,
    result: { classes: ['fb-page-bg'], style: { padding: 16 } }
  },
  {
    match: /^min-h-screen bg-gray-50(?: p-8)?$/,
    result: { classes: ['fb-page-bg'], style: {} }
  },
  // Panel
  {
    match: /^bg-white rounded-lg shadow p-6$/,
    result: { classes: ['panel', 'panel-default'], style: { padding: 24 } }
  },
  {
    match: /^bg-white rounded-lg shadow-xl w-full max-w-md$/,
    result: { classes: ['panel', 'panel-default'], style: { width: '100%', maxWidth: 448 } }
  },
  // Grid → row
  {
    match: /^grid grid-cols-1(?: gap-\d+)?$/,
    result: null // let token-by-token handle it: grid→display, grid-cols-1→template
  },
];

// ============ TOKEN MAP ============
const TOKEN_MAP = {
  // Layout
  flex: { classes: ['fb-d-flex'], style: {} },
  'inline-flex': { style: { display: 'inline-flex' } },
  'flex-col': { style: { flexDirection: 'column' } },
  'flex-row': { style: { flexDirection: 'row' } },
  'flex-wrap': { style: { flexWrap: 'wrap' } },
  'flex-nowrap': { style: { flexWrap: 'nowrap' } },
  'flex-1': { style: { flex: 1 } },
  'flex-shrink-0': { style: { flexShrink: 0 } },
  'flex-grow': { style: { flexGrow: 1 } },
  'justify-between': { classes: ['fb-justify-between'], style: {} },
  'justify-end': { style: { justifyContent: 'flex-end' } },
  'justify-start': { style: { justifyContent: 'flex-start' } },
  'justify-center': { style: { justifyContent: 'center' } },
  'items-center': { classes: ['fb-align-center'], style: {} },
  'items-start': { classes: ['fb-align-start'], style: {} },
  'items-end': { style: { alignItems: 'flex-end' } },
  'self-end': { style: { alignSelf: 'flex-end' } },
  'self-center': { style: { alignSelf: 'center' } },
  'gap-1': { classes: ['fb-gap-1'], style: {} },
  'gap-2': { classes: ['fb-gap-2'], style: {} },
  'gap-3': { classes: ['fb-gap-3'], style: {} },
  'gap-4': { style: { gap: 16 } },
  'gap-6': { style: { gap: 24 } },
  'space-x-2': { style: { display: 'flex', gap: 8 } },
  'space-x-3': { style: { display: 'flex', gap: 12 } },
  'space-x-4': { style: { display: 'flex', gap: 16 } },
  'space-y-1': { style: { display: 'flex', flexDirection: 'column', gap: 4 } },
  'space-y-2': { style: { display: 'flex', flexDirection: 'column', gap: 8 } },
  'space-y-4': { style: { display: 'flex', flexDirection: 'column', gap: 16 } },
  'space-y-6': { style: { display: 'flex', flexDirection: 'column', gap: 24 } },
  'space-y-8': { style: { display: 'flex', flexDirection: 'column', gap: 32 } },

  // Sizing
  'w-full': { style: { width: '100%' } },
  'w-auto': { style: { width: 'auto' } },
  'w-1/2': { style: { width: '50%' } },
  'w-4': { style: { width: 16 } },
  'w-5': { style: { width: 20 } },
  'w-6': { style: { width: 24 } },
  'w-8': { style: { width: 32 } },
  'w-10': { style: { width: 40 } },
  'w-12': { style: { width: 48 } },
  'w-16': { style: { width: 64 } },
  'w-20': { style: { width: 80 } },
  'w-24': { style: { width: 96 } },
  'w-32': { style: { width: 128 } },
  'w-48': { style: { width: 192 } },
  'w-64': { style: { width: 256 } },
  'h-0.5': { style: { height: 2 } },
  'h-1': { style: { height: 4 } },
  'h-4': { style: { height: 16 } },
  'h-5': { style: { height: 20 } },
  'h-6': { style: { height: 24 } },
  'h-8': { style: { height: 32 } },
  'h-10': { style: { height: 40 } },
  'h-12': { style: { height: 48 } },
  'h-16': { style: { height: 64 } },
  'h-32': { style: { height: 128 } },
  'h-64': { style: { height: 256 } },
  'h-full': { style: { height: '100%' } },
  'max-w-md': { style: { maxWidth: 448 } },
  'max-w-lg': { style: { maxWidth: 512 } },
  'max-w-xl': { style: { maxWidth: 576 } },
  'max-w-2xl': { style: { maxWidth: 672 } },
  'max-w-7xl': { style: { maxWidth: '80rem' } },
  'max-w-[80%]': { style: { maxWidth: '80%' } },
  'max-w-6xl': { style: { maxWidth: '72rem' } },
  'max-w-xs': { style: { maxWidth: 320 } },
  'max-h-32': { style: { maxHeight: 128 } },
  'max-h-60': { style: { maxHeight: 240 } },
  'max-h-96': { style: { maxHeight: 384 } },
  'max-h-[90vh]': { style: { maxHeight: '90vh' } },
  'min-w-0': { style: { minWidth: 0 } },
  'min-w-full': { style: { minWidth: '100%' } },
  'min-h-screen': { classes: ['fb-page-bg'], style: {} },

  // Spacing (padding)
  'p-0': { style: { padding: 0 } },
  'p-0.5': { style: { padding: 2 } },
  'p-1': { style: { padding: 4 } },
  'p-2': { style: { padding: 8 } },
  'p-3': { style: { padding: 12 } },
  'p-4': { style: { padding: 16 } },
  'p-5': { style: { padding: 20 } },
  'p-6': { style: { padding: 24 } },
  'p-8': { style: { padding: 32 } },
  'p-10': { style: { padding: 40 } },
  'p-12': { style: { padding: 48 } },
  'px-0': { style: { paddingLeft: 0, paddingRight: 0 } },
  'px-1': { style: { paddingLeft: 4, paddingRight: 4 } },
  'px-2': { style: { paddingLeft: 8, paddingRight: 8 } },
  'px-3': { style: { paddingLeft: 12, paddingRight: 12 } },
  'px-4': { style: { paddingLeft: 16, paddingRight: 16 } },
  'px-5': { style: { paddingLeft: 20, paddingRight: 20 } },
  'px-6': { style: { paddingLeft: 24, paddingRight: 24 } },
  'px-8': { style: { paddingLeft: 32, paddingRight: 32 } },
  'py-0.5': { style: { paddingTop: 2, paddingBottom: 2 } },
  'py-1': { style: { paddingTop: 4, paddingBottom: 4 } },
  'py-1.5': { style: { paddingTop: 6, paddingBottom: 6 } },
  'py-2': { style: { paddingTop: 8, paddingBottom: 8 } },
  'py-2.5': { style: { paddingTop: 10, paddingBottom: 10 } },
  'py-3': { style: { paddingTop: 12, paddingBottom: 12 } },
  'py-4': { style: { paddingTop: 16, paddingBottom: 16 } },
  'py-6': { style: { paddingTop: 24, paddingBottom: 24 } },
  'py-8': { style: { paddingTop: 32, paddingBottom: 32 } },
  'pt-0': { style: { paddingTop: 0 } },
  'pt-1': { style: { paddingTop: 4 } },
  'pt-2': { style: { paddingTop: 8 } },
  'pt-3': { style: { paddingTop: 12 } },
  'pt-4': { style: { paddingTop: 16 } },
  'pt-8': { style: { paddingTop: 32 } },
  'pb-0': { style: { paddingBottom: 0 } },
  'pb-2': { style: { paddingBottom: 8 } },
  'pb-4': { style: { paddingBottom: 16 } },
  'pr-2': { style: { paddingRight: 8 } },
  'pr-3': { style: { paddingRight: 12 } },
  'pr-4': { style: { paddingRight: 16 } },
  'pl-3': { style: { paddingLeft: 12 } },
  'pl-4': { style: { paddingLeft: 16 } },
  'pl-10': { style: { paddingLeft: 40 } },

  // Spacing (margin)
  'm-0': { style: { margin: 0 } },
  'mt-0': { style: { marginTop: 0 } },
  'mt-1': { style: { marginTop: 4 } },
  'mt-2': { style: { marginTop: 8 } },
  'mt-3': { style: { marginTop: 12 } },
  'mt-4': { style: { marginTop: 16 } },
  'mt-6': { style: { marginTop: 24 } },
  'mt-8': { style: { marginTop: 32 } },
  'mb-0': { style: { marginBottom: 0 } },
  'mb-1': { style: { marginBottom: 4 } },
  'mb-2': { style: { marginBottom: 8 } },
  'mb-3': { style: { marginBottom: 12 } },
  'mb-4': { style: { marginBottom: 16 } },
  'mb-6': { style: { marginBottom: 24 } },
  'mb-8': { style: { marginBottom: 32 } },
  'mr-0': { style: { marginRight: 0 } },
  'mr-1': { style: { marginRight: 4 } },
  'mr-2': { style: { marginRight: 8 } },
  'mr-3': { style: { marginRight: 12 } },
  'mr-4': { style: { marginRight: 16 } },
  'ml-0': { style: { marginLeft: 0 } },
  'ml-1': { style: { marginLeft: 4 } },
  'ml-2': { style: { marginLeft: 8 } },
  'ml-3': { style: { marginLeft: 12 } },
  'ml-4': { style: { marginLeft: 16 } },
  'mx-2': { style: { marginLeft: 8, marginRight: 8 } },
  'mx-4': { style: { marginLeft: 16, marginRight: 16 } },
  'mx-auto': { style: { marginLeft: 'auto', marginRight: 'auto' } },
  '-ml-1': { style: { marginLeft: -4 } },
  '-mt-1': { style: { marginTop: -4 } },

  // Position
  relative: { style: { position: 'relative' } },
  absolute: { style: { position: 'absolute' } },
  fixed: { style: { position: 'fixed' } },
  sticky: { style: { position: 'sticky' } },
  'inset-0': { style: { top: 0, right: 0, bottom: 0, left: 0 } },
  'top-0': { style: { top: 0 } },
  'top-2': { style: { top: 8 } },
  'top-2.5': { style: { top: 10 } },
  'left-0': { style: { left: 0 } },
  'right-0': { style: { right: 0 } },
  'right-2': { style: { right: 8 } },
  'right-3': { style: { right: 12 } },
  'bottom-0': { style: { bottom: 0 } },
  'z-10': { style: { zIndex: 10 } },
  'z-20': { style: { zIndex: 20 } },
  'z-50': { style: { zIndex: 50 } },

  // Display
  hidden: { style: { display: 'none' } },
  block: { style: { display: 'block' } },
  'inline-block': { style: { display: 'inline-block' } },
  'inline': { style: { display: 'inline' } },

  // Overflow
  'overflow-hidden': { style: { overflow: 'hidden' } },
  'overflow-y-auto': { style: { overflowY: 'auto' } },
  'overflow-x-auto': { style: { overflowX: 'auto' } },

  // Background colors
  'bg-transparent': { style: { backgroundColor: 'transparent' } },
  'bg-white': { style: { backgroundColor: '#fff' } },
  'bg-gray-50': { style: { backgroundColor: '#f9fafb' } },
  'bg-gray-100': { style: { backgroundColor: '#f3f4f6' } },
  'bg-gray-200': { style: { backgroundColor: '#e5e7eb' } },
  'bg-gray-300': { style: { backgroundColor: '#d1d5db' } },
  'bg-blue-50': { style: { backgroundColor: '#eff6ff' } },
  'bg-blue-100': { style: { backgroundColor: '#dbeafe' } },
  'bg-blue-500': { style: { backgroundColor: '#3b82f6' } },
  'bg-blue-600': { style: { backgroundColor: '#2563eb' } },
  'bg-green-50': { style: { backgroundColor: '#f0fdf4' } },
  'bg-green-100': { style: { backgroundColor: '#dcfce7' } },
  'bg-green-600': { style: { backgroundColor: '#16a34a' } },
  'bg-green-700': { style: { backgroundColor: '#15803d' } },
  'bg-red-50': { style: { backgroundColor: '#fef2f2' } },
  'bg-red-100': { style: { backgroundColor: '#fee2e2' } },
  'bg-red-600': { style: { backgroundColor: '#dc2626' } },
  'bg-red-700': { style: { backgroundColor: '#b91c1c' } },
  'bg-yellow-50': { style: { backgroundColor: '#fffbeb' } },
  'bg-yellow-100': { style: { backgroundColor: '#fef3c7' } },
  'bg-yellow-500': { style: { backgroundColor: '#eab308' } },
  'bg-purple-50': { style: { backgroundColor: '#faf5ff' } },
  'bg-purple-100': { style: { backgroundColor: '#f3e8ff' } },
  'bg-indigo-50': { style: { backgroundColor: '#eef2ff' } },
  'bg-indigo-100': { style: { backgroundColor: '#e0e7ff' } },
  'bg-black': { style: { backgroundColor: '#000' } },
  'bg-opacity-50': { style: {} }, // handled separately
  'bg-opacity-20': { style: {} },
  'border-opacity-50': { style: {} },

  // Text colors
  'text-white': { style: { color: '#fff' } },
  'text-gray-200': { style: { color: '#e5e7eb' } },
  'text-gray-300': { style: { color: '#d1d5db' } },
  'text-gray-400': { style: { color: '#9ca3af' } },
  'text-gray-500': { classes: ['text-muted'], style: {} },
  'text-gray-600': { classes: ['text-muted'], style: {} },
  'text-gray-700': { style: { color: '#374151' } },
  'text-gray-800': { style: { color: '#1f2937' } },
  'text-gray-900': { style: { color: '#111827' } },
  'text-blue-400': { style: { color: '#60a5fa' } },
  'text-blue-500': { style: { color: '#3b82f6' } },
  'text-blue-600': { style: { color: '#2563eb' } },
  'text-blue-700': { style: { color: '#1d4ed8' } },
  'text-blue-800': { style: { color: '#1e40af' } },
  'text-blue-900': { style: { color: '#1e3a5f' } },
  'text-green-500': { style: { color: '#22c55e' } },
  'text-green-600': { style: { color: '#16a34a' } },
  'text-green-700': { style: { color: '#15803d' } },
  'text-green-800': { style: { color: '#166534' } },
  'text-red-400': { style: { color: '#f87171' } },
  'text-red-500': { style: { color: '#ef4444' } },
  'text-red-600': { style: { color: '#dc2626' } },
  'text-red-700': { style: { color: '#b91c1c' } },
  'text-red-800': { style: { color: '#991b1b' } },
  'text-yellow-400': { style: { color: '#facc15' } },
  'text-yellow-500': { style: { color: '#eab308' } },
  'text-yellow-600': { style: { color: '#ca8a04' } },
  'text-yellow-700': { style: { color: '#a16207' } },
  'text-yellow-800': { style: { color: '#854d0e' } },
  'text-purple-800': { style: { color: '#6b21a8' } },
  'text-indigo-800': { style: { color: '#3730a3' } },

  // Font
  'font-light': { style: { fontWeight: 300 } },
  'font-normal': { style: { fontWeight: 400 } },
  'font-medium': { style: { fontWeight: 500 } },
  'font-semibold': { style: { fontWeight: 600 } },
  'font-bold': { style: { fontWeight: 700 } },
  'text-xs': { style: { fontSize: '0.75rem', lineHeight: '1rem' } },
  'text-sm': { style: { fontSize: '0.875rem', lineHeight: '1.25rem' } },
  'text-base': { style: { fontSize: '1rem', lineHeight: '1.5rem' } },
  'text-lg': { style: { fontSize: '1.125rem', lineHeight: '1.75rem' } },
  'text-xl': { style: { fontSize: '1.25rem', lineHeight: '1.75rem' } },
  'text-2xl': { style: { fontSize: '1.5rem', lineHeight: '2rem' } },
  'text-3xl': { style: { fontSize: '1.875rem', lineHeight: '2.25rem' } },
  'text-4xl': { style: { fontSize: '2.25rem', lineHeight: '2.5rem' } },
  'text-6xl': { style: { fontSize: '3.75rem', lineHeight: 1 } },
  'text-center': { classes: ['text-center'], style: {} },
  'text-left': { classes: ['text-left'], style: {} },
  'text-right': { classes: ['text-right'], style: {} },
  'whitespace-pre-wrap': { style: { whiteSpace: 'pre-wrap' } },
  'whitespace-nowrap': { style: { whiteSpace: 'nowrap' } },
  'leading-4': { style: { lineHeight: '1rem' } },
  'leading-5': { style: { lineHeight: '1.25rem' } },
  'leading-6': { style: { lineHeight: '1.5rem' } },
  truncate: { style: { overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' } },
  'break-all': { style: { wordBreak: 'break-all' } },
  'no-underline': { style: { textDecoration: 'none' } },
  underline: { style: { textDecoration: 'underline' } },

  // Borders
  border: { style: { border: '1px solid #ddd' } },
  'border-0': { style: { border: 'none' } },
  'border-2': { style: { borderWidth: 2 } },
  'border-b': { style: { borderBottom: '1px solid #e5e7eb' } },
  'border-t': { style: { borderTop: '1px solid #e5e7eb' } },
  'border-l': { style: { borderLeft: '1px solid #e5e7eb' } },
  'border-r': { style: { borderRight: '1px solid #e5e7eb' } },
  'border-l-4': { style: { borderLeftWidth: 4 } },
  'border-b-2': { style: { borderBottomWidth: 2 } },
  'border-dashed': { style: { borderStyle: 'dashed' } },
  'border-solid': { style: { borderStyle: 'solid' } },
  'border-gray-200': { style: { borderColor: '#e5e7eb' } },
  'border-gray-300': { style: { borderColor: '#d1d5db' } },
  'border-blue-200': { style: { borderColor: '#bfdbfe' } },
  'border-blue-300': { style: { borderColor: '#93c5fd' } },
  'border-blue-400': { style: { borderColor: '#60a5fa' } },
  'border-green-200': { style: { borderColor: '#bbf7d0' } },
  'border-red-200': { style: { borderColor: '#fecaca' } },
  'border-red-300': { style: { borderColor: '#fca5a5' } },
  'border-yellow-200': { style: { borderColor: '#fef08a' } },
  'border-yellow-400': { style: { borderColor: '#facc15' } },
  'border-purple-200': { style: { borderColor: '#e9d5ff' } },
  'border-indigo-200': { style: { borderColor: '#c7d2fe' } },
  'border-white': { style: { borderColor: '#fff' } },
  'border-opacity-50': null,

  // Border radius
  rounded: { style: { borderRadius: 4 } },
  'rounded-sm': { style: { borderRadius: 2 } },
  'rounded-md': { style: { borderRadius: 6 } },
  'rounded-lg': { style: { borderRadius: 8 } },
  'rounded-xl': { style: { borderRadius: 12 } },
  'rounded-2xl': { style: { borderRadius: 16 } },
  'rounded-full': { style: { borderRadius: 9999 } },
  'rounded-t': { style: { borderTopLeftRadius: 4, borderTopRightRadius: 4 } },
  'rounded-b': { style: { borderBottomLeftRadius: 4, borderBottomRightRadius: 4 } },
  'rounded-tr-none': { style: { borderTopRightRadius: 0 } },
  'rounded-tl-none': { style: { borderTopLeftRadius: 0 } },

  // Shadow
  shadow: { style: { boxShadow: '0 1px 3px 0 rgba(0,0,0,0.1)' } },
  'shadow-sm': { style: { boxShadow: '0 1px 2px 0 rgba(0,0,0,0.05)' } },
  'shadow-md': { style: { boxShadow: '0 4px 6px -1px rgba(0,0,0,0.1)' } },
  'shadow-lg': { style: { boxShadow: '0 10px 15px -3px rgba(0,0,0,0.1)' } },
  'shadow-xl': { style: { boxShadow: '0 20px 25px -5px rgba(0,0,0,0.1)' } },

  // Opacity
  'opacity-0': { style: { opacity: 0 } },
  'opacity-25': { style: { opacity: 0.25 } },
  'opacity-50': { style: { opacity: 0.5 } },
  'opacity-75': { style: { opacity: 0.75 } },
  'opacity-100': { style: { opacity: 1 } },
  'opacity-30': { style: { opacity: 0.3 } },

  // Cursor
  'cursor-pointer': { style: { cursor: 'pointer' } },
  'cursor-grab': { style: { cursor: 'grab' } },
  'cursor-not-allowed': { style: { cursor: 'not-allowed' } },
  'cursor-grabbing': { style: { cursor: 'grabbing' } },
  'cursor-default': { style: { cursor: 'default' } },
  'resize-none': { style: { resize: 'none' } },
  'select-none': { style: { userSelect: 'none' } },

  // Transition
  'transition-colors': { style: { transitionProperty: 'colors' } },
  'transition-all': { style: { transitionProperty: 'all' } },
  'transition-opacity': { style: { transitionProperty: 'opacity' } },
  'duration-150': { style: { transitionDuration: '150ms' } },
  'duration-200': { style: { transitionDuration: '200ms' } },
  'duration-300': { style: { transitionDuration: '300ms' } },

  // Text
  uppercase: { style: { textTransform: 'uppercase' } },
  lowercase: { style: { textTransform: 'lowercase' } },
  capitalize: { style: { textTransform: 'capitalize' } },
  'tracking-wider': { style: { letterSpacing: '0.05em' } },
  'tracking-wide': { style: { letterSpacing: '0.025em' } },
  'tracking-tight': { style: { letterSpacing: '-0.025em' } },

  // List
  'list-disc': { style: { listStyleType: 'disc' } },
  'list-inside': { style: { listStylePosition: 'inside' } },
  'list-none': { style: { listStyleType: 'none' } },

  // Grid
  'grid-cols-1': { style: { gridTemplateColumns: 'repeat(1, 1fr)' } },
  grid: { style: { display: 'grid' } },

  // Table
  'divide-y': { style: { borderTop: '1px solid #e5e7eb' } },
  'divide-gray-200': { style: { borderColor: '#e5e7eb' } },

  // Transition additional
  'transition-shadow': { style: { transitionProperty: 'box-shadow' } },

  // Font
  'font-mono': { style: { fontFamily: 'ui-monospace, SFMono-Regular, monospace' } },

  // Missing border colors
  'border-yellow-100': { style: { borderColor: '#fef9c3' } },
  'border-orange-100': { style: { borderColor: '#ffedd5' } },
  'border-orange-200': { style: { borderColor: '#fed7aa' } },
  'border-gray-100': { style: { borderColor: '#f3f4f6' } },

  // Missing bg colors
  'bg-orange-50': { style: { backgroundColor: '#fff7ed' } },
  'bg-orange-100': { style: { backgroundColor: '#ffedd5' } },
  'bg-purple-600': { style: { backgroundColor: '#9333ea' } },
  'bg-purple-700': { style: { backgroundColor: '#7e22ce' } },

  // Missing text colors
  'text-orange-700': { style: { color: '#c2410c' } },
  'text-orange-800': { style: { color: '#9a3412' } },
  'text-purple-600': { style: { color: '#9333ea' } },
  'text-purple-700': { style: { color: '#7e22ce' } },

  // animate
  'animate-spin': { classes: ['fb-spinner'], style: {} },
  'animate-pulse': { classes: ['fb-spinner'], style: {} },
  'animate-bounce': { classes: ['fb-spinner'], style: {} },
};

// ============ BOOTSTRAP CLASSES (never modify) ============
const BOOTSTRAP_PREFIXES = [
  'btn', 'label', 'panel', 'breadcrumb', 'container', 'row',
  'text-muted', 'text-primary', 'text-success', 'text-danger', 'text-center', 'text-right', 'text-left',
  'small', 'form-control', 'form-group', 'alert', 'table', 'well', 'badge',
  'list-inline', 'list-unstyled', 'pull-left', 'pull-right',
  'nav', 'navbar', 'dropdown', 'dropdown-menu', 'caret', 'modal', 'close', 'sr-only',
  'input-group', 'glyphicon', 'img-responsive', 'page-header', 'jumbotron', 'progress',
  'help-block', 'list-group',
];

function isBootstrapClass(cls) {
  if (/^col-(xs|sm|md|lg)-\d+$/.test(cls)) return true;
  if (/^col-(xs|sm|md|lg)-(\d+)$/.test(cls)) return true;
  return BOOTSTRAP_PREFIXES.some(p => cls === p || cls.startsWith(p + '-') || cls.startsWith(p + ' '));
}

function isFBClass(cls) {
  return cls.startsWith('fb-');
}

/**
 * Convert a flat list of tokens. Returns { classes: string[], style: object }
 */
function convertTokens(tokens) {
  const outClasses = [];
  const outStyle = {};

  for (const token of tokens) {
    if (!token || !token.trim()) continue;

    // Keep Bootstrap classes
    if (isBootstrapClass(token)) { outClasses.push(token); continue; }
    // Keep fb-* classes
    if (isFBClass(token)) { outClasses.push(token); continue; }

    // Handle responsive variants: strip prefix and convert base
    const respMatch = token.match(/^(sm|md|lg|xl|2xl):(.+)$/);
    if (respMatch) {
      const baseToken = respMatch[2];
      const mapped = TOKEN_MAP[baseToken];
      if (mapped) {
        if (mapped.classes) outClasses.push(...mapped.classes);
        Object.assign(outStyle, mapped.style);
      }
      continue;
    }

    // Handle pseudo-class variants
    const pseudoMatch = token.match(/^(hover|focus|disabled|active|group-hover):(.+)$/);
    if (pseudoMatch) {
      const prefix = pseudoMatch[1];
      const baseToken = pseudoMatch[2];
      if (prefix === 'hover') {
        if (baseToken === 'bg-gray-50') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#f9fafb' };
        else if (baseToken === 'bg-gray-100') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#f3f4f6' };
        else if (baseToken === 'bg-blue-50') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#eff6ff' };
        else if (baseToken === 'bg-blue-700') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#1d4ed8' };
        else if (baseToken === 'bg-green-700') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#15803d' };
        else if (baseToken === 'bg-red-700') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), backgroundColor: '#b91c1c' };
        else if (baseToken === 'text-blue-600' || baseToken === 'text-blue-500' || baseToken === 'text-blue-700') outClasses.push('fb-link');
        else if (baseToken === 'text-gray-700' || baseToken === 'text-gray-800') outClasses.push('fb-link');
        else if (baseToken === 'text-red-500' || baseToken === 'text-red-600') {
          outStyle[':hover'] = { ...(outStyle[':hover'] || {}), color: '#ef4444' };
        }
        else if (baseToken === 'border-blue-300') outStyle[':hover'] = { ...(outStyle[':hover'] || {}), borderColor: '#93c5fd' };
        else {
          const mapped = TOKEN_MAP[baseToken];
          if (mapped) {
            if (mapped.classes) outClasses.push(...mapped.classes);
            Object.assign(outStyle, mapped.style);
          }
        }
      }
      // focus: and disabled: are handled by Bootstrap, skip
      continue;
    }

    // Look up in token map
    const mapped = TOKEN_MAP[token];
    if (mapped) {
      if (mapped.classes) outClasses.push(...mapped.classes);
      if (mapped.style) Object.assign(outStyle, mapped.style);
    } else {
      // Unknown token - could be custom, keep as-is
      outClasses.push(token);
    }
  }

  return { classes: outClasses, style: outStyle };
}

function styleToString(style) {
  if (!style || Object.keys(style).length === 0) return '';
  const pairs = [];
  // Skip pseudo-class keys like ':hover' (not supported in React inline styles)
  const normalKeys = Object.keys(style).filter(k => !k.startsWith(':'));
  for (const key of normalKeys) {
    const val = style[key];
    if (val === undefined || val === null) continue;
    if (typeof val === 'string') pairs.push(`${key}:"${val}"`);
    else pairs.push(`${key}:${val}`);
  }
  return `{${pairs.join(',')}}`;
}

/**
 * Try to match a composite pattern for the entire class string
 */
function matchComposite(classStr) {
  const trimmed = classStr.trim();
  for (const pattern of COMPOSITE_PATTERNS) {
    if (pattern.match.test(trimmed)) {
      return pattern.result;
    }
  }
  return null;
}

/**
 * Process a single file.
 */
function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  let changeCount = 0;

  // === PASS 1: Static className="..." strings ===
  const staticRegex = /className="([^"{}]*?)"/g;
  let match;
  const replacements = [];

  while ((match = staticRegex.exec(content)) !== null) {
    const fullMatch = match[0];
    const classStr = match[1];

    // First try composite pattern
    const composite = matchComposite(classStr);
    if (composite) {
      let replacement = `className="${composite.classes.join(' ')}"`;
      const styleStr = styleToString(composite.style);
      if (styleStr) replacement += ` style={${styleStr}}`;
      replacements.push({ old: fullMatch, new: replacement, idx: match.index });
      continue;
    }

    // Token-by-token conversion
    const tokens = classStr.split(/\s+/).filter(Boolean);
    const hasTailwind = tokens.some(t => {
      if (isBootstrapClass(t) || isFBClass(t)) return false;
      if (/^(sm|md|lg|xl|2xl):/.test(t)) return true;
      if (/^(hover|focus|disabled|active):/.test(t)) return true;
      return t in TOKEN_MAP;
    });

    if (!hasTailwind) continue;

    const result = convertTokens(tokens);
    const newClassStr = result.classes.join(' ') || '';
    const styleStr = result.style && Object.keys(result.style).length > 0 ? styleToString(result.style) : '';

    let replacement = '';
    if (newClassStr) replacement += `className="${newClassStr}"`;
    if (styleStr) {
      if (replacement) replacement += ' ';
      replacement += `style={${styleStr}}`;
    }
    if (!replacement) continue;

    replacements.push({ old: fullMatch, new: replacement, idx: match.index });
  }

  // === PASS 2: Template literals className={`...`} ===
  const templateRegex = /className=\{`([^`]*)`\}/g;
  while ((match = templateRegex.exec(content)) !== null) {
    const fullMatch = match[0];
    const templateContent = match[1];

    // Split by ${...} expressions (handle nested braces)
    const parts = [];
    let remaining = templateContent;
    let lastIdx = 0;
    const exprRegex = /\$\{([^}]*)\}/g;
    let exprMatch;
    while ((exprMatch = exprRegex.exec(templateContent)) !== null) {
      if (exprMatch.index > lastIdx) {
        parts.push({ type: 'text', value: templateContent.slice(lastIdx, exprMatch.index) });
      }
      parts.push({ type: 'expr', value: exprMatch[1] });
      lastIdx = exprMatch.index + exprMatch[0].length;
    }
    if (lastIdx < templateContent.length) {
      parts.push({ type: 'text', value: templateContent.slice(lastIdx) });
    }

    // Convert static text parts
    let hasConversion = false;
    const convertedParts = parts.map(part => {
      if (part.type === 'expr') return part;
      const tokens = part.value.split(/\s+/).filter(Boolean);
      const hasTailwind = tokens.some(t => {
        if (isBootstrapClass(t) || isFBClass(t)) return false;
        if (/^(hover|focus|disabled|active):/.test(t)) return true;
        return t in TOKEN_MAP;
      });
      if (!hasTailwind) return part;
      hasConversion = true;
      const result = convertTokens(tokens);
      return { type: 'converted', classes: result.classes, style: result.style };
    });

    if (!hasConversion) continue;

    // Build new className and style
    const newClassParts = [];
    const allStyle = {};
    let hasDynamicExpr = false;

    for (const part of convertedParts) {
      if (part.type === 'text') {
        newClassParts.push(part.value);
      } else if (part.type === 'expr') {
        newClassParts.push(`\$\{${part.value}\}`);
        hasDynamicExpr = true;
      } else if (part.type === 'converted') {
        if (part.classes.length > 0) newClassParts.push(part.classes.join(' '));
        if (part.style) Object.assign(allStyle, part.style);
      }
    }

    const newClassStr = newClassParts.join(' ').trim();
    const styleStr = Object.keys(allStyle).length > 0 ? styleToString(allStyle) : '';

    let replacement;
    if (hasDynamicExpr) {
      // Keep as template literal
      replacement = `className={\`${newClassStr}\`}`;
      if (styleStr) replacement += ` style={${styleStr}}`;
    } else {
      // Convert to static
      replacement = `className="${newClassStr}"`;
      if (styleStr) replacement += ` style={${styleStr}}`;
    }

    replacements.push({ old: fullMatch, new: replacement, idx: match.index });
  }

  // Apply replacements (process in reverse order to preserve positions)
  replacements.sort((a, b) => a.idx - b.idx);
  let offset = 0;
  for (const r of replacements) {
    const actualIdx = r.idx + offset;
    if (content.slice(actualIdx, actualIdx + r.old.length) !== r.old) {
      // The text shifted, try to find it
      const foundIdx = content.indexOf(r.old, actualIdx - 50);
      if (foundIdx === -1) {
        console.warn(`  ⚠️  Could not find pattern at expected position`);
        continue;
      }
      content = content.slice(0, foundIdx) + r.new + content.slice(foundIdx + r.old.length);
      offset += r.new.length - r.old.length;
    } else {
      content = content.slice(0, actualIdx) + r.new + content.slice(actualIdx + r.old.length);
      offset += r.new.length - r.old.length;
    }
    changeCount++;
  }

  if (changeCount > 0) {
    fs.writeFileSync(filePath, content, 'utf8');
    console.log(`  ✅ ${changeCount} conversions`);
  } else {
    console.log(`  ⏭️  No changes`);
  }

  return changeCount;
}

// Main
const files = process.argv.slice(2);
if (files.length === 0) {
  console.error('Usage: node convert-tailwind.cjs <file1.tsx> ...');
  process.exit(1);
}

console.log(`🔧 Converting ${files.length} files...\n`);
let total = 0;
for (const file of files) {
  console.log(`📄 ${file}`);
  total += processFile(file);
}
console.log(`\n✨ Total: ${total} conversions`);
