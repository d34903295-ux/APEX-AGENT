// ════════════════════════════════════════════════════════════════════
// APEX FINANCIAL — HUD DECORATIVE ELEMENTS
// Scanlines, ambient blobs, grid background
// ════════════════════════════════════════════════════════════════════

import React from 'react';

export const Scanlines = () => (
  <div className="hud-scanlines" aria-hidden="true" />
);

export const AmbientBlobs = () => (
  <div className="hud-ambient" aria-hidden="true">
    <div className="blob blob--cyan" />
    <div className="blob blob--emerald" />
    <div className="blob blob--rose" />
  </div>
);

export const GridBackground = () => (
  <div className="hud-grid-bg" aria-hidden="true" />
);

// Corner bracket decorators for cards
export const CornerBrackets = () => (
  <>
    <span className="hud-corner-tr" aria-hidden="true" />
    <span className="hud-corner-bl" aria-hidden="true" />
  </>
);

export default { Scanlines, AmbientBlobs, GridBackground, CornerBrackets };
