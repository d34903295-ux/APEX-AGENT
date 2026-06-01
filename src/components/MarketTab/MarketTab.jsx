// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MARKET TAB
// Real CoinGecko, Fear & Greed, Wallbit assets, CryptoCompare news
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  fetchCryptoPrices,
  fetchCryptoChart,
  fetchFearGreed,
  fetchMarketNews,
  fetchPopularAssets,
} from '../../services/wallbit';
import './MarketTab.scss';

const FearGreedGauge = ({ value, label }) => {
  const v = parseInt(value) || 50;
  const angle = (v / 100) * 180 - 90;
  const color = v < 25 ? '#f87171' : v < 45 ? '#FBBF24' : v < 55 ? '#8A8F98' : v < 75 ? '#34D399' : '#00D1FF';

  return (
    <div className="fg-gauge">
      <svg viewBox="0 0 120 70" className="fg-gauge__svg">
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke="rgba(255,255,255,0.08)" strokeWidth="10" strokeLinecap="round" />
        <path d="M10 60 A50 50 0 0 1 110 60" fill="none" stroke={color} strokeWidth="10"
          strokeDasharray={`${(v / 100) * 157} 157`} strokeLinecap="round" />
        <line x1="60" y1="60" x2="60" y2="18"
          stroke={color} strokeWidth="2" strokeLinecap="round"
          style={{ transformOrigin: '60px 60px', transform: `rotate(${angle}deg)` }} />
        <circle cx="60" cy="60" r="4" fill={color} />
        <text x="10" y="68" className="fg-label">Miedo</text>
        <text x="110" y="68" textAnchor="end" className="fg-label">Codicia</text>
      </svg>
      <div className="fg-value" style={{ color }}>{v}</div>
      <div className="fg-label-main">{label || 'Neutral'}</div>
    </div>
  );
};

const Sparkline = ({ prices, positive }) => {
  if (!prices?.length) return <div className="spark-placeholder" />;
  const min = Math.min(...prices), max = Math.max(...prices), range = max - min || 1;
  const w = 80, h = 28;
  const pts = prices.map((v, i) => {
    const x = (i / (prices.length - 1)) * w;
    const y = h - ((v - min) / range) * (h - 2) - 1;
    return `${x},${y}`;
  }).join(' ');
  return (
    <svg width={w} height={h} className="spark-svg">
      <polyline points={pts} fill="none" stroke={positive ? '#34D399' : '#f87171'} strokeWidth="1.5" />
    </svg>
  );
};

const CRYPTO_IDS = {
  bitcoin:  { symbol: 'BTC', name: 'Bitcoin',  icon: '₿' },
  ethereum: { symbol: 'ETH', name: 'Ethereum', icon: 'Ξ' },
  solana:   { symbol: 'SOL', name: 'Solana',   icon: '◎' },
  cardano:  { symbol: 'ADA', name: 'Cardano',  icon: '₳' },
};

