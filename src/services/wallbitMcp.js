// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — WALLBIT MCP CLIENT
// Direct browser → mcp.wallbit.io (Authorization header for CORS)
// ════════════════════════════════════════════════════════════════════

const normalizeApiKey = (key) =>
  (key || '').trim().replace(/[\u200B-\u200D\uFEFF]/g, '').replace(/\s+/g, '');

const MCP_URL = 'https://mcp.wallbit.io/mcp';

export const MCP_TOOLS = [
  { name: 'get_checking_balance', label: 'Balance Checking', icon: '💵' },
  { name: 'get_stocks_balance',   label: 'Portfolio Stocks', icon: '📊' },
  { name: 'list_transactions',    label: 'Transacciones',    icon: '📜' },
  { name: 'get_asset',            label: 'Info Asset',       icon: '🔍' },
  { name: 'create_trade',         label: 'Ejecutar Trade',   icon: '⚡' },
];

const mcpHeaders = (apiKey) => {
  const key = normalizeApiKey(apiKey);
  return {
    'Content-Type': 'application/json',
    'Accept': 'application/json',
  // MCP CORS permite Authorization (no x-api-key) desde el browser
    'Authorization': `Bearer ${key}`,
    'X-API-Key': key,
  };
};

// ─── PARSE MCP RESPONSE (JSON or SSE) ────────────────────────────────
const parseMcpBody = (text) => {
  const trimmed = text.trim();
  if (!trimmed) return null;

  if (trimmed.includes('data:')) {
    const lines = trimmed.split('\n').filter(l => l.startsWith('data:'));
    const last = lines[lines.length - 1]?.replace(/^data:\s*/, '');
    if (last && last !== '[DONE]') {
      try { return JSON.parse(last); } catch {}
    }
  }

  try { return JSON.parse(trimmed); } catch {
    const matches = trimmed.match(/\{[\s\S]*\}/g);
    if (matches?.length) {
      for (let i = matches.length - 1; i >= 0; i--) {
        try { return JSON.parse(matches[i]); } catch {}
      }
    }
  }
  return null;
};

const extractToolResult = (payload) => {
  if (!payload) return null;
  if (payload.error) throw new Error(payload.error.message || JSON.stringify(payload.error));

  const result = payload.result;
  if (!result) return null;

  if (result.isError) {
    const errText = result.content?.find(c => c.type === 'text')?.text || 'Error MCP';
    if (/401|invalid|expired|api key/i.test(errText)) {
      throw new Error('API Key rechazada por Wallbit. Verifica que la copiaste completa desde Agents.');
    }
    throw new Error(errText);
  }

  const content = result.content;
  if (Array.isArray(content)) {
    const textBlock = content.find(c => c.type === 'text' && c.text);
    if (textBlock?.text) {
      if (/401|invalid|expired api key/i.test(textBlock.text)) {
        throw new Error('API Key rechazada por Wallbit. Verifica que la copiaste completa desde Agents.');
      }
      try { return JSON.parse(textBlock.text); } catch { return textBlock.text; }
    }
  }

  if (result.structuredContent) return result.structuredContent;
  if (typeof result === 'object' && result.data !== undefined) return result;
  return result;
};

export const mcpCall = async (toolName, args, apiKey) => {
  let res;
  try {
    res = await fetch(MCP_URL, {
      method: 'POST',
      headers: mcpHeaders(apiKey),
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: Date.now(),
        method: 'tools/call',
        params: { name: toolName, arguments: args || {} },
      }),
    });
  } catch (err) {
    throw new Error(`MCP sin conexión: ${err.message}`);
  }

  const text = await res.text();
  if (!res.ok) {
    let msg = `MCP ${res.status}`;
    try {
      const err = parseMcpBody(text);
      msg = err?.error?.message || err?.message || msg;
    } catch {}
    throw new Error(msg);
  }

  return extractToolResult(parseMcpBody(text));
};

export const mcpPing = async (apiKey) => {
  let res;
  try {
    res = await fetch(MCP_URL, {
      method: 'POST',
      headers: mcpHeaders(apiKey),
      body: JSON.stringify({
        jsonrpc: '2.0',
        id: 1,
        method: 'tools/list',
        params: {},
      }),
    });
  } catch (err) {
    throw new Error(`MCP sin conexión: ${err.message}`);
  }

  const text = await res.text();
  const payload = parseMcpBody(text);
  if (!res.ok) throw new Error(payload?.error?.message || `MCP ${res.status}`);

  const tools = payload?.result?.tools || [];
  return { ok: true, tools: tools.map(t => t.name) };
};

export const mcpGetCheckingBalance = (apiKey) =>
  mcpCall('get_checking_balance', {}, apiKey);

export const mcpGetStocksBalance = (apiKey) =>
  mcpCall('get_stocks_balance', {}, apiKey);

export const mcpListTransactions = (apiKey, { page = 1, limit = 50, status } = {}) =>
  mcpCall('list_transactions', { page, limit, ...(status ? { status } : {}) }, apiKey);

export const mcpGetAsset = (apiKey, symbol) =>
  mcpCall('get_asset', { symbol }, apiKey);

export const mcpCreateTrade = (apiKey, { symbol, direction, order_type = 'MARKET', amount, shares, currency = 'USD' }) =>
  mcpCall('create_trade', { symbol, direction, order_type, currency, ...(amount ? { amount } : {}), ...(shares ? { shares } : {}) }, apiKey);

export const normalizeMcpData = (raw) => {
  if (!raw) return null;
  if (raw.data !== undefined) return raw;
  if (Array.isArray(raw)) return { data: raw };
  return { data: raw };
};
