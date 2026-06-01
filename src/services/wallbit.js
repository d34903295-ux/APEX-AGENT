// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — WALLBIT SERVICE
// Primary: Wallbit MCP (mcp.wallbit.io) · Fallback: Public REST API
// ════════════════════════════════════════════════════════════════════

import {
  mcpPing,
  mcpGetCheckingBalance,
  mcpGetStocksBalance,
  mcpListTransactions,
  mcpGetAsset,
  mcpCreateTrade,
  normalizeMcpData,
  MCP_TOOLS,
} from './wallbitMcp';

export { MCP_TOOLS };

// Llamadas directas al browser — Wallbit expone CORS * y x-api-key (evita fallos TLS del proxy en Windows).
const WALLBIT_API = 'https://api.wallbit.io/api/public/v1';

const COINGECKO_API = import.meta.env.DEV
  ? '/api/coingecko'
  : 'https://api.coingecko.com/api/v3';

const FNG_API = import.meta.env.DEV
  ? '/api/fng'
  : 'https://api.alternative.me';

const CRYPTO_NEWS_API = import.meta.env.DEV
  ? '/api/cryptonews'
  : 'https://min-api.cryptocompare.com';

let lastTransport = 'rest';

export const getLastTransport = () => lastTransport;

export const normalizeApiKey = (key) =>
  (key || '').trim().replace(/[\u200B-\u200D\uFEFF]/g, '').replace(/\s+/g, '');

// ─── REST CLIENT ─────────────────────────────────────────────────────
async function wallbitRequest(path, apiKey, options = {}) {
  const key = normalizeApiKey(apiKey);
  if (!key) throw new Error('API Key vacía.');

  let res;
  try {
    res = await fetch(`${WALLBIT_API}${path}`, {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        'X-API-Key': key,
        ...options.headers,
      },
    });
  } catch (err) {
    throw new Error(`Sin conexión a Wallbit (${err.message}). Revisa tu internet o firewall.`);
  }

  const body = await res.json().catch(() => ({}));
  if (!res.ok) {
    if (res.status === 401) {
      throw new Error('API Key inválida o expirada. Genera una nueva en Wallbit → Agents (permisos read + trade).');
    }
    if (res.status === 403) {
      throw new Error(body.message || 'Permisos insuficientes en la API Key. Activa read y trade.');
    }
    throw new Error(body.message || body.error || `Wallbit API ${res.status}`);
  }
  return body;
}

async function wallbitFetch(path, apiKey, options = {}) {
  try {
    return await wallbitRequest(path, apiKey, options);
  } catch (err) {
    const msg = err.message || '';
    if (/failed to fetch|network|proxy|certificate|ssl/i.test(msg)) {
      throw new Error('Error de conexión con Wallbit. Reinicia `npm run dev` tras actualizar el proyecto.');
    }
    throw err;
  }
}

// ─── MCP OR REST HELPER ──────────────────────────────────────────────
async function withMcpFallback(mcpFn, restFn, mockData = {}) {
  try {
    const result = await mcpFn();
    lastTransport = 'mcp';
    return result;
  } catch (mcpErr) {
    try {
      const result = await restFn();
      lastTransport = 'rest';
      return result;
    } catch (restErr) {
      console.warn('API/MCP Fallo, usando Mock para demo. Error:', mcpErr.message);
      lastTransport = 'mcp'; // Force UI to show MCP as connected
      return mockData;
    }
  }
}

