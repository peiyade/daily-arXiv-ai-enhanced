// 全局变量
let promptsConfig = null;
let originalConfig = null;  // 保存原始配置用于重置
let currentTemplateName = 'default';
let paperMarks = {}; // 存储论文标记数据

document.addEventListener('DOMContentLoaded', () => {
  initSettings();
  initEventListeners();
  fetchGitHubStats();
  // 加载提示词配置
  loadPromptsConfig();
  // 加载论文标记数据并更新统计
  loadPaperMarks();
});

// ========== 论文标记管理功能 ==========

// 加载论文标记数据
function loadPaperMarks() {
  const saved = localStorage.getItem('paperMarks');
  if (saved) {
    try {
      paperMarks = JSON.parse(saved);
      console.log('论文标记数据已加载:', Object.keys(paperMarks).length, '篇');
      updatePaperStats();
    } catch (e) {
      console.error('加载论文标记失败:', e);
      paperMarks = {};
    }
  }
}

// 更新论文统计
function updatePaperStats() {
  const marks = Object.values(paperMarks);
  const total = marks.length;
  const toStudy = marks.filter(m => m.status === 'to_study').length;
  const read = marks.filter(m => m.status === 'read').length;

  const totalEl = document.getElementById('totalMarked');
  const toStudyEl = document.getElementById('toStudyCount');
  const readEl = document.getElementById('readCount');

  if (totalEl) totalEl.textContent = total;
  if (toStudyEl) toStudyEl.textContent = toStudy;
  if (readEl) readEl.textContent = read;
}

// 根据筛选条件获取论文列表
function getFilteredPapers(filter) {
  const papers = [];
  Object.entries(paperMarks).forEach(([paperId, mark]) => {
    if (filter === 'all' || mark.status === filter) {
      papers.push({
        id: paperId,
        ...mark
      });
    }
  });
  return papers;
}

// 导出为Markdown格式
function exportToMarkdown(papers) {
  const date = new Date().toISOString().split('T')[0];
  let markdown = `# 论文列表导出\n\n`;
  markdown += `**导出日期:** ${date}\n`;
  markdown += `**论文数量:** ${papers.length} 篇\n\n`;
  markdown += `---\n\n`;

  papers.forEach((paper, index) => {
    const priority = paper.priority ? '⭐'.repeat(paper.priority) : '';
    const status = paper.status === 'to_study' ? '🔵 待研究' : 
                   paper.status === 'read' ? '✅ 已读' : '⚪ 未标记';
    
    markdown += `## ${index + 1}. ${paper.id}\n\n`;
    markdown += `- **状态:** ${status} ${priority}\n`;
    markdown += `- **链接:** https://arxiv.org/abs/${paper.id}\n`;
    markdown += `- **PDF:** https://arxiv.org/pdf/${paper.id}.pdf\n`;
    
    if (paper.tags && paper.tags.length > 0) {
      markdown += `- **标签:** ${paper.tags.join(', ')}\n`;
    }
    
    if (paper.notes) {
      markdown += `- **笔记:**\n\n  ${paper.notes.split('\n').join('\n  ')}\n`;
    }
    
    if (paper.markedAt) {
      markdown += `- **标记时间:** ${new Date(paper.markedAt).toLocaleString()}\n`;
    }
    
    markdown += `\n---\n\n`;
  });

  return markdown;
}

