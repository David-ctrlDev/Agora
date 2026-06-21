import { Construction } from "lucide-react";

import { Card, PageHeader } from "../components/ui";

export default function PlaceholderPage({ title }: { title: string }) {
  return (
    <div className="space-y-8">
      <PageHeader title={title} />
      <Card className="flex flex-col items-center gap-3 p-12 text-center">
        <div className="flex h-12 w-12 items-center justify-center rounded-full bg-slate-100 text-slate-400">
          <Construction className="h-6 w-6" />
        </div>
        <p className="text-sm text-slate-500">
          Próximamente — esta sección se construirá en un slice posterior.
        </p>
      </Card>
    </div>
  );
}
