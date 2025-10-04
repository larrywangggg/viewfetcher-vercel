const form = document.getElementById('upload-form');
const statusBox = document.getElementById('status');
const submitBtn = document.getElementById('submit-btn');
const refreshBtn = document.getElementById('refresh-btn');
const resultsBody = document.getElementById('results-body');

function renderStatus(message, type = 'info') {
  statusBox.textContent = message;
  statusBox.dataset.type = type;
  if (!message) {
    statusBox.classList.add('hidden');
  } else {
    statusBox.classList.remove('hidden');
  }
}

function renderResults(items) {
  resultsBody.innerHTML = '';
  if (!items.length) {
    const row = document.createElement('tr');
    row.innerHTML = '<td colspan="12" class="empty">暂无数据</td>';
    resultsBody.appendChild(row);
    return;
  }

  for (const item of items) {
    const row = document.createElement('tr');
    row.innerHTML = `
      <td>${item.id ?? ''}</td>
      <td>${item.platform ?? ''}</td>
      <td><a href="${item.url}" target="_blank" rel="noopener">链接</a></td>
      <td>${item.creator ?? ''}</td>
      <td>${item.campaign_id ?? ''}</td>
      <td>${item.posted_at ? formatDate(item.posted_at) : ''}</td>
      <td>${item.views ?? 0}</td>
      <td>${item.likes ?? 0}</td>
      <td>${item.comments ?? 0}</td>
      <td>${item.engagement_rate ?? 0}</td>
      <td>${item.notes ?? ''}</td>
      <td>${item.fetched_at ? formatDate(item.fetched_at) : ''}</td>
    `;
    resultsBody.appendChild(row);
  }
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString('zh-CN', { hour12: false });
  } catch (_) {
    return value;
  }
}

async function fetchResults() {
  try {
    const res = await fetch('/api/results');
    if (!res.ok) {
      throw new Error(`加载失败：${res.status}`);
    }
    const data = await res.json();
    renderResults(data.items ?? []);
  } catch (err) {
    renderStatus(err.message, 'error');
  }
}

form.addEventListener('submit', async (event) => {
  event.preventDefault();
  const fileInput = document.getElementById('file');
  if (!fileInput.files.length) {
    renderStatus('请选择文件', 'error');
    return;
  }

  const formData = new FormData(form);
  renderStatus('正在上传和抓取，请稍候...', 'info');
  submitBtn.disabled = true;

  try {
    const res = await fetch('/api/fetch', { method: 'POST', body: formData });
    const data = await res.json();
    if (!res.ok) {
      throw new Error(data.detail || '服务端返回错误');
    }

    const errorMsg = data.errors && data.errors.length ? `。警告：${data.errors.join('；')}` : '';
    renderStatus(`共写入 ${data.saved} 条记录${errorMsg}`, 'success');
    renderResults(data.items ?? []);
    await fetchResults();
  } catch (err) {
    renderStatus(err.message, 'error');
  } finally {
    submitBtn.disabled = false;
  }
});

refreshBtn.addEventListener('click', async () => {
  renderStatus('正在刷新...', 'info');
  await fetchResults();
  renderStatus('', 'info');
});

fetchResults();