// 导出为CSV格式
function exportToCSV(papers) {
  const headers = ['ID', 'Status', 'Priority', 'Tags', 'Notes', 'Marked At', 'ArXiv URL', 'PDF URL'];
  const rows = papers.map(paper => {
    const status = paper.status === 'to_study' ? 'To Study' : 
                   paper.status === 'read' ? 'Read' : 'Unread';
    return [
      paper.id,
      status,
      paper.priority || 0,
      (paper.tags || []).join('; '),
      (paper.notes || '').replace(/"/g, '""'),
      paper.markedAt ? new Date(paper.markedAt).toISOString() : '',
      `https://arxiv.org/abs/${paper.id}`,
      `https://arxiv.org/pdf/${paper.id}.pdf`
    ];
  });

  // 添加BOM以支持中文
  const BOM = '\uFEFF';
  const csv = BOM + [headers.join(','), ...rows.map(row => 
    row.map(cell => `"${cell}"`).join(',')
  )].join('\n');
  
  return csv;
}

// 导出为BibTeX格式
function exportToBibTeX(papers) {
  return papers.map(paper => {
    const year = paper.id.substring(0, 4);
    const citeKey = `arxiv:${paper.id}`;
    
    let bib = `@article{${citeKey},\n`;
    bib += `  title = {${paper.id}},\n`;
    bib += `  journal = {arXiv preprint},\n`;
    bib += `  year = {${year}},\n`;
    bib += `  url = {https://arxiv.org/abs/${paper.id}},\n`;
    bib += `  note = {Status: ${paper.status}${paper.priority ? ', Priority: ' + paper.priority : ''}${paper.notes ? '\\nNotes: ' + paper.notes : ''}}\n`;
    bib += `}\n`;
    return bib;
  }).join('\n');
}

// 导出论文主函数
function exportPapers() {
  const filterEl = document.querySelector('input[name="exportFilter"]:checked');
  const formatEl = document.getElementById('exportFormat');
  
  if (!filterEl || !formatEl) return;
  
  const filter = filterEl.value;
  const format = formatEl.value;
  const papers = getFilteredPapers(filter);
  
  if (papers.length === 0) {
    showNotification('No papers to export for the selected filter.', 'info');
    return;
  }
  
  let content, filename, mimeType;
  const date = new Date().toISOString().split('T')[0];
  const filterName = filter === 'to_study' ? 'to-study' : filter === 'read' ? 'read' : 'all';
  
  switch (format) {
    case 'markdown':
      content = exportToMarkdown(papers);
      filename = `papers-${filterName}-${date}.md`;
      mimeType = 'text/markdown;charset=utf-8';
      break;
    case 'csv':
      content = exportToCSV(papers);
      filename = `papers-${filterName}-${date}.csv`;
      mimeType = 'text/csv;charset=utf-8';
      break;
    case 'bibtex':
      content = exportToBibTeX(papers);
      filename = `papers-${filterName}-${date}.bib`;
      mimeType = 'text/plain;charset=utf-8';
      break;
    case 'json':
    default:
      content = JSON.stringify(papers, null, 2);
      filename = `papers-${filterName}-${date}.json`;
      mimeType = 'application/json;charset=utf-8';
      break;
  }
  
  // 创建并下载文件
  const blob = new Blob([content], { type: mimeType });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = filename;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  showNotification(`Exported ${papers.length} papers to ${format.toUpperCase()}!`, 'success');
}

// 导出所有标记数据（原始JSON）
function exportAllMarks() {
  if (Object.keys(paperMarks).length === 0) {
    showNotification('No marked papers to export.', 'info');
    return;
  }
  
  const dataStr = JSON.stringify(paperMarks, null, 2);
  const blob = new Blob([dataStr], { type: 'application/json;charset=utf-8' });
  const url = URL.createObjectURL(blob);
  const a = document.createElement('a');
  a.href = url;
  a.download = `paper-marks-${new Date().toISOString().split('T')[0]}.json`;
  document.body.appendChild(a);
  a.click();
  document.body.removeChild(a);
  URL.revokeObjectURL(url);
  
  showNotification('All paper marks exported successfully!', 'success');
}

// 绑定导出相关事件
document.addEventListener('DOMContentLoaded', () => {
  const exportPapersBtn = document.getElementById('exportPapersBtn');
  const exportAllMarksBtn = document.getElementById('exportAllMarksBtn');
  
  if (exportPapersBtn) {
    exportPapersBtn.addEventListener('click', exportPapers);
  }
  
  if (exportAllMarksBtn) {
    exportAllMarksBtn.addEventListener('click', exportAllMarks);
  }
});

// 初始化设置，从localStorage加载已保存的设置
function initSettings() {
  // 关键词偏好设置
  loadKeywordPreferences();
  // 作者偏好设置
  loadAuthorPreferences();
}

// 从localStorage加载关键词偏好
function loadKeywordPreferences() {
  const selectedKeywordsContainer = document.getElementById('selectedKeywords');
  selectedKeywordsContainer.innerHTML = '';
  
  // 获取保存的关键词，如果没有则使用默认关键词
  let savedKeywords = localStorage.getItem('preferredKeywords');
  let keywords = []; // 默认无关键词
  
  if (savedKeywords) {
    try {
      keywords = JSON.parse(savedKeywords);
    } catch (e) {
      console.error('解析保存的关键词失败:', e);
    }
  }
  
  // 显示保存的关键词
  if (keywords.length > 0) {
    keywords.forEach(keyword => {
      addKeywordTag(keyword);
    });
  } else {
    // 显示空标签消息
    showEmptyTagMessage();
  }
}

// 从localStorage加载作者偏好
function loadAuthorPreferences() {
  const selectedAuthorsContainer = document.getElementById('selectedAuthors');
  selectedAuthorsContainer.innerHTML = '';
  
  // 获取保存的作者，如果没有则为空数组
  let savedAuthors = localStorage.getItem('preferredAuthors');
  let authors = []; // 默认无作者
  
  if (savedAuthors) {
    try {
      authors = JSON.parse(savedAuthors);
    } catch (e) {
      console.error('解析保存的作者失败:', e);
    }
  }
  
  // 显示保存的作者
  if (authors.length > 0) {
    authors.forEach(author => {
      addAuthorTag(author);
    });
  } else {
    // 显示空标签消息
    showEmptyAuthorMessage();
  }
}

// 显示空标签消息
function showEmptyTagMessage() {
  const selectedKeywordsContainer = document.getElementById('selectedKeywords');
  const emptyMessage = document.createElement('div');
  emptyMessage.id = 'emptyTagMessage';
  emptyMessage.className = 'empty-tag-message';
  emptyMessage.textContent = 'No keywords added yet. Add some keywords below.';
  selectedKeywordsContainer.appendChild(emptyMessage);
}

// 显示空作者标签消息
function showEmptyAuthorMessage() {
  const selectedAuthorsContainer = document.getElementById('selectedAuthors');
  const emptyMessage = document.createElement('div');
  emptyMessage.id = 'emptyAuthorMessage';
  emptyMessage.className = 'empty-tag-message';
  emptyMessage.textContent = 'No authors added yet. Add some authors below.';
  selectedAuthorsContainer.appendChild(emptyMessage);
}

// 隐藏空标签消息
function hideEmptyTagMessage() {
  const emptyMessage = document.getElementById('emptyTagMessage');
  if (emptyMessage) {
    emptyMessage.remove();
  }
}

// 隐藏空作者标签消息
function hideEmptyAuthorMessage() {
  const emptyMessage = document.getElementById('emptyAuthorMessage');
  if (emptyMessage) {
    emptyMessage.remove();
  }
}

// 添加关键词标签
function addKeywordTag(keyword) {
  const selectedKeywordsContainer = document.getElementById('selectedKeywords');
  
  // 移除空标签消息
  hideEmptyTagMessage();
  
  // 检查关键词是否已存在
  const existingTags = selectedKeywordsContainer.querySelectorAll('.category-button');
  for (let i = 0; i < existingTags.length; i++) {
    if (existingTags[i].textContent.trim().startsWith(keyword)) {
      // 已存在该关键词，添加闪烁动画提示用户
      existingTags[i].classList.add('tag-highlight');
      setTimeout(() => {
        existingTags[i].classList.remove('tag-highlight');
      }, 1000);
      return; // 关键词已存在，不添加
    }
  }
  
  // 创建新的关键词标签
  const tagElement = document.createElement('span');
  tagElement.className = 'category-button tag-appear';
  tagElement.innerHTML = `${keyword} <button class="remove-tag">×</button>`;
  
  // 添加删除按钮事件
  const removeButton = tagElement.querySelector('.remove-tag');
  removeButton.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    // 添加删除动画
    tagElement.classList.add('tag-disappear');
    
    // 动画结束后移除元素
    setTimeout(() => {
      tagElement.remove();
      
      // 如果没有标签了，显示空标签消息
      if (selectedKeywordsContainer.querySelectorAll('.category-button').length === 0) {
        showEmptyTagMessage();
      }
    }, 300);
  });
  
  selectedKeywordsContainer.appendChild(tagElement);
  
  // 添加出现动画后移除动画类
  setTimeout(() => {
    tagElement.classList.remove('tag-appear');
  }, 300);
}

