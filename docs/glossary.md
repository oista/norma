# Glossary (Norma)

Публичные термины shared-слоя. Продуктовые термины живут в глоссариях продуктов.

| Term | Definition |
|------|------------|
| **capability** | Dot-slug naming a connector skill. Implemented drivers: `http.rest`, `sql.catalog`, `git.repo`. Also known (not yet driven): `tracker.jira`, `graph.sparql`. Validated by `norma.canalis.capability.validate_capability`. |
| **ConnectorSpec** | Declarative identity of a connector: `id`, `capability`, `endpoint`, `options`, `secrets`. |
| **Connector** | Synchronous Protocol: `connect` / `close` / `capabilities` / `health`. Async is a non-goal for v0.x. |
| **git.repo** | Canalis driver for Git hosting HTTP APIs (`api_style=gitlab` in 0.2). DocumentSource (tree/commits/project) + BlobSource (raw file). |
| **SecretRef** | Named reference to a secret (`name`, optional `env`). Products own env prefixes (`PRODATA_`, `ONTOLOGY_`, …). |
| **AuditEvent** | Structured record of a connector operation (outcome, duration, record_count). Persistence/RBAC stay in products. |
| **forma** | Design-token package (`norma-forma`). |
| **libella** | Agent runtime package (`norma-libella`). |
| **canalis** | External-system connector package (`norma-canalis`); see [ADR-0002](adr/ADR-0002-connector-contract.md). |
| **seam** | Versioned artifact or API between producer and consumer; indexed in [seam-registry.md](seam-registry.md). |
