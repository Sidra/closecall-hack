import type { ReactNode } from "react";

// Tiny, dependency-free markdown renderer for model-written memos (headings, lists, bold,
// inline code, clip ids, paragraphs). It builds React elements, so model text is always
// rendered as text; no HTML from the model is ever injected.
function inline(s: string, key: string): ReactNode[] {
  const out: ReactNode[] = [];
  const re = /\*\*(.+?)\*\*|`([^`]+)`|\[([a-z0-9-]+-\d+-\d+)\]/gi;
  let last = 0;
  let m: RegExpExecArray | null;
  let i = 0;
  while ((m = re.exec(s))) {
    if (m.index > last) out.push(s.slice(last, m.index));
    if (m[1] !== undefined) out.push(<strong key={`${key}-${i++}`}>{m[1]}</strong>);
    else out.push(<code key={`${key}-${i++}`}>{m[2] ?? m[3]}</code>);
    last = m.index + m[0].length;
  }
  if (last < s.length) out.push(s.slice(last));
  return out;
}

export function Markdown({ text }: { text: string }) {
  const blocks: ReactNode[] = [];
  let list: { kind: "ul" | "ol"; items: ReactNode[] } | null = null;
  const close = () => {
    if (!list) return;
    const k = `l${blocks.length}`;
    blocks.push(list.kind === "ul" ? <ul key={k}>{list.items}</ul> : <ol key={k}>{list.items}</ol>);
    list = null;
  };
  text.split("\n").forEach((raw, n) => {
    const line = raw.trimEnd();
    const h = line.match(/^(#{1,4})\s+(.*)$/);
    const ul = line.match(/^\s*[-*]\s+(.*)$/);
    const ol = line.match(/^\s*\d+[.)]\s+(.*)$/);
    if (h) { close(); blocks.push(<h3 key={n}>{inline(h[2], `h${n}`)}</h3>); }
    else if (ul || ol) {
      const kind = ul ? "ul" : "ol";
      if (!list || list.kind !== kind) { close(); list = { kind, items: [] }; }
      list.items.push(<li key={n}>{inline((ul ?? ol)![1], `i${n}`)}</li>);
    } else if (!line.trim()) close();
    else { close(); blocks.push(<p key={n}>{inline(line, `p${n}`)}</p>); }
  });
  close();
  return <div className="memo">{blocks}</div>;
}
