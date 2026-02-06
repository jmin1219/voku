export default function Home() {
  return (
    <div className="h-full flex items-center justify-center">
      <div className="text-center">
        <h1
          className="text-4xl font-bold tracking-tight mb-2"
          style={{ color: "var(--text-dark-primary)" }}
        >
          Voku
        </h1>
        <p
          className="text-sm"
          style={{ color: "var(--text-dark-muted)" }}
        >
          v0.3 — Knowledge graph foundation
        </p>
      </div>
    </div>
  );
}
