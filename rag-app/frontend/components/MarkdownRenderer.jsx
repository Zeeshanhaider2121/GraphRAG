import ReactMarkdown from "react-markdown";
import remarkMath from "remark-math";
import rehypeKatex from "rehype-katex";
import remarkGfm from "remark-gfm";
import "katex/dist/katex.min.css";

/**
 * Normalise LaTeX so KaTeX can render it:
 *  1. \begin{equation}...\end{equation}  →  $$...$$
 *  2. \(...\)  →  $...$     and     \[...\]  →  $$...$$
 *  3. Collapse runs of 2+ spaces inside $ $ without touching \commandNames
 *  4. Same for $$ $$ blocks (allows newlines inside)
 *  5. Close any unclosed $$ pair caused by a truncated stream
 */
function normalizeLatex(text) {
  // 1. Named LaTeX environments → display math
  text = text.replace(
    /\\begin\{(?:equation|align|gather|multline)\*?\}([\s\S]*?)\\end\{(?:equation|align|gather|multline)\*?\}/g,
    (_, body) => `$$${body.trim()}$$`
  );

  // 2. Bracket/paren delimiter conversion
  text = text.replace(/\\\(/g, "$").replace(/\\\)/g, "$");
  text = text.replace(/\\\[/g, "$$").replace(/\\\]/g, "$$");

  // 3. Inline math: collapse 2+ spaces to one (lookbehind/lookahead keeps single spaces)
  text = text.replace(/\$([^$\n]+?)\$/g, (_, m) => {
    const cleaned = m
      .replace(/(?<=\S) {2,}/g, " ")
      .replace(/ {2,}(?=\S)/g, " ");
    return `$${cleaned}$`;
  });

  // 4. Display math: collapse tabs and 2+ spaces (newlines are fine inside $$)
  text = text.replace(/\$\$([\s\S]+?)\$\$/g, (_, m) => {
    const cleaned = m.replace(/[ \t]{2,}/g, " ");
    return `$$${cleaned}$$`;
  });

  // 5. Repair unclosed $$ (odd number of $$ tokens = one was never closed)
  const ddCount = (text.match(/\$\$/g) || []).length;
  if (ddCount % 2 === 1) text += "$$";

  return text;
}

export default function MarkdownRenderer({ children }) {
  if (typeof children !== "string") return children;
  const sanitized = normalizeLatex(children);
  return (
    <ReactMarkdown
      remarkPlugins={[remarkMath, remarkGfm]}
      rehypePlugins={[rehypeKatex]}
    >
      {sanitized}
    </ReactMarkdown>
  );
}