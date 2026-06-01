// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — NAVIGATION BAR
// Bottom fixed navigation with 4 tabs
// ════════════════════════════════════════════════════════════════════

import React from 'react';
import './NavBar.scss';

const TABS = [
  {
    id: 'home',
    label: 'Home',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="m3 9 9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
        <polyline points="9 22 9 12 15 12 15 22" />
      </svg>
    ),
  },
  {
    id: 'assets',
    label: 'Assets',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <rect width="20" height="14" x="2" y="5" rx="2" />
        <line x1="2" x2="22" y1="10" y2="10" />
      </svg>
    ),
  },
  {
    id: 'market',
    label: 'Market',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <polyline points="22 12 18 12 15 21 9 3 6 12 2 12" />
      </svg>
    ),
  },
  {
    id: 'agent',
    label: 'Agente',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <path d="M12 2a4 4 0 0 1 4 4v2h2.5A2.5 2.5 0 0 1 21 10.5v7a2.5 2.5 0 0 1-2.5 2.5h-13A2.5 2.5 0 0 1 3 17.5v-7A2.5 2.5 0 0 1 5.5 8H8V6a4 4 0 0 1 4-4z"/>
        <path d="M8 8v2"/>
        <path d="M16 8v2"/>
        <path d="M12 14v4"/>
        <path d="M9 14h6"/>
      </svg>
    ),
  },
  {
    id: 'menu',
    label: 'Menu',
    icon: (
      <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
        <line x1="4" x2="20" y1="12" y2="12" />
        <line x1="4" x2="20" y1="6" y2="6" />
        <line x1="4" x2="20" y1="18" y2="18" />
      </svg>
    ),
  },
];

const NavBar = ({ activeTab = 'home', onTabChange, horizontal, vertical }) => {
  return (
    <nav className={`navbar ${horizontal ? 'navbar--horizontal' : ''} ${vertical ? 'navbar--vertical' : ''}`} id="main-nav">
      {TABS.map((tab) => {
        const isActive = activeTab === tab.id;
        return (
          <button
            key={tab.id}
            className={`navbar__tab ${isActive ? 'navbar__tab--active' : ''}`}
            onClick={() => onTabChange?.(tab.id)}
            aria-label={tab.label}
          >
            <div className="navbar__icon">{tab.icon}</div>
            {!vertical && <span className="navbar__label">{tab.label}</span>}
            {isActive && <div className="navbar__indicator" />}
          </button>
        );
      })}
    </nav>
  );
};

export default NavBar;
