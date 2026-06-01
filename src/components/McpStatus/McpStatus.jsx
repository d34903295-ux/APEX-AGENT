// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — MCP STATUS BADGE
// Live Wallbit MCP connection indicator
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import { motion } from 'framer-motion';
import './McpStatus.scss';

const McpStatus = ({ status, tools = [], lastSync, compact }) => {
  const isLive = status === 'connected';
  const isSync = status === 'syncing';
  const isError = status === 'error';

  const label = isLive ? 'MCP LIVE' : isSync ? 'MCP SYNC' : isError ? 'MCP ERR' : 'MCP OFF';

  if (compact) {
    return (
      <span className={`mcp-badge mcp-badge--${status}`} title={tools.length ? `Tools: ${tools.join(', ')}` : ''}>
        <span className="mcp-badge__dot" />
        {label}
      </span>
    );
  }

  return (
    <motion.div
      className={`mcp-status mcp-status--${status}`}
      initial={{ opacity: 0, y: -4 }}
      animate={{ opacity: 1, y: 0 }}
    >
      <div className="mcp-status__header">
        <span className="mcp-status__dot" />
        <span className="mcp-status__title">WALLBIT MCP</span>
        <span className="mcp-status__label">{label}</span>
      </div>
      {isLive && tools.length > 0 && (
        <div className="mcp-status__tools">
          {tools.slice(0, 5).map(t => (
            <span key={t} className="mcp-status__tool">{t.replace(/_/g, ' ')}</span>
          ))}
        </div>
      )}
      {lastSync && (
        <div className="mcp-status__sync mono">
          Última sync: {new Date(lastSync).toLocaleTimeString('es-ES')}
        </div>
      )}
    </motion.div>
  );
};

export default McpStatus;
