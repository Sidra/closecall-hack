// Fixed-window, per-IP limiter for routes that spend API credits. In-memory: fine for one
// instance; swap for Redis if this is ever scaled out.
const hits = new Map<string, { n: number; reset: number }>();

export function limited(req: Request, max: number, windowMs = 60_000): boolean {
  const ip = req.headers.get("x-forwarded-for")?.split(",")[0]?.trim() || "local";
  const now = Date.now();
  const h = hits.get(ip);
  if (!h || now > h.reset) {
    hits.set(ip, { n: 1, reset: now + windowMs });
    if (hits.size > 5000) for (const [k, v] of hits) if (now > v.reset) hits.delete(k);
    return false;
  }
  h.n += 1;
  return h.n > max;
}
