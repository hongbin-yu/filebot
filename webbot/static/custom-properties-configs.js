// Custom metadata properties — 配置驱动
// 新 project 用法：在此文件加一个配置对象，然后访问
//   /static/custom-properties.html?path=<page-path>&cfg=<config-id>
// 配置字段说明：
//   fields[].name      metadata 字段名（保存为 {name} 和 {name}_key）
//   fields[].title     表单标签 + content 中 <dt> 的标题
//   fields[].cat       tags 分类路径（选项从 GET /api/v1/tags?parent_path=<cat> 加载）
//   fields[].multi     多选（true）或单选（false）
//   fields[].render    保存到 content 的方式：
//       'dl'      默认：<dt><dd data-tag-key="...">（需 dtMatch 匹配现有 dt）
//       'p-label' 特殊段落：<p class="<labelClass>" data-<keyAttr>="key">text</p>
//   fields[].dtMatch   content 中 <dt> 文本匹配关键词（render='dl' 时用）
//   fields[].labelClass / fields[].keyAttr   render='p-label' 专用
//   dateField          日期字段（<input type=date> → <time datetime>）
//   sectionSelector    content 中 metadata section 的选择器
window.CUSTOM_PROPERTIES_CONFIGS = Object.assign({}, window.CUSTOM_PROPERTIES_CONFIGS || {}, {
    'oag': {
        title: 'OAG / BVG custom tags',
        hint: 'Tags from /canadasite/tags/custom/oag-bvg (7 categories) + audited entities. Saved as page custom tags (metadata + content).',
        sectionSelector: 'section.oag-brdr, .wb-metadata-editor, [data-metadata-editor="oag"]',
        fields: [
            { name: 'report_type', title: 'Report type', cat: '/canadasite/tags/custom/oag-bvg/report-type', multi: false, render: 'p-label', labelClass: 'report-type-label', keyAttr: 'data-report-type-key' },
            { name: 'issue_year', title: 'Issue year', cat: '/canadasite/tags/custom/oag-bvg/issue-year', multi: false, dtMatch: 'issue year' },
            { name: 'issues', title: 'Issues', cat: '/canadasite/tags/custom/oag-bvg/issues', multi: true, dtMatch: 'issues' },
            { name: 'location', title: 'Location', cat: '/canadasite/tags/custom/oag-bvg/location', multi: false, dtMatch: 'location' },
            { name: 'media_type', title: 'Media type', cat: '/canadasite/tags/custom/oag-bvg/media-type', multi: false, dtMatch: 'media' },
            { name: 'status', title: 'Status', cat: '/canadasite/tags/custom/oag-bvg/status', multi: false, dtMatch: 'status' },
            { name: 'audited_entities', title: 'Audited entities', cat: '/canadasite/tags/institutions', multi: true, dtMatch: 'audited' },
            { name: 'topics', title: 'Topics', cat: '/canadasite/tags/custom/oag-bvg/topics', multi: true, dtMatch: 'topic' }
        ],
        dateField: { name: 'tabling_date', title: 'Tabling date' }
    }
});
