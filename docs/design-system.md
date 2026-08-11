# Design system (триада)

SSOT токенов: [`../tokens/stone.toml`](../tokens/stone.toml). Генерация: `norma-forma emit`.

**Architecture Design Language (полный SoT):** [`architecture-design-language.md`](architecture-design-language.md) · living board [`adl/index.html`](adl/index.html).

## Пять принципов

1. **Токены, не hex** — в шаблонах модулей только CSS-переменные / `pw-*` / `entan-*`.
2. **Кнопки одной схемы** — primary = accent (терракота), secondary = hairline на paper.
3. **Волосяные линии вместо теней** — `shadow: none`; границы через `hairline`.
4. **Светлая бумага** — фон `paper` `#f5f4ef`, текст `ink` `#222829`.
5. **Один тёплый акцент** — терракота `#e85828` для CTA и фокуса; камень `#c4b494` для заливок иконок/чипов.
6. **3D только в гербах** — UI строго 2D (см. ADL).

## Слои

1. Токены (`stone.toml`) → генераторы forma / `adl.css`.
2. Компоненты продукта (`pw-*` в PRODATA, классы ENTAN).
3. Модули — только композиция.

PRODATA-специфика (`pw-split`, `pw-tree`, operation lists) остаётся в `moex-prodata-platform/docs/design-notes/design-system.md`.
