/**
 * Marca del asistente Ágora: un "punto de reunión" que irradia (no el típico
 * destello de IA). Reutilizable en cabecera, estado vacío y botón flotante.
 */
export default function AgoraMark({
  className = "h-9 w-9",
  glyphClassName = "h-[56%] w-[56%]",
}: {
  className?: string;
  glyphClassName?: string;
}) {
  return (
    <span
      className={`relative inline-flex shrink-0 items-center justify-center overflow-hidden rounded-[28%] bg-gradient-to-br from-brand-400 via-brand-500 to-brand-700 text-white ${className}`}
    >
      <span
        aria-hidden
        className="pointer-events-none absolute inset-0 bg-[radial-gradient(120%_80%_at_30%_12%,rgba(255,255,255,0.38),transparent_55%)]"
      />
      <svg viewBox="0 0 24 24" fill="none" className={`relative ${glyphClassName}`} aria-hidden>
        <circle cx="12" cy="15.6" r="2.3" fill="currentColor" />
        <path d="M7 12.6a6.6 6.6 0 0 1 10 0" stroke="currentColor" strokeWidth="1.9" strokeLinecap="round" />
        <path
          d="M4.2 9.4a10.4 10.4 0 0 1 15.6 0"
          stroke="currentColor"
          strokeWidth="1.9"
          strokeLinecap="round"
          opacity="0.5"
        />
      </svg>
    </span>
  );
}
