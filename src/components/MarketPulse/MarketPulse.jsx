// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MARKET PULSE
// Alerts generated from real market data
// ════════════════════════════════════════════════════════════════════

import React, { useState, useEffect, useMemo } from 'react';
import { motion } from 'framer-motion';
import './MarketPulse.scss';

const buildAlerts = (marketData) => {
  const alerts = [];
  const btc = marketData?.find(t => t.symbol === 'BTC/USD' || t.symbol === 'BTC');
  const eth = marketData?.find(t => t.symbol === 'ETH/USD' || t.symbol === 'ETH');

  if (btc) {
    const up = btc.change >= 0;
    alerts.push({
      id: 'btc',
      icon: up ? '📈' : '⚠',
      title: `BTC ${up ? 'en alza' : 'en corrección'} — $${btc.price?.toLocaleString()}`,
      desc: `Variación 24h: ${btc.change >= 0 ? '+' : ''}${(btc.change || 0).toFixed(2)}%. Monitoree niveles de soporte/resistencia.`,
      color: up ? 'emerald' : 'rose',
    });
  }

  if (eth) {
    const up = eth.change >= 0;
    alerts.push({
      id: 'eth',
      icon: 'Ξ',
      title: `ETH cotiza $${eth.price?.toLocaleString()}`,
      desc: `Momentum ${up ? 'positivo' : 'negativo'} al ${(eth.change || 0).toFixed(2)}% en 24h.`,
      color: up ? 'cyan' : 'gold',
    });
  }

  const volatile = marketData?.filter(t => Math.abs(t.change || 0) > 3);
  if (volatile?.length) {
    const top = volatile[0];
    alerts.push({
      id: 'vol',
      icon: '⚡',
      title: `Alta volatilidad: ${top.symbol}`,
      desc: `${top.name || top.symbol} movió ${top.change >= 0 ? '+' : ''}${(top.change || 0).toFixed(2)}% — evalúe riesgo de concentración.`,
      color: 'gold',
    });
  }

  if (!alerts.length) {
    alerts.push({
      id: 'sync',
      icon: '✓',
      title: 'Feeds de mercado sincronizados',
      desc: 'Datos en vivo desde Wallbit y CoinGecko. Sin alertas críticas en este momento.',
      color: 'emerald',
    });
  }

  return alerts;
};

const MarketPulse = ({ marketData }) => {
  const alerts = useMemo(() => buildAlerts(marketData), [marketData]);
  const [currentAlert, setCurrentAlert] = useState(0);

  useEffect(() => {
    setCurrentAlert(0);
  }, [alerts.length]);

  useEffect(() => {
    if (alerts.length <= 1) return;
    const interval = setInterval(() => {
      setCurrentAlert(prev => (prev + 1) % alerts.length);
    }, 8000);
    return () => clearInterval(interval);
  }, [alerts.length]);

  const alert = alerts[currentAlert] || alerts[0];
  const btcData = marketData?.find(t => t.symbol === 'BTC/USD' || t.symbol === 'BTC');

  if (!alert) return null;

  return (
    <motion.div
      className="market-pulse"
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.5, ease: [0.16, 1, 0.3, 1], delay: 0.2 }}
    >
      <div className="hud-section-header" style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
        <span>MARKET PULSE</span>
        {btcData && (
          <span className="market-pulse__btc mono">
            BTC <span className={btcData.change >= 0 ? 'text-emerald' : 'text-rose'}>
              ${btcData.price?.toLocaleString()}
            </span>
          </span>
        )}
      </div>

      {btcData && (
        <div style={{ marginBottom: '16px', background: 'rgba(0,0,0,0.2)', padding: '12px', borderRadius: '8px', border: '1px solid rgba(255,255,255,0.05)' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', fontSize: '10px', color: '#8A8F98', marginBottom: '8px', letterSpacing: '0.05em' }}>
            <span>FEAR & GREED INDEX</span>
            <span style={{ color: btcData.change >= 0 ? '#34D399' : '#F87171' }}>
              {btcData.change >= 2 ? 'EXTREME GREED' : btcData.change >= 0 ? 'GREED' : btcData.change <= -2 ? 'EXTREME FEAR' : 'FEAR'}
            </span>
          </div>
          <div style={{ height: '4px', background: '#111', borderRadius: '2px', overflow: 'hidden', display: 'flex' }}>
            {/* Simple gradient meter based on change */}
            <motion.div 
              initial={{ width: 0 }}
              animate={{ width: `${Math.min(100, Math.max(0, 50 + (btcData.change * 10)))}%` }}
              style={{ background: btcData.change >= 0 ? 'linear-gradient(90deg, #10B981, #34D399)' : 'linear-gradient(90deg, #EF4444, #F87171)' }}
              transition={{ duration: 1, ease: 'easeOut' }}
            />
          </div>
        </div>
      )}

      <motion.div
        key={alert.id}
        className={`market-pulse__alert market-pulse__alert--${alert.color}`}
        initial={{ opacity: 0, x: -10 }}
        animate={{ opacity: 1, x: 0 }}
        exit={{ opacity: 0, x: 10 }}
        transition={{ duration: 0.4 }}
      >
        <div className="market-pulse__icon">{alert.icon}</div>
        <div className="market-pulse__content">
          <div className="market-pulse__title">{alert.title}</div>
          <div className="market-pulse__desc">{alert.desc}</div>
        </div>
        {alerts.length > 1 && (
          <div className="market-pulse__controls">
            <div className="market-pulse__dots">
              {alerts.map((_, i) => (
                <div
                  key={i}
                  className={`market-pulse__dot ${i === currentAlert ? 'market-pulse__dot--active' : ''}`}
                />
              ))}
            </div>
            <div className="market-pulse__timer">
              <motion.div 
                className="market-pulse__timer-fill"
                initial={{ height: '0%' }}
                animate={{ height: '100%' }}
                transition={{ duration: 8, ease: "linear" }}
              />
            </div>
          </div>
        )}
      </motion.div>
    </motion.div>
  );
};

export default MarketPulse;
