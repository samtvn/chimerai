# Inventory Core - CellarTracker
- bottle（producer / cuvée / vintage）：Optical Character Recognition
- quantity
- location（rack / case / offsite）
- purchase price vs current value
- drink window
# Valuation Engine
- iDealwine / Zachys / wine searcher
# Preference Engine - Sommelier Brain
- user input: acid / tannin / body / oak / style
- mapping
# Decision Engine
- constrained optimization

---

# Alignement des priorités avec les critères d’évaluation
## Exécution technique (20 %) — ne réinventez pas la roue

Ne perdez pas de temps à développer un OCR ou un scraper from scratch.
Utilisez directement l’API de GPT-4o Vision. Elle peut reconnaître les informations présentes sur une étiquette de vin et retourner un JSON structuré.

Ce que vous devez démontrer, ce n’est pas la capacité à coder des briques bas niveau, mais la manière dont vous utilisez LangChain ou LangGraph pour orchestrer la logique de l’Agent :

Reconnaissance → Recherche de prix → Matching culinaire → Génération de recommandation

## Innovation & créativité (20 %) — insistez sur l’aspect “Agentic”

Si l’application se limite à “scanner une bouteille et afficher une note”, cela reste un simple outil.

Un Agent se distingue par sa capacité à :

- raisonner,
- prendre des décisions,
- utiliser des outils,
- agir de manière autonome.

```
Exemple :

L’utilisateur photographie le contenu de son réfrigérateur.

L’Agent :

analyse l’image,
vérifie automatiquement le stock de la cave,
détecte une bouteille de Riesling à forte acidité,
propose un accord avec le poisson présent dans le frigo,
recommande la température de service idéale.
```

L’intérêt n’est pas uniquement la recommandation, mais le raisonnement autonome derrière celle-ci.

## Présentation & Storytelling (20 %) — visualiser le “raisonnement” de l’Agent

Les jurys adorent voir comment un Agent “pense”.

Afficher dans l’interface :

- Thought
- Action
- Observation

sera souvent plus impactant qu’une interface très esthétique mais statique.

L’objectif est de rendre visible :

- la chaîne de décision,
- les outils appelés,
- les étapes de raisonnement.

# Version “allégée” du projet : conserver le squelette, abandonner le reste

Pour sortir un prototype crédible en un mois, adoptez une approche :

“Narrow but Deep” (étroit mais profond)
Données (à réduire)

Abandonnez l’idée d’une base de données exhaustive.

Conservez uniquement :

50 à 100 références soigneusement choisies,
couvrant les principaux profils acidité / tanins / corps.

Pendant la démonstration, assurez-vous simplement que les bouteilles scannées existent dans cette base.

Estimation de valeur (à simplifier)

Ne tentez pas une intégration temps réel avec des APIs de prix coûteuses.

Utilisez :

des Mock Data,
ou des prix moyens statiques.

Le but est surtout de démontrer :

- l’évolution de valeur,
- la logique d’analyse,
- la visualisation.
- Fonctionnalités (à prioriser)

Concentrez-vous sur le Mapping des profils gustatifs.

C’est ici que votre expertise métier et l’IA deviennent réellement différenciantes :

Transformer :

- acidité,
- structure,
- tanins,
- élevage,
- texture,

en recommandations compréhensibles pour un utilisateur non expert.

# Organisation du projet sur 4 semaines

1. Semaine 1 — Prompt Engineering & Data Schema

Définir :

le format JSON d’une bouteille,
les attributs gustatifs,
les règles de raisonnement,
les prompts Agent.
2. Semaine 2 — Backend minimal

Construire rapidement une interface avec :

`Streamlit` ou `Gradio`

afin d’éviter la complexité d’un vrai front-end mobile et rester concentré sur la démonstration fonctionnelle.

3. Semaine 3 — Logique Agent

Implémenter les deux chaînes principales :

inventaire intelligent de cave,
recommandation et matching.

L’objectif principal :
obtenir une boucle complète fonctionnelle :

Image → OCR → Recherche → Raisonnement → Recommandation

4. Semaine 4 — Storytelling & Démo

Préparer :

la vidéo de démonstration,
les scénarios,
la narration produit.

Prévoir idéalement :

un scénario B2C (dîner à domicile),
un scénario B2B (restaurant / génération rapide de carte des vins).

# Questions essentielles à poser lors du premier coaching

1. Sur la définition de “Agentic AI”

Aux yeux du jury, un Agentic AI crédible repose-t-il davantage sur :

- son autonomie d’action (tool calling, orchestration),
- ou sur la profondeur de l’interaction utilisateur ?

2. Devons-nous concentrer l’effort technique sur le Function Calling et l’orchestration multi-outils ?

3. Sur le positionnement B2B vs B2C

Pour une démo dans un délai d’un mois :

- vaut-il mieux approfondir un cas d’usage B2C très fluide,
- ou montrer une capacité d’extension vers le B2B (ex. génération de carte des vins pour restaurant) afin de renforcer la crédibilité business ?
4. Sur les données de marché

- Si nous utilisons des données simulées
- ou des prix moyens au lieu d’APIs premium temps réel, cela sera-t-il perçu comme une faiblesse importante dans le critère “Technical Execution” ?

5. Sur le format du livrable

Le jury accorde-t-il davantage de valeur :

- à une démo réellement interactive,
- ou à une vidéo de présentation très bien scénarisée et techniquement claire ?
6. Sur l’aspect éducatif

Nous envisageons une fonctionnalité de “Wine Mapping” destinée à éduquer progressivement l’utilisateur dans ses choix de vin.

Cette dimension pédagogique peut-elle être considérée comme un élément fort d’Impact dans l’évaluation du projet ?
