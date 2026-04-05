// 测试 addGCWebHeaderFooter 函数
const fs = require('fs');
const path = require('path');

// 读取 editor.html 文件
const editorHtmlPath = path.join(__dirname, 'webbot/static/editor.html');
const htmlContent = fs.readFileSync(editorHtmlPath, 'utf8');

// 提取 addGCWebHeaderFooter 函数
function extractFunction(html, functionName) {
    const regex = new RegExp(`function ${functionName}\\([^)]*\\)\\s*{([\\s\\S]*?\\n}\\s*function|\\n})`, 'm');
    const match = html.match(regex);
    return match ? match[0] : null;
}

console.log('Testing addGCWebHeaderFooter function...');
const functionText = extractFunction(htmlContent, 'addGCWebHeaderFooter');
if (functionText) {
    console.log('Function found, length:', functionText.length);
    
    // 检查函数中是否包含反引号
    const backtickMatches = functionText.match(/`/g);
    console.log('Backticks in function:', backtickMatches ? backtickMatches.length : 0);
    
    // 检查函数中是否包含模板字符串
    const templateStringMatches = functionText.match(/`[^`]*`/g);
    console.log('Template string literals found:', templateStringMatches ? templateStringMatches.length : 0);
    
    if (templateStringMatches) {
        console.log('Template strings found:');
        templateStringMatches.forEach((match, i) => {
            console.log(`  ${i}: ${match.substring(0, 100)}...`);
        });
    }
    
    // 提取 gcwebHeader 和 gcwebFooter 定义
    const headerMatch = functionText.match(/const gcwebHeader = ([^;]+);/);
    const footerMatch = functionText.match(/const gcwebFooter = ([^;]+);/);
    
    console.log('Header definition found:', !!headerMatch);
    console.log('Footer definition found:', !!footerMatch);
    
    if (headerMatch && headerMatch[1]) {
        const headerDef = headerMatch[1];
        console.log('Header definition length:', headerDef.length);
        console.log('Header starts with:', headerDef.substring(0, 100));
        console.log('Header contains backslash:', headerDef.includes('\\'));
    }
} else {
    console.log('Function not found!');
}