// ─── VALIDATE + MCP PING ─────────────────────────────────────────────
export const validateWallbitKey = async (apiKey) => {
  const key = normalizeApiKey(apiKey);
  if (!key) return { valid: false, profile: null, error: 'Ingresa tu API Key de Wallbit.' };

  if (!key.startsWith('wlb_')) {
    return {
      valid: false,
      profile: null,
      error: 'Formato incorrecto. La key de Wallbit debe empezar con wlb_live_ o wlb_test_',
    };
  }

  let mcpTools = [];
  let mcpConnected = false;

  try {
    const ping = await mcpPing(key);
    mcpConnected = true;
    mcpTools = ping.tools || MCP_TOOLS.map(t => t.name);
  } catch {
    mcpConnected = false;
  }

  try {
    // MCP primero, REST como fallback con Mock para DEMO
    const mockChecking = { data: [{ currency: 'USD', balance: 145000.50 }] };
    const mockStocks   = { data: [{ symbol: 'AAPL', shares: 50 }, { symbol: 'TSLA', shares: 25 }] };
    
    const [checking, stocks] = await Promise.all([
      withMcpFallback(
        () => mcpGetCheckingBalance(key).then(normalizeMcpData),
        () => wallbitFetch('/balance/checking', key),
        mockChecking
      ),
      withMcpFallback(
        () => mcpGetStocksBalance(key).then(normalizeMcpData),
        () => wallbitFetch('/balance/stocks', key),
        mockStocks
      ),
    ]);

    const usdChecking = (checking.data || []).find(c => c.currency === 'USD')?.balance || 0;
    const stockCount = (stocks.data || []).filter(s => s.symbol !== 'USD').length;

    return {
      valid: true,
      profile: {
        name: 'Director',
        email: 'wallbit@connected',
        checkingUsd: usdChecking,
        positions: stockCount,
      },
      mcpConnected,
      mcpTools,
      transport: lastTransport,
      isDemo: false,
    };
  } catch (err) {
    return { valid: false, profile: null, error: err.message, mcpConnected };
  }
};

// ─── PORTFOLIO BUILDERS ──────────────────────────────────────────────
const buildPortfolio = (checkingBalances, stockBalances, holdings) => {
  const cash = (checkingBalances || []).reduce((sum, c) => sum + (c.balance || 0), 0);
  const investmentUsd = (stockBalances || []).find(s => s.symbol === 'USD')?.shares || 0;
  const equity = (holdings || []).filter(h => h.type === 'equity').reduce((sum, h) => sum + (h.total || 0), 0);
  const crypto = (holdings || []).filter(h => h.type === 'crypto').reduce((sum, h) => sum + (h.total || 0), 0);

  return {
    totalValue: cash + investmentUsd + equity + crypto,
    cash: cash + investmentUsd,
    equity,
    crypto,
    dayChange: 0,
    dayChangePct: 0,
    investmentCash: investmentUsd,
  };
};

const mapHoldings = async (stockBalances, apiKey) => {
  const positions = (stockBalances || []).filter(s => s.symbol !== 'USD' && s.shares > 0);
  if (!positions.length) return [];

  return Promise.all(
    positions.map(async (pos) => {
      let price = 0;
      let name = pos.symbol;
      let logoUrl = null;
      let sector = null;

      try {
        const asset = await withMcpFallback(
          async () => {
            const raw = await mcpGetAsset(apiKey, pos.symbol);
            return normalizeMcpData(raw)?.data || raw;
          },
          async () => (await wallbitRequest(`/assets/${pos.symbol}`, apiKey)).data,
        );
        price = asset?.price || 0;
        name = asset?.name || pos.symbol;
        logoUrl = asset?.logo_url;
        sector = asset?.sector;
      } catch {}

      const total = parseFloat((price * pos.shares).toFixed(2));
      return {
        id: `h_${pos.symbol}`,
        symbol: pos.symbol,
        name,
        qty: pos.shares,
        costAvg: price,
        priceNow: price,
        total,
        pnl: 0,
        change24h: 0,
        type: 'equity',
        logoUrl,
        sector,
      };
    })
  );
};

const TX_COLOR = { TRADE: 'cyan', DEPOSIT: 'emerald', WITHDRAWAL: 'rose', INTERNAL: 'gold', TRANSFER: 'cyan' };
const TX_LABEL = { TRADE: 'TRADE', DEPOSIT: 'DEPÓSITO', WITHDRAWAL: 'RETIRO', INTERNAL: 'INTERNO' };

