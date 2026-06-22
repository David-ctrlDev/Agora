import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

import Mermaid from "./Mermaid";

/** ¿Es este nodo `code` un bloque ```mermaid```? */
function isMermaid(className: unknown): boolean {
  return typeof className === "string" && className.includes("language-mermaid");
}

/** Renderiza Markdown del agente (listas, negritas, enlaces, diagramas) con estilos sobrios. */
export default function Markdown({
  children,
  diagramsSaveable = false,
}: {
  children: string;
  diagramsSaveable?: boolean;
}) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
        pre: ({ node, children: kids, ...props }) => {
          // Un bloque mermaid lo pinta <Mermaid> directamente (sin envolver en <pre>).
          const child = Array.isArray(kids) ? kids[0] : kids;
          const cls = (child as { props?: { className?: string } })?.props?.className;
          if (isMermaid(cls)) return <>{kids}</>;
          return (
            <pre className="my-2 overflow-x-auto rounded-xl bg-slate-900 p-3 text-xs text-slate-100" {...props}>
              {kids}
            </pre>
          );
        },
        code: ({ node, className, children: kids, ...props }) => {
          if (isMermaid(className)) {
            return <Mermaid code={String(kids).replace(/\n$/, "")} saveable={diagramsSaveable} />;
          }
          return (
            <code className="rounded bg-slate-200/70 px-1 py-0.5 text-[0.8em]" {...props}>
              {kids}
            </code>
          );
        },
        p: ({ node, ...props }) => <p className="mb-2 last:mb-0" {...props} />,
        ul: ({ node, ...props }) => (
          <ul className="mb-2 list-disc space-y-1 pl-4 last:mb-0" {...props} />
        ),
        ol: ({ node, ...props }) => (
          <ol className="mb-2 list-decimal space-y-1 pl-4 last:mb-0" {...props} />
        ),
        li: ({ node, ...props }) => <li className="marker:text-slate-400" {...props} />,
        strong: ({ node, ...props }) => (
          <strong className="font-semibold text-slate-900" {...props} />
        ),
        a: ({ node, ...props }) => (
          <a className="font-medium text-brand-600 underline" target="_blank" rel="noreferrer" {...props} />
        ),
        h1: ({ node, ...props }) => (
          <h3 className="mb-1.5 mt-3 text-base font-semibold text-slate-900 first:mt-0" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h3 className="mb-1.5 mt-3 text-base font-semibold text-slate-900 first:mt-0" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="mb-1 mt-2.5 text-[15px] font-semibold text-slate-900 first:mt-0" {...props} />
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
