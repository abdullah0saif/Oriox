import React from 'react';

const styles = {
  container: {
    background: '#12121f',
    borderRadius: 10,
    border: '1px solid #1a1a2e',
    overflow: 'hidden',
  },
  header: {
    padding: '16px 20px',
    borderBottom: '1px solid #1a1a2e',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  symbol: {
    fontSize: 20,
    fontWeight: 700,
  },
  dirBadge: {
    fontSize: 13,
    padding: '4px 12px',
    borderRadius: 6,
    fontWeight: 700,
  },
  body: {
    padding: 20,
  },
  section: {
    marginBottom: 20,
  },
  sectionTitle: {
    fontSize: 12,
    fontWeight: 600,
    color: '#888',
    textTransform: 'uppercase',
    letterSpacing: '0.5px',
    marginBottom: 8,
  },
  levelRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '6px 0',
    fontSize: 13,
    borderBottom: '1px solid #0d0d18',
  },
  levelLabel: {
    color: '#888',
  },
  levelValue: {
    fontWeight: 600,
    fontFamily: 'monospace',
  },
  confluenceItem: {
    fontSize: 13,
    padding: '4px 0',
    color: '#b0f0b0',
  },
  riskItem: {
    fontSize: 13,
    padding: '4px 0',
    color: '#ffab00',
  },
  explanation: {
    fontSize: 13,
    lineHeight: 1.6,
    color: '#ccc',
  },
  scoreGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: 8,
  },
  scoreCard: {
    background: '#0d0d18',
    padding: '10px 14px',
    borderRadius: 6,
    textAlign: 'center',
  },
  scoreLabel: {
    fontSize: 10,
    color: '#666',
    textTransform: 'uppercase',
  },
  scoreValue: {
    fontSize: 18,
    fontWeight: 700,
    marginTop: 4,
  },
  riskMgmt: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr 1fr',
    gap: 8,
    marginTop: 8,
  },
  riskCard: {
    background: '#0d0d18',
    padding: '8px 12px',
    borderRadius: 6,
    textAlign: 'center',
    fontSize: 12,
  },
  warning: {
    fontSize: 12,
    color: '#ffab00',
    padding: '4px 0',
  },
  empty: {
    padding: 60,
    textAlign: 'center',
    color: '#555',
    fontSize: 14,
  },
  invalidation: {
    fontSize: 13,
    color: '#ff6d00',
    padding: '8px 12px',
    background: 'rgba(255, 109, 0, 0.08)',
    borderRadius: 6,
    marginTop: 8,
  },
};

function getScoreColor(value) {
  if (value >= 75) return '#00e676';
  if (value >= 60) return '#76ff03';
  if (value >= 45) return '#ffab00';
  return '#ff6d00';
}

