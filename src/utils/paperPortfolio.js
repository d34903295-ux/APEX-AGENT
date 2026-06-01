// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — SIMULATED FUNDS (Demo + Live Paper)
// Shared portfolio math — single source of truth for balances & holdings
// ════════════════════════════════════════════════════════════════════

export const TRADE_BUY_TYPES = ['COMPRA', 'TRADE_BUY', 'BUY', 'MARKET BUY'];
export const TRADE_SELL_TYPES = ['VENTA', 'TRADE_SELL', 'SELL', 'MARKET SELL'];
export const DEPOSIT_TYPES = ['DEPÓSITO', 'DEPOSITO', 'DEPOSIT'];
export const WITHDRAW_TYPES = ['RETIRO', 'WITHDRAWAL', 'WITHDRAW'];

export const isBuyType = (type) => TRADE_BUY_TYPES.includes(String(type || '').toUpperCase());
export const isSellType = (type) => TRADE_SELL_TYPES.includes(String(type || '').toUpperCase());
export const isTradeType = (type) => isBuyType(type) || isSellType(type);
export const isDepositType = (type) => DEPOSIT_TYPES.includes(String(type || '').toUpperCase());
export const isWithdrawType = (type) => WITHDRAW_TYPES.includes(String(type || '').toUpperCase());

/** USD amount always positive for trade math */
export const normalizeUsdAmount = (tx) =>
  Math.abs(parseFloat(tx?.amountUsd ?? tx?.amount ?? 0)) || 0;

export const resolveUnitPrice = (tx, marketData, symbol) => {
  const fromTx = parseFloat(tx?.price ?? 0);
  if (fromTx > 0) return fromTx;
  const mItem = getMarketItem(marketData, symbol);
  const fromMarket = parseFloat(mItem?.price ?? 0);
  return fromMarket > 0 ? fromMarket : 0;
};

export const normalizeAssetQty = (tx, usdAmount, unitPrice) => {
  const price = parseFloat(unitPrice || tx?.price || 0);
  if (!price || price <= 0) return 0;
  const fromTx = parseFloat(tx?.units ?? tx?.amountAsset ?? 0);
  if (fromTx > 0) return fromTx;
  return usdAmount / price;
};

/** Registro unificado para ledger + factura */
export const buildTradeTxRecord = ({
  idPrefix = 'tx',
  tx,
  isBuy,
  isSell,
  usdAmount,
  unitPrice,
  assetQty,
  mItem,
  status,
  paper = false,
}) => {
  const displayType = isBuy ? 'COMPRA' : isSell ? 'VENTA' : tx.type;
  const sym = tx.asset;
  const name = mItem?.name || tx.assetName || sym;
  const qty = Number(assetQty) || 0;
  const price = Number(unitPrice) || 0;
  const total = Number(usdAmount) || 0;

  return {
    id: `${idPrefix}_${Date.now()}`,
    date: new Date().toISOString(),
    type: displayType,
    desc: paper
      ? `[PAPER] ${displayType} ${qty.toLocaleString('en-US', { maximumFractionDigits: 6 })} ${sym} @ $${price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`
      : `${displayType} ${qty.toLocaleString('en-US', { maximumFractionDigits: 6 })} ${sym} @ $${price.toLocaleString('en-US', { minimumFractionDigits: 2 })}`,
    asset: sym,
    assetName: name,
    amount: isBuy ? -total : total,
    amountUsd: total,
    price,
    units: qty,
    total,
    color: isBuy ? 'cyan' : isSell ? 'gold' : 'emerald',
    status,
  };
};

export const getMarketItem = (marketData, symbol) =>
  (marketData || []).find(
    (m) => m.symbol === symbol || m.symbol === `${symbol}/USD` || m.symbol?.replace('/USD', '') === symbol
  );

