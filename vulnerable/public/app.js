// Frontend tối giản cho demo. BẢN ĐÃ SỬA: hiển thị dữ liệu bằng textContent.
const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('token');

// ---------- Hàm tiện ích ----------
// Tạo phần tử và gán chữ bằng textContent: dữ liệu luôn là chữ, không bao giờ là mã.
function el(tag, className, text) {
  const e = document.createElement(tag);
  if (className) e.className = className;
  if (text !== undefined) e.textContent = text;
  return e;
}

function money(v) {
  const n = Number(v);
  return Number.isFinite(n) ? new Intl.NumberFormat('vi-VN').format(n) + ' ₫' : String(v);
}

function when(iso) {
  const d = new Date(iso);
  return isNaN(d) ? String(iso) : d.toLocaleString('vi-VN');
}

function decodePayload(t) {
  try {
    const part = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(part)); // payload của JWT chỉ là base64, ai cũng đọc được
  } catch (e) {
    return null;
  }
}

const HINTS = {
  0: 'Không kết nối được tới server.',
  400: 'Dữ liệu gửi lên không hợp lệ.',
  401: 'Chưa đăng nhập, hoặc token sai hay đã hết hạn.',
  403: 'Đã đăng nhập nhưng không có quyền làm việc này.',
  404: 'Không tìm thấy.',
  413: 'Dữ liệu gửi lên quá lớn.',
  429: 'Gửi quá nhiều yêu cầu, hãy chờ một lúc rồi thử lại.',
  500: 'Lỗi phía server.',
};

// Hiện một khung thông báo (kind: ok, warn, err, info) vào vùng box; kind rỗng thì xóa thông báo.
function setAlert(box, kind, title, detail) {
  box.replaceChildren();
  if (!kind) return;
  const a = el('div', 'alert ' + kind);
  a.append(el('strong', '', title));
  if (detail) a.append(' ' + detail);
  box.append(a);
}

function showError(box, status, data) {
  const msg = data && typeof data === 'object' && data.error ? String(data.error) : typeof data === 'string' ? data : '';
  const a = el('div', 'alert err');
  a.append(el('strong', '', status ? 'HTTP ' + status : 'Lỗi'));
  a.append(' ' + (HINTS[status] || ''));
  if (msg) {
    if (msg.length > 100 || msg.includes('\n')) {
      a.append(el('div', '', 'Server trả về:'), el('pre', '', msg));
    } else {
      a.append(' Server trả về: "' + msg + '".');
    }
  }
  box.replaceChildren(a);
}

async function withBusy(btn, label, fn) {
  const old = btn.textContent;
  btn.disabled = true;
  btn.textContent = label;
  try {
    return await fn();
  } finally {
    btn.disabled = false;
    btn.textContent = old;
  }
}

function showLog(method, path, status, data) {
  const body = typeof data === 'string' ? data : JSON.stringify(data, null, 2);
  $('out').textContent = method + ' ' + path + '\n=> HTTP ' + status + '\n' + body;
}

async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = 'Bearer ' + token;
  let res;
  let text;
  try {
    res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
    text = await res.text();
  } catch (e) {
    const data = { error: 'Không kết nối được tới server' };
    showLog(method, path, 0, data);
    return { status: 0, data };
  }
  let data;
  try { data = JSON.parse(text); } catch (e) { data = text; }
  showLog(method, path, res.status, data);
  return { status: res.status, data };
}

// ---------- Hai chỗ hiển thị dữ liệu người dùng (nơi XSS xảy ra hoặc được chặn) ----------
// SỬA #3: gán bằng textContent -> dữ liệu luôn là chữ, không bao giờ là mã
function renderProductName(target, p) {
  target.textContent = p.name;
}

// SỬA #3: nhận xét hiển thị như chữ thuần; thêm CSP ở server làm lớp bảo vệ thứ hai
function renderReview(target, r) {
  target.append(el('b', '', r.email), ': ' + r.comment);
}

