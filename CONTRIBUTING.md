# Contribuer

## Mise en place

```bash
make init        # venv + deps + hooks pre-commit
cp .env.example .env
```

## Workflow

1. Brancher depuis `develop`.
2. Coder en respectant les conventions (`AGENTS.md`) : typage strict, pas de commentaires,
   structlog, types concrets.
3. Ajouter/mettre a jour les tests (au moins un cas nominal + un cas d'erreur).
4. `make build` (lint + typecheck + test) doit etre vert avant tout push.
5. Ouvrir une PR vers `develop` ; la CI rejoue lint, format-check, typecheck, tests + couverture.

## Conventions de commit

Messages courts a l'imperatif (`feat:`, `fix:`, `docs:`, `test:`, `refactor:`).

## Tests

- Hors-ligne par defaut (providers scriptés, `httpx.MockTransport`).
- Marquer `@pytest.mark.integration` les tests necessitant vLLM/Qdrant.
