export default function BacklotShell({ children, appMode, setAppMode }) {
  return (
    <div className="backlot-shell">
      <div className="cinematic-grain-overlay"></div>
      <div className="cinematic-vignette"></div>
      
      {setAppMode && (
        <div className="mode-selector" style={{ position: 'absolute', top: '20px', right: '20px', zIndex: 1000, display: 'flex', gap: '15px', background: 'rgba(0,0,0,0.6)', padding: '5px', borderRadius: '30px', border: '1px solid rgba(255,255,255,0.1)' }}>
          <button 
            onClick={() => setAppMode('demo')}
            style={{ 
              padding: '10px 20px', 
              background: appMode === 'demo' ? 'linear-gradient(135deg, #ff4b4b, #ff0000)' : 'transparent', 
              color: appMode === 'demo' ? '#ffffff' : 'rgba(255,255,255,0.5)', 
              border: appMode === 'demo' ? '1px solid #ff8888' : 'none',
              borderRadius: '25px',
              cursor: 'pointer', 
              fontFamily: 'var(--font-mono)',
              fontWeight: appMode === 'demo' ? 'bold' : 'normal',
              letterSpacing: '1px',
              transition: 'all 0.3s ease',
              boxShadow: appMode === 'demo' ? '0 0 20px rgba(255, 0, 0, 0.8), 0 0 40px rgba(255, 0, 0, 0.4)' : 'none',
              textShadow: appMode === 'demo' ? '0 0 5px rgba(255, 255, 255, 0.5)' : 'none'
            }}
          >
            DEMO MODE
          </button>
          <button 
            onClick={() => setAppMode('manual')}
            style={{ 
              padding: '10px 20px', 
              background: appMode === 'manual' ? 'linear-gradient(135deg, #ff4b4b, #ff0000)' : 'transparent', 
              color: appMode === 'manual' ? '#ffffff' : 'rgba(255,255,255,0.5)', 
              border: appMode === 'manual' ? '1px solid #ff8888' : 'none',
              borderRadius: '25px',
              cursor: 'pointer', 
              fontFamily: 'var(--font-mono)',
              fontWeight: appMode === 'manual' ? 'bold' : 'normal',
              letterSpacing: '1px',
              transition: 'all 0.3s ease',
              boxShadow: appMode === 'manual' ? '0 0 20px rgba(255, 0, 0, 0.8), 0 0 40px rgba(255, 0, 0, 0.4)' : 'none',
              textShadow: appMode === 'manual' ? '0 0 5px rgba(255, 255, 255, 0.5)' : 'none'
            }}
          >
            MANUAL INCIDENT
          </button>
        </div>
      )}

      <div className="content-wrapper">
        {children}
      </div>
    </div>
  );
}
