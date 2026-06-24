#!/usr/bin/env node
/**
 * Post-process: merge duplicate style={{}} attributes on the same line
 */
const fs = require('fs');

function mergeStyles(line) {
  // Pattern: style={{...}} style={{...}} → style={{...,...}}
  let modified = line;
  // Match consecutive style={{{...}}} style={{{...}}}
  const regex = /style=\{\{(.+?)\}\}\s+style=\{\{(.+?)\}\}/g;
  let changed = true;
  while (changed) {
    changed = false;
    modified = modified.replace(regex, (match, s1, s2) => {
      changed = true;
      return `style={{${s1},${s2}}}`;
    });
  }
  return modified;
}

function processFile(filePath) {
  let content = fs.readFileSync(filePath, 'utf8');
  const lines = content.split('\n');
  let count = 0;
  for (let i = 0; i < lines.length; i++) {
    const newLine = mergeStyles(lines[i]);
    if (newLine !== lines[i]) {
      lines[i] = newLine;
      count++;
    }
  }
  if (count > 0) {
    fs.writeFileSync(filePath, lines.join('\n'), 'utf8');
    console.log(`  ✅ Fixed ${count} lines`);
  } else {
    console.log(`  ⏭️  No issues`);
  }
}

const files = process.argv.slice(2);
for (const file of files) {
  console.log(`📄 ${file}`);
  processFile(file);
}
