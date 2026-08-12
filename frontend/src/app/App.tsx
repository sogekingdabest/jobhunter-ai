import { Icon, type IconName } from "../shared/ui/Icon";
import { ThemeToggle } from "../shared/ui/ThemeToggle";

const navigation: ReadonlyArray<{ label: string; icon: IconName }> = [
  { label: "Overview", icon: "compass" },
  { label: "Master profile", icon: "profile" },
  { label: "Opportunities", icon: "briefcase" },
  { label: "Resume studio", icon: "resume" },
  { label: "Insights", icon: "chart" },
];

const principles: ReadonlyArray<{
  title: string;
  description: string;
  icon: IconName;
  accent: string;
}> = [
  {
    title: "Explainable matching",
    description: "Every score is broken down into skills, experience, language and location evidence.",
    icon: "chart",
    accent: "accent-blue",
  },
  {
    title: "Truthful by design",
    description: "Generated resume content stays connected to verified facts in your master profile.",
    icon: "shield",
    accent: "accent-green",
  },
  {
    title: "Private when you want",
    description: "Local and in-browser AI options keep sensitive career data under your control.",
    icon: "sparkles",
    accent: "accent-violet",
  },
];

function Brand() {
  return (
    <a className="brand" href="#top" aria-label="JobHunter AI home">
      <span className="brand-mark"><Icon className="size-5" name="compass" /></span>
      <span>JobHunter <strong>AI</strong></span>
    </a>
  );
}

function Navigation({ compact = false }: { compact?: boolean }) {
  return (
    <nav aria-label="Primary navigation" className={compact ? "mobile-nav" : "sidebar-nav"}>
      {navigation.map(({ label, icon }, index) => (
        <a
          aria-current={index === 0 ? "page" : undefined}
          className="nav-link"
          href={`#${label.toLowerCase().replace(" ", "-")}`}
          key={label}
        >
          <Icon className="size-5" name={icon} />
          <span>{label}</span>
        </a>
      ))}
    </nav>
  );
}

export function App() {
  return (
    <div className="app-shell" id="top">
      <aside className="sidebar">
        <Brand />
        <Navigation />
        <div className="trust-note">
          <Icon className="size-4" name="shield" />
          <span>Your profile remains your source of truth.</span>
        </div>
      </aside>

      <div className="content-shell">
        <header className="topbar">
          <div className="mobile-brand"><Brand /></div>
          <span className="status-pill"><span className="status-dot" />Local workspace</span>
          <ThemeToggle />
        </header>

        <main className="main-content">
          <section className="hero" aria-labelledby="hero-title">
            <div className="hero-copy">
              <span className="eyebrow"><Icon className="size-4" name="sparkles" />Career intelligence, with evidence</span>
              <h1 id="hero-title">Find the right role.<br /><em>Stay true to your story.</em></h1>
              <p>
                Build one trusted professional profile, understand why an opportunity fits,
                and tailor every application without inventing a thing.
              </p>
              <div className="hero-actions">
                <button className="primary-button" type="button">
                  Create master profile <span aria-hidden="true">→</span>
                </button>
                <span className="preview-label">Foundation preview</span>
              </div>
            </div>

            <div className="match-card" aria-label="Example explainable match preview">
              <div className="match-card-header">
                <div>
                  <span className="card-kicker">Match preview</span>
                  <h2>Backend Engineer</h2>
                  <p>Acme Systems · Remote</p>
                </div>
                <div className="score-ring" aria-label="87 percent match"><strong>87</strong><span>%</span></div>
              </div>
              <div className="score-list">
                {[["Skills", "92%"], ["Experience", "78%"], ["Location", "100%"]].map(([label, score]) => (
                  <div className="score-row" key={label}>
                    <span><Icon className="size-4" name="check" />{label}</span><strong>{score}</strong>
                  </div>
                ))}
              </div>
              <div className="evidence-note"><span />Every result links back to profile evidence.</div>
            </div>
          </section>

          <section aria-labelledby="principles-title" className="principles-section">
            <div className="section-heading">
              <div><span className="section-index">01</span><h2 id="principles-title">Built around your real experience</h2></div>
              <p>AI assists with interpretation and writing. Your verified career history remains in charge.</p>
            </div>
            <div className="principle-grid">
              {principles.map(({ title, description, icon, accent }) => (
                <article className="principle-card" key={title}>
                  <span className={`principle-icon ${accent}`}><Icon className="size-6" name={icon} /></span>
                  <h3>{title}</h3>
                  <p>{description}</p>
                  <span className="learn-more">Product principle <span aria-hidden="true">↗</span></span>
                </article>
              ))}
            </div>
          </section>
        </main>

        <Navigation compact />
      </div>
    </div>
  );
}
