# 0004 — Sistema de diseño (UI/UX)

- **Estado:** Aceptada
- **Fecha:** 2026-06-20

## Contexto

Se decidió fijar el UI/UX de forma consistente desde temprano (no estilos sueltos), para que cada pantalla nueva herede el mismo lenguaje visual y se vea terminada.

## Decisión

- **Paleta de marca: índigo** (tokens `brand-50..950` en `tailwind.config.js`) sobre neutros `slate`. Centralizada para re-tematizar fácil.
- **Tipografía: Inter**, auto-alojada vía `@fontsource/inter` (sin CDN; funciona offline/en Docker).
- **Iconos: `lucide-react`**.
- **Dirección visual:** limpia y espaciosa (estilo Linear/Notion); modo claro con barra lateral blanca y acentos de marca.
- **Componentes reutilizables propios** en `src/components/ui` (`Button`, `Input`, `Card`, `Badge`, `PageHeader`, `Spinner`). Sin librería de componentes externa por ahora.
- **Vite:** `optimizeDeps.include` de las dependencias principales para estabilizar el dev server (evita el ciclo "descubrir dep → recargar → caída").

## Consecuencias

- Toda pantalla nueva usa estos componentes y tokens → consistencia garantizada.
- Re-tematizar (p. ej. a la marca oficial de Invesa) = cambiar los tokens `brand`.
- Dark mode queda preparado (vía tokens) para una fase posterior.

## Alternativas consideradas

- **shadcn/ui (Radix):** más potente pero más peso y setup; se prefirió control propio para una superficie pequeña.
- **Azul/índigo vs verde vs monocromo:** se eligió índigo por sobriedad corporativa.
