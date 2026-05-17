const sections = [
  "Guidance Rules",
  "Users",
  "Memories",
  "Safety Events",
  "Prompt Configuration",
  "Metrics"
];

const rules = [
  { topic: "anger", status: "Approved", priority: 90 },
  { topic: "burnout", status: "Approved", priority: 80 },
  { topic: "breakup", status: "Approved", priority: 70 }
];

export default function AdminHome() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8005";

  return (
    <main className="shell">
      <aside className="sidebar">
        <div>
          <p className="eyebrow">ForgeMind</p>
          <h1>Admin</h1>
        </div>
        <nav>
          {sections.map((section) => (
            <a href={`#${section.toLowerCase().replaceAll(" ", "-")}`} key={section}>
              {section}
            </a>
          ))}
        </nav>
      </aside>
      <section className="content">
        <header className="topbar">
          <div>
            <p className="eyebrow">Operations</p>
            <h2>Guidance and safety controls</h2>
          </div>
          <a className="metricLink" href={`${apiBaseUrl}/metrics`}>Prometheus metrics</a>
        </header>

        <section id="guidance-rules" className="panel">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Guidance Rules</p>
              <h3>Approved coaching rules</h3>
            </div>
            <button type="button">New rule</button>
          </div>
          <div className="table">
            <div className="row head">
              <span>Topic</span>
              <span>Status</span>
              <span>Priority</span>
            </div>
            {rules.map((rule) => (
              <div className="row" key={rule.topic}>
                <span>{rule.topic}</span>
                <span>{rule.status}</span>
                <span>{rule.priority}</span>
              </div>
            ))}
          </div>
        </section>

        <section className="grid">
          {["Users", "Memories", "Safety Events", "Prompt Configuration"].map((title) => (
            <article className="panel compact" id={title.toLowerCase().replaceAll(" ", "-")} key={title}>
              <p className="eyebrow">{title}</p>
              <h3>{title === "Safety Events" ? "Recent risk classifications" : "MVP viewer"}</h3>
              <p>Connects to the FastAPI endpoints for review and operations workflows.</p>
            </article>
          ))}
        </section>
      </section>
    </main>
  );
}
