"use client";

/**
 * CronPreview — shows the next N execution times for a 5-field cron expression.
 * No external deps — manual cron evaluation for the common iPaaS subset:
 *   minute hour dom month dow
 * Supports: "*", exact values, comma-lists, ranges (a-b), and step /n.
 * Does NOT support L, W, #, or ? (Quartz extensions).
 */

interface CronPreviewProps {
  expression: string;
  count?: number;
}

function parseField(field: string, min: number, max: number): Set<number> {
  const values = new Set<number>();
  for (const part of field.split(",")) {
    if (part === "*") {
      for (let i = min; i <= max; i++) values.add(i);
    } else if (part.includes("/")) {
      const [range, stepStr] = part.split("/");
      const step = parseInt(stepStr, 10);
      let start = min;
      let end = max;
      if (range !== "*") {
        const [a, b] = range.split("-").map(Number);
        start = a;
        end = b ?? a;
      }
      for (let i = start; i <= end; i += step) values.add(i);
    } else if (part.includes("-")) {
      const [a, b] = part.split("-").map(Number);
      for (let i = a; i <= b; i++) values.add(i);
    } else {
      const n = parseInt(part, 10);
      if (!isNaN(n)) values.add(n);
    }
  }
  return values;
}

function nextRuns(expr: string, count: number, from: Date): Date[] {
  const parts = expr.trim().split(/\s+/);
  if (parts.length !== 5) return [];
  try {
    const [minuteF, hourF, domF, monthF, dowF] = parts;
    const minutes = parseField(minuteF, 0, 59);
    const hours = parseField(hourF, 0, 23);
    const doms = parseField(domF, 1, 31);
    const months = parseField(monthF, 1, 12);
    const dows = parseField(dowF, 0, 6);

    const results: Date[] = [];
    const cursor = new Date(from);
    cursor.setSeconds(0, 0);
    cursor.setMinutes(cursor.getMinutes() + 1); // start from next minute

    let iterations = 0;
    while (results.length < count && iterations < 1_000_000) {
      iterations++;
      if (!months.has(cursor.getMonth() + 1)) {
        cursor.setDate(1);
        cursor.setHours(0, 0, 0, 0);
        cursor.setMonth(cursor.getMonth() + 1);
        continue;
      }
      const domWild = domF === "*";
      const dowWild = dowF === "*";
      const domMatch = doms.has(cursor.getDate());
      const dowMatch = dows.has(cursor.getDay());
      const dayMatch = domWild && dowWild ? true : domWild ? dowMatch : dowWild ? domMatch : domMatch || dowMatch;

      if (!dayMatch) {
        cursor.setDate(cursor.getDate() + 1);
        cursor.setHours(0, 0, 0, 0);
        continue;
      }
      if (!hours.has(cursor.getHours())) {
        const nextHour = [...hours].find((h) => h > cursor.getHours());
        if (nextHour === undefined) {
          cursor.setDate(cursor.getDate() + 1);
          cursor.setHours(0, 0, 0, 0);
        } else {
          cursor.setHours(nextHour, 0, 0, 0);
        }
        continue;
      }
      if (!minutes.has(cursor.getMinutes())) {
        const nextMin = [...minutes].sort((a, b) => a - b).find((m) => m > cursor.getMinutes());
        if (nextMin === undefined) {
          cursor.setHours(cursor.getHours() + 1, 0, 0, 0);
        } else {
          cursor.setMinutes(nextMin, 0, 0);
        }
        continue;
      }
      results.push(new Date(cursor));
      cursor.setMinutes(cursor.getMinutes() + 1);
    }
    return results;
  } catch {
    return [];
  }
}

const FORMAT: Intl.DateTimeFormatOptions = {
  weekday: "short",
  month: "short",
  day: "numeric",
  hour: "2-digit",
  minute: "2-digit"
};

export function CronPreview({ expression, count = 3 }: CronPreviewProps) {
  const runs = nextRuns(expression, count, new Date());

  if (!expression.trim() || runs.length === 0) {
    return (
      <p className="text-xs text-slate-400 italic mt-1">
        Enter a valid 5-field cron expression to preview next runs.
      </p>
    );
  }

  return (
    <div className="mt-1 space-y-0.5">
      <p className="text-xs font-medium text-slate-500 mb-1">Next {count} runs:</p>
      {runs.map((d, i) => (
        <p key={i} className="text-xs text-slate-600 font-mono">
          {d.toLocaleString(undefined, FORMAT)}
        </p>
      ))}
    </div>
  );
}
