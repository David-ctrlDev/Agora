export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="space-y-3">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
        Próximamente — esta sección se construirá en un slice posterior.
      </div>
    </div>
  );
}