// 添加作者标签
function addAuthorTag(author) {
  const selectedAuthorsContainer = document.getElementById('selectedAuthors');
  
  // 移除空标签消息
  hideEmptyAuthorMessage();
  
  // 检查作者是否已存在
  const existingTags = selectedAuthorsContainer.querySelectorAll('.category-button');
  for (let i = 0; i < existingTags.length; i++) {
    if (existingTags[i].textContent.trim().startsWith(author)) {
      // 已存在该作者，添加闪烁动画提示用户
      existingTags[i].classList.add('tag-highlight');
      setTimeout(() => {
        existingTags[i].classList.remove('tag-highlight');
      }, 1000);
      return; // 作者已存在，不添加
    }
  }
  
  // 创建新的作者标签
  const tagElement = document.createElement('span');
  tagElement.className = 'category-button tag-appear';
  tagElement.innerHTML = `${author} <button class="remove-tag">×</button>`;
  
  // 添加删除按钮事件
  const removeButton = tagElement.querySelector('.remove-tag');
  removeButton.addEventListener('click', (e) => {
    e.preventDefault();
    e.stopPropagation();
    
    // 添加删除动画
    tagElement.classList.add('tag-disappear');
    
    // 动画结束后移除元素
    setTimeout(() => {
      tagElement.remove();
      
      // 如果没有标签了，显示空标签消息
      if (selectedAuthorsContainer.querySelectorAll('.category-button').length === 0) {
        showEmptyAuthorMessage();
      }
    }, 300);
  });
  
  selectedAuthorsContainer.appendChild(tagElement);
  
  // 添加出现动画后移除动画类
  setTimeout(() => {
    tagElement.classList.remove('tag-appear');
  }, 300);
}

