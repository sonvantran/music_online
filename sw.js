// Service Worker: lưu bản trang + phát nhạc từ bộ nhớ khi mất mạng
const SHELL = "shell-v1";
const AUDIO = "audio-v1";

self.addEventListener("install", e => {
  e.waitUntil(
    caches.open(SHELL)
      .then(c => c.addAll(["./", "./index.html"]))
      .then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", e => {
  e.waitUntil((async () => {
    for (const k of await caches.keys()) {
      if (k !== SHELL && k !== AUDIO) await caches.delete(k);
    }
    await self.clients.claim();
  })());
});

self.addEventListener("fetch", e => {
  const req = e.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);
  if (url.origin !== location.origin) return;

  if (url.pathname.includes("/music/")) e.respondWith(audioResponse(req));
  else if (url.pathname.endsWith("/library.json")) e.respondWith(networkFirst(req));
  else e.respondWith(staleWhileRevalidate(req));
});

// Nhạc: có trong bộ nhớ thì phát từ đó (hỗ trợ tua), không có thì lấy từ mạng
async function audioResponse(req) {
  const cache = await caches.open(AUDIO);
  const hit = await cache.match(req.url);
  if (!hit) return fetch(req);
  const range = req.headers.get("range");
  if (!range) return hit;
  return sliceRange(hit, range);
}

async function sliceRange(res, range) {
  const m = /bytes=(\d*)-(\d*)/.exec(range);
  const buf = await res.arrayBuffer();
  const size = buf.byteLength;
  let start, end;
  if (!m || (m[1] === "" && m[2] === "")) { start = 0; end = size - 1; }
  else if (m[1] === "") { start = Math.max(0, size - parseInt(m[2], 10)); end = size - 1; }
  else {
    start = parseInt(m[1], 10);
    end = m[2] === "" ? size - 1 : Math.min(parseInt(m[2], 10), size - 1);
  }
  if (start >= size) {
    return new Response(null, { status: 416, headers: { "Content-Range": `bytes */${size}` } });
  }
  return new Response(buf.slice(start, end + 1), {
    status: 206,
    headers: {
      "Content-Type": res.headers.get("Content-Type") || "audio/mpeg",
      "Content-Range": `bytes ${start}-${end}/${size}`,
      "Content-Length": String(end - start + 1),
      "Accept-Ranges": "bytes",
    },
  });
}

// library.json: ưu tiên bản mới nhất, mạng chậm quá 4 giây hoặc mất mạng thì dùng bản đã lưu
async function networkFirst(req) {
  const cache = await caches.open(SHELL);
  try {
    const ctl = new AbortController();
    const t = setTimeout(() => ctl.abort(), 4000);
    const res = await fetch(req, { signal: ctl.signal, cache: "no-store" });
    clearTimeout(t);
    if (res.ok) cache.put(req, res.clone());
    return res;
  } catch (err) {
    const hit = await cache.match(req, { ignoreSearch: true });
    return hit || Response.error();
  }
}

// Trang: mở ngay từ bộ nhớ, cập nhật ngầm cho lần sau
async function staleWhileRevalidate(req) {
  const cache = await caches.open(SHELL);
  const hit = await cache.match(req, { ignoreSearch: true });
  const net = fetch(req)
    .then(res => { if (res.ok) cache.put(req, res.clone()); return res; })
    .catch(() => null);
  if (hit) return hit;
  return (await net) || Response.error();
}