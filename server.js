#!/usr/bin/env node
/*
 * Zero-dependency dev server for Youtyers.
 *   - serves the static site (index.html)
 *   - exposes /api/cobalt as a same-origin relay to the Cobalt API instance
 *
 *   node server.js            # http://0.0.0.0:3000
 *   PORT=8080 node server.js
 *
 * The browser talks to Cobalt directly first (fast, streams the file from the
 * instance). The relay is only used as a fallback when CORS / network blocks
 * a direct call.
 */
'use strict';
const http = require('http');
const fs = require('fs');
const path = require('path');

const ROOT = __dirname;
const PORT = Number(process.env.PORT || 3000);
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

function sendJson(res, status, body) {
  res.writeHead(status, {
    'Content-Type': 'application/json; charset=utf-8',
    'Cache-Control': 'no-store',
    'Access-Control-Allow-Origin': '*'
  });
  res.end(JSON.stringify(body));
}

async function relay(req, res, url) {
  const target = normalizeApi(url.searchParams.get('api'));
  if (!target) return sendJson(res, 400, { status: 'error', error: { code: 'error.api.link.invalid', context: { hint: 'Invalid ?api= URL' } } });

  const headers = { 'Accept': 'application/json' };
  if (req.headers.authorization) headers['Authorization'] = req.headers.authorization;
  let body;
  if (req.method === 'POST') {
    headers['Content-Type'] = 'application/json';
    body = await new Promise((resolve, reject) => {
      let raw = '';
      req.on('data', c => { raw += c; if (raw.length > 1e6) reject(new Error('body too large')); });
      req.on('end', () => resolve(raw));
      req.on('error', reject);
    });
    if (!body) return sendJson(res, 400, { status: 'error', error: { code: 'error.api.link.invalid' } });
  }

  const ctrl = new AbortController();
  const timer = setTimeout(() => ctrl.abort(), 60000);
  try {
    const upstream = await fetch(target, {
      method: req.method === 'POST' ? 'POST' : 'GET',
      headers, body, signal: ctrl.signal
    });
    const text = await upstream.text();
    res.writeHead(upstream.status, {
      'Content-Type': upstream.headers.get('content-type') || 'application/json; charset=utf-8',
      'Cache-Control': 'no-store',
      'Access-Control-Allow-Origin': '*'
    });
    res.end(text);
  } catch (e) {
    sendJson(res, 502, {
      status: 'error',
      error: { code: 'error.api.fetch.fail', context: { message: 'Relay could not reach the Cobalt instance: ' + (e.message || e) } }
    });
  } finally { clearTimeout(timer); }
}

const MIME = { '.html': 'text/html; charset=utf-8', '.js': 'text/javascript; charset=utf-8', '.css': 'text/css; charset=utf-8', '.svg': 'image/svg+xml', '.png': 'image/png', '.ico': 'image/x-icon', '.json': 'application/json' };

http.createServer((req, res) => {
  const url = new URL(req.url, 'http://' + (req.headers.host || 'localhost'));
  if (url.pathname === '/api/cobalt') {
    if (req.method === 'OPTIONS') {
      res.writeHead(204, { 'Access-Control-Allow-Origin': '*', 'Access-Control-Allow-Headers': '*', 'Access-Control-Allow-Methods': 'GET,POST,OPTIONS' });
      return res.end();
    }
    if (req.method !== 'GET' && req.method !== 'POST') return sendJson(res, 405, { error: 'method not allowed' });
    return relay(req, res, url).catch(() => sendJson(res, 502, { status: 'error', error: { code: 'error.api.fetch.fail' } }));
  }
  let file = url.pathname === '/' ? '/index.html' : url.pathname;
  file = path.normalize(file).replace(/^(\.\.[/\\])+/, '');
  const full = path.join(ROOT, file);
  if (!full.startsWith(ROOT)) { res.writeHead(403); return res.end('forbidden'); }
  fs.readFile(full, (err, data) => {
    if (err) { res.writeHead(404, { 'Content-Type': 'text/plain' }); return res.end('not found'); }
    res.writeHead(200, { 'Content-Type': MIME[path.extname(full)] || 'application/octet-stream', 'Cache-Control': 'no-cache' });
    res.end(data);
  });
}).listen(PORT, '0.0.0.0', () => {
  console.log('Youtyers running on http://0.0.0.0:' + PORT + '  (Cobalt: ' + DEFAULT_API + ')');
});
