import { Card } from "@/components/ui/card";

export default function Loading() {
  return (
    <main className="min-h-screen bg-background">
      <header className="border-b border-border bg-white">
        <div className="mx-auto max-w-7xl px-6 py-5">
          <div className="h-4 w-48 rounded-md bg-muted" />
          <div className="mt-3 h-8 w-72 rounded-md bg-muted" />
        </div>
      </header>
      <section className="mx-auto grid max-w-7xl gap-5 px-6 py-8 lg:grid-cols-3">
        {[0, 1, 2].map((item) => (
          <Card key={item}>
            <div className="h-4 w-28 rounded-md bg-muted" />
            <div className="mt-5 h-8 w-40 rounded-md bg-muted" />
          </Card>
        ))}
      </section>
    </main>
  );
}
