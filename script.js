const form = document.getElementById('upload-form');
const statusBox = document.getElementById('status');
const submitBtn = document.getElementById('submit-btn');
const refreshBtn = document.getElementById('refresh-btn');
const resultsBody = document.getElementById('results-body');
const numberFormatter = new Intl.NumberFormat('zh-CN');

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
    row.innerHTML = '<td colspan="10" class="empty">暂无数据</td>';
    resultsBody.appendChild(row);
    return;
  }

  for (const item of items) {
    const row = document.createElement('tr');
    row.dataset.id = item.id;

    row.appendChild(createTextCell(item.platform ?? ''));
    row.appendChild(createLinkCell(item.url));
    row.appendChild(createTextCell(item.creator ?? ''));
    row.appendChild(createTextCell(item.posted_at ? formatDate(item.posted_at) : ''));
    row.appendChild(createNumericCell(item.views, 'views-cell'));
    row.appendChild(createNumericCell(item.likes));
    row.appendChild(createNumericCell(item.comments));
    row.appendChild(createNumericCell(item.engagement_rate));
    row.appendChild(createNoteCell(item));
    row.appendChild(createTextCell(item.fetched_at ? formatDate(item.fetched_at) : ''));

    resultsBody.appendChild(row);
  }
}

function createTextCell(value) {
  const td = document.createElement('td');
  td.textContent = value ?? '';
  return td;
}

function createNumericCell(value, extraClass) {
  const td = document.createElement('td');
  td.classList.add('numeric');
  if (extraClass) {
    td.classList.add(extraClass);
  }
  td.textContent = value != null && value !== '' ? formatNumber(value) : '';
  return td;
}

function createLinkCell(url) {
  const td = document.createElement('td');
  if (!url) {
    td.textContent = '';
    return td;
  }
  const link = document.createElement('a');
  link.href = url;
  link.target = '_blank';
  link.rel = 'noopener';
  link.ariaLabel = '打开链接';
  link.textContent = '🔗';
  td.appendChild(link);
  return td;
}

function createNoteCell(item) {
  const td = document.createElement('td');
  const wrapper = document.createElement('div');
  wrapper.classList.add('note-cell');

  const input = document.createElement('input');
  input.type = 'text';
  input.value = item.notes ?? '';
  input.placeholder = '添加备注';

  const button = document.createElement('button');
  button.type = 'button';
  button.textContent = '保存';

  const saveNote = async () => {
    const note = input.value;
    button.disabled = true;
    button.textContent = '保存中';
    try {
      const formData = new FormData();
      formData.append('note', note);
      const res = await fetch(`/api/results/${item.id}/note`, {
        method: 'POST',
        body: formData,
      });
      const data = await res.json();
      if (!res.ok) {
        throw new Error(data.detail || '保存失败');
      }
      button.textContent = '已保存';
      setTimeout(() => (button.textContent = '保存'), 1500);
    } catch (err) {
      button.textContent = '重试';
      renderStatus(String(err.message || err), 'error');
    } finally {
      button.disabled = false;
    }
  };

  button.addEventListener('click', saveNote);
  input.addEventListener('keydown', (event) => {
    if (event.key === 'Enter') {
      event.preventDefault();
      saveNote();
    }
  });

  wrapper.appendChild(input);
  wrapper.appendChild(button);
  td.appendChild(wrapper);
  return td;
}

function formatDate(value) {
  try {
    return new Date(value).toLocaleString('zh-CN', {
      hour12: false,
      timeZone: 'Asia/Shanghai',
    });
  } catch (_) {
    return value;
  }
}

function formatNumber(value) {
  const num = Number(value);
  if (Number.isNaN(num)) {
    return value;
  }
  return numberFormatter.format(num);
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
