# Structory Carbon (BYOS Carbon)

Module open source (Apache-2.0) qui estime les émissions de gaz à effet de serre **évitées**
(en kg CO2e par an) quand une organisation garde ses données dans **son propre stockage**
(architecture BYOS / « Own Storage first » de Structory) au lieu de les confier à une
application SaaS qui les recopie dans sa propre infrastructure.

> Version 0.1 : méthode de travail, non revue par un tiers. Les résultats sont des **ordres de
> grandeur** encadrés par une fourchette, pas une mesure.

## Ce que le module mesure

Pour une organisation et une année, il compare deux architectures, poste par poste :

- **stockage** des données (énergie d'usage + fabrication des supports) ;
- **réplication et sauvegardes** ajoutées par l'éditeur SaaS ;
- **environnements** hors production (pré-production, recette) contenant des copies ;
- **compute** : serveurs permanents du SaaS contre calcul à la demande de Structory ;
- **réseau** entre centres de données (réplication, ingestion) ;
- **fabrication** (embodied) des serveurs et disques, au prorata de l'usage.

Côté BYOS, seul l'**impact marginal** est compté : les octets que Structory **ajoute** au
stockage que l'organisation possède déjà. Ce stockage préexistant (son Google Drive, par exemple)
n'est **pas** imputé, puisqu'il existe sans Structory. Le détail est dans
[METHODOLOGIE.md](METHODOLOGIE.md).

## Ce qu'il ne mesure pas

- les terminaux des utilisateurs et le réseau d'accès (supposés identiques dans les deux cas) ;
- le développement logiciel, les bureaux, les déplacements ;
- la fin de vie des équipements ;
- les autres impacts environnementaux (eau, métaux, énergie primaire) ;
- le cas d'une organisation qui **crée** un stockage pour Structory (le module refuse alors de
  calculer, plutôt que de produire un chiffre trompeur).

## Facteurs d'impact

Tous les facteurs sont dans [`factors/factors.yaml`](factors/factors.yaml), avec leur source
(ADEME Base Empreinte, Our World in Data / Ember, Cloud Carbon Footprint, Boavizta, Uptime
Institute, Google), leur URL, leur date d'accès et leur version. Aucun facteur n'est inventé :
ceux qui n'ont pas de source vérifiable sont à `null` avec le statut `A_SOURCER`, et le calcul
exige alors une hypothèse explicite dans le profil.

## Lancer le calcul

Prérequis : Python 3.10 ou plus.

```bash
python -m venv .venv && . .venv/bin/activate
pip install -e ".[test]"

# calcul sur le profil d'exemple : écrit un rapport Markdown et un rapport JSON
structory-carbon examples/org_exemple.yaml --out examples/
# ou sans installation :
python -m structory_carbon examples/org_exemple.yaml --out examples/

# tests
pytest
```

Pour votre organisation : copiez `examples/org_exemple.yaml`, adaptez les volumes et les
hypothèses (chaque hypothèse peut être une valeur unique ou un triplet `bas` / `central` /
`haut`), puis relancez. Le rapport rappelle toutes les hypothèses utilisées et la version des
facteurs.

## Structure

```
METHODOLOGIE.md          périmètre, équation, hypothèses, limites
factors/factors.yaml     facteurs d'impact sourcés et versionnés
structory_carbon/        bibliothèque Python + CLI
tests/                   tests pytest
examples/                profil d'exemple et rapports générés
```

## Licence

Apache-2.0, voir [LICENSE](LICENSE).
