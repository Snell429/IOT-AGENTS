# Schema C4 simplifie

Ce document propose une vue C4 simplifiee du projet pour une soutenance ou une lecture rapide sur GitHub.

## Niveau 1 : Contexte

```mermaid
flowchart LR
    user[Utilisateur]
    repo[Plateforme Smart Home Multi-Agent]
    user -->|Pilote les objets et consulte le dashboard| repo
```

## Niveau 2 : Conteneurs

```mermaid
flowchart LR
    user[Utilisateur / Navigateur]

    subgraph system[Smart Home Multi-Agent Platform]
        ui[ui-agent<br/>FastAPI<br/>Dashboard + API HTTP]
        redis[(Redis Streams)]
        coordinator[coordinator<br/>Parsing + routage]
        lamp[lamp-agent]
        plug[plug-agent]
        thermo[thermostat-agent]
    end

    user -->|HTTP| ui
    ui -->|nl.command| redis
    redis --> coordinator
    coordinator -->|device.command| redis
    redis --> lamp
    redis --> plug
    redis --> thermo
    lamp -->|device.result| redis
    plug -->|device.result| redis
    thermo -->|device.result| redis
    redis --> ui
```

## Niveau 3 : Composants logiques

```mermaid
flowchart TB
    subgraph ui_agent[ui-agent]
        api[API /command]
        dashboard[Dashboard / monitoring overview]
        pending[Pending requests par trace_id]
    end

    subgraph common[smart_home.common]
        messaging[Messaging / Redis Streams]
        parsing[Parsing langage naturel]
        observability[Logs + metriques + evenements]
        device_base[Base des agents objets]
    end

    subgraph services[Services]
        coordinator[Coordinator]
        lamp[Lamp Agent]
        plug[Plug Agent]
        thermo[Thermostat Agent]
    end

    api --> messaging
    dashboard --> observability
    pending --> messaging
    coordinator --> parsing
    coordinator --> messaging
    lamp --> device_base
    plug --> device_base
    thermo --> device_base
    device_base --> messaging
    device_base --> observability
    coordinator --> observability
    ui_agent --> observability
```

## Lecture rapide

- Niveau 1 : l'utilisateur interagit avec une seule plateforme.
- Niveau 2 : la plateforme est composee de 5 conteneurs applicatifs et d'un bus Redis.
- Niveau 3 : la logique reutilisable est mutualisee dans `smart_home.common`.
