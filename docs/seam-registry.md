# Seam registry

Нормативный ADR: [ADR-0001](adr/ADR-0001-seam-contract.md).

Реестр индексирует существующие швы. Содержимое контрактов живёт у производителя; здесь — указатель.

| id                        | producer | consumer(s)     | artifact                                      | schema home                                                                 | versioning        | gate / status                                                                 |
|---------------------------|----------|-----------------|-----------------------------------------------|-----------------------------------------------------------------------------|-------------------|-------------------------------------------------------------------------------|
| `forma-tokens`            | Norma    | ENTAN, PRODATA  | `static/css/tokens.css`, `themes.toml`        | `norma/tokens/stone.toml`                                                   | token file + emit | ENTAN `tests/test_design_tokens.py`; PRODATA design drift                     |
| `libella-runtime`         | Norma    | ENTAN, PRODATA  | pip / `PYTHONPATH` mount `norma-libella`      | `norma.libella` Python API                                                  | package semver    | import smoke in Dockerfiles                                                   |
| `canalis-connect`         | Norma    | PRODATA, Clavis | pip / `PYTHONPATH` mount `norma-canalis`      | `norma.canalis` Python API                                                  | package semver    | Norma CI pytest (http/sql/git); Clavis `tests/test_rowsource_canalis.py`; PRODATA `tests/unit/test_canalis_gitlab_source.py` |
| `ontology-projections`    | Clavis   | ENTAN, kgraph   | `ontology_manifest.yaml`, `etl_import.yaml`, `ref_types.csv` | Clavis `docs/architecture/projection-contract.md`                  | CalVer / checksum | Clavis projection checksum / staleness gate                                   |
| `prodata-entan-boundary`  | PRODATA  | ENTAN           | HTTP-only (no code import)                    | PRODATA `docs/architecture/boundary-contract.md`                            | API contract      | boundary review / architecture sync                                           |
| `module-ontology-binding` | PRODATA  | Clavis, modules | `module.toml` `produces` / `consumes`         | PRODATA ADR-0013; Clavis ADR-0011                                           | `ontology_version`| PRODATA `scripts/check_ontology_bindings.py`                                  |
| `env-prefixes`            | Norma    | all products    | env var prefixes                              | [config-contract.md](config-contract.md)                                    | doc               | naming review                                                                 |
| `harvest-cir-facts`       | Clavis   | ENTAN           | CIR bundle → curated fact memory              | Clavis `docs/architecture/harvest-contract.md`                              | CIR v1            | **Proposed** — адаптер в ENTAN ещё не построен                                |

## Правила заполнения

1. Новая строка только при наличии реального шва (код или артефакт), не «на будущее».
2. Колонка `schema home` — путь к контракту у **производителя**, не копия текста.
3. Статус `Proposed` допустим ровно до появления гейта; после — указать конкретный чекер.
4. Любое изменение строки = тот же PR, что меняет шов.