// ---------- 1. Đăng nhập ----------
function refreshWho() {
  const p = token ? decodePayload(token) : null;
  const role = p && ['admin', 'customer'].includes(p.role) ? p.role : '';
  $('who').classList.toggle('on', !!p);
  $('avatar').textContent = p ? (String(p.role || '?').charAt(0).toUpperCase() || '?') : '?';
  $('whoName').textContent = p ? 'Đang đăng nhập: user ' + p.sub : 'Chưa đăng nhập';
  $('whoRole').textContent = p ? String(p.role) : '';
  $('whoRole').className = 'pill' + (role ? ' ' + role : '');
  $('whoRole').hidden = !p;
}

$('loginForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  await withBusy($('login'), 'Đang đăng nhập…', async () => {
    const { status, data } = await api('POST', '/login', {
      email: $('email').value,
      password: $('password').value,
    });
    if (status === 200) {
      token = data.token;
      localStorage.setItem('token', token);
      const p = decodePayload(token);
      const expiry = p && p.exp
        ? 'Token hết hạn lúc ' + new Date(p.exp * 1000).toLocaleTimeString('vi-VN') + '.'
        : 'Token này không có hạn dùng (exp).';
      setAlert($('loginMsg'), 'ok', 'Đăng nhập thành công.', expiry);
    } else {
      showError($('loginMsg'), status, data);
    }
    refreshWho();
  });
});

$('logout').addEventListener('click', () => {
  token = null;
  localStorage.removeItem('token');
  refreshWho();
  setAlert($('loginMsg'), 'info', 'Đã đăng xuất.', 'Token đã bị xóa khỏi trình duyệt.');
});

document.querySelectorAll('[data-email]').forEach((b) => {
  b.addEventListener('click', () => {
    $('email').value = b.dataset.email;
    $('password').value = b.dataset.password;
  });
});

// ---------- 2. Tìm sản phẩm ----------
function productCard(p) {
  const li = el('li', 'product');
  const name = el('div', 'product-name');
  renderProductName(name, p);
  const foot = el('div', 'product-foot');
  foot.append(el('span', 'price', money(p.price)), el('span', 'stock', 'Còn ' + p.stock));
  li.append(name, el('div', 'product-desc', p.description || ''), foot);
  return li;
}

$('searchForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  await withBusy($('search'), 'Đang tìm…', async () => {
    const { status, data } = await api('GET', '/products?search=' + encodeURIComponent($('q').value));
    const list = $('products');
    list.replaceChildren();
    if (status !== 200 || !Array.isArray(data)) return showError($('productsMsg'), status, data);
    if (data.length === 0) return setAlert($('productsMsg'), 'info', 'Không có sản phẩm nào khớp.');
    setAlert($('productsMsg'), 'ok', 'Tìm thấy ' + data.length + ' sản phẩm.');
    for (const p of data) list.appendChild(productCard(p));
  });
});

// ---------- 3. Xem đơn hàng (kết quả hiện ngay bên dưới) ----------
const STATUS_LABEL = {
  pending: 'Chờ thanh toán',
  paid: 'Đã thanh toán',
  shipped: 'Đang giao',
  cancelled: 'Đã hủy',
};