/** Holdings row shape for UI (Holdings tab, Assets, etc.) */
export const normalizeHoldingRow = (h, marketItem = null) => {
  const symbol = h?.symbol || '?';
  const amount = Number(h?.amount) || 0;
  const priceNow = Number(
    marketItem?.price ?? h?.priceNow ?? h?.currentPrice ?? h?.costAvg ?? 0
  ) || 0;
  const value = Number(h?.value) ?? amount * priceNow;
  const costAvg = Number(h?.costAvg) || (amount > 0 ? value / amount : priceNow);

  return {
    ...h,
    id: h?.id || `h_${symbol}${h?.isPaper ? '_paper' : ''}`,
    symbol,
    name: h?.name || symbol,
    amount,
    costAvg,
    priceNow,
    currentPrice: priceNow,
    total: value,
    value,
    type: h?.type || (['BTC', 'ETH', 'SOL', 'BNB'].includes(symbol) ? 'crypto' : 'equity'),
    dayChangePct: Number(h?.dayChangePct) || 0,
  };
};

/** Weighted average cost on buy */
export const applyBuyToHolding = (existing, assetQty, usdAmount, unitPrice, mItem, isPaper = false) => {
  if (!existing) {
    const sym = mItem?.symbol || 'ASSET';
    return {
      symbol: sym,
      name: mItem?.name || sym,
      type: mItem?.type || 'equity',
      amount: assetQty,
      costAvg: unitPrice,
      currentPrice: unitPrice,
      priceNow: unitPrice,
      value: usdAmount,
      dayChangePct: 0,
      ...(isPaper ? { isPaper: true } : {}),
    };
  }

  const oldAmt = Number(existing.amount) || 0;
  const oldCost = Number(existing.costAvg) || Number(existing.currentPrice) || unitPrice;
  const newAmt = oldAmt + assetQty;
  const newCostAvg = newAmt > 0 ? (oldAmt * oldCost + usdAmount) / newAmt : unitPrice;
  const newValue = newAmt * unitPrice;

  return {
    ...existing,
    amount: newAmt,
    costAvg: newCostAvg,
    currentPrice: unitPrice,
    priceNow: unitPrice,
    value: newValue,
    ...(isPaper ? { isPaper: true } : {}),
  };
};

export const applySellToHolding = (existing, assetQty, unitPrice) => {
  const oldAmt = Number(existing?.amount) || 0;
  const newAmt = oldAmt - assetQty;
  if (newAmt <= 0.000001) return null;

  const newValue = newAmt * unitPrice;
  return {
    ...existing,
    amount: newAmt,
    currentPrice: unitPrice,
    priceNow: unitPrice,
    value: newValue,
  };
};

export const sumHoldingsByType = (holdings) => {
  let crypto = 0;
  let equity = 0;
  (holdings || []).forEach((h) => {
    const v = Number(h.value) ?? (Number(h.amount) || 0) * (Number(h.currentPrice) || 0);
    if (h.type === 'crypto') crypto += v;
    else equity += v;
  });
  return { crypto, equity };
};

export const recalculatePortfolioFromHoldings = (cash, holdings, extra = {}) => {
  const safeCash = Number(cash) || 0;
  const { crypto, equity } = sumHoldingsByType(holdings);
  return {
    ...extra,
    cash: safeCash,
    crypto,
    equity,
    totalValue: safeCash + crypto + equity,
  };
};

/** Revalue demo/paper holdings with live market prices */
export const revalueHoldingsWithMarket = (holdings, marketData) =>
  (holdings || []).map((h) => {
    const mItem = getMarketItem(marketData, h.symbol);
    const currentPrice = mItem ? Number(mItem.price) || 0 : Number(h.currentPrice) || 0;
    const amount = Number(h.amount) || 0;
    const value = amount * currentPrice;
    return normalizeHoldingRow({ ...h, currentPrice, value }, mItem);
  });

/** Spendable USD: demo cash or live paper wallet */
export const getSpendableCash = (portfolio, isDemo) => {
  if (isDemo) return Number(portfolio?.cash) || 0;
  const paper = Number(portfolio?.paperCash) || 0;
  if (paper > 0) return paper;
  return Number(portfolio?.cash) || 0;
};

/**
 * Merge real Wallbit portfolio (from API cache) + live paper layer for display.
 * paper cash/holdings are ADDITIVE — never double-count inside real totalValue.
 */