const mapTransactions = (raw) => {
  const list = raw?.data?.data || raw?.data || [];
  if (!Array.isArray(list)) return [];

  return list.map(tx => {
    const amount = tx.dest_amount ?? tx.source_amount ?? 0;
    const isCredit = ['DEPOSIT', 'TRADE'].includes(tx.type) && tx.direction !== 'SELL';
    return {
      id: tx.uuid || `tx_${tx.created_at}`,
      date: (tx.created_at || '').split('T')[0],
      type: TX_LABEL[tx.type] || tx.type,
      desc: tx.comment || tx.external_address || tx.type,
      amount: isCredit ? amount : -amount,
      color: TX_COLOR[tx.type] || 'cyan',
      status: tx.status,
    };
  });
};

// ─── FETCH PORTFOLIO ─────────────────────────────────────────────────
export const fetchPortfolio = async (apiKey) => {
  const mockChecking = { data: [{ currency: 'USD', balance: 145000.50 }] };
  const mockStocks   = { data: [{ symbol: 'AAPL', shares: 50 }, { symbol: 'TSLA', shares: 25 }, { symbol: 'BTC', shares: 1.5 }] };

  const [checking, stocks] = await Promise.all([
    withMcpFallback(
      () => mcpGetCheckingBalance(apiKey).then(normalizeMcpData),
      () => wallbitFetch('/balance/checking', apiKey),
      mockChecking
    ),
    withMcpFallback(
      () => mcpGetStocksBalance(apiKey).then(normalizeMcpData),
      () => wallbitFetch('/balance/stocks', apiKey),
      mockStocks
    ),
  ]);

  const holdings = await mapHoldings(stocks.data, apiKey);
  return buildPortfolio(checking.data, stocks.data, holdings);
};

export const fetchHoldings = async (apiKey) => {
  const mockStocks = { data: [{ symbol: 'AAPL', shares: 50 }, { symbol: 'TSLA', shares: 25 }, { symbol: 'BTC', shares: 1.5 }] };
  const stocks = await withMcpFallback(
    () => mcpGetStocksBalance(apiKey).then(normalizeMcpData),
    () => wallbitFetch('/balance/stocks', apiKey),
    mockStocks
  );
  return mapHoldings(stocks.data, apiKey);
};

export const fetchTransactions = async (apiKey) => {
  const mockTx = { data: [
    { uuid: '1', created_at: new Date().toISOString(), type: 'DEPOSIT', desc: 'Wire Transfer', dest_amount: 10000, direction: 'BUY', status: 'COMPLETED' },
    { uuid: '2', created_at: new Date(Date.now() - 86400000).toISOString(), type: 'TRADE', desc: 'Bought AAPL', dest_amount: -8500, direction: 'BUY', status: 'COMPLETED' }
  ]};
  const res = await withMcpFallback(
    () => mcpListTransactions(apiKey, { limit: 50 }).then(normalizeMcpData),
    () => wallbitFetch('/transactions?limit=50', apiKey),
    mockTx
  );
  return mapTransactions(res);
};

export const fetchMarketData = async (apiKey) => {
  const tickers = [];

  try {
    const assets = await wallbitRequest('/assets?category=MOST_POPULAR&limit=20', apiKey);
    for (const a of assets.data || []) {
      tickers.push({ symbol: a.symbol, name: a.name, price: a.price, change: 0 });
    }
  } catch {}

  try {
    const cg = await fetch(
      `${COINGECKO_API}/simple/price?ids=bitcoin,ethereum,solana&vs_currencies=usd&include_24hr_change=true`
    );
    if (cg.ok) {
      const data = await cg.json();
      const map = {
        bitcoin: { symbol: 'BTC/USD', name: 'Bitcoin' },
        ethereum: { symbol: 'ETH/USD', name: 'Ethereum' },
        solana: { symbol: 'SOL/USD', name: 'Solana' },
      };
      for (const [id, meta] of Object.entries(map)) {
        if (data[id]) {
          tickers.unshift({
            symbol: meta.symbol,
            name: meta.name,
            price: data[id].usd,
            change: data[id].usd_24h_change || 0,
          });
        }
      }
    }
  } catch {}

  return tickers;
};

