# Docs conventions (артель)

Канон правил ведения документации для репозиториев артели (Norma, ENTAN, PRODATA, Clavis).
Продуктовые `docs/README.md` ссылаются сюда и добавляют только локальные отличия.

## Общие правила

1. **Глоссарий.** Любой новый публичный термин (код, ADR, design note, UI-facing имя) описывается в `docs/glossary.md` **в том же изменении**.

2. **Таблицы.** GFM-таблицы пишутся с выравниванием колонок по самой широкой ячейке (padding + separator той же ширины). Не оставлять «сжатые» пайпы без пробелов. Advisory-форматтер: `mdformat docs/`.

3. **Серийные папки.** Если в каталоге серия однотипных файлов (`docs/adr/`, `docs/design-notes/`), в нём же обязательны `template.md` и индекс (`ADR-INDEX.md`, `DN-INDEX.md`). Новую серию без template + index не заводить.

4. **ADR.** Без YAML-фронтматтера; метаданные инлайн (`**Статус:**`, `**Дата:**`, `**Related:**`). Статусы: `Proposed | Accepted | Deprecated | Superseded`. Имя файла `ADR-NNNN-short-slug.md` совпадает с H1. Не править Accepted ADR «по месту» — новый ADR со статусом Superseded / supersedes.

## Межрепозиторные швы

Правила зависимости и реестр швов: [ADR-0001](adr/ADR-0001-seam-contract.md), [seam-registry.md](seam-registry.md).
Имена продуктов: [naming.md](naming.md). Env-префиксы: [config-contract.md](config-contract.md).