export const buildMergedLivePortfolio = (realBase, paperData, marketData = []) => {
  const base = realBase || { totalValue: 0, cash: 0, equity: 0, crypto: 0, dayChange: 0, dayChangePct: 0 };
  const paperCash = Number(paperData?.cash) || 0;
  const paperHoldingsRaw = paperData?.holdings || [];

  if (!paperCash && !paperHoldingsRaw.length) {
    return { ...base, paperCash: 0, spendableCash: Number(base.cash) || 0 };
  }

  const paperHoldings = revalueHoldingsWithMarket(
    paperHoldingsRaw.map((ph) => ({ ...ph, isPaper: true })),
    marketData
  );
  const { crypto: paperCrypto, equity: paperEquity } = sumHoldingsByType(paperHoldings);

  const realTotal = Number(base.totalValue) || (Number(base.cash) || 0) + (Number(base.equity) || 0) + (Number(base.crypto) || 0);

  return {
    ...base,
    paperCash,
    spendableCash: paperCash,
    crypto: (Number(base.crypto) || 0) + paperCrypto,
    equity: (Number(base.equity) || 0) + paperEquity,
    totalValue: realTotal + paperCash + paperCrypto + paperEquity,
  };
};

/** Elimina filas corruptas (símbolo ?, cash fantasma, qty 0 sin valor) */
export const sanitizeHoldingsList = (holdings) =>
  (holdings || []).filter((h) => {
    const sym = String(h?.symbol || '').trim().toUpperCase();
    if (!sym || sym === '?' || sym === 'ASSET' || sym === 'USD') return false;
    const qty = Number(h.qty ?? h.amount) || 0;
    const val = Number(h.total ?? h.value) || 0;
    if (qty <= 0.0000001 && val <= 0.01) return false;
    return true;
  });

/**
 * Formato unificado para AssetsTab / Holdings (qty, priceNow, total, pnl).
 */
export const toAssetsRow = (h, marketData = []) => {
  const sym = String(h?.symbol || '').trim();
  if (!sym) return null;

  const mItem = getMarketItem(marketData, sym);
  const base = normalizeHoldingRow(h, mItem);
  const qty = Number(base.amount) || Number(h.qty) || 0;
  let priceNow = Number(base.priceNow) || Number(h.priceNow) || Number(h.currentPrice) || 0;
  if (priceNow <= 0 && mItem?.price) priceNow = Number(mItem.price);

  let costAvg = Number(base.costAvg) || Number(h.costAvg) || 0;
  if (costAvg <= 0 && qty > 0) {
    costAvg = Number(h.costAvg) || (Number(h.total) / qty) || priceNow;
  }

  const total = Number(base.total) || Number(h.total) || Number(h.value) || qty * priceNow;
  const pnl = typeof h.pnl === 'number' ? h.pnl : total - qty * costAvg;
  const pnlPct = costAvg > 0 ? ((priceNow - costAvg) / costAvg) * 100 : 0;

  return {
    ...base,
    qty,
    amount: qty,
    costAvg,
    priceNow,
    total,
    value: total,
    pnl,
    pnlPct,
    isPaper: !!h.isPaper,
    isDemo: !!h.isDemo,
    isLive: !!h.isLive && !h.isPaper && !h.isDemo,
  };
};

/** Lista final ordenada: simulados primero, luego por valor */
export const prepareHoldingsForUI = (holdings, marketData = [], options = {}) => {
  const { isDemo = false } = options;
  const rows = (holdings || [])
    .map((h) => toAssetsRow({ ...h, isDemo: isDemo || h.isDemo }, marketData))
    .filter(Boolean);

  return sanitizeHoldingsList(rows).sort((a, b) => {
    const aSim = a.isPaper || a.isDemo;
    const bSim = b.isPaper || b.isDemo;
    if (aSim !== bSim) return aSim ? -1 : 1;
    return (b.total || 0) - (a.total || 0);
  });
};