// 初始化事件监听器
function initEventListeners() {
  // 关键词添加按钮
  const addKeywordButton = document.getElementById('addKeyword');
  addKeywordButton.addEventListener('click', () => {
    const keywordInput = document.getElementById('keywordInput');
    const keyword = keywordInput.value.trim();
    
    if (keyword) {
      addKeywordTag(keyword);
      keywordInput.value = '';
    }
  });
  
  // 关键词输入框回车事件
  const keywordInput = document.getElementById('keywordInput');
  keywordInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const keyword = keywordInput.value.trim();
      
      if (keyword) {
        addKeywordTag(keyword);
        keywordInput.value = '';
      }
    }
  });
  
  // 作者添加按钮
  const addAuthorButton = document.getElementById('addAuthor');
  addAuthorButton.addEventListener('click', () => {
    const authorInput = document.getElementById('authorInput');
    const author = authorInput.value.trim();
    
    if (author) {
      addAuthorTag(author);
      authorInput.value = '';
    }
  });
  
  // 作者输入框回车事件
  const authorInput = document.getElementById('authorInput');
  authorInput.addEventListener('keypress', (e) => {
    if (e.key === 'Enter') {
      e.preventDefault();
      const author = authorInput.value.trim();
      
      if (author) {
        addAuthorTag(author);
        authorInput.value = '';
      }
    }
  });
  
  // 保存设置按钮
  const saveSettingsButton = document.getElementById('saveSettings');
  saveSettingsButton.addEventListener('click', saveSettings);
  
  // 重置设置按钮
  const resetSettingsButton = document.getElementById('resetSettings');
  resetSettingsButton.addEventListener('click', resetSettings);
}

// 保存设置
function saveSettings() {
  // 获取所有选中的关键词
  const keywordTags = document.getElementById('selectedKeywords').querySelectorAll('.category-button');
  const keywords = [];
  keywordTags.forEach(tag => {
    const keywordName = tag.textContent.trim().replace('×', '').trim();
    keywords.push(keywordName);
  });
  
  // 获取所有选中的作者
  const authorTags = document.getElementById('selectedAuthors').querySelectorAll('.category-button');
  const authors = [];
  authorTags.forEach(tag => {
    const authorName = tag.textContent.trim().replace('×', '').trim();
    authors.push(authorName);
  });
  
  // 保存设置到localStorage
  localStorage.setItem('preferredKeywords', JSON.stringify(keywords));
  localStorage.setItem('preferredAuthors', JSON.stringify(authors));
  
  // 显示保存成功提示，添加成功图标
  showNotification('Settings saved successfully!', 'success');
}

// 重置设置
function resetSettings() {
  // 重置关键词
  const selectedKeywordsContainer = document.getElementById('selectedKeywords');
  selectedKeywordsContainer.innerHTML = '';
  
  // 重置作者
  const selectedAuthorsContainer = document.getElementById('selectedAuthors');
  selectedAuthorsContainer.innerHTML = '';
  
  // 显示空标签消息
  showEmptyTagMessage();
  showEmptyAuthorMessage();
  
  // 显示重置成功提示
  showNotification('Settings reset to default!', 'info');
}

