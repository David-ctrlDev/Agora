import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";

/** Renderiza Markdown del agente (listas, negritas, enlaces) con estilos sobrios. */
export default function Markdown({ children }: { children: string }) {
  return (
    <ReactMarkdown
      remarkPlugins={[remarkGfm]}
      components={{
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
        code: ({ node, ...props }) => (
          <code className="rounded bg-slate-200/70 px-1 py-0.5 text-[0.8em]" {...props} />
        ),
        h1: ({ node, ...props }) => (
          <h3 className="mb-1 mt-2 text-sm font-semibold text-slate-900" {...props} />
        ),
        h2: ({ node, ...props }) => (
          <h3 className="mb-1 mt-2 text-sm font-semibold text-slate-900" {...props} />
        ),
        h3: ({ node, ...props }) => (
          <h3 className="mb-1 mt-2 text-sm font-semibold text-slate-900" {...props} />
        ),
      }}
    >
      {children}
    </ReactMarkdown>
  );
}