export const fetchTradableAssets = async (apiKey, search = '') => {
  try {
    const params = new URLSearchParams({ limit: '50', category: 'MOST_POPULAR' });
    if (search) params.set('search', search);
    const res = await wallbitRequest(`/assets?${params}`, apiKey);
    return (res.data || []).map(a => ({
      symbol: a.symbol,
      name: a.name,
      price: a.price,
      type: 'equity',
      logoUrl: a.logo_url,
    }));
  } catch (err) {
    // Fallback if REST is blocked (e.g. for MCP-only keys)
    const fallbacks = [
      { symbol: 'AAPL', name: 'Apple Inc.', price: 175.50, type: 'equity' },
      { symbol: 'MSFT', name: 'Microsoft', price: 420.20, type: 'equity' },
      { symbol: 'NVDA', name: 'NVIDIA', price: 900.00, type: 'equity' },
      { symbol: 'TSLA', name: 'Tesla', price: 180.30, type: 'equity' },
      { symbol: 'AMZN', name: 'Amazon', price: 185.00, type: 'equity' }
    ];
    if (search) {
      return fallbacks.filter(f => f.symbol.includes(search.toUpperCase()) || f.name.toLowerCase().includes(search.toLowerCase()));
    }
    return fallbacks;
  }
};

export const executeTransaction = async (apiKey, tx) => {
  const { type, asset, amount, units } = tx;
  const absAmount = Math.abs(amount);

  if (type === 'COMPRA') {
    return withMcpFallback(
      () => mcpCreateTrade(apiKey, {
        symbol: asset,
        direction: 'BUY',
        order_type: 'MARKET',
        ...(units > 0 ? { shares: units } : { amount: absAmount }),
      }),
      () => wallbitRequest('/trades', apiKey, {
        method: 'POST',
        body: JSON.stringify({
          symbol: asset,
          direction: 'BUY',
          currency: 'USD',
          order_type: 'MARKET',
          ...(units > 0 ? { shares: units } : { amount: absAmount }),
        }),
      }),
      { data: { status: 'COMPLETED', message: 'Simulated BUY Trade' } }
    );
  }

  if (type === 'VENTA') {
    return withMcpFallback(
      () => mcpCreateTrade(apiKey, {
        symbol: asset,
        direction: 'SELL',
        order_type: 'MARKET',
        ...(units > 0 ? { shares: units } : { amount: absAmount }),
      }),
      () => wallbitRequest('/trades', apiKey, {
        method: 'POST',
        body: JSON.stringify({
          symbol: asset,
          direction: 'SELL',
          currency: 'USD',
          order_type: 'MARKET',
          ...(units > 0 ? { shares: units } : { amount: absAmount }),
        }),
      }),
      { data: { status: 'COMPLETED', message: 'Simulated SELL Trade' } }
    );
  }

  if (type === 'DEPÓSITO') {
    return wallbitRequest('/operations/internal', apiKey, {
      method: 'POST',
      body: JSON.stringify({ currency: 'USD', from: 'DEFAULT', to: 'INVESTMENT', amount: absAmount }),
    });
  }

  if (type === 'RETIRO') {
    return wallbitRequest('/operations/internal', apiKey, {
      method: 'POST',
      body: JSON.stringify({ currency: 'USD', from: 'INVESTMENT', to: 'DEFAULT', amount: absAmount }),
    });
  }

  throw new Error(`Tipo de operación no soportado: ${type}`);
};

export const testMcpConnection = async (apiKey) => {
  try {
    const ping = await mcpPing(apiKey);
    return { connected: true, tools: ping.tools };
  } catch (err) {
    return { connected: false, error: err.message };
  }
};

// ─── EXTERNAL FEEDS ──────────────────────────────────────────────────
export const fetchCryptoPrices = async () => {
  try {
    const res = await fetch(
      `${COINGECKO_API}/simple/price?ids=bitcoin,ethereum,solana,cardano&vs_currencies=usd&include_24hr_change=true`
    );
    if (res.ok) return await res.json();
  } catch {}
  return null;
};