const MarketTab = ({ apiKey }) => {
  const [cryptoPrices, setCryptoPrices] = useState(null);
  const [charts, setCharts]             = useState({});
  const [fearGreed, setFearGreed]       = useState(null);
  const [indices, setIndices]           = useState([]);
  const [news, setNews]                 = useState([]);
  const [loading, setLoading]           = useState(true);

  useEffect(() => {
    let mounted = true;
    const load = async () => {
      setLoading(true);
      const [prices, fg, popular, marketNews] = await Promise.all([
        fetchCryptoPrices(),
        fetchFearGreed(),
        apiKey ? fetchPopularAssets(apiKey) : Promise.resolve([]),
        fetchMarketNews(),
      ]);
      if (!mounted) return;
      if (prices) setCryptoPrices(prices);
      if (fg) setFearGreed(fg);
      if (popular?.length) setIndices(popular);
      if (marketNews?.length) setNews(marketNews);
      setLoading(false);

      for (const id of Object.keys(CRYPTO_IDS)) {
        const data = await fetchCryptoChart(id, 7);
        if (mounted && data.length) setCharts(prev => ({ ...prev, [id]: data }));
        await new Promise(r => setTimeout(r, 350));
      }
    };
    load();
    const refresh = setInterval(load, 60000);
    return () => { mounted = false; clearInterval(refresh); };
  }, [apiKey]);

  const cryptoCards = Object.entries(CRYPTO_IDS).map(([id, meta]) => {
    const p = cryptoPrices?.[id];
    const price = p?.usd ?? 0;
    const change = p?.usd_24h_change ?? 0;
    const positive = change >= 0;
    return { id, ...meta, price, change, positive, chartData: charts[id] };
  });

  return (
    <div className="market-tab">
      <motion.div className="market-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }}>
        <div className="hud-section-header"><span>CRYPTO — LIVE (CoinGecko)</span>
          <span className="market-live-dot"><span className="live-dot" />{loading ? 'SYNC' : 'LIVE'}</span>
        </div>
        <div className="market-crypto-grid">
          {cryptoCards.map((c, i) => (
            <motion.div key={c.id} className="market-crypto-card"
              initial={{ opacity: 0, y: 8 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: i * 0.07 }}>
              <div className="mc-top">
                <div>
                  <div className="mc-icon">{c.icon}</div>
                  <div className="mc-symbol">{c.symbol}</div>
                  <div className="mc-name">{c.name}</div>
                </div>
                <Sparkline prices={c.chartData} positive={c.positive} />
              </div>
              <div className="mc-price">
                {c.price > 0 ? `$${c.price.toLocaleString(undefined, { maximumFractionDigits: c.price > 100 ? 0 : 4 })}` : '—'}
              </div>
              <div className={`mc-change ${c.positive ? 'mc-change--up' : 'mc-change--down'}`}>
                {c.price > 0 ? `${c.positive ? '▲' : '▼'} ${Math.abs(c.change).toFixed(2)}%` : 'Sin datos'}
              </div>
            </motion.div>
          ))}
        </div>
      </motion.div>

      {indices.length > 0 && (
        <motion.div className="market-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
          <div className="hud-section-header"><span>ACCIONES — LIVE (Wallbit)</span></div>
          <div className="market-indices">
            {indices.map(idx => (
              <div key={idx.symbol} className="market-index-row">
                <div>
                  <div className="mi-symbol">{idx.symbol}</div>
                  <div className="mi-name">{idx.name}</div>
                </div>
                <div className="mi-right">
                  <div className="mi-price mono">${idx.price?.toLocaleString()}</div>
                </div>
              </div>
            ))}
          </div>
        </motion.div>
      )}

      <motion.div className="market-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
        <div className="hud-section-header"><span>ÍNDICE MIEDO / CODICIA</span>
          <span style={{ fontSize: 10, color: '#8A8F98' }}>Alternative.me</span>
        </div>
        <div style={{ padding: '16px', display: 'flex', justifyContent: 'center' }}>
          {fearGreed ? (
            <FearGreedGauge value={fearGreed.value} label={fearGreed.value_classification} />
          ) : (
            <span style={{ fontSize: 11, color: '#8A8F98' }}>Cargando índice...</span>
          )}
        </div>
      </motion.div>

      <motion.div className="market-section" initial={{ opacity: 0, y: 12 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
        <div className="hud-section-header"><span>NOTICIAS DEL MERCADO</span>
          <span style={{ fontSize: 10, color: '#34D399' }}>CryptoCompare</span>
        </div>
        <div className="market-news">
          {news.length === 0 ? (
            <p style={{ padding: 16, fontSize: 11, color: '#8A8F98' }}>Cargando noticias...</p>
          ) : news.map((n, i) => (
            <motion.a key={n.id} href={n.url} target="_blank" rel="noreferrer" className="market-news-item"
              initial={{ opacity: 0, x: -8 }} animate={{ opacity: 1, x: 0 }} transition={{ delay: i * 0.05 }}
              style={{ textDecoration: 'none', color: 'inherit' }}>
              <span className="mn-icon">{n.icon}</span>
              <div className="mn-content">
                <div className="mn-title">{n.title}</div>
                <div className="mn-meta">
                  <span className="mn-tag">{n.tag}</span>
                  <span className="mn-ts">{n.ts}</span>
                </div>
              </div>
            </motion.a>
          ))}
        </div>
      </motion.div>
    </div>
  );
};

export default MarketTab;
