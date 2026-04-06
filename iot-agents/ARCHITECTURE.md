# Architecture

## Vue d'ensemble

Le projet implemente une architecture micro-services simple pour illustrer le pilotage d'objets connectes simules.

Flux principal :

1. Le client envoie une commande texte au `ui-agent`
2. Le `ui-agent` publie un message `nl.command` sur Redis Streams
3. Le `coordinator` parse la commande et determine la cible
4. L'agent objet execute l'action et renvoie un `device.result`
5. Le `ui-agent` retourne la reponse HTTP et met a jour le dashboard

## Services

### `ui-agent`

- expose `POST /command`
- sert le dashboard web sur `/`
- collecte les metriques des autres services
- maintient les commandes en attente par `trace_id`

### `coordinator`

- transforme une commande naturelle en action structuree
- route vers `lamp-agent`, `plug-agent` ou `thermostat-agent`
- renvoie une erreur propre si la commande n'est pas comprise

### Agents objets

- `lamp-agent`
- `plug-agent`
- `thermostat-agent`

Chaque agent :

- ecoute le topic `device.command`
- applique une action metier locale
- renvoie un `device.result`
- expose `/state`, `/healthz`, `/metrics` et `/dump`

## Observabilite

Chaque service partage une couche commune d'observabilite :

- logs JSON sur stdout
- buffer de logs recent en memoire
- buffer d'evenements recent en memoire
- compteurs de messages publies, consommes, traites, en erreur

Cette approche reste legere, sans ajouter Prometheus ou Grafana, tout en etant suffisante pour une demo, une soutenance ou un depot GitHub propre.
