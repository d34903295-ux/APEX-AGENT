// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — WALLBIT API HOOK (REWRITTEN & OPTIMIZED)
// MCP-first sync + REST fallback · 30s refresh · Demo Mode
// ════════════════════════════════════════════════════════════════════

import { useState, useEffect, useCallback, useRef } from 'react';
import {
  fetchPortfolio,
  fetchHoldings,
  fetchTransactions,
  fetchMarketData,
  executeTransaction,
  testMcpConnection,
  getLastTransport,
  saveLocalData,
  loadLocalData,
} from '../services/wallbit';
import { MCP_TOOLS } from '../services/wallbitMcp';
import {
  isBuyType,
  isSellType,
  isTradeType,
  isDepositType,
  isWithdrawType,
  normalizeUsdAmount,
  normalizeAssetQty,
  getMarketItem,
  applyBuyToHolding,
  applySellToHolding,
  recalculatePortfolioFromHoldings,
  revalueHoldingsWithMarket,
  buildMergedLivePortfolio,
  mergeLiveHoldings,
  mergeLiveTransactions,
  getSpendableCash,
  getDataMode,
  buildPaperOnlyPortfolio,
  buildRealOnlyPortfolio,
  getPaperOnlyHoldings,
  getRealOnlyHoldings,
  getPaperOnlyTransactions,
  resolveUnitPrice,
  buildTradeTxRecord,
  prepareHoldingsForUI,
} from '../utils/paperPortfolio';

const REFRESH_MS = 30000;
const INITIAL_DEMO_PORTFOLIO = { totalValue: 10000, cash: 10000, equity: 0, crypto: 0, dayChange: 0, dayChangePct: 0, dataMode: 'demo' };