/** Composición cash/equity/crypto coherente con filas visibles */
export const computePortfolioComposition = (portfolio, holdings, { isDemo = false } = {}) => {
  const cashVal = isDemo
    ? Number(portfolio?.cash) || 0
    : Number(portfolio?.paperCash) > 0
      ? Number(portfolio.paperCash)
      : Number(portfolio?.cash) || 0;

  let equity = 0;
  let crypto = 0;
  (holdings || []).forEach((h) => {
    const v = Number(h.total ?? h.value) || 0;
    if (h.type === 'crypto') crypto += v;
    else equity += v;
  });

  const total = cashVal + equity + crypto || Number(portfolio?.totalValue) || 1;
  const pct = (v) => Math.max(0, Math.min(100, (v / total) * 100));

  return {
    total,
    cash: cashVal,
    equity,
    crypto,
    segments: [
      { label: 'Cash', pct: pct(cashVal), color: '#00D1FF' },
      { label: 'Equity', pct: pct(equity), color: '#FBBF24' },
      { label: 'Crypto', pct: pct(crypto), color: '#34D399' },
    ],
  };
};

export const mergeLiveHoldings = (realHoldings, paperData, marketData = []) => {
  const market = marketData || [];
  const paperRaw = (paperData?.holdings || []).map((ph) => ({ ...ph, isPaper: true }));
  const paperRows = prepareHoldingsForUI(paperRaw, market);

  const realRows = prepareHoldingsForUI(
    (realHoldings || []).map((h) => ({ ...h, isLive: true, isPaper: false })),
    market
  ).map((r) => ({
    ...r,
    name: paperRows.some((p) => p.symbol === r.symbol)
      ? `${r.name || r.symbol} (Wallbit)`
      : r.name || r.symbol,
    isLive: true,
  }));

  return sanitizeHoldingsList([...paperRows, ...realRows]);
};

export const mergeLiveTransactions = (realTxs, paperData) => {
  const paperTxs = paperData?.transactions || [];
  if (!paperTxs.length) return realTxs || [];
  return [...paperTxs, ...(realTxs || [])].sort(
    (a, b) => new Date(b.date).getTime() - new Date(a.date).getTime()
  );
};

/** Map TRADE_BUY / voice types → SimModal COMPRA|VENTA */
export const toSimModalType = (type) => {
  const t = String(type || '').toUpperCase();
  if (TRADE_BUY_TYPES.includes(t)) return 'COMPRA';
  if (TRADE_SELL_TYPES.includes(t)) return 'VENTA';
  return type;
};

export const presetAssetSymbol = (preselectedAsset) =>
  typeof preselectedAsset === 'string'
    ? preselectedAsset
    : preselectedAsset?.symbol || '';

export const getDataMode = (isDemo, livePaperEnabled) => {
  if (isDemo) return 'demo';
  if (livePaperEnabled) return 'paper';
  return 'real';
};

export const buildPaperOnlyPortfolio = (paperData, marketData) => {
  const paperCash = Number(paperData?.cash) || 0;
  const paperHoldingsRaw = (paperData?.holdings || []).map((ph) => ({ ...ph, isPaper: true }));
  const paperHoldings = revalueHoldingsWithMarket(paperHoldingsRaw, marketData);
  const { crypto, equity } = sumHoldingsByType(paperHoldings);
  return {
    totalValue: paperCash + crypto + equity,
    cash: paperCash,
    paperCash,
    spendableCash: paperCash,
    crypto,
    equity,
    dayChange: 0,
    dayChangePct: 0,
    dataMode: 'paper'
  };
};

export const buildRealOnlyPortfolio = (realBase) => {
  return {
    ...realBase,
    paperCash: 0,
    spendableCash: Number(realBase?.cash) || 0,
    dataMode: 'real'
  };
};

export const getPaperOnlyHoldings = (paperData, marketData) => {
  const paperHoldingsRaw = (paperData?.holdings || []).map((ph) => ({ ...ph, isPaper: true }));
  return prepareHoldingsForUI(paperHoldingsRaw, marketData, { isDemo: false });
};

export const getRealOnlyHoldings = (realHoldings, marketData) => {
  const rows = (realHoldings || []).map((h) => ({ ...h, isLive: true, isPaper: false }));
  return prepareHoldingsForUI(rows, marketData, { isDemo: false });
};

export const getPaperOnlyTransactions = (paperData) => {
  return paperData?.transactions || [];
};
