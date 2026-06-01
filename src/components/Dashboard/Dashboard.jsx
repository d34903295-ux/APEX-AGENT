// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — DASHBOARD HEADER
// Main header with logo and live status badge
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import './Dashboard.scss';

const Dashboard = ({ mcpStatus, transport }) => {
  const transportLabel = transport === 'mcp' ? 'MCP' : 'REST';
  const live = mcpStatus === 'connected' || mcpStatus === 'syncing';

  return (
    <header className="dash-header">
      <div className="dash-header__left">
        <span className="dash-header__brand">APEX FINANCIAL</span>
        <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
          <h1 className="dash-header__title">Voice Copilot</h1>
          <svg width="64" height="24" viewBox="0 0 64 24" fill="none" xmlns="http://www.w3.org/2000/svg">
            <rect x="0" y="10" width="2" height="4" rx="1" fill="#00D1FF" opacity="0.3"/>
            <rect x="4" y="8" width="2" height="8" rx="1" fill="#00D1FF" opacity="0.5"/>
            <rect x="8" y="4" width="2" height="16" rx="1" fill="#00D1FF" opacity="0.7"/>
            <rect x="12" y="2" width="2" height="20" rx="1" fill="#00D1FF" opacity="0.9"/>
            <rect x="16" y="6" width="2" height="12" rx="1" fill="#00D1FF"/>
            <rect x="20" y="8" width="2" height="8" rx="1" fill="#00D1FF" opacity="0.6"/>
            <rect x="24" y="10" width="2" height="4" rx="1" fill="#00D1FF" opacity="0.3"/>
            
            <circle cx="32" cy="12" r="2" fill="#00D1FF"/>
            <circle cx="38" cy="12" r="1.5" fill="#00D1FF" opacity="0.7"/>
            <circle cx="44" cy="12" r="1" fill="#00D1FF" opacity="0.4"/>
            <circle cx="50" cy="12" r="1" fill="#00D1FF" opacity="0.2"/>
            <circle cx="56" cy="12" r="0.5" fill="#00D1FF" opacity="0.1"/>
          </svg>
        </div>
      </div>
      <div className="dash-header__right">
        {live && (
          <span className="dash-header__badge dash-header__badge--mcp">
            <span className="dash-header__dot dash-header__dot--mcp" />
            MCP LIVE
          </span>
        )}
        <span className="dash-header__badge">
          <span className="dash-header__dot" />
          Wallbit · {transportLabel}
        </span>
      </div>
      <div className="dash-header__divider" />
    </header>
  );
};

export default Dashboard;
