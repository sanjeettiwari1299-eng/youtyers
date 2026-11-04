/* Vercel serverless relay for the Cobalt API.
 * GET  /api/cobalt?api=<instance>   -> instance info (GET /)
 * POST /api/cobalt?api=<instance>   -> cobalt processing (POST /)
 *
 * The browser calls the Cobalt instance directly first; this function is the
 * fallback when the instance blocks cross-origin (CORS) requests.
 */
'use strict';

const DEFAULT_API = process.env.COBALT_API_URL || 'https://youtyers-528be.containers.snapdeploy.app/';

function normalizeApi(raw) {
  const v = String(raw || '').trim() || DEFAULT_API;
  try {
    const u = new URL(v);
    if (u.protocol !== 'https:' && u.protocol !== 'http:') return null;
    u.hash = ''; u.search = '';
    if (!u.pathname.endsWith('/')) u.pathname += '/';
    return u.toString();
  } catch { return null; }
}

module.exports = async function handler(req, res) {
  res.setHeader('Access-Control-Allow-Origin', '*');
  res.setHeader('Access-Control-Allow-Headers', '*');
  res.setHeader('Access-Control-Allow-Methods', 'GET,POST,OPTIONS');
  res.setHeader('Cache-Control', 'no-store');
  if (req.method === 'OPTIONS') { res.statusCode = 204; return res.end(); }
  if (req.method !== 'GET' && req.method !== 'POST') {
    res.statusCode = 405; return res.end(JSON.stringify({ error: 'method not allowed' }));
  }

  const target = normalizeApi(req.query && req.query.api);
  if (!target) {
    res.statusCode = 400;
    return res.end(JSON.stringify({ status: 'error', error: { code: 'error.api.link.invalid' } }));
  }

  const headers = { 'Accept': 'application/json' };
  if (req.headers.authorization) headers['Authorization'] = req.headers.authorization;
  let body;
  if (req.method === 'POST') {
    headers['Content-Type'] = 'application/json';
    body = typeof req.body === 'string' ? req.body : (req.body ? JSON.stringify(req.body) : '');
    if (!body) {
      res.statusCode = 400;
      return res.end(JSON.stringify({ status: 'error', error: { code: 'error.api.link.invalid' } }));
    }
  }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 60000);
  try {
    const upstream = await fetch(target, {
      method: req.method, headers, body, signal: ctrl.signal
    });
    const text = await upstream.text();
    res.setHeader('Content-Type', upstream.headers.get('content-type') || 'application/json; charset=utf-8');
    res.statusCode = upstream.status;
    res.end(text);
  } catch (e) {
    res.statusCode = 502;
    res.setHeader('Content-Type', 'application/json; charset=utf-8');
    res.end(JSON.stringify({
      status: 'error',
      error: { code: 'error.api.fetch.fail', context: { message: 'Relay could not reach the Cobalt instance' } }
    }));
  } finally { clearTimeout(timer); }
};
