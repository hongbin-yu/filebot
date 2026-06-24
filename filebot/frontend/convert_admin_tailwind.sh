#!/bin/bash
# Comprehensive Tailwind → Bootstrap/WET conversion for admin pages
# Process 8 files with ordered sed replacements

set -e

DIR="/home/hongb/.openclaw/workspace/filebot/frontend/src/pages/admin"
FILES=(
  "AdminAppsDashboard.tsx"
  "AdminDocuments.tsx"
  "AdminInstitutions.tsx"
  "AdminTasks.tsx"
  "AdminPathView.tsx"
  "AdminUsers.tsx"
  "AdminUpload.tsx"
  "AdminAppFolders.tsx"
)

cd "$DIR"

for FILE in "${FILES[@]}"; do
  echo "Processing $FILE..."
  cp "$FILE" "$FILE.bak2"
  
  # === PHASE 1: Combined/multi-class patterns (MOST specific first) ===
  
  # Panel patterns (bg-white + rounded-lg + shadow combos)
  sed -i 's`className="bg-white rounded-lg shadow overflow-hidden"`className="panel panel-default" style={{overflow:"hidden"}}`g' "$FILE"
  sed -i 's`className="bg-white rounded-lg shadow p-6"`className="panel panel-default" style={{padding:24}}`g' "$FILE"
  sed -i 's`className="bg-white rounded-lg shadow p-4"`className="panel panel-default" style={{padding:16}}`g' "$FILE"
  sed -i 's`className="bg-white rounded-lg shadow p-8 text-center"`className="panel panel-default text-center" style={{padding:32}}`g' "$FILE"
  sed -i 's`className="bg-white rounded-lg shadow"`className="panel panel-default"`g' "$FILE"
  sed -i 's`className="bg-white rounded-lg shadow-xl w-full max-w-md"`className="panel panel-default" style={{width:"100%",maxWidth:448}}`g' "$FILE"
  
  # Button patterns
  sed -i 's`className="px-4 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"`className="btn btn-primary"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-green-600 text-white rounded hover:bg-green-700"`className="btn btn-success"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700 disabled:opacity-50 disabled:cursor-not-allowed"`className="btn btn-danger" disabled`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-red-600 text-white rounded hover:bg-red-700"`className="btn btn-danger"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-gray-600 text-white rounded hover:bg-gray-700"`className="btn btn-default"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-yellow-600 text-white rounded hover:bg-yellow-700"`className="btn btn-warning"`g' "$FILE"
  sed -i 's`className="px-4 py-2 border border-gray-300 rounded hover:bg-gray-50"`className="btn btn-default"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-blue-600 text-white rounded-md hover:bg-blue-700"`className="btn btn-primary"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-red-600 text-white rounded-md hover:bg-red-700"`className="btn btn-danger"`g' "$FILE"
  sed -i 's`className="px-4 py-2 bg-green-600 text-white rounded-md hover:bg-green-700"`className="btn btn-success"`g' "$FILE"
  sed -i 's`className="px-3 py-2 bg-blue-600 text-white rounded hover:bg-blue-700"`className="btn btn-primary" style={{padding:"8px 12px"}}`g' "$FILE"
  
  # State cards (colored backgrounds with borders)
  sed -i 's`className="bg-red-50 border border-red-200 rounded-lg p-6 text-center"`className="text-center" style={{background:"#fef2f2",border:"1px solid #fecaca",borderRadius:8,padding:24}}`g' "$FILE"
  sed -i 's`className="bg-yellow-50 border border-yellow-200 rounded-lg p-6 text-center"`className="text-center" style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:24}}`g' "$FILE"
  sed -i 's`className="bg-yellow-50 border border-yellow-200 rounded-lg p-8 text-center"`className="text-center" style={{background:"#fefce8",border:"1px solid #fef08a",borderRadius:8,padding:32}}`g' "$FILE"
  sed -i 's`className="bg-blue-50 border border-blue-200 rounded-lg p-6 text-center"`className="text-center" style={{background:"#eff6ff",border:"1px solid #bfdbfe",borderRadius:8,padding:24}}`g' "$FILE"
  sed -i 's`className="bg-green-50 border border-green-200 rounded-lg p-6 text-center"`className="text-center" style={{background:"#f0fdf4",border:"1px solid #bbf7d0",borderRadius:8,padding:24}}`g' "$FILE"
  
  # Form inputs
  sed -i 's`className="w-full px-3 py-2 border border-gray-300 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent"`className="form-control"`g' "$FILE"
  sed -i 's`className="w-full px-3 py-2 border border-gray-300 rounded focus:outline-none focus:ring-2 focus:ring-blue-500"`className="form-control"`g' "$FILE"
  
  # Spinner patterns
  sed -i 's`className="inline-block animate-spin rounded-full h-12 w-12 border-b-2 border-blue-600"`className="fb-spinner" style={{borderWidth:2,borderColor:"#2563eb",height:48,width:48,borderRadius:"50%"}}`g' "$FILE"
  sed -i 's`className="inline-block animate-spin rounded-full h-4 w-4 border-b-2 border-white mr-2"`className="fb-spinner" style={{borderWidth:2,borderColor:"#ffffff",height:16,width:16,borderRadius:"50%",marginRight:8}}`g' "$FILE"
  sed -i 's`className="animate-spin rounded-full h-8 w-8 border-b-2 border-blue-600"`className="fb-spinner" style={{borderWidth:2,borderColor:"#2563eb",height:32,width:32,borderRadius:"50%"}}`g' "$FILE"
  sed -i 's`className="animate-spin rounded-full h-5 w-5 border-b-2 border-blue-600"`className="fb-spinner" style={{borderWidth:2,borderColor:"#2563eb",height:20,width:20,borderRadius:"50%"}}`g' "$FILE"
  sed -i 's`className="animate-spin rounded-full h-6 w-6 border-b-2 border-blue-600"`className="fb-spinner" style={{borderWidth:2,borderColor:"#2563eb",height:24,width:24,borderRadius:"50%"}}`g' "$FILE"
  sed -i 's`className="animate-spin rounded-full h-4 w-4 border-b-2 border-white"`className="fb-spinner" style={{borderWidth:2,borderColor:"#ffffff",height:16,width:16,borderRadius:"50%"}}`g' "$FILE"
  sed -i 's`className="animate-spin rounded-full h-4 w-4 border-b-2 border-blue-600"`className="fb-spinner" style={{borderWidth:2,borderColor:"#2563eb",height:16,width:16,borderRadius:"50%"}}`g' "$FILE"
  
  # Loading states
  sed -i 's`className="flex justify-center items-center h-64"`className="fb-d-flex fb-justify-center fb-align-center" style={{height:256}}`g' "$FILE"
  
  # Typography combos
  sed -i 's`className="text-2xl font-bold text-gray-800"`style={{fontSize:"1.5rem",fontWeight:700,color:"#1f2937"}}`g' "$FILE"
  sed -i 's`className="text-xl font-bold text-gray-800"`style={{fontSize:"1.25rem",fontWeight:700,color:"#1f2937"}}`g' "$FILE"
  sed -i 's`className="text-lg font-semibold text-gray-800"`style={{fontSize:"1.125rem",fontWeight:600,color:"#1f2937"}}`g' "$FILE"
  sed -i 's`className="text-sm text-gray-500"`className="text-muted" style={{fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="text-xs text-gray-500"`className="text-muted" style={{fontSize:"0.75rem"}}`g' "$FILE"
  sed -i 's`className="text-sm font-medium"`style={{fontSize:"0.875rem",fontWeight:500}}`g' "$FILE"
  sed -i 's`className="text-lg font-medium text-gray-900 mb-2"`className="fb-label" style={{fontSize:"1.125rem",marginBottom:8}}`g' "$FILE"
  sed -i 's`className="text-lg font-medium text-gray-900 mb-4"`className="fb-label" style={{fontSize:"1.125rem",marginBottom:16}}`g' "$FILE"
  sed -i 's`className="text-lg font-medium text-blue-600 hover:text-blue-800"`className="fb-link" style={{fontSize:"1.125rem",fontWeight:500,color:"#2563eb"}}`g' "$FILE"
  sed -i 's`className="text-lg font-medium text-red-800 mb-2"`style={{fontSize:"1.125rem",fontWeight:500,color:"#991b1b",marginBottom:8}}`g' "$FILE"
  sed -i 's`className="text-lg font-medium text-yellow-800 mb-2"`style={{fontSize:"1.125rem",fontWeight:500,color:"#854d0e",marginBottom:8}}`g' "$FILE"
  sed -i 's`className="text-lg font-semibold"`style={{fontSize:"1.125rem",fontWeight:600}}`g' "$FILE"
  sed -i 's`className="text-blue-600 hover:text-blue-800 text-sm"`className="fb-link" style={{fontSize:"0.875rem",color:"#2563eb"}}`g' "$FILE"
  sed -i 's`className="text-red-600 hover:text-red-800 text-sm"`className="fb-link" style={{fontSize:"0.875rem",color:"#dc2626"}}`g' "$FILE"
  sed -i 's`className="text-red-600 hover:text-red-800"`className="fb-link" style={{color:"#dc2626"}}`g' "$FILE"
  sed -i 's`className="text-emerald-600 hover:text-emerald-800 text-sm font-medium bg-transparent border-0 p-0 cursor-pointer"`className="fb-link" style={{fontSize:"0.875rem",fontWeight:500,color:"#059669",background:"transparent",border:"none",padding:0,cursor:"pointer"}}`g' "$FILE"
  
  # Special - color badge pills
  sed -i 's`className="px-3 py-1 bg-blue-100 text-blue-800 rounded-full text-sm hover:bg-blue-200 focus:outline-none focus:ring-2 focus:ring-blue-300"`className="fb-badge fb-badge-blue fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-3 py-1 bg-red-100 text-red-800 rounded-full text-sm hover:bg-red-200 focus:outline-none focus:ring-2 focus:ring-red-300"`className="fb-badge fb-badge-red fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-3 py-1 bg-purple-100 text-purple-800 rounded-full text-sm hover:bg-purple-200"`className="fb-badge fb-badge-purple fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-3 py-1 bg-green-100 text-green-800 rounded-full text-sm hover:bg-green-200"`className="fb-badge fb-badge-green fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-3 py-1 bg-yellow-100 text-yellow-800 rounded-full text-sm hover:bg-yellow-200"`className="fb-badge fb-badge-yellow fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-3 py-1 bg-gray-100 text-gray-800 rounded-full text-sm hover:bg-gray-200"`className="fb-badge fb-badge-gray fb-hover-btn" style={{padding:"4px 12px",borderRadius:"50%",fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="px-2 py-1 text-xs font-medium bg-gray-100 text-gray-800 rounded"`className="badge" style={{padding:"4px 8px",fontSize:"0.75rem",fontWeight:500,background:"#f3f4f6",color:"#1f2937",borderRadius:4}}`g' "$FILE"
  
  # Special - modal overlay
  sed -i 's`className="fixed inset-0 bg-gray-500 bg-opacity-75 flex items-center justify-center z-50 p-4"`className="fb-d-flex fb-align-center fb-justify-center" style={{position:"fixed",top:0,right:0,bottom:0,left:0,background:"rgba(107,114,128,0.75)",zIndex:50,padding:16}}`g' "$FILE"
  
  # flex justify-between items-center
  sed -i 's`className="flex justify-between items-center mb-6"`className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:24}}`g' "$FILE"
  sed -i 's`className="flex justify-between items-center mb-4"`className="fb-d-flex fb-justify-between fb-align-center" style={{marginBottom:16}}`g' "$FILE"
  sed -i 's`className="flex justify-between items-center"`className="fb-d-flex fb-justify-between fb-align-center"`g' "$FILE"
  
  # flex items-center combos
  sed -i 's`className="flex items-center space-x-2 text-sm text-gray-500 mb-2"`className="fb-d-flex fb-align-center text-muted" style={{gap:8,fontSize:"0.875rem",marginBottom:8}}`g' "$FILE"
  sed -i 's`className="flex items-center mb-4"`className="fb-d-flex fb-align-center" style={{marginBottom:16}}`g' "$FILE"
  sed -i 's`className="flex items-center"`className="fb-d-flex fb-align-center"`g' "$FILE"
  
  # flex space-x combos
  sed -i 's`className="flex space-x-2"`className="fb-d-flex fb-gap-1"`g' "$FILE"
  sed -i 's`className="flex space-x-3"`className="fb-d-flex fb-gap-2"`g' "$FILE"
  sed -i 's`className="flex justify-center space-x-3"`className="fb-d-flex fb-justify-center fb-gap-2"`g' "$FILE"
  sed -i 's`className="flex justify-end space-x-3 mt-6"`className="fb-d-flex fb-justify-end fb-gap-2" style={{marginTop:24}}`g' "$FILE"
  
  # Grid patterns
  sed -i 's`className="grid grid-cols-1 md:grid-cols-4 gap-4 mb-6"`className="row" style={{marginBottom:24}}`g' "$FILE"
  sed -i 's`className="grid grid-cols-2 gap-4"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 gap-6"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-3 gap-4"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 md:grid-cols-2 gap-4"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 md:grid-cols-3 lg:grid-cols-4 gap-6"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 md:grid-cols-3 gap-6"`className="row"`g' "$FILE"
  sed -i 's`className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6"`className="row"`g' "$FILE"
  
  # hover:text-blue → fb-link
  sed -i 's`className="hover:text-blue-600"`className="fb-link"`g' "$FILE"
  sed -i 's`className="hover:bg-gray-50"`className="fb-hover-btn"`g' "$FILE"
  sed -i 's`className="hover:bg-gray-100"`className="fb-hover-btn"`g' "$FILE"
  
  # Misc combined patterns
  sed -i 's`className="mt-8 p-4 bg-blue-50 rounded-lg"`style={{marginTop:32,padding:16,background:"#eff6ff",borderRadius:8}}`g' "$FILE"
  sed -i 's`className="p-4 hover:bg-gray-50"`className="fb-hover-btn" style={{padding:16}}`g' "$FILE"
  sed -i 's`className="p-4 border-b"`style={{padding:16,borderBottom:"1px solid #e5e7eb"}}`g' "$FILE"
  sed -i 's`className="p-6 border-t"`style={{padding:24,borderTop:"1px solid #e5e7eb"}}`g' "$FILE"
  sed -i 's`className="block text-sm font-medium text-gray-700 mb-1"`className="fb-label" style={{display:"block",fontSize:"0.875rem",marginBottom:4}}`g' "$FILE"
  
  # === PHASE 2: Individual class patterns ===
  
  # Text colors
  sed -i 's`className="text-gray-900"`style={{color:"#111827"}}`g' "$FILE"
  sed -i 's`className="text-gray-800"`style={{color:"#1f2937"}}`g' "$FILE"
  sed -i 's`className="text-gray-700"`style={{color:"#374151"}}`g' "$FILE"
  sed -i 's`className="text-gray-600"`className="text-muted"`g' "$FILE"
  sed -i 's`className="text-gray-500"`className="text-muted"`g' "$FILE"
  sed -i 's`className="text-gray-400"`style={{color:"#9ca3af"}}`g' "$FILE"
  sed -i 's`className="text-gray-300"`style={{color:"#d1d5db"}}`g' "$FILE"
  sed -i 's`className="text-blue-600"`style={{color:"#2563eb"}}`g' "$FILE"
  sed -i 's`className="text-blue-700"`style={{color:"#1d4ed8"}}`g' "$FILE"
  sed -i 's`className="text-blue-800"`style={{color:"#1e40af"}}`g' "$FILE"
  sed -i 's`className="text-red-600"`style={{color:"#dc2626"}}`g' "$FILE"
  sed -i 's`className="text-red-700"`style={{color:"#b91c1c"}}`g' "$FILE"
  sed -i 's`className="text-red-800"`style={{color:"#991b1b"}}`g' "$FILE"
  sed -i 's`className="text-green-600"`style={{color:"#16a34a"}}`g' "$FILE"
  sed -i 's`className="text-green-700"`style={{color:"#15803d"}}`g' "$FILE"
  sed -i 's`className="text-green-800"`style={{color:"#166534"}}`g' "$FILE"
  sed -i 's`className="text-yellow-600"`style={{color:"#ca8a04"}}`g' "$FILE"
  sed -i 's`className="text-yellow-700"`style={{color:"#a16207"}}`g' "$FILE"
  sed -i 's`className="text-yellow-800"`style={{color:"#854d0e"}}`g' "$FILE"
  sed -i 's`className="text-purple-600"`style={{color:"#9333ea"}}`g' "$FILE"
  sed -i 's`className="text-purple-700"`style={{color:"#7e22ce"}}`g' "$FILE"
  sed -i 's`className="text-purple-800"`style={{color:"#6b21a8"}}`g' "$FILE"
  sed -i 's`className="text-indigo-600"`style={{color:"#4f46e5"}}`g' "$FILE"
  sed -i 's`className="text-white"`style={{color:"#ffffff"}}`g' "$FILE"
  sed -i 's`className="text-black"`style={{color:"#000000"}}`g' "$FILE"
  
  # Font weights (standalone)
  sed -i 's`className="font-bold"`style={{fontWeight:700}}`g' "$FILE"
  sed -i 's`className="font-semibold"`style={{fontWeight:600}}`g' "$FILE"
  sed -i 's`className="font-medium"`style={{fontWeight:500}}`g' "$FILE"
  sed -i 's`className="font-normal"`style={{fontWeight:400}}`g' "$FILE"
  sed -i 's`className="font-light"`style={{fontWeight:300}}`g' "$FILE"
  
  # Font sizes
  sed -i 's`className="text-xs"`style={{fontSize:"0.75rem"}}`g' "$FILE"
  sed -i 's`className="text-sm"`style={{fontSize:"0.875rem"}}`g' "$FILE"
  sed -i 's`className="text-base"`style={{fontSize:"1rem"}}`g' "$FILE"
  sed -i 's`className="text-lg"`style={{fontSize:"1.125rem"}}`g' "$FILE"
  sed -i 's`className="text-xl"`style={{fontSize:"1.25rem"}}`g' "$FILE"
  sed -i 's`className="text-2xl"`style={{fontSize:"1.5rem"}}`g' "$FILE"
  sed -i 's`className="text-3xl"`style={{fontSize:"1.875rem"}}`g' "$FILE"
  
  # Spacing
  sed -i 's`className="m-0"`style={{margin:0}}`g' "$FILE"
  sed -i 's`className="mx-auto"`style={{marginLeft:"auto",marginRight:"auto"}}`g' "$FILE"
  sed -i 's`className="ml-auto"`style={{marginLeft:"auto"}}`g' "$FILE"
  sed -i 's`className="mr-auto"`style={{marginRight:"auto"}}`g' "$FILE"
  sed -i 's`className="mt-1"`style={{marginTop:4}}`g' "$FILE"
  sed -i 's`className="mt-2"`style={{marginTop:8}}`g' "$FILE"
  sed -i 's`className="mt-4"`style={{marginTop:16}}`g' "$FILE"
  sed -i 's`className="mt-6"`style={{marginTop:24}}`g' "$FILE"
  sed -i 's`className="mt-8"`style={{marginTop:32}}`g' "$FILE"
  sed -i 's`className="mb-1"`style={{marginBottom:4}}`g' "$FILE"
  sed -i 's`className="mb-2"`style={{marginBottom:8}}`g' "$FILE"
  sed -i 's`className="mb-4"`style={{marginBottom:16}}`g' "$FILE"
  sed -i 's`className="mb-6"`style={{marginBottom:24}}`g' "$FILE"
  sed -i 's`className="mb-8"`style={{marginBottom:32}}`g' "$FILE"
  sed -i 's`className="ml-1"`style={{marginLeft:4}}`g' "$FILE"
  sed -i 's`className="ml-2"`style={{marginLeft:8}}`g' "$FILE"
  sed -i 's`className="ml-4"`style={{marginLeft:16}}`g' "$FILE"
  sed -i 's`className="mr-1"`style={{marginRight:4}}`g' "$FILE"
  sed -i 's`className="mr-2"`style={{marginRight:8}}`g' "$FILE"
  sed -i 's`className="mr-4"`style={{marginRight:16}}`g' "$FILE"
  sed -i 's`className="p-0"`style={{padding:0}}`g' "$FILE"
  sed -i 's`className="p-1"`style={{padding:4}}`g' "$FILE"
  sed -i 's`className="p-2"`style={{padding:8}}`g' "$FILE"
  sed -i 's`className="p-3"`style={{padding:12}}`g' "$FILE"
  sed -i 's`className="p-4"`style={{padding:16}}`g' "$FILE"
  sed -i 's`className="p-6"`style={{padding:24}}`g' "$FILE"
  sed -i 's`className="p-8"`style={{padding:32}}`g' "$FILE"
  sed -i 's`className="px-1"`style={{paddingLeft:4,paddingRight:4}}`g' "$FILE"
  sed -i 's`className="px-2"`style={{paddingLeft:8,paddingRight:8}}`g' "$FILE"
  sed -i 's`className="px-3"`style={{paddingLeft:12,paddingRight:12}}`g' "$FILE"
  sed -i 's`className="px-4"`style={{paddingLeft:16,paddingRight:16}}`g' "$FILE"
  sed -i 's`className="px-6"`style={{paddingLeft:24,paddingRight:24}}`g' "$FILE"
  sed -i 's`className="py-1"`style={{paddingTop:4,paddingBottom:4}}`g' "$FILE"
  sed -i 's`className="py-2"`style={{paddingTop:8,paddingBottom:8}}`g' "$FILE"
  sed -i 's`className="py-3"`style={{paddingTop:12,paddingBottom:12}}`g' "$FILE"
  sed -i 's`className="py-4"`style={{paddingTop:16,paddingBottom:16}}`g' "$FILE"
  sed -i 's`className="py-12"`className="text-center" style={{paddingTop:48,paddingBottom:48}}`g' "$FILE"
  
  # Width/Height standalones
  sed -i 's`className="w-full"`style={{width:"100%"}}`g' "$FILE"
  sed -i 's`className="w-16"`style={{width:64}}`g' "$FILE"
  sed -i 's`className="w-12"`style={{width:48}}`g' "$FILE"
  sed -i 's`className="w-10"`style={{width:40}}`g' "$FILE"
  sed -i 's`className="w-8"`style={{width:32}}`g' "$FILE"
  sed -i 's`className="w-6"`style={{width:24}}`g' "$FILE"
  sed -i 's`className="w-5"`style={{width:20}}`g' "$FILE"
  sed -i 's`className="w-4"`style={{width:16}}`g' "$FILE"
  sed -i 's`className="h-16"`style={{height:64}}`g' "$FILE"
  sed -i 's`className="h-12"`style={{height:48}}`g' "$FILE"
  sed -i 's`className="h-10"`style={{height:40}}`g' "$FILE"
  sed -i 's`className="h-8"`style={{height:32}}`g' "$FILE"
  sed -i 's`className="h-6"`style={{height:24}}`g' "$FILE"
  sed -i 's`className="h-5"`style={{height:20}}`g' "$FILE"
  sed -i 's`className="h-4"`style={{height:16}}`g' "$FILE"
  sed -i 's`className="h-64"`style={{height:256}}`g' "$FILE"
  sed -i 's`className="min-h-screen"`style={{minHeight:"100vh"}}`g' "$FILE"
  sed -i 's`className="min-w-full"`style={{minWidth:"100%"}}`g' "$FILE"
  sed -i 's`className="max-w-7xl"`style={{maxWidth:1280}}`g' "$FILE"
  sed -i 's`className="max-w-3xl"`style={{maxWidth:768}}`g' "$FILE"
  sed -i 's`className="max-w-md"`style={{maxWidth:448}}`g' "$FILE"
  sed -i 's`className="max-w-sm"`style={{maxWidth:384}}`g' "$FILE"
  sed -i 's`className="max-w-lg"`style={{maxWidth:512}}`g' "$FILE"
  sed -i 's`className="max-w-xl"`style={{maxWidth:576}}`g' "$FILE"
  sed -i 's`className="max-w-2xl"`style={{maxWidth:672}}`g' "$FILE"
  
  # Border radius
  sed -i 's`className="rounded-lg"`style={{borderRadius:8}}`g' "$FILE"
  sed -i 's`className="rounded-md"`style={{borderRadius:6}}`g' "$FILE"
  sed -i 's`className="rounded"`style={{borderRadius:4}}`g' "$FILE"
  sed -i 's`className="rounded-full"`style={{borderRadius:"50%"}}`g' "$FILE"
  
  # Shadows (standalone)
  sed -i 's`className="shadow"`style={{boxShadow:"0 1px 3px 0 rgba(0,0,0,0.1)"}}`g' "$FILE"
  sed -i 's`className="shadow-md"`style={{boxShadow:"0 4px 6px -1px rgba(0,0,0,0.1)"}}`g' "$FILE"
  sed -i 's`className="shadow-lg"`style={{boxShadow:"0 10px 15px -3px rgba(0,0,0,0.1)"}}`g' "$FILE"
  sed -i 's`className="shadow-sm"`style={{boxShadow:"0 1px 2px 0 rgba(0,0,0,0.05)"}}`g' "$FILE"
  
  # Backgrounds
  sed -i 's`className="bg-white"`style={{background:"#ffffff"}}`g' "$FILE"
  sed -i 's`className="bg-gray-50"`style={{background:"#f9fafb"}}`g' "$FILE"
  sed -i 's`className="bg-gray-100"`style={{background:"#f3f4f6"}}`g' "$FILE"
  sed -i 's`className="bg-gray-200"`style={{background:"#e5e7eb"}}`g' "$FILE"
  sed -i 's`className="bg-gray-500"`style={{background:"#6b7280"}}`g' "$FILE"
  sed -i 's`className="bg-gray-800"`style={{background:"#1f2937"}}`g' "$FILE"
  sed -i 's`className="bg-blue-50"`style={{background:"#eff6ff"}}`g' "$FILE"
  sed -i 's`className="bg-blue-100"`style={{background:"#dbeafe"}}`g' "$FILE"
  sed -i 's`className="bg-blue-600"`style={{background:"#2563eb"}}`g' "$FILE"
  sed -i 's`className="bg-red-50"`style={{background:"#fef2f2"}}`g' "$FILE"
  sed -i 's`className="bg-red-100"`style={{background:"#fee2e2"}}`g' "$FILE"
  sed -i 's`className="bg-red-600"`style={{background:"#dc2626"}}`g' "$FILE"
  sed -i 's`className="bg-green-50"`style={{background:"#f0fdf4"}}`g' "$FILE"
  sed -i 's`className="bg-green-100"`style={{background:"#dcfce7"}}`g' "$FILE"
  sed -i 's`className="bg-green-600"`style={{background:"#16a34a"}}`g' "$FILE"
  sed -i 's`className="bg-yellow-50"`style={{background:"#fefce8"}}`g' "$FILE"
  sed -i 's`className="bg-yellow-100"`style={{background:"#fef9c3"}}`g' "$FILE"
  sed -i 's`className="bg-yellow-600"`style={{background:"#ca8a04"}}`g' "$FILE"
  sed -i 's`className="bg-purple-100"`style={{background:"#f3e8ff"}}`g' "$FILE"
  sed -i 's`className="bg-purple-600"`style={{background:"#9333ea"}}`g' "$FILE"
  sed -i 's`className="bg-indigo-600"`style={{background:"#4f46e5"}}`g' "$FILE"
  sed -i 's`className="bg-indigo-100"`style={{background:"#e0e7ff"}}`g' "$FILE"
  sed -i 's`className="bg-transparent"`style={{background:"transparent"}}`g' "$FILE"
  
  # Opacity
  sed -i 's`className="bg-opacity-75"`style={{opacity:0.75}}`g' "$FILE"
  
  # Borders
  sed -i 's`className="border"`style={{border:"1px solid #e5e7eb"}}`g' "$FILE"
  sed -i 's`className="border-0"`style={{border:"none"}}`g' "$FILE"
  sed -i 's`className="border-b"`style={{borderBottom:"1px solid #e5e7eb"}}`g' "$FILE"
  sed -i 's`className="border-t"`style={{borderTop:"1px solid #e5e7eb"}}`g' "$FILE"
  sed -i 's`className="border-gray-200"`style={{borderColor:"#e5e7eb"}}`g' "$FILE"
  sed -i 's`className="border-gray-300"`style={{borderColor:"#d1d5db"}}`g' "$FILE"
  sed -i 's`className="border-red-200"`style={{borderColor:"#fecaca"}}`g' "$FILE"
  sed -i 's`className="border-red-300"`style={{borderColor:"#fca5a5"}}`g' "$FILE"
  sed -i 's`className="border-yellow-200"`style={{borderColor:"#fef08a"}}`g' "$FILE"
  sed -i 's`className="border-blue-200"`style={{borderColor:"#bfdbfe"}}`g' "$FILE"
  sed -i 's`className="border-green-200"`style={{borderColor:"#bbf7d0"}}`g' "$FILE"
  sed -i 's`className="border-orange-200"`style={{borderColor:"#fed7aa"}}`g' "$FILE"
  
  # Divide
  sed -i 's`className="divide-y"`className="fb-divide-y"`g' "$FILE"
  sed -i 's` fb-divide-y divide-gray-200` fb-divide-y`g' "$FILE"
  
  # Flex/grid other
  sed -i 's`className="flex-col"`className="fb-d-flex" style={{flexDirection:"column"}}`g' "$FILE"
  sed -i 's`className="flex-wrap"`style={{flexWrap:"wrap"}}`g' "$FILE"
  sed -i 's`className="flex-1"`style={{flex:1}}`g' "$FILE"
  sed -i 's`className="flex-shrink-0"`style={{flexShrink:0}}`g' "$FILE"
  sed -i 's`className="shrink-0"`style={{flexShrink:0}}`g' "$FILE"
  sed -i 's`className="justify-end"`className="fb-justify-end"`g' "$FILE"
  sed -i 's`className="justify-center"`className="fb-justify-center"`g' "$FILE"
  
  # Overflow
  sed -i 's`className="overflow-hidden"`style={{overflow:"hidden"}}`g' "$FILE"
  sed -i 's`className="overflow-auto"`style={{overflow:"auto"}}`g' "$FILE"
  sed -i 's`className="overflow-x-auto"`style={{overflowX:"auto"}}`g' "$FILE"
  sed -i 's`className="overflow-y-auto"`style={{overflowY:"auto"}}`g' "$FILE"
  
  # Whitespace & truncate
  sed -i 's`className="whitespace-nowrap"`style={{whiteSpace:"nowrap"}}`g' "$FILE"
  sed -i 's`className="truncate"`style={{overflow:"hidden",textOverflow:"ellipsis",whiteSpace:"nowrap"}}`g' "$FILE"
  
  # Gap standalone
  sed -i 's`className="gap-2"`style={{gap:8}}`g' "$FILE"
  sed -i 's`className="gap-4"`style={{gap:16}}`g' "$FILE"
  sed -i 's`className="gap-6"`style={{gap:24}}`g' "$FILE"
  sed -i 's`className="gap-8"`style={{gap:32}}`g' "$FILE"
  
  # Space-y
  sed -i 's`className="space-y-1"`className="fb-space-y" style={{gap:4}}`g' "$FILE"
  sed -i 's`className="space-y-2"`className="fb-space-y" style={{gap:8}}`g' "$FILE"
  sed -i 's`className="space-y-3"`className="fb-space-y" style={{gap:12}}`g' "$FILE"
  sed -i 's`className="space-y-4"`className="fb-space-y" style={{gap:16}}`g' "$FILE"
  sed -i 's`className="space-y-6"`className="fb-space-y" style={{gap:24}}`g' "$FILE"
  sed -i 's`className="space-x-4"`className="fb-space-x" style={{gap:16}}`g' "$FILE"
  
  # Transition
  sed -i 's`className="transition-colors"`style={{transition:"color, background-color, border-color 0.2s ease"}}`g' "$FILE"
  sed -i 's`className="transition"`style={{transition:"all 0.2s ease"}}`g' "$FILE"
  sed -i 's`className="duration-200"`style={{transitionDuration:"200ms"}}`g' "$FILE"
  sed -i 's`className="duration-300"`style={{transitionDuration:"300ms"}}`g' "$FILE"
  
  # Tracking
  sed -i 's`className="tracking-wider"`style={{letterSpacing:"0.05em"}}`g' "$FILE"
  sed -i 's`className="tracking-wide"`style={{letterSpacing:"0.025em"}}`g' "$FILE"
  sed -i 's`className="tracking-tight"`style={{letterSpacing:"-0.025em"}}`g' "$FILE"
  
  # Leading
  sed -i 's`className="leading-tight"`style={{lineHeight:"1.25"}}`g' "$FILE"
  sed -i 's`className="leading-normal"`style={{lineHeight:"1.5"}}`g' "$FILE"
  
  # Cursor
  sed -i 's`className="cursor-pointer"`style={{cursor:"pointer"}}`g' "$FILE"
  sed -i 's`className="cursor-not-allowed"`style={{cursor:"not-allowed"}}`g' "$FILE"
  
  # Animation
  sed -i 's`className="animate-spin"`className="fb-spinner"`g' "$FILE"
  sed -i 's`className="animate-pulse"`className="fb-pulse"`g' "$FILE"
  
  # Order
  sed -i 's`className="order-first"`style={{order:-9999}}`g' "$FILE"
  sed -i 's`className="order-last"`style={{order:9999}}`g' "$FILE"
  sed -i 's`className="order-1"`style={{order:1}}`g' "$FILE"
  sed -i 's`className="order-2"`style={{order:2}}`g' "$FILE"
  
  # Positioning
  sed -i 's`className="relative"`style={{position:"relative"}}`g' "$FILE"
  sed -i 's`className="absolute"`style={{position:"absolute"}}`g' "$FILE"
  sed -i 's`className="fixed"`style={{position:"fixed"}}`g' "$FILE"
  sed -i 's`className="inset-0"`style={{position:"absolute",top:0,right:0,bottom:0,left:0}}`g' "$FILE"
  
  # Display
  sed -i 's`className="inline-block"`style={{display:"inline-block"}}`g' "$FILE"
  sed -i 's`className="inline-flex"`style={{display:"inline-flex"}}`g' "$FILE"
  sed -i 's`className="block"`style={{display:"block"}}`g' "$FILE"
  sed -i 's`className="hidden"`style={{display:"none"}}`g' "$FILE"
  
  # Justify-self
  sed -i 's`className="justify-self-end"`style={{justifySelf:"end"}}`g' "$FILE"
  
  # Object-fit
  sed -i 's`className="object-cover"`style={{objectFit:"cover"}}`g' "$FILE"
  sed -i 's`className="object-contain"`style={{objectFit:"contain"}}`g' "$FILE"
  
  # Vertical align
  sed -i 's`className="align-middle"`style={{verticalAlign:"middle"}}`g' "$FILE"
  
  # Col-span
  sed -i 's`className="col-span-2"`className="col-lg-2"`g' "$FILE"
  sed -i 's`className="col-span-3"`className="col-lg-3"`g' "$FILE"
  sed -i 's`className="col-span-full"`style={{gridColumn:"1 / -1"}}`g' "$FILE"
  
  # Border-width
  sed -i 's`className="border-2"`style={{borderWidth:2}}`g' "$FILE"
  sed -i 's`className="border-b-2"`style={{borderBottomWidth:2}}`g' "$FILE"
  sed -i 's`className="border-t-2"`style={{borderTopWidth:2}}`g' "$FILE"
  
  # Border styles
  sed -i 's`className="border-dashed"`style={{borderStyle:"dashed"}}`g' "$FILE"
  
  # Text decoration
  sed -i 's`className="underline"`style={{textDecoration:"underline"}}`g' "$FILE"
  sed -i 's`className="underline-offset-2"`style={{textUnderlineOffset:2}}`g' "$FILE"
  sed -i 's`className="underline-offset-4"`style={{textUnderlineOffset:4}}`g' "$FILE"
  
  # Uppercase
  sed -i 's`className="uppercase"`style={{textTransform:"uppercase"}}`g' "$FILE"
  sed -i 's`className="capitalize"`style={{textTransform:"capitalize"}}`g' "$FILE"
  
  # Opacity standalone
  sed -i 's`className="opacity-50"`style={{opacity:0.5}}`g' "$FILE"
  sed -i 's`className="opacity-75"`style={{opacity:0.75}}`g' "$FILE"
  
  # Invisible
  sed -i 's`className="invisible"`style={{visibility:"hidden"}}`g' "$FILE"
  
  # Z-index
  sed -i 's`className="z-10"`style={{zIndex:10}}`g' "$FILE"
  sed -i 's`className="z-50"`style={{zIndex:50}}`g' "$FILE"
  
  # Select-none
  sed -i 's`className="select-none"`style={{userSelect:"none"}}`g' "$FILE"
  
  # Pointer events
  sed -i 's`className="pointer-events-none"`style={{pointerEvents:"none"}}`g' "$FILE"
  
  # List style
  sed -i 's`className="list-none"`style={{listStyle:"none"}}`g' "$FILE"
  
  # Ring (shadow replacement)
  sed -i 's`className="ring-2"`style={{boxShadow:"0 0 0 2px rgba(59,130,246,0.5)"}}`g' "$FILE"
  sed -i 's`className="ring-1 ring-gray-200"`style={{boxShadow:"0 0 0 1px rgba(229,231,235,1)"}}`g' "$FILE"
  
  # Now handle remaining combined patterns that might have been created by individual conversions
  # Fix: className="text-muted" style={{...}} → merge (don't duplicate)
  # Fix: className="text-muted" style={{marginTop:4}} → should just be combined
  
  # SR-only
  sed -i 's`className="sr-only"`className="sr-only"`g' "$FILE"
  
  echo "  ✅ Done $FILE"
done

echo ""
echo "All files processed. Checking for remaining Tailwind patterns..."