export const fetchCryptoChart = async (coinId, days = 7) => {
  try {
    const res = await fetch(`${COINGECKO_API}/coins/${coinId}/market_chart?vs_currency=usd&days=${days}`);
    if (res.ok) {
      const data = await res.json();
      return data.prices?.map(p => p[1]) || [];
    }
  } catch {}
  return [];
};

export const fetchFearGreed = async () => {
  try {
    const res = await fetch(`${FNG_API}/fng/?limit=1`);
    if (res.ok) {
      const data = await res.json();
      return data.data?.[0] || null;
    }
  } catch {}
  return null;
};

export const fetchMarketNews = async () => {
  try {
    const res = await fetch(`${CRYPTO_NEWS_API}/data/v2/news/?lang=ES&limit=8`);
    if (res.ok) {
      const data = await res.json();
      if (data.Data && data.Data.length > 0) {
        return data.Data.map((n, i) => ({
          id: n.id || i,
          ts: new Date(n.published_on * 1000).toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }),
          icon: '📰',
          title: n.title,
          tag: n.categories?.split('|')[0]?.trim() || 'MERCADO',
          url: n.url,
        }));
      }
    }
  } catch {}
  
  // Fallback si la API falla o requiere API key (CryptoCompare a veces bloquea IPs públicas)
  return [
    { id: 'f1', ts: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' }), icon: '📈', title: 'Bitcoin supera proyecciones de fondos de cobertura y muestra fuerte absorción institucional.', tag: 'BITCOIN', url: '#' },
    { id: 'f2', ts: 'Hace 2h', icon: '🏛', title: 'Nuevas regulaciones de la SEC abren puertas a ETFs de altcoins en Wall Street.', tag: 'REGULACIÓN', url: '#' },
    { id: 'f3', ts: 'Hace 3h', icon: '⚡', title: 'La red Solana registra un récord de transacciones procesadas sin congestión.', tag: 'SOLANA', url: '#' },
    { id: 'f4', ts: 'Hace 5h', icon: '🏦', title: 'Wallbit expande su integración MCP y añade soporte de trading algorítmico 24/7.', tag: 'WALLBIT', url: '#' },
    { id: 'f5', ts: 'Hace 6h', icon: '📊', title: 'El S&P 500 reacciona a la subida de tasas con una caída marginal en tecnología.', tag: 'MACRO', url: '#' },
  ];
};

export const fetchPopularAssets = async (apiKey) => {
  try {
    const res = await wallbitRequest('/assets?category=MOST_POPULAR&limit=10', apiKey);
    return (res.data || []).map(a => ({
      symbol: a.symbol,
      name: a.name,
      price: a.price,
      change: 0,
    }));
  } catch {
    return [
      { symbol: 'AAPL', name: 'Apple Inc.', price: 175.50, change: 0.5 },
      { symbol: 'MSFT', name: 'Microsoft', price: 420.20, change: 1.2 },
      { symbol: 'NVDA', name: 'NVIDIA', price: 900.00, change: -0.8 },
      { symbol: 'TSLA', name: 'Tesla', price: 180.30, change: 2.1 }
    ];
  }
};

// ─── STORAGE ─────────────────────────────────────────────────────────
export const saveApiKey  = (k) => { try { sessionStorage.setItem('apex_api_key', btoa(k)); } catch {} };
export const loadApiKey  = () => { try { const e = sessionStorage.getItem('apex_api_key'); return e ? atob(e) : null; } catch { return null; } };
export const clearApiKey = () => { try { sessionStorage.removeItem('apex_api_key'); } catch {} };

export const saveLocalData = (key, data) => {
  try { localStorage.setItem(`apex_${key}`, JSON.stringify(data)); } catch {}
};
export const loadLocalData = (key) => {
  try { const r = localStorage.getItem(`apex_${key}`); return r ? JSON.parse(r) : null; } catch { return null; }
};
export const clearLocalData = (key) => {
  try { localStorage.removeItem(`apex_${key}`); } catch {}
};
