// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — TICKER BAR
// Infinite scrolling market tickers with sparklines
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import { useMarketData } from '../../hooks/useMarketData';
import './TickerBar.scss';

const TickerBar = ({ marketData = [] }) => {
  const safeData = Array.isArray(marketData) ? marketData : [];
  const { getSparklinePath } = useMarketData(safeData);

  if (!safeData.length) return null;

  // Duplicate for seamless infinite scroll
  const tickers = [...safeData, ...safeData];

  return (
    <div className="ticker-bar" id="ticker-bar">
      <div className="ticker-bar__track">
        {tickers.map((ticker, i) => (
          <div className="ticker-item" key={`${ticker.symbol}-${i}`}>
            <span className="ticker-item__symbol">{ticker.symbol}</span>
            <span className={`ticker-item__price ${ticker.change >= 0 ? 'ticker-item__price--up' : 'ticker-item__price--down'}`}>
              {ticker.price >= 1000
                ? ticker.price.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })
                : ticker.price.toFixed(2)
              }
            </span>
            <span className={`ticker-item__change ${ticker.change >= 0 ? 'ticker-item__change--up' : 'ticker-item__change--down'}`}>
              {ticker.change >= 0 ? '+' : ''}{ticker.change.toFixed(2)}%
            </span>
            <svg className="ticker-item__spark" viewBox="0 0 60 20" preserveAspectRatio="none">
              <path
                d={getSparklinePath(ticker.symbol)}
                fill="none"
                stroke={ticker.change >= 0 ? '#34D399' : '#f87171'}
                strokeWidth="1.2"
                strokeLinecap="round"
                strokeLinejoin="round"
              />
            </svg>
          </div>
        ))}
      </div>
    </div>
  );
};

export default TickerBar;
