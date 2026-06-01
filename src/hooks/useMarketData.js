// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MARKET DATA HOOK
// Sparklines derived from price history (no random simulation)
// ════════════════════════════════════════════════════════════════════

import { useState, useEffect, useCallback } from 'react';
import { fetchCryptoChart } from '../services/wallbit';

const CRYPTO_SYMBOL_MAP = {
  'BTC/USD': 'bitcoin',
  'BTC': 'bitcoin',
  'ETH/USD': 'ethereum',
  'ETH': 'ethereum',
  'SOL/USD': 'solana',
  'SOL': 'solana',
};

export const useMarketData = (initialData) => {
  const [sparklines, setSparklines] = useState({});

  useEffect(() => {
    if (!initialData?.length) return;

    let cancelled = false;

    const load = async () => {
      const updated = {};
      for (const ticker of initialData) {
        const coinId = CRYPTO_SYMBOL_MAP[ticker.symbol];
        if (coinId) {
          const chart = await fetchCryptoChart(coinId, 1);
          if (chart.length >= 2) {
            updated[ticker.symbol] = chart;
            continue;
          }
        }
        // Flat line from current price if no history available
        if (ticker.price) {
          updated[ticker.symbol] = Array(20).fill(ticker.price);
        }
      }
      if (!cancelled) setSparklines(updated);
    };

    load();
    const interval = setInterval(load, 60000);
    return () => { cancelled = true; clearInterval(interval); };
  }, [initialData]);

  const getSparklinePath = useCallback((symbol, width = 60, height = 20) => {
    const data = sparklines[symbol];
    if (!data || data.length < 2) return '';

    const min = Math.min(...data);
    const max = Math.max(...data);
    const range = max - min || 1;

    const points = data.map((val, i) => {
      const x = (i / (data.length - 1)) * width;
      const y = height - ((val - min) / range) * height;
      return `${x},${y}`;
    });

    return `M${points.join(' L')}`;
  }, [sparklines]);

  return { sparklines, getSparklinePath };
};
