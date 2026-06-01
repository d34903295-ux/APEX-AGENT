import React from 'react';
import { motion } from 'framer-motion';

const ModeBanner = ({ dataMode, onOpenSettings }) => {
  if (dataMode === 'real') return null;

  return (
    <motion.div
      initial={{ opacity: 0, y: -20 }}
      animate={{ opacity: 1, y: 0 }}
      style={{
        padding: '8px 16px',
        background: dataMode === 'demo' ? 'rgba(234, 179, 8, 0.1)' : 'rgba(56, 189, 248, 0.1)',
        borderBottom: `1px solid ${dataMode === 'demo' ? 'rgba(234, 179, 8, 0.3)' : 'rgba(56, 189, 248, 0.3)'}`,
        color: dataMode === 'demo' ? '#facc15' : '#38bdf8',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        fontSize: '12px',
        fontFamily: "'Fira Code', monospace",
      }}
    >
      <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
        <span style={{ width: 6, height: 6, borderRadius: '50%', background: 'currentColor', boxShadow: '0 0 4px currentColor' }} />
        {dataMode === 'demo' ? 'DEMO MODE - SIMULATED FUNDS' : 'PAPER TRADING - LIVE MARKET DATA'}
      </div>
      <button 
        onClick={onOpenSettings}
        style={{ 
          background: 'none', border: '1px solid currentColor', borderRadius: 4, 
          color: 'currentColor', padding: '4px 8px', fontSize: '10px', cursor: 'pointer',
          fontFamily: "inherit",
          textTransform: 'uppercase'
        }}
        onMouseOver={(e) => {
          e.currentTarget.style.background = dataMode === 'demo' ? 'rgba(234, 179, 8, 0.15)' : 'rgba(56, 189, 248, 0.15)';
        }}
        onMouseOut={(e) => {
          e.currentTarget.style.background = 'none';
        }}
      >
        Settings
      </button>
    </motion.div>
  );
};

export default ModeBanner;
