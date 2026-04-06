# Presentation PowerPoint - plan suggere

## Slide 1 - Sujet

- Plateforme de pilotage intelligent d'objets connectes simules.
- Architecture micro-services avec agents IA simples.

## Slide 2 - Objectif

- Recevoir une commande en langage naturel.
- Identifier l'objet cible.
- Transmettre la commande a l'agent adequat.
- Retourner l'etat ou le resultat.

## Slide 3 - Architecture

- `ui-agent`
- `coordinator`
- `lamp-agent`
- `plug-agent`
- `thermostat-agent`
- `redis`

## Slide 4 - Flux de messages

1. L'utilisateur envoie une commande a `ui-agent`.
2. `ui-agent` publie un message `nl.command`.
3. `coordinator` analyse la phrase et publie `device.command`.
4. L'agent-objet execute puis repond en `device.result`.
5. `ui-agent` retourne la reponse HTTP.

## Slide 5 - Contrat JSON

- `schema_version`
- `msg_id`
- `trace_id`
- `from`
- `to`
- `topic`
- `content`
- `ts`

## Slide 6 - Demonstrations

- Allumer une lampe.
- Eteindre une prise.
- Consulter l'etat du thermostat.
- Bonus : regler la temperature cible.

## Slide 7 - Difficultes

- Parsing simple du langage naturel.
- Gestion d'un bus d'evenements Redis Streams.
- Synchronisation entre HTTP et architecture asynchrone.

## Slide 8 - Bilan

- Prototype fonctionnel et modulaire.
- Facile a etendre avec de nouveaux objets.
- Base compatible avec une future integration d'un vrai LLM local.