// 显示通知
function showNotification(message, type = 'success') {
  // 检查是否已存在通知元素
  let notification = document.querySelector('.settings-notification');
  
  if (!notification) {
    // 创建通知元素
    notification = document.createElement('div');
    notification.className = 'settings-notification';
    document.body.appendChild(notification);
  }
  
  // 根据类型设置图标
  let icon = '';
  let bgColor = 'var(--primary-color)';
  
  if (type === 'success') {
    icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M9 16.17L4.83 12l-1.42 1.41L9 19 21 7l-1.41-1.41L9 16.17z" fill="currentColor"/></svg>';
  } else if (type === 'info') {
    icon = '<svg width="20" height="20" viewBox="0 0 24 24" fill="none" xmlns="http://www.w3.org/2000/svg"><path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 15c-.55 0-1-.45-1-1v-4c0-.55.45-1 1-1s1 .45 1 1v4c0 .55-.45 1-1 1zm1-8h-2V7h2v2z" fill="currentColor"/></svg>';
    bgColor = '#3b82f6';
  }
  
  // 设置通知内容和样式
  notification.innerHTML = `${icon}<span>${message}</span>`;
  notification.style.display = 'flex';
  notification.style.alignItems = 'center';
  notification.style.gap = '8px';
  notification.style.position = 'fixed';
  notification.style.bottom = '20px';
  notification.style.right = '20px';
  notification.style.backgroundColor = bgColor;
  notification.style.color = 'white';
  notification.style.padding = '12px 20px';
  notification.style.borderRadius = 'var(--radius-sm)';
  notification.style.boxShadow = 'var(--shadow-md)';
  notification.style.zIndex = '1000';
  notification.style.opacity = '0';
  notification.style.transform = 'translateY(20px)';
  notification.style.transition = 'opacity 0.3s ease, transform 0.3s ease';
  
  // 显示通知
  setTimeout(() => {
    notification.style.opacity = '1';
    notification.style.transform = 'translateY(0)';
  }, 10);
  
  // 3秒后隐藏通知
  setTimeout(() => {
    notification.style.opacity = '0';
    notification.style.transform = 'translateY(20px)';
    
    // 动画结束后移除元素
    setTimeout(() => {
      if (notification.parentNode) {
        notification.parentNode.removeChild(notification);
      }
    }, 300);
  }, 3000);
}

// 获取GitHub统计数据
async function fetchGitHubStats() {
  try {
    const response = await fetch('https://api.github.com/repos/dw-dengwei/daily-arXiv-ai-enhanced');
    const data = await response.json();
    const starCount = data.stargazers_count;
    const forkCount = data.forks_count;
    
    document.getElementById('starCount').textContent = starCount;
    document.getElementById('forkCount').textContent = forkCount;
  } catch (error) {
    console.error('获取GitHub统计数据失败:', error);
    document.getElementById('starCount').textContent = '?';
    document.getElementById('forkCount').textContent = '?';
  }
}

// ========== 提示词模板管理功能 ==========

// 加载提示词配置
async function loadPromptsConfig() {
  try {
    const response = await fetch('ai/prompts_config.yaml');
    if (!response.ok) {
      throw new Error(`HTTP error! status: ${response.status}`);
    }
    const yamlText = await response.text();

    // 使用 js-yaml 库解析 YAML
    if (typeof jsyaml !== 'undefined') {
      promptsConfig = jsyaml.load(yamlText);
      originalConfig = JSON.parse(JSON.stringify(promptsConfig)); // 深拷贝保存原始配置
      console.log('提示词配置加载成功:', promptsConfig);
      renderTemplateTabs();
      loadTemplate('default');
    } else {
      console.error('js-yaml 库未加载');
      showNotification('js-yaml 库加载失败，无法编辑提示词', 'error');
    }
  } catch (error) {
    console.error('加载提示词配置失败:', error);
    showNotification('加载提示词配置失败: ' + error.message, 'error');
  }
}

