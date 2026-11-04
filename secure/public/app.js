// Frontend tối giản cho demo. BẢN ĐÃ SỬA: hiển thị dữ liệu bằng textContent.
const $ = (id) => document.getElementById(id);
let token = localStorage.getItem('token');

function decodePayload(t) {
  try {
    const part = t.split('.')[1].replace(/-/g, '+').replace(/_/g, '/');
    return JSON.parse(atob(part)); // payload của JWT chỉ là base64, ai cũng đọc được
  } catch (e) {
    return null;
  }
}

function refreshWho() {
  const p = token ? decodePayload(token) : null;
  $('who').textContent = p
    ? 'Đang đăng nhập: user ' + p.sub + ', role ' + p.role
    : 'Chưa đăng nhập';
}

async function api(method, path, body) {
  const headers = { 'Content-Type': 'application/json' };
  if (token) headers.Authorization = 'Bearer ' + token;
  const res = await fetch(path, { method, headers, body: body ? JSON.stringify(body) : undefined });
  const text = await res.text();
  let data;
  try { data = JSON.parse(text); } catch (e) { data = text; }
  $('out').textContent = method + ' ' + path + '\n=> HTTP ' + res.status + '\n' + JSON.stringify(data, null, 2);
  return { status: res.status, data };
}

$('login').addEventListener('click', async () => {
  const { status, data } = await api('POST', '/login', {
    email: $('email').value,
    password: $('password').value,
  });
  if (status === 200) {
    token = data.token;
    localStorage.setItem('token', token);
  }
  refreshWho();
});

$('logout').addEventListener('click', () => {
  token = null;
  localStorage.removeItem('token');
  refreshWho();
});

$('search').addEventListener('click', async () => {
  const { status, data } = await api('GET', '/products?search=' + encodeURIComponent($('q').value));
  const list = $('products');
  list.innerHTML = '';
  if (status !== 200 || !Array.isArray(data)) return;
  for (const p of data) {
    const li = document.createElement('li');
    // SỬA #3: tạo phần tử rồi gán bằng textContent -> dữ liệu luôn là chữ, không bao giờ là mã
    const b = document.createElement('b');
    b.textContent = p.name;
    li.append(b, ' - ' + p.price + ' đ (còn ' + p.stock + ')');
    list.appendChild(li);
  }
});

$('viewOrder').addEventListener('click', () => {
  api('GET', '/orders/' + encodeURIComponent($('orderId').value));
});

$('postReview').addEventListener('click', () => {
  api('POST', '/orders/' + encodeURIComponent($('orderId').value) + '/reviews', {
    comment: $('comment').value,
  });
});

$('loadReviews').addEventListener('click', async () => {
  const { status, data } = await api('GET', '/orders/' + encodeURIComponent($('orderId').value) + '/reviews');
  const list = $('reviews');
  list.innerHTML = '';
  if (status !== 200 || !Array.isArray(data)) return;
  for (const r of data) {
    const li = document.createElement('li');
    // SỬA #3: nhận xét hiển thị như chữ thuần; thêm CSP ở server làm lớp bảo vệ thứ hai
    const b = document.createElement('b');
    b.textContent = r.email;
    li.append(b, ': ' + r.comment);
    list.appendChild(li);
  }
});

refreshWho();
