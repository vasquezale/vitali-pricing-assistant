# Proyecto Vitali - Estado Activo

Este archivo es la fuente operativa de estado del proyecto dentro del repositorio.
Debe mantenerse breve, seguro para GitHub y actualizado al cierre de cada sesion relevante.

## Uso de este archivo

- Registrar estado actual del proyecto en formato ejecutivo.
- Mantener visibles los logros, pendientes, bloqueos y siguiente paso.
- Documentar estado de GitHub y seguridad sin incluir contexto privado, prompts internos o rutas sensibles no necesarias.
- Si hace falta una bitacora detallada o notas de coordinacion, eso debe vivir en el vault privado, no aqui.

## Resumen actual

| Area | Estado actual |
|---|---|
| Objetivo del proyecto | Pricing assistant / decision support system para un Airbnb en Cartago, Costa Rica |
| Etapa funcional | Scaffolding base listo; Fase 1 aun pendiente de cierre; Fase 2 bloqueada hasta contar con datos raw locales |
| Rama segura para publicar | `codex/public-ready` |
| Rama con historial previo local | `main` |
| Respaldo de seguridad local | `codex/prepublish-backup` |
| Remoto GitHub | Aun no creado/configurado |

## Logros confirmados

| Tema | Logro |
|---|---|
| Saneamiento Git | Se creo una historia Git limpia en `codex/public-ready` para evitar publicar el historial interno anterior |
| Respaldo | Se preservo la historia previa en `codex/prepublish-backup` para no perder contexto local |
| Seleccion de archivos publicables | La rama limpia contiene solo codigo, tests, configuracion, scripts, `README.md`, `.gitignore`, `uv.lock` y `artifacts/registry.json` |
| Hardening inicial | `.gitignore` bloquea datos, secretos, tooling personal y documentacion interna como `context/`, `research/`, `docs/`, `notebooks/`, `AGENTS.md` y `CLAUDE.md` |
| Documentacion publica | `README.md` ya refleja la separacion repo/vault y la politica de manejo seguro de datos |
| Validacion tecnica | La rama limpia paso `ruff`, `pylint` y `pytest` |

## Seguridad y GitHub - Estado actual

| Tema | Estado | Nota |
|---|---|---|
| Datos raw de Airbnb | Protegido | `data/` esta ignorado y no debe subirse nunca |
| PII de huespedes | Sin evidencia actual en la rama limpia | Mantener criterio de exclusion por defecto |
| Secretos y credenciales | Protegido parcialmente | `.env`, `secrets/`, `credentials/`, llaves y certificados estan ignorados |
| Historial privado anterior | Contenido | Ya no esta en la rama limpia, pero sigue existiendo en ramas locales privadas |
| Documentacion interna | Bloqueada en la rama publica | `context/`, `research/`, `docs/` y `notebooks/` quedaron fuera por defecto |
| Riesgo de publicacion accidental desde `main` | Aun existe si se usa la rama equivocada | El remoto debe crearse desde `codex/public-ready`, no desde `main` |

## Pendientes abiertos

| Prioridad | Pendiente | Motivo |
|---|---|---|
| Alta | Crear o revisar `.env.example` | Evita improvisar con un `.env` real cuando aparezcan variables de entorno |
| Alta | Agregar chequeo pre-push minimo de seguridad | Reduce riesgo humano antes de publicar o empujar cambios |
| Alta | Crear repo remoto desde `codex/public-ready` | Es la rama segura; `main` no debe usarse para el primer push publico |
| Media | Definir si habra documentacion publica adicional | `docs/` esta bloqueado por defecto; cualquier excepcion debe revisarse archivo por archivo |
| Media | Definir rutina de cierre de sesion | Mantener este archivo actualizado al final de trabajos relevantes |

## Riesgos vigentes

| Severidad | Riesgo | Mitigacion |
|---|---|---|
| Alta | Empujar `main` por error y exponer historial interno | Publicar solo desde `codex/public-ready` |
| Media | Subir futuros secretos por descuido | Usar `.env.example`, revisar `git status`, `git ls-files` y ejecutar chequeo pre-push |
| Media | Reintroducir documentacion privada al repo | Mantener `.gitignore` estricto y revisar cualquier Markdown nuevo antes de trackearlo |
| Media | Asumir que un archivo Markdown es seguro solo por ser texto | Revisar contenido; notas operativas internas deben quedarse fuera del repo |

## Siguiente sesion

| Orden | Paso previsto |
|---|---|
| 1 | Revisar juntos si conviene crear `.env.example` ahora y con que placeholders |
| 2 | Agregar un chequeo pre-push minimo de seguridad |
| 3 | Preparar la guia exacta para crear el repo remoto desde `codex/public-ready` |

## Regla operativa recomendada

Al cerrar cada sesion relevante, actualizar como minimo:

1. `Resumen actual`
2. `Logros confirmados`
3. `Pendientes abiertos`
4. `Siguiente sesion`

Si en algun momento necesitas una bitacora detallada cronologica, recomiendo mantenerla por separado y preferiblemente en el vault privado.