export default function SetupDetail({ setup }) {
  if (!setup) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>Select a setup to view details</div>
      </div>
    );
  }

  const isLong = setup.direction === 'long';
  const dirStyle = {
    ...styles.dirBadge,
    background: isLong ? 'rgba(0, 230, 118, 0.15)' : 'rgba(255, 23, 68, 0.15)',
    color: isLong ? '#00e676' : '#ff1744',
  };

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <span style={styles.symbol}>{setup.symbol}</span>
        <span style={dirStyle}>{setup.direction.toUpperCase()}</span>
      </div>

      <div style={styles.body}>
        {/* Scores */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Scores</div>
          <div style={styles.scoreGrid}>
            <div style={styles.scoreCard}>
              <div style={styles.scoreLabel}>Final Score</div>
              <div style={{ ...styles.scoreValue, color: getScoreColor(setup.final_score) }}>
                {setup.final_score.toFixed(0)}
              </div>
            </div>
            <div style={styles.scoreCard}>
              <div style={styles.scoreLabel}>Confidence</div>
              <div style={{ ...styles.scoreValue, color: getScoreColor(setup.confidence) }}>
                {setup.confidence}%
              </div>
            </div>
            <div style={styles.scoreCard}>
              <div style={styles.scoreLabel}>Confluence</div>
              <div style={{ ...styles.scoreValue, color: getScoreColor(setup.confluence_score) }}>
                {setup.confluence_score.toFixed(0)}
              </div>
            </div>
            <div style={styles.scoreCard}>
              <div style={styles.scoreLabel}>Risk</div>
              <div style={{ ...styles.scoreValue, color: getScoreColor(100 - setup.risk_score) }}>
                {setup.risk_score.toFixed(0)}
              </div>
            </div>
          </div>
        </div>

        {/* Levels */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Trade Levels</div>
          <div style={styles.levelRow}>
            <span style={styles.levelLabel}>Entry Zone</span>
            <span style={styles.levelValue}>
              {setup.entry_low.toFixed(4)} — {setup.entry_high.toFixed(4)}
            </span>
          </div>
          <div style={styles.levelRow}>
            <span style={{ ...styles.levelLabel, color: '#ff1744' }}>Stop Loss</span>
            <span style={{ ...styles.levelValue, color: '#ff1744' }}>
              {setup.stop_loss.toFixed(4)}
            </span>
          </div>
          <div style={styles.levelRow}>
            <span style={{ ...styles.levelLabel, color: '#00e676' }}>TP1</span>
            <span style={{ ...styles.levelValue, color: '#00e676' }}>
              {setup.tp1.toFixed(4)}
            </span>
          </div>
          {setup.tp2 && (
            <div style={styles.levelRow}>
              <span style={{ ...styles.levelLabel, color: '#00e676' }}>TP2</span>
              <span style={{ ...styles.levelValue, color: '#00e676' }}>
                {setup.tp2.toFixed(4)}
              </span>
            </div>
          )}
          {setup.tp3 && (
            <div style={styles.levelRow}>
              <span style={{ ...styles.levelLabel, color: '#00e676' }}>TP3</span>
              <span style={{ ...styles.levelValue, color: '#00e676' }}>
                {setup.tp3.toFixed(4)}
              </span>
            </div>
          )}
          <div style={styles.levelRow}>
            <span style={styles.levelLabel}>R:R Ratio</span>
            <span style={styles.levelValue}>{setup.rr_ratio}</span>
          </div>
        </div>

        {/* Confluence */}
        <div style={styles.section}>
          <div style={styles.sectionTitle}>Why This Setup Exists</div>
          {setup.confluence_factors.map((f, i) => (
            <div key={i} style={styles.confluenceItem}>+ {f}</div>
          ))}
        </div>

        {/* AI Analysis */}
        {setup.explanation && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>AI Analysis</div>
            <div style={styles.explanation}>{setup.explanation}</div>
          </div>
        )}

        {/* Risks */}
        {(setup.risk_factors.length > 0 || setup.risk_summary) && (
          <div style={styles.section}>
            <div style={styles.sectionTitle}>Risks</div>
            {setup.risk_factors.map((r, i) => (
              <div key={i} style={styles.riskItem}>! {r}</div>
            ))}
            {setup.risk_summary && (
              <div style={styles.riskItem}>! {setup.risk_summary}</div>
            )}
          </div>
        )}

        {/* Invalidation */}
        <div style={styles.invalidation}>
          Invalidation: {setup.invalidation}
        </div>

        {/* Risk Management */}
        {setup.risk_approved && setup.position_size_pct != null && (
          <div style={{ ...styles.section, marginTop: 16 }}>
            <div style={styles.sectionTitle}>Risk Management</div>
            <div style={styles.riskMgmt}>
              <div style={styles.riskCard}>
                <div style={{ color: '#888', fontSize: 10 }}>Position</div>
                <div style={{ fontWeight: 700, marginTop: 4 }}>
                  {setup.position_size_pct.toFixed(1)}%
                </div>
              </div>
              <div style={styles.riskCard}>
                <div style={{ color: '#888', fontSize: 10 }}>Leverage</div>
                <div style={{ fontWeight: 700, marginTop: 4 }}>
                  {setup.suggested_leverage}x
                </div>
              </div>
              <div style={styles.riskCard}>
                <div style={{ color: '#888', fontSize: 10 }}>Max Loss</div>
                <div style={{ fontWeight: 700, marginTop: 4 }}>
                  {setup.max_loss_pct.toFixed(1)}%
                </div>
              </div>
            </div>
            {setup.risk_warnings?.map((w, i) => (
              <div key={i} style={styles.warning}>! {w}</div>
            ))}
          </div>
        )}
      </div>
    </div>
  );
}
