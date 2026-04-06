# Demo GitHub

## Captures recommandees

Ajoutez vos vraies captures dans `docs/media/` avec ces noms pour que le README reste stable :

- `dashboard-preview.png`
- `dashboard-command-result.png`
- `monitoring-overview.png`
- `demo.gif`

En attendant, le depot contient deja deux apercus SVG versionnables :

- `docs/media/dashboard-preview.svg`
- `docs/media/flow-overview.svg`

## Script de demo video

Une demo courte de 45 a 60 secondes suffit largement pour GitHub.

1. Lancez la stack avec `docker compose up --build`
2. Ouvrez `http://localhost:8010`
3. Montrez la sante des 5 services
4. Envoyez `allume la lampe du salon`
5. Montrez le changement d'etat
6. Envoyez `regle le thermostat a 23 degres`
7. Affichez les logs et evenements recents
8. Terminez sur l'endpoint `/monitoring/overview`

## Texte de legende possible

`Smart Home Multi-Agent Platform demo: dashboard web, commands in natural language, Redis event routing, and lightweight monitoring.`
