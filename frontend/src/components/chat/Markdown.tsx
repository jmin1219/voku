/**
 * Lightweight markdown renderer for assistant messages.
 * Handles: **bold**, *italic*, `code`, ```code blocks```,
 * ## headers, - bullet lists, numbered lists, paragraphs.
 *
 * v2: Parses [N] citation markers and renders interactive ContextMarker
 * components linked to retrieved trace IDs.
 *
 * No dependencies — just React + regex.
 */

import { type CSSProperties } from "react";
import { ContextMarker } from "./ContextMarker";

interface MarkdownProps {
  content: string;
  style?: CSSProperties;
  retrievalIds?: string[];
}

function parseInline(text: string, retrievalIds?: string[]): (string | JSX.Element)[] {
  const parts: (string | JSX.Element)[] = [];
  // Match: **bold**, *italic*, `code`, [N] or [N,N] citations
  const regex = /(\*\*(.+?)\*\*|\*(.+?)\*|`([^`]+?)`|\[(\d+(?:,\s*\d+)*)\])/g;
  let lastIndex = 0;
  let match: RegExpExecArray | null;
  let key = 0;

  while ((match = regex.exec(text)) !== null) {
    if (match.index > lastIndex) {
      parts.push(text.slice(lastIndex, match.index));
    }
    if (match[2]) {
      // **bold**
      parts.push(
        <strong key={key++} style={{ fontWeight: 600, color: "var(--voku-text-primary)" }}>
          {match[2]}
        </strong>
      );
    } else if (match[3]) {
      // *italic*
      parts.push(<em key={key++}>{match[3]}</em>);
    } else if (match[4]) {
      // `inline code`
      parts.push(
        <code
          key={key++}
          style={{
            background: "var(--voku-bg-hover)",
            padding: "1px 5px",
            borderRadius: "3px",
            fontSize: "0.88em",
            fontFamily: "var(--voku-font-mono)",
            color: "var(--voku-accent-gold-glow)",
          }}
        >
          {match[4]}
        </code>
      );
    } else if (match[5]) {
      // [N] or [N,N] citation markers
      const indices = match[5].split(",").map((s) => parseInt(s.trim(), 10));
      for (let ci = 0; ci < indices.length; ci++) {
        const idx = indices[ci];
        const traceId = retrievalIds && retrievalIds[idx - 1]; // [1] → retrievalIds[0]
        parts.push(
          <ContextMarker key={key++} index={idx} traceId={traceId} />
        );
      }
    }
    lastIndex = regex.lastIndex;
  }
  if (lastIndex < text.length) {
    parts.push(text.slice(lastIndex));
  }
  return parts;
}

export function Markdown({ content, style, retrievalIds }: MarkdownProps) {
  const lines = content.split("\n");
  const elements: JSX.Element[] = [];
  let i = 0;
  let key = 0;

  while (i < lines.length) {
    const line = lines[i];

    // Code block
    if (line.startsWith("```")) {
      const codeLines: string[] = [];
      i++;
      while (i < lines.length && !lines[i].startsWith("```")) {
        codeLines.push(lines[i]);
        i++;
      }
      i++; // skip closing ```
      elements.push(
        <pre
          key={key++}
          style={{
            background: "var(--voku-bg-hover)",
            border: "1px solid var(--voku-border-subtle)",
            borderRadius: "var(--voku-radius-md)",
            padding: "0.6rem 0.75rem",
            margin: "0.4rem 0",
            overflowX: "auto",
            fontSize: "0.85rem",
            fontFamily: "var(--voku-font-mono)",
            lineHeight: 1.5,
            color: "var(--voku-text-primary)",
          }}
        >
          <code>{codeLines.join("\n")}</code>
        </pre>
      );
      continue;
    }

    // Headers
    if (line.startsWith("### ")) {
      elements.push(
        <div
          key={key++}
          style={{
            fontSize: "0.9rem",
            fontWeight: 600,
            color: "var(--voku-text-primary)",
            margin: "0.6rem 0 0.2rem",
          }}
        >
          {parseInline(line.slice(4), retrievalIds)}
        </div>
      );
      i++;
      continue;
    }
    if (line.startsWith("## ")) {
      elements.push(
        <div
          key={key++}
          style={{
            fontSize: "0.95rem",
            fontWeight: 600,
            color: "var(--voku-text-primary)",
            margin: "0.7rem 0 0.25rem",
          }}
        >
          {parseInline(line.slice(3), retrievalIds)}
        </div>
      );
      i++;
      continue;
    }
    if (line.startsWith("# ")) {
      elements.push(
        <div
          key={key++}
          style={{
            fontSize: "1.05rem",
            fontWeight: 600,
            color: "var(--voku-text-primary)",
            margin: "0.8rem 0 0.3rem",
          }}
        >
          {parseInline(line.slice(2), retrievalIds)}
        </div>
      );
      i++;
      continue;
    }

    // Bullet list
    if (line.match(/^[-*]\s/)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^[-*]\s/)) {
        items.push(lines[i].replace(/^[-*]\s/, ""));
        i++;
      }
      elements.push(
        <ul
          key={key++}
          style={{
            margin: "0.3rem 0",
            paddingLeft: "1.2rem",
            listStyleType: "disc",
          }}
        >
          {items.map((item, j) => (
            <li key={j} style={{ margin: "0.15rem 0", lineHeight: 1.5 }}>
              {parseInline(item, retrievalIds)}
            </li>
          ))}
        </ul>
      );
      continue;
    }

    // Numbered list
    if (line.match(/^\d+\.\s/)) {
      const items: string[] = [];
      while (i < lines.length && lines[i].match(/^\d+\.\s/)) {
        items.push(lines[i].replace(/^\d+\.\s/, ""));
        i++;
      }
      elements.push(
        <ol
          key={key++}
          style={{
            margin: "0.3rem 0",
            paddingLeft: "1.2rem",
          }}
        >
          {items.map((item, j) => (
            <li key={j} style={{ margin: "0.15rem 0", lineHeight: 1.5 }}>
              {parseInline(item, retrievalIds)}
            </li>
          ))}
        </ol>
      );
      continue;
    }

    // Empty line = paragraph break
    if (line.trim() === "") {
      elements.push(<div key={key++} style={{ height: "0.4rem" }} />);
      i++;
      continue;
    }

    // Regular paragraph
    elements.push(
      <div key={key++} style={{ margin: "0.15rem 0", lineHeight: 1.6 }}>
        {parseInline(line, retrievalIds)}
      </div>
    );
    i++;
  }

  return <div style={style}>{elements}</div>;
}