export const useWallbitAPI = (apiKey, isDemo = false, livePaperEnabled = false) => {
  const dataMode = getDataMode(isDemo, livePaperEnabled);
  const [portfolio, setPortfolio]         = useState(() => loadLocalData(isDemo ? 'demo_portfolio' : 'portfolio') || (isDemo ? INITIAL_DEMO_PORTFOLIO : { totalValue: 0, cash: 0, equity: 0, crypto: 0, dayChange: 0, dayChangePct: 0 }));
  const [holdings, setHoldings]           = useState(() => loadLocalData(isDemo ? 'demo_holdings' : 'holdings') || []);
  const [transactions, setTransactions]   = useState(() => loadLocalData(isDemo ? 'demo_transactions' : 'transactions') || []);
  const [marketData, setMarketData]       = useState(() => loadLocalData('market') || []);
  const [isLoading, setIsLoading]         = useState(false);
  const [error, setError]                 = useState(null);
  const [mcpStatus, setMcpStatus]         = useState(isDemo ? 'connected' : 'idle');
  const [mcpTools, setMcpTools]           = useState(MCP_TOOLS.map(t => t.name));
  const [lastSync, setLastSync]           = useState(null);
  const [transport, setTransport]         = useState(isDemo ? 'demo' : 'rest');

  // FIX: Previene setState en componentes desmontados
  const isMounted = useRef(true);
  useEffect(() => {
    isMounted.current = true;
    return () => { isMounted.current = false; };
  }, []);

  const checkMcp = useCallback(async () => {
    if (!apiKey || isDemo) return;
    setMcpStatus('syncing');
    try {
      const result = await testMcpConnection(apiKey);
      if (!isMounted.current) return;
      if (result.connected) {
        setMcpStatus('connected');
        setMcpTools(result.tools?.length ? result.tools : MCP_TOOLS.map(t => t.name));
      } else {
        setMcpStatus('error');
      }
    } catch (err) {
      if (isMounted.current) setMcpStatus('error');
    }
  }, [apiKey, isDemo]);

  // FIX: Efecto seguro para cambiar de modo. Limpia estados y evita race conditions.
  useEffect(() => {
    if (isDemo) {
      const savedDemo     = loadLocalData('demo_portfolio');
      const savedHoldings = loadLocalData('demo_holdings') || [];
      // FIX: Validación estricta para evitar estados corruptos o $NaN
      const validDemo = savedDemo && typeof savedDemo.totalValue === 'number' && !isNaN(savedDemo.totalValue) && (savedDemo.totalValue > 0 || savedHoldings.length > 0)
        ? savedDemo
        : INITIAL_DEMO_PORTFOLIO;
        
      const market = loadLocalData('market') || [];
      setPortfolio(validDemo);
      setHoldings(prepareHoldingsForUI(savedHoldings, market, { isDemo: true }));
      setTransactions(loadLocalData('demo_transactions') || []);
      setMcpStatus('connected');
      setTransport('demo');
    } else {
      setPortfolio(loadLocalData('portfolio') || { totalValue: 0, cash: 0, equity: 0, crypto: 0, dayChange: 0, dayChangePct: 0 });
      setHoldings(loadLocalData('holdings') || []);
      setTransactions(loadLocalData('transactions') || []);
      setMcpStatus('idle');
      setTransport('rest');
    }
  }, [isDemo, livePaperEnabled, dataMode]);

  // FIX: Uso seguro de fetch con timeout para evitar colgar la app
  const fetchPublicMarketData = useCallback(async () => {
    try {
      const cg = await fetch('/api/coingecko/simple/price?ids=bitcoin,ethereum,solana,binancecoin&vs_currencies=usd&include_24hr_change=true', { signal: AbortSignal.timeout(5000) });
      if (!cg.ok) throw new Error('API Error');
      const data = await cg.json();
      const map = [
        { id: 'bitcoin',    symbol: 'BTC', name: 'Bitcoin' },
        { id: 'ethereum',   symbol: 'ETH', name: 'Ethereum' },
        { id: 'solana',     symbol: 'SOL', name: 'Solana' },
        { id: 'binancecoin',symbol: 'BNB', name: 'BNB' },
      ];
      return map.filter(m => data[m.id]).map(m => ({
        symbol: m.symbol,
        name: m.name,
        price: Number(data[m.id].usd) || 0,
        change: Number(data[m.id].usd_24h_change) || 0,
        type: 'crypto',
      }));
    } catch {
      return [
        { symbol: 'BTC', name: 'Bitcoin',  price: 65000, change: 1.5,  type: 'crypto' },
        { symbol: 'ETH', name: 'Ethereum', price: 3200,  change: 0.8,  type: 'crypto' },
        { symbol: 'SOL', name: 'Solana',   price: 145,   change: 2.1,  type: 'crypto' },
        { symbol: 'AAPL', name: 'Apple',   price: 189,   change: 0.5,  type: 'equity' },
        { symbol: 'TSLA', name: 'Tesla',   price: 250,   change: -1.2, type: 'equity' },
      ];
    }
  }, []);

  const refetch = useCallback(async () => {
    if (!apiKey && !isDemo) return;
    setIsLoading(true);
    setError(null);
    if (!isDemo) setMcpStatus(prev => prev === 'connected' ? 'syncing' : prev);

    try {
      const m = isDemo ? await fetchPublicMarketData() : await fetchMarketData(apiKey);
      if (!isMounted.current) return;
      
      setMarketData(m);
      saveLocalData('market', m);

      if (isDemo) {
        const currentHoldings = loadLocalData('demo_holdings') || [];
        const currentPortfolio = loadLocalData('demo_portfolio') || INITIAL_DEMO_PORTFOLIO;
        const safeCash = Number(currentPortfolio.cash) || 0;

        const newHoldings = prepareHoldingsForUI(
          revalueHoldingsWithMarket(currentHoldings, m),
          m,
          { isDemo: true }
        );
        const newPortfolio = recalculatePortfolioFromHoldings(safeCash, newHoldings, {
          dayChange: currentPortfolio.dayChange ?? 0,
          dayChangePct: currentPortfolio.dayChangePct ?? 0,
          spendableCash: safeCash,
        });

        setHoldings(newHoldings);
        setPortfolio(newPortfolio);
        saveLocalData('demo_holdings', newHoldings);
        saveLocalData('demo_portfolio', newPortfolio);
        setLastSync(new Date().toISOString());

      } else {
        const [p, h, t] = await Promise.all([
          fetchPortfolio(apiKey).catch(() => null),
          fetchHoldings(apiKey).catch(() => []),
          fetchTransactions(apiKey).catch(() => []),
        ]);

        if (!isMounted.current) return;

        const marketCache = m.length ? m : (loadLocalData('market') || []);

        // Siempre cachear datos REALES de Wallbit (nunca mezclar en UI)
        if (p) saveLocalData('portfolio', p);
        saveLocalData('holdings', h);
        saveLocalData('transactions', t);

        const realBase = p ? { ...p } : { totalValue: 0, cash: 0, equity: 0, crypto: 0, dayChange: 0, dayChangePct: 0 };
        const paperData = loadLocalData('live_paper');

        if (dataMode === 'paper') {
          setPortfolio(buildPaperOnlyPortfolio(paperData, marketCache));
          setHoldings(getPaperOnlyHoldings(paperData, marketCache));
          setTransactions(getPaperOnlyTransactions(paperData));
          setTransport('paper');
        } else {
          setPortfolio(buildRealOnlyPortfolio(realBase));
          setHoldings(getRealOnlyHoldings(h, marketCache));
          setTransactions(t || []);
          setTransport(getLastTransport());
        }

        setLastSync(new Date().toISOString());
        if (getLastTransport() === 'mcp') setMcpStatus('connected');
      }
    } catch (err) {
      if (!isMounted.current) return;
      setError(err.message || 'Error de conexión.');
      if (!isDemo) setMcpStatus('error');
    } finally {
      if (isMounted.current) setIsLoading(false);
    }
  }, [apiKey, isDemo, livePaperEnabled, dataMode, fetchPublicMarketData]);

  // FIX: Timer robusto con setTimeout recursivo que no estropea llamadas asíncronas lentas (Memory Leak fijo)
  useEffect(() => {
    if (!apiKey && !isDemo) return;
    
    checkMcp();
    refetch();

    let timeoutId;
    const poll = async () => {
      await refetch();
      if (isMounted.current) {
        timeoutId = setTimeout(poll, REFRESH_MS);
      }
    };
    timeoutId = setTimeout(poll, REFRESH_MS);

    return () => clearTimeout(timeoutId);
  }, [apiKey, checkMcp, refetch, isDemo, livePaperEnabled]);

  // FIX: Prevención de valores nulos o NaN asegurando una conversión estricta
  const addDemoFunds = useCallback((amount = 10000) => {
    if (!isDemo) return;
    
    const amountNum = Number(amount) || 10000;
    const currentPortfolio = loadLocalData('demo_portfolio') || INITIAL_DEMO_PORTFOLIO;
    const currentTxs = loadLocalData('demo_transactions') || [];

    const safeCash = Number(currentPortfolio.cash) || 0;
    const newCash = safeCash + amountNum;
    const newPortfolio = recalculatePortfolioFromHoldings(newCash, loadLocalData('demo_holdings') || [], {
      dayChange: currentPortfolio.dayChange ?? 0,
      dayChangePct: currentPortfolio.dayChangePct ?? 0,
      spendableCash: newCash,
    });

    const newTx = {
      id: `demo_dep_${Date.now()}`,
      date: new Date().toISOString(),
      type: 'DEPOSIT',
      asset: 'USD',
      amount: amountNum,
      price: 1,
      total: amountNum,
      status: 'COMPLETED'
    };

    const updatedTxs = [newTx, ...currentTxs];

    // Persistencia y actualización síncrona
    saveLocalData('demo_portfolio', newPortfolio);
    saveLocalData('demo_transactions', updatedTxs);
    
    setPortfolio(newPortfolio);
    setTransactions(updatedTxs);
  }, [isDemo]);

  // FIX: Se removieron estados de las dependencias para evitar recálculos en bucle.
  const submitTransaction = useCallback(async (tx) => {
    if (!apiKey && !isDemo) throw new Error('API Key no configurada');

    const isBuy = isBuyType(tx.type);
    const isSell = isSellType(tx.type);

    // ═══════════════════════════════════════════════════════════════
    // DEMO MODE ENGINE — fondos virtuales + compra/venta/depósito
    // ═══════════════════════════════════════════════════════════════
    if (isDemo) {
      const currentPortfolio = loadLocalData('demo_portfolio') || INITIAL_DEMO_PORTFOLIO;
      const currentHoldings  = loadLocalData('demo_holdings')  || [];
      const currentTxs       = loadLocalData('demo_transactions') || [];
      const marketCache    = loadLocalData('market') || [];
      let newHoldings = [...currentHoldings];
      let newCash = Number(currentPortfolio.cash) || 0;

      // Depósito / retiro interno (solo mueve cash demo)
      if (isDepositType(tx.type) || isWithdrawType(tx.type)) {
        const usdAmount = normalizeUsdAmount(tx);
        if (isWithdrawType(tx.type) && newCash < usdAmount) {
          throw new Error('Saldo Demo insuficiente para el retiro.');
        }
        newCash = isDepositType(tx.type) ? newCash + usdAmount : newCash - usdAmount;
        const txRecord = {
          id: `demo_tx_${Date.now()}`,
          date: new Date().toISOString(),
          type: tx.type,
          desc: tx.desc || tx.type,
          asset: 'USD',
          amount: isDepositType(tx.type) ? usdAmount : -usdAmount,
          price: 1,
          total: usdAmount,
          color: isDepositType(tx.type) ? 'emerald' : 'rose',
          status: 'COMPLETED (DEMO)',
        };
        const newPortfolio = recalculatePortfolioFromHoldings(newCash, newHoldings, {
          dayChange: currentPortfolio.dayChange ?? 0,
          dayChangePct: currentPortfolio.dayChangePct ?? 0,
          spendableCash: newCash,
        });
        saveLocalData('demo_holdings', newHoldings);
        saveLocalData('demo_portfolio', newPortfolio);
        saveLocalData('demo_transactions', [txRecord, ...currentTxs]);
        setHoldings(newHoldings);
        setPortfolio(newPortfolio);
        setTransactions([txRecord, ...currentTxs]);
        return txRecord;
      }

      if (!isTradeType(tx.type)) {
        throw new Error(`Operación "${tx.type}" no disponible en modo Demo.`);
      }

      if (!tx.asset) throw new Error('Selecciona un activo para la operación.');

      const usdAmount = normalizeUsdAmount(tx);
      const mItem = getMarketItem(marketCache, tx.asset) || { symbol: tx.asset, name: tx.assetName || tx.asset, type: 'equity', price: 0 };
      const unitPrice = resolveUnitPrice(tx, marketCache, tx.asset);
      if (!unitPrice || unitPrice <= 0) {
        throw new Error(`Sin precio en vivo para ${tx.asset}. Espera unos segundos a que cargue el mercado.`);
      }
      const assetQty = normalizeAssetQty(tx, usdAmount, unitPrice);
      if (!assetQty || assetQty <= 0) {
        throw new Error('Cantidad de activo inválida. Revisa monto y precio.');
      }

      if (isBuy && newCash < usdAmount) {
        throw new Error(`Saldo Demo insuficiente. Disponible: $${newCash.toLocaleString('en-US', { minimumFractionDigits: 2 })} USD`);
      }

      const existing = newHoldings.find((h) => h.symbol === tx.asset);

      if (isBuy) {
        newCash -= usdAmount;
        const updated = applyBuyToHolding(existing, assetQty, usdAmount, unitPrice, { ...mItem, symbol: tx.asset }, false);
        if (existing) {
          newHoldings = newHoldings.map((h) => (h.symbol === tx.asset ? updated : h));
        } else {
          newHoldings.push(updated);
        }
      } else if (isSell) {
        if (!existing || (Number(existing.amount) || 0) < assetQty) {
          throw new Error(`No tienes suficiente ${tx.asset} para vender (${(Number(existing?.amount) || 0).toFixed(6)} disponibles).`);
        }
        newCash += usdAmount;
        const updated = applySellToHolding(existing, assetQty, unitPrice);
        newHoldings = updated
          ? newHoldings.map((h) => (h.symbol === tx.asset ? updated : h))
          : newHoldings.filter((h) => h.symbol !== tx.asset);
      }

      newHoldings = prepareHoldingsForUI(
        revalueHoldingsWithMarket(newHoldings, marketCache),
        marketCache,
        { isDemo: true }
      );
      const newPortfolio = recalculatePortfolioFromHoldings(newCash, newHoldings, {
        dayChange: currentPortfolio.dayChange ?? 0,
        dayChangePct: currentPortfolio.dayChangePct ?? 0,
        spendableCash: newCash,
      });

      const txRecord = buildTradeTxRecord({
        idPrefix: 'demo_tx',
        tx,
        isBuy,
        isSell,
        usdAmount,
        unitPrice,
        assetQty,
        mItem,
        status: 'COMPLETED (DEMO)',
        paper: false,
      });

      saveLocalData('demo_holdings', newHoldings);
      saveLocalData('demo_portfolio', newPortfolio);
      saveLocalData('demo_transactions', [txRecord, ...currentTxs]);
      setHoldings(newHoldings);
      setPortfolio(newPortfolio);
      setTransactions([txRecord, ...currentTxs]);
      return txRecord;
    }

    // ═══════════════════════════════════════════════════════════════
    // LIVE PAPER ENGINE — activo cuando hay fondos simulados en live
    // Lee de live_paper (cash + holdings + txs) — NUNCA toca Wallbit API
    // ═══════════════════════════════════════════════════════════════
    const paperData = loadLocalData('live_paper') || { cash: 0, holdings: [], transactions: [] };
    const paperCash = Number(paperData.cash) || 0;
    const marketCache = loadLocalData('market') || [];

    // Trades simulados — solo en modo paper (nunca mezclar con Wallbit real)
    if (dataMode === 'paper' && isTradeType(tx.type)) {
      if (!tx.asset) throw new Error('Selecciona un activo para la operación paper.');

      const usdAmount = normalizeUsdAmount(tx);
      const mItem = getMarketItem(marketCache, tx.asset) || { symbol: tx.asset, name: tx.assetName || tx.asset, type: 'equity', price: 0 };
      const unitPrice = resolveUnitPrice(tx, marketCache, tx.asset);
      if (!unitPrice || unitPrice <= 0) {
        throw new Error(`Sin precio en vivo para ${tx.asset}. Espera unos segundos a que cargue el mercado.`);
      }
      const assetQty = normalizeAssetQty(tx, usdAmount, unitPrice);
      if (!assetQty || assetQty <= 0) {
        throw new Error('Cantidad de activo inválida. Revisa monto y precio.');
      }

      if (isBuy && paperCash < usdAmount) {
        throw new Error(`Saldo paper insuficiente. Disponible: $${paperCash.toLocaleString('en-US', { minimumFractionDigits: 2 })} USD`);
      }

      let paperHoldings = [...(paperData.holdings || [])];
      const existing = paperHoldings.find((h) => h.symbol === tx.asset);

      if (isBuy) {
        const updated = applyBuyToHolding(existing, assetQty, usdAmount, unitPrice, { ...mItem, symbol: tx.asset }, true);
        if (existing) {
          paperHoldings = paperHoldings.map((h) => (h.symbol === tx.asset ? updated : h));
        } else {
          paperHoldings.push(updated);
        }
      } else if (isSell) {
        if (!existing || (Number(existing.amount) || 0) < assetQty) {
          throw new Error(`No tienes suficiente ${tx.asset} en cartera paper.`);
        }
        const updated = applySellToHolding(existing, assetQty, unitPrice);
        paperHoldings = updated
          ? paperHoldings.map((h) => (h.symbol === tx.asset ? updated : h))
          : paperHoldings.filter((h) => h.symbol !== tx.asset);
      }

      const newPaperCash = isBuy ? paperCash - usdAmount : paperCash + usdAmount;
      paperHoldings = revalueHoldingsWithMarket(paperHoldings, marketCache);

      const txRecord = buildTradeTxRecord({
        idPrefix: 'paper_tx',
        tx,
        isBuy,
        isSell,
        usdAmount,
        unitPrice,
        assetQty,
        mItem,
        status: 'PAPER TRADE',
        paper: true,
      });

      const updatedPaper = {
        cash: newPaperCash,
        holdings: paperHoldings,
        transactions: [txRecord, ...(paperData.transactions || [])],
      };
      saveLocalData('live_paper', updatedPaper);

      setPortfolio(buildPaperOnlyPortfolio(updatedPaper, marketCache));
      setHoldings(getPaperOnlyHoldings(updatedPaper, marketCache));
      setTransactions(getPaperOnlyTransactions(updatedPaper));
      return txRecord;
    }

    // ═══════════════════════════════════════════════════════════════
    // LIVE REAL ENGINE — solo en modo real (Wallbit API)
    // ═══════════════════════════════════════════════════════════════
    try {
      await executeTransaction(apiKey, tx);
      await refetch();
      const marketCache = loadLocalData('market') || [];
      if (isTradeType(tx.type) && tx.asset) {
        const usdAmount = normalizeUsdAmount(tx);
        const unitPrice = resolveUnitPrice(tx, marketCache, tx.asset);
        const assetQty = normalizeAssetQty(tx, usdAmount, unitPrice);
        return buildTradeTxRecord({
          idPrefix: 'live_tx',
          tx,
          isBuy,
          isSell,
          usdAmount,
          unitPrice,
          assetQty,
          mItem: getMarketItem(marketCache, tx.asset),
          status: 'COMPLETADO (WALLBIT)',
          paper: false,
        });
      }
      return {
        id: `live_tx_${Date.now()}`,
        date: new Date().toISOString(),
        type: tx.type,
        desc: tx.desc || tx.type,
        asset: tx.asset || 'USD',
        amount: tx.amount,
        total: normalizeUsdAmount(tx),
        price: 1,
        units: normalizeUsdAmount(tx),
        status: 'COMPLETADO (WALLBIT)',
      };
    } catch (err) {
      throw new Error(`Error en operación Live: ${err.message}`);
    }
  }, [apiKey, isDemo, livePaperEnabled, dataMode, refetch]);

  // ─── ADD LIVE PAPER FUNDS ────────────────────────────────────────
  // Works in LIVE (real) mode. Adds simulated paper cash stored separately
  // from the real Wallbit balance so the API data is never corrupted.
  const addLivePaperFunds = useCallback((amount = 10000) => {
    if (isDemo) return; // Demo mode has its own addDemoFunds
    const amountNum = Number(amount) || 10000;

    // Read separate live paper storage (never mixed with real balance)
    const paperData = loadLocalData('live_paper') || { cash: 0, transactions: [] };
    const safeCash  = Number(paperData.cash) || 0;
    const newPaperCash = safeCash + amountNum;

    const newTx = {
      id:     `paper_dep_${Date.now()}`,
      date:   new Date().toISOString(),
      type:   'DEPOSIT',
      desc:   'Fondos Simulados (Live Paper)',
      asset:  'USD',
      amount: amountNum,
      price:  1,
      total:  amountNum,
      color:  'emerald',
      status: 'COMPLETED (PAPER)',
    };

    const updatedPaper = {
      cash: newPaperCash,
      holdings: paperData.holdings || [],
      transactions: [newTx, ...(paperData.transactions || [])],
    };

    saveLocalData('live_paper', updatedPaper);

    const marketCache = loadLocalData('market') || [];
    if (dataMode === 'paper') {
      setPortfolio(buildPaperOnlyPortfolio(updatedPaper, marketCache));
      setHoldings(getPaperOnlyHoldings(updatedPaper, marketCache));
      setTransactions(getPaperOnlyTransactions(updatedPaper));
    }
  }, [isDemo, livePaperEnabled, dataMode]);

  const spendableCash = getSpendableCash(portfolio, dataMode);

  return {
    portfolio,
    holdings,
    transactions,
    marketData,
    dataMode,
    livePaperEnabled,
    spendableCash,
    isLoading,
    error,
    mcpStatus,
    mcpTools,
    lastSync,
    transport,
    refetch,
    submitTransaction,
    checkMcp,
    addDemoFunds,
    addLivePaperFunds,
  };
};
