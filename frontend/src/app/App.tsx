import { BrowserAILab } from "../features/browser-ai/BrowserAILab";
import { MvpWorkspace } from "../features/workflow/MvpWorkspace";
import { Icon, type IconName } from "../shared/ui/Icon";
import { ThemeToggle } from "../shared/ui/ThemeToggle";

const navigation: ReadonlyArray<{ label: string; href: string; icon: IconName }> = [
  { label: "Overview", href: "#overview", icon: "compass" },
  { label: "Master profile", href: "#master-profile", icon: "profile" },
  { label: "Opportunity", href: "#opportunities", icon: "briefcase" },
  { label: "Matching", href: "#matching", icon: "chart" },
  { label: "Resume studio", href: "#resume-studio", icon: "resume" },
];

function Brand() {
  return (
    <a className="brand" href="#overview" aria-label="JobHunter AI home">
      <span className="brand-mark"><Icon className="size-5" name="compass" /></span>
      <span>JobHunter <strong>AI</strong></span>
    </a>
  );
}

function Navigation({ compact = false }: { compact?: boolean }) {
  return (
    <nav aria-label="Primary navigation" className={compact ? "mobile-nav" : "sidebar-nav"}>
      {navigation.map(({ label, href, icon }, index) => (
        <a aria-current={index === 0 ? "page" : undefined} className="nav-link" href={href} key={label}>
          <Icon className="size-5" name={icon} />
          <span>{label}</span>
        </a>
      ))}
    </nav>
  );
}

export function App() {
  return (
    <div className="app-shell">
      <aside className="sidebar">
        <Brand />
        <Navigation />
        <div className="trust-note"><Icon className="size-4" name="shield" /><span>Your profile remains the only source of candidate truth.</span></div>
      </aside>
      <div className="content-shell">
        <header className="topbar">
          <div className="mobile-brand"><Brand /></div>
          <span className="status-pill"><span className="status-dot" />Local MVP</span>
          <a className="ai-lab-link" href="#browser-ai">Browser AI lab</a>
          <ThemeToggle />
        </header>
        <main className="main-content">
          <MvpWorkspace />
          <section className="browser-ai-section" id="browser-ai" aria-labelledby="browser-ai-title">
            <div className="section-heading"><div><span className="section-index">LAB</span><h2 id="browser-ai-title">Optional in-browser AI</h2></div><p>This isolated experiment never receives workspace data automatically.</p></div>
            <BrowserAILab />
          </section>
        </main>
        <Navigation compact />
      </div>
    </div>
  );
}