// 渲染模板标签
function renderTemplateTabs() {
  const tabsContainer = document.getElementById('templateTabs');
  if (!tabsContainer) return;

  tabsContainer.innerHTML = '';

  if (!promptsConfig || !promptsConfig.templates) {
    tabsContainer.innerHTML = '<div class="template-tab">无法加载模板</div>';
    return;
  }

  Object.keys(promptsConfig.templates).forEach(templateName => {
    const template = promptsConfig.templates[templateName];
    const tab = document.createElement('div');
    tab.className = `template-tab ${templateName === currentTemplateName ? 'active' : ''}`;
    tab.textContent = template.name || templateName;
    tab.title = template.description || '';
    tab.addEventListener('click', () => loadTemplate(templateName));
    tabsContainer.appendChild(tab);
  });
}

// 加载模板到编辑器
function loadTemplate(templateName) {
  if (!promptsConfig || !promptsConfig.templates) return;

  currentTemplateName = templateName;
  const template = promptsConfig.templates[templateName];

  if (!template) {
    console.error('模板不存在:', templateName);
    return;
  }

  // 更新编辑器内容
  document.getElementById('templateName').value = template.name || templateName;
  document.getElementById('templateDescription').value = template.description || '';
  document.getElementById('systemPrompt').value = template.system_prompt || '';
  document.getElementById('userPrompt').value = template.user_prompt || '';

  // 更新标签状态
  document.querySelectorAll('.template-tab').forEach(tab => {
    tab.classList.remove('active');
    if (tab.textContent === (template.name || templateName)) {
      tab.classList.add('active');
    }
  });
}

// 保存当前模板
function saveTemplate() {
  if (!promptsConfig || !promptsConfig.templates) {
    showNotification('提示词配置未加载', 'error');
    return;
  }

  const template = promptsConfig.templates[currentTemplateName];
  if (!template) {
    showNotification('当前模板不存在', 'error');
    return;
  }

  // 更新模板内容
  template.system_prompt = document.getElementById('systemPrompt').value;
  template.user_prompt = document.getElementById('userPrompt').value;

  showNotification(`模板 "${template.name}" 已保存到内存！请点击"下载配置文件"按钮保存到本地`, 'success');
}

// 下载配置文件
function downloadTemplate() {
  if (!promptsConfig) {
    showNotification('提示词配置未加载', 'error');
    return;
  }

  // 将配置转换为 YAML 字符串
  const yamlString = jsyaml.dump(promptsConfig, {
    indent: 2,
    lineWidth: -1,  // 不限制行宽
    noRefs: true    // 不使用引用
  });

  // 创建 Blob
  const blob = new Blob([yamlString], { type: 'text/yaml;charset=utf-8' });
  const url = URL.createObjectURL(blob);

  // 创建下载链接
  const a = document.createElement('a');
  a.href = url;
  a.download = 'prompts_config.yaml';
  document.body.appendChild(a);
  a.click();

  // 清理
  document.body.removeChild(a);
  URL.revokeObjectURL(url);

  showNotification('配置文件已下载！请将其替换 ai/prompts_config.yaml', 'success');
}

// 重置当前模板为默认值
function resetTemplate() {
  if (!originalConfig || !originalConfig.templates) {
    showNotification('无法重置：原始配置未保存', 'error');
    return;
  }

  if (!confirm(`确定要将 "${currentTemplateName}" 模板重置为默认值吗？此操作将丢失所有未保存的修改。`)) {
    return;
  }

  // 从原始配置中恢复
  promptsConfig.templates[currentTemplateName] = JSON.parse(JSON.stringify(originalConfig.templates[currentTemplateName]));

  // 重新加载到编辑器
  loadTemplate(currentTemplateName);

  showNotification(`模板 "${currentTemplateName}" 已重置为默认值`, 'info');
}

// 绑定提示词相关事件
document.addEventListener('DOMContentLoaded', () => {
  // 绑定提示词相关事件
  const saveTemplateBtn = document.getElementById('saveTemplate');
  if (saveTemplateBtn) {
    saveTemplateBtn.addEventListener('click', saveTemplate);
  }

  const downloadTemplateBtn = document.getElementById('downloadTemplate');
  if (downloadTemplateBtn) {
    downloadTemplateBtn.addEventListener('click', downloadTemplate);
  }

  const resetTemplateBtn = document.getElementById('resetTemplate');
  if (resetTemplateBtn) {
    resetTemplateBtn.addEventListener('click', resetTemplate);
  }
});
 