import { ProfilePolicyPanel, type ProfileFactPolicy } from "./ProfilePolicyPanel";

const sections = ["Guidance Rules", "Users", "Memories", "PII Capture Policy", "Safety Events", "Prompt Configuration", "Metrics"];
const demoUserId = "00000000-0000-4000-8000-000000000001";

type GuidanceRule = {
  id: string;
  topic: string;
  tags: string[];
  goal: string;
  safety_level: string;
  priority: number;
  active: boolean;
};

type MemoryItem = {
  id: string;
  type: string;
  content: string;
  status: string;
  importance: number;
  confidence: number;
  updated_at: string;
};

type SafetyEvent = {
  id: string;
  user_id: string;
  level: string;
  reasons: string[];
  created_at: string;
};

async function fetchJson<T>(url: string, fallback: T): Promise<T> {
  try {
    const response = await fetch(url, { cache: "no-store" });
    if (!response.ok) return fallback;
    return response.json();
  } catch {
    return fallback;
  }
}

export default async function AdminHome() {
  const apiBaseUrl = process.env.NEXT_PUBLIC_API_BASE_URL ?? "http://127.0.0.1:8005";
  const [rules, memories, safetyEvents] = await Promise.all([
    fetchJson<GuidanceRule[]>(`${apiBaseUrl}/guidance/rules`, []),
    fetchJson<{ items: MemoryItem[] }>(`${apiBaseUrl}/memories?user_id=${demoUserId}`, { items: [] }),
    fetchJson<{ items: SafetyEvent[] }>(`${apiBaseUrl}/safety/events`, { items: [] })
  ]);
  const profileFactPolicy = await fetchJson<ProfileFactPolicy>(`${apiBaseUrl}/profile-facts/policy`, {
    capture_terms: {},
    blocked_terms: {},
    ttl_days_by_type: {}
  });

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
            <h2>Guidance, memory, and safety controls</h2>
          </div>
          <a className="metricLink" href={`${apiBaseUrl}/metrics`}>
            Prometheus metrics
          </a>
        </header>

        <section id="guidance-rules" className="panel">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Guidance Rules</p>
              <h3>Approved support rules</h3>
            </div>
            <code>{apiBaseUrl}/guidance/rules</code>
          </div>
          <div className="table">
            <div className="row head guidanceRow">
              <span>Topic</span>
              <span>Safety</span>
              <span>Priority</span>
              <span>Status</span>
            </div>
            {rules.map((rule) => (
              <div className="row guidanceRow" key={rule.id}>
                <span>
                  <strong>{rule.topic}</strong>
                  <small>{rule.goal}</small>
                </span>
                <span>{rule.safety_level}</span>
                <span>{rule.priority}</span>
                <span>{rule.active ? "Active" : "Inactive"}</span>
              </div>
            ))}
            {rules.length === 0 ? <EmptyRow label="No guidance rules returned." /> : null}
          </div>
        </section>

        <section className="grid">
          <article className="panel compact" id="users">
            <p className="eyebrow">Users</p>
            <h3>Demo user context</h3>
            <p>Current operational views use the stable demo user until authentication-backed admin filters are added.</p>
            <code>{demoUserId}</code>
          </article>

          <article className="panel compact" id="prompt-configuration">
            <p className="eyebrow">Prompt Configuration</p>
            <h3>Forge response stack</h3>
            <p>Conversation responses combine safety classification, retrieved memories, guidance rules, and the Forge persona instructions.</p>
          </article>
        </section>

        <section id="memories" className="panel">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Memories</p>
              <h3>Recent stored memory candidates</h3>
            </div>
            <code>{apiBaseUrl}/memories</code>
          </div>
          <div className="table">
            <div className="row head memoryRow">
              <span>Memory</span>
              <span>Status</span>
              <span>Importance</span>
              <span>Confidence</span>
            </div>
            {memories.items.map((memory) => (
              <div className="row memoryRow" key={memory.id}>
                <span>
                  <strong>{memory.type}</strong>
                  <small>{memory.content}</small>
                </span>
                <span>{memory.status}</span>
                <span>{memory.importance.toFixed(2)}</span>
                <span>{memory.confidence.toFixed(2)}</span>
              </div>
            ))}
            {memories.items.length === 0 ? <EmptyRow label="No memories stored for the demo user yet." /> : null}
          </div>
        </section>

        <ProfilePolicyPanel initialPolicy={profileFactPolicy} />

        <section id="safety-events" className="panel">
          <div className="panelHeader">
            <div>
              <p className="eyebrow">Safety Events</p>
              <h3>Recent risk classifications</h3>
            </div>
            <code>{apiBaseUrl}/safety/events</code>
          </div>
          <div className="table">
            <div className="row head safetyRow">
              <span>Level</span>
              <span>Reasons</span>
              <span>Created</span>
            </div>
            {safetyEvents.items.map((event) => (
              <div className="row safetyRow" key={event.id}>
                <span>{event.level}</span>
                <span>{event.reasons.length > 0 ? event.reasons.join(", ") : "No reasons stored"}</span>
                <span>{new Date(event.created_at).toLocaleString()}</span>
              </div>
            ))}
            {safetyEvents.items.length === 0 ? <EmptyRow label="No safety events recorded yet." /> : null}
          </div>
        </section>
      </section>
    </main>
  );
}

function EmptyRow({ label }: { label: string }) {
  return (
    <div className="emptyRow">
      <span>{label}</span>
    </div>
  );
}
