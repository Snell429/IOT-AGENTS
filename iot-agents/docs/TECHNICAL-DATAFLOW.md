# Architecture technique et flux de donnees

Ce schema rassemble la vue technique et le parcours d'une commande sur une seule page.

## Schema principal

Image de reference du projet :

![Architecture technique et flux de donnees](./media/architecture-technique-flux-donnees.png)

Version SVG alternative du depot :

![Architecture technique et flux de donnees - SVG](./media/architecture-technical-dataflow.svg)

```mermaid
flowchart LR
    classDef ext fill:#f7f1e8,stroke:#cdbda8,color:#2a3135;
    classDef api fill:#eef7f8,stroke:#7ca8ad,color:#1f2b33;
    classDef bus fill:#fff1e8,stroke:#d7885d,color:#4c2d1c;
    classDef svc fill:#f9fbfc,stroke:#a9bbc3,color:#24323a;
    classDef obs fill:#eef6ef,stroke:#7fb08c,color:#203127;

    user[Utilisateur / Browser]:::ext

    ui[ui-agent<br/>FastAPI<br/>Dashboard<br/>POST /command]:::api
    redis[(Redis Streams<br/>a2a_bus)]:::bus
    coordinator[coordinator<br/>NL parsing<br/>routing]:::svc
    lamp[lamp-agent<br/>state + metrics]:::svc
    plug[plug-agent<br/>state + metrics]:::svc
    thermo[thermostat-agent<br/>state + metrics]:::svc

    monitor[Monitoring global<br/>/monitoring/overview]:::obs
    logs[Logs JSON<br/>Events buffer<br/>Metrics snapshot]:::obs

    user -->|1. HTTP command| ui
    ui -->|2. publish nl.command| redis
    redis -->|3. consume| coordinator
    coordinator -->|4. publish device.command| redis
    redis -->|5a. lamp action| lamp
    redis -->|5b. plug action| plug
    redis -->|5c. thermostat action| thermo

    lamp -->|6. device.result| redis
    plug -->|6. device.result| redis
    thermo -->|6. device.result| redis
    redis -->|7. response| ui
    ui -->|8. HTTP response| user

    ui -. collect .-> coordinator
    ui -. collect .-> lamp
    ui -. collect .-> plug
    ui -. collect .-> thermo

    ui --> monitor
    coordinator --> logs
    lamp --> logs
    plug --> logs
    thermo --> logs
    ui --> logs
```

## Parcours d'une commande

1. L'utilisateur envoie une commande HTTP au `ui-agent`.
2. Le `ui-agent` publie un message `nl.command` dans Redis Streams.
3. Le `coordinator` lit ce message et interprete l'intention.
4. Le `coordinator` publie une commande structuree `device.command`.
5. L'agent cible applique l'action.
6. L'agent publie un `device.result`.
7. Le `ui-agent` recupere la reponse.
8. Le resultat est retourne au client et visible dans le dashboard.
