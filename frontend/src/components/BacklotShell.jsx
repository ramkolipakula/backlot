export default function BacklotShell({ children }) {
  return (
    <div className="backlot-shell">
      <div className="cinematic-grain-overlay"></div>
      <div className="cinematic-vignette"></div>
      <div className="content-wrapper">
        {children}
      </div>
    </div>
  );
}