function orderCard(o) {
  const card = el('div', 'order');

  const head = el('div', 'order-head');
  const title = el('div');
  title.append(el('h3', '', 'Đơn #' + o.id), el('div', 'order-owner', 'Chủ đơn: user ' + o.user_id));
  const known = Object.prototype.hasOwnProperty.call(STATUS_LABEL, o.status);
  head.append(title, el('span', 'status' + (known ? ' ' + o.status : ''), known ? STATUS_LABEL[o.status] : String(o.status)));

  const body = el('div', 'order-body');

  // Nếu server để lộ đơn của người khác thì nói rõ ngay trên giao diện
  const me = token ? decodePayload(token) : null;
  if (me && me.role !== 'admin' && Number(me.sub) !== Number(o.user_id)) {
    const warn = el('div', 'alert warn');
    warn.append(
      el('strong', '', 'Đơn này thuộc về user ' + o.user_id + ', không phải của bạn.'),
      ' Server lẽ ra phải trả 403 (lỗi phân quyền tầng 2).'
    );
    body.append(warn);
  }

  const meta = el('dl', 'meta');
  for (const [label, value] of [
    ['Ngày đặt', when(o.created_at)],
    ['Địa chỉ giao hàng', o.shipping_address],
    ['Tổng tiền', money(o.total)],
  ]) {
    const box = el('div');
    box.append(el('dt', '', label), el('dd', '', String(value)));
    meta.append(box);
  }
  body.append(meta);

  const items = Array.isArray(o.items) ? o.items : [];
  const table = el('table', 'items');
  const headRow = el('tr');
  for (const [text, cls] of [['Sản phẩm', ''], ['SL', 'num'], ['Đơn giá', 'num'], ['Thành tiền', 'num']]) {
    headRow.append(el('th', cls, text));
  }
  const thead = el('thead');
  thead.append(headRow);
  const tbody = el('tbody');
  for (const it of items) {
    const tr = el('tr');
    tr.append(
      el('td', '', 'Sản phẩm #' + it.product_id),
      el('td', 'num', String(it.quantity)),
      el('td', 'num', money(it.unit_price)),
      el('td', 'num', money(Number(it.unit_price) * Number(it.quantity)))
    );
    tbody.append(tr);
  }
  const foot = el('tfoot');
  const footRow = el('tr');
  const label = el('td', '', 'Tổng cộng');
  label.colSpan = 3;
  footRow.append(label, el('td', 'num', money(o.total)));
  foot.append(footRow);
  table.append(thead, tbody, foot);
  const wrap = el('div', 'table-wrap');
  wrap.append(table);
  body.append(wrap);

  const raw = el('details', 'raw');
  raw.append(el('summary', '', 'Xem JSON gốc'), el('pre', '', JSON.stringify(o, null, 2)));
  body.append(raw);

  card.append(head, body);
  return card;
}

$('orderForm').addEventListener('submit', async (ev) => {
  ev.preventDefault();
  await withBusy($('viewOrder'), 'Đang tải…', async () => {
    const { status, data } = await api('GET', '/orders/' + encodeURIComponent($('orderId').value));
    const box = $('orderResult');
    box.replaceChildren();
    if (status === 200 && data && typeof data === 'object') box.append(orderCard(data));
    else showError(box, status, data);
  });
});

// ---------- 4. Nhận xét ----------
function updateHint() {
  $('reviewHint').textContent = 'Đang thao tác trên đơn #' + ($('orderId').value || '?') + ' (đổi id ở mục 3).';
}
$('orderId').addEventListener('input', updateHint);

$('postReview').addEventListener('click', () => withBusy($('postReview'), 'Đang gửi…', async () => {
  const { status, data } = await api('POST', '/orders/' + encodeURIComponent($('orderId').value) + '/reviews', {
    comment: $('comment').value,
  });
  if (status === 201) {
    $('comment').value = '';
    setAlert($('reviewMsg'), 'ok', 'Đã gửi nhận xét.', 'Bấm "Tải nhận xét" để xem danh sách.');
  } else {
    showError($('reviewMsg'), status, data);
  }
}));

$('loadReviews').addEventListener('click', () => withBusy($('loadReviews'), 'Đang tải…', async () => {
  const { status, data } = await api('GET', '/orders/' + encodeURIComponent($('orderId').value) + '/reviews');
  const list = $('reviews');
  list.replaceChildren();
  if (status !== 200 || !Array.isArray(data)) return showError($('reviewMsg'), status, data);
  if (data.length === 0) return setAlert($('reviewMsg'), 'info', 'Đơn này chưa có nhận xét.');
  setAlert($('reviewMsg'), '');
  for (const r of data) {
    const li = el('li', 'review');
    const text = el('div', 'review-text');
    renderReview(text, r);
    li.append(text, el('div', 'review-date', when(r.created_at)));
    list.appendChild(li);
  }
}));

refreshWho();
updateHint();
