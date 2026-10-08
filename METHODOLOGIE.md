# Méthodologie carbone — Structory Green V0.1

> Statut : **V0.1, méthode de travail, non revue par un tiers.** Ce document décrit comment le
> module estime les émissions de gaz à effet de serre (en kg CO2e) **évitées** par une architecture
> BYOS + Structory par rapport à une architecture SaaS de référence. Il ne constitue ni une ACV
> conforme ISO 14040/14044, ni un bilan GES réglementaire.

## 1. Question posée

Pour **une organisation** utilisant Structory pendant **un an**, combien d'émissions sont évitées
parce que ses données restent dans **son propre stockage, déjà existant** (par exemple son Google
Drive), au lieu d'être recopiées dans l'infrastructure d'un éditeur SaaS ?

Les deux architectures comparées :

| | **BYOS + Structory** (« Own Storage first ») | **SaaS de référence** |
|---|---|---|
| Source de vérité | Journal en ajout seul, dans le stockage de l'organisation | Base de données de l'éditeur |
| Données dérivées (bilan, trésorerie, reporting) | Recalculées à la demande, jamais stockées en double | Souvent matérialisées (tables, index, caches) |
| Pièces jointes / documents | Restent là où l'organisation les a déjà | Recopiées dans le stockage objet de l'éditeur |
| Réplication, sauvegardes | Celles du stockage de l'organisation, **déjà existantes** | Ajoutées par l'éditeur (multi-zone, instantanés, rétention) |
| Environnements | Aucun environnement hébergeant les données de l'organisation | Production + pré-production / recette, parfois avec copie de données |
| Compute | À la demande (Addon Google Sheets, Main web, Game, Appli mobile) | Serveurs applicatifs et base **permanents** (24 h/24) |

## 2. Unité fonctionnelle

> **Tenir la comptabilité (journal + états recalculés) d'une organisation pendant 1 an**, pour un
> volume de `N` écritures par mois de `b` octets chacune, un historique de `H` années conservé,
> et `A` Go de pièces jointes rattachées.

Ces paramètres sont fournis par le **profil d'organisation** (fichier YAML, voir
`examples/org_exemple.yaml`). Le résultat est exprimé en **kg CO2e évités par an** pour cette
organisation.

## 3. Frontières du système

**Inclus :**

- stockage des données de l'organisation (énergie d'usage + part de fabrication des supports) ;
- copies dues à la réplication, aux sauvegardes et aux environnements hors production ;
- compute serveur (énergie d'usage + part de fabrication) attribuable à l'organisation ;
- réseau **entre centres de données** induit par la réplication et l'ingestion des données ;
- refroidissement et pertes du centre de données, via le PUE.

**Exclus (identiques dans les deux architectures ou hors périmètre) :**

- terminaux des utilisateurs (ordinateurs, téléphones) et leur affichage ;
- trafic réseau vers l'utilisateur final (supposé équivalent : l'utilisateur consulte les mêmes
  états dans les deux cas — hypothèse discutée en §8) ;
- développement logiciel, bureaux, déplacements de l'éditeur ;
- fin de vie des équipements (non incluse dans les facteurs Boavizta utilisés) ;
- autres indicateurs environnementaux (eau, métaux, énergie primaire) : V0.1 ne traite que le
  changement climatique (GWP).

### 3.1 Règle centrale : marginal BYOS ≠ stockage préexistant

C'est la règle la plus importante de cette méthode, et la plus facile à mal appliquer.

- L'organisation **possède déjà** un stockage (Google Drive, OneDrive, NAS…), avec sa propre
  réplication, ses propres sauvegardes et ses propres serveurs. Cette infrastructure existe
  **indépendamment** de Structory. Elle **n'est pas imputée** au scénario BYOS.
- Seul l'**impact marginal** du BYOS est imputé : les **octets ajoutés** par Structory à ce
  stockage (le journal en ajout seul et les éventuels fichiers techniques), multipliés par les
  facteurs de stockage, de réplication et de PUE de ce stockage.
- Les **pièces jointes que l'organisation avait déjà** dans son stockage ne sont **pas** imputées
  au BYOS (elles y étaient avant). Dans le scénario SaaS, en revanche, leur **recopie** chez
  l'éditeur **est** imputée.

Conséquence assumée : si l'organisation n'avait aucun stockage et en souscrivait un pour Structory,
cette méthode **sous-estimerait** l'impact du BYOS. Le profil doit alors le déclarer
(`byos.preexisting_storage: false`), et V0.1 refuse de calculer (voir §8).

## 4. Équation comparative

```
CO2e_évité = Σ_postes [ E_SaaS(poste) − E_BYOS(poste) ]        (kg CO2e / an)
postes = stockage, réplication et sauvegardes, environnements, compute, réseau, fabrication
```

Notations (toutes par an) :

| Symbole | Sens | Origine |
|---|---|---|
| `V_j` | volume du journal = `N × 12 × b × H` (Go) | profil |
| `A` | pièces jointes (Go) | profil |
| `k_d` | surcoût des données dérivées matérialisées et index côté SaaS (fraction de `V_j`) | profil (hypothèse) |
| `R` | facteur de réplication d'un service de stockage | facteurs / profil |
| `B` | nombre de copies complètes équivalentes conservées en sauvegarde | profil (hypothèse) |
| `n_env` | nombre d'environnements hors production contenant une copie des données | profil (hypothèse) |
| `c_s` | énergie de stockage (Wh/To·h), SSD ou HDD | facteurs (CCF) |
| `PUE` | efficacité énergétique du centre de données | facteurs |
| `CI` | intensité carbone de l'électricité de la zone | facteurs |
| `EF_s` | fabrication du support de stockage (kgCO2e/To) | facteurs (Boavizta) |
| `L_s` | durée de vie du support (ans) | profil (hypothèse) |
| `P_vcpu(u)` | `W_min + u × (W_max − W_min)` par vCPU, `u` = taux d'utilisation | facteurs (CCF) + profil |
| `c_m` | énergie mémoire (kWh/Go·h) | facteurs (CCF) |
| `EF_vcpu` | fabrication allouée par vCPU·an | facteurs (Boavizta) |
| `c_net` | énergie réseau inter-centres (kWh/Go) | facteurs (CCF) |

### 4.1 Stockage (y compris réplication, sauvegardes, environnements)

Volume physique stocké (To) :

```
SaaS : S_saas = [ V_j × (1 + k_d) × (R_db × (1 + n_env) + B × R_bkp) + A × R_obj ] / 1000
BYOS : S_byos = V_j × R_byos / 1000            (pièces jointes préexistantes : non imputées)
```

Énergie et émissions d'usage :

```
E_stockage = S × c_s × 8760 / 1000 × PUE × CI          (kWh × kgCO2e/kWh)
```

Fabrication des supports, allouée au volume occupé et à la durée de vie :

```
F_stockage = S × EF_s / L_s
```

Les postes « réplication et sauvegardes » et « environnements » sont rapportés **séparément** dans
le rapport : on calcule le stockage de base (`R = 1`, sans sauvegarde ni environnement), puis
l'écart dû à chaque multiplicateur.

### 4.2 Compute

```
SaaS : E_compute = Σ_env [ vcpu × P_vcpu(u) × 8760 / 1000 + mem × c_m × 8760 ] × part_org × PUE × CI
BYOS : E_compute = [ h_vcpu × P_vcpu(u) / 1000 + h_vcpu × mem_par_vcpu × c_m ] × PUE × CI
```

- `part_org` : part de l'infrastructure SaaS attribuable à l'organisation (une plateforme SaaS
  est mutualisée : une instance sert de nombreux clients). **Hypothèse du profil, très
  sensible.**
- `h_vcpu` : vCPU·heures réellement consommées à la demande par les applications Structory
  (recalcul du bilan, de la trésorerie…). Le compute **préexistant** du stockage de l'organisation
  (serveurs de Google Drive) n'est pas imputé.

Fabrication :

```
SaaS : F_compute = Σ_env vcpu × part_org × EF_vcpu
BYOS : F_compute = h_vcpu / 8760 × EF_vcpu
```

### 4.3 Réseau (inter-centres)

```
SaaS : E_réseau = [ ingestion_annuelle × (R_db − 1) + volume_sauvegardé_annuel ] × c_net × CI
BYOS : E_réseau = V_j_annuel × (R_byos − 1) × c_net × CI
```

avec `ingestion_annuelle = (N × 12 × b) × (1 + k_d) + A_nouvelles` et
`volume_sauvegardé_annuel = ingestion_annuelle × B`. V0.1 n'applique pas de PUE au réseau (le
coefficient CCF est déjà un ordre de grandeur d'énergie par Go transféré).

### 4.4 Infrastructure et fabrication (embodied)

La fabrication est traitée **dans chaque poste** (`F_stockage`, `F_compute`) plutôt qu'en poste
isolé, afin que la même règle « marginal vs préexistant » s'applique. Le rapport présente
néanmoins un sous-total « fabrication ». Les bâtiments, réseaux électriques et équipements de
refroidissement ne sont pas modélisés séparément : ils sont partiellement couverts par le PUE
(énergie) et non couverts pour leur fabrication (limite, §8).

## 5. Facteurs d'impact

Tous les facteurs sont dans [`factors/factors.yaml`](factors/factors.yaml), **versionnés** (champ
`version`, actuellement `2026.10.0`). Chaque facteur porte : valeur, unité, source, URL, date
d'accès, version de la source, et un statut :

- `SOURCE` : valeur reprise telle quelle d'une source publique vérifiée le 2026-10-07 ;
- `DERIVE` : valeur calculée à partir de facteurs `SOURCE`, formule donnée ;
- `A_SOURCER` : **aucune source vérifiable** trouvée ; valeur `null`. Le calcul ne l'invente
  pas : il exige une hypothèse explicite dans le profil, ou refuse de calculer.

Sources principales :

| Domaine | Source | Pourquoi |
|---|---|---|
| Électricité France | ADEME Base Empreinte (via la documentation Nos Gestes Climat) | Référence officielle française, ACV |
| Électricité UE, monde, US, Irlande | Our World in Data / Ember (2026) | Séries à jour, cycle de vie |
| PUE | Uptime Institute 2024 ; Google 2025 ; Cloud Carbon Footprint (AWS) | Moyenne du secteur vs hyperscalers |
| Énergie stockage, compute, mémoire, réseau, réplication | Cloud Carbon Footprint (Thoughtworks, open source) | Méthode publique et largement reprise |
| Fabrication (SSD, HDD, instance cloud) | Boavizta (API 2.4.1, d'après UBA « Green Cloud Computing » 2021) | Référence open source française |

Facteurs **À SOURCER** à ce jour :

1. `replication_google_drive` — Google ne publie pas le facteur de réplication de Drive. Le profil
   doit donner `byos.replication` ; l'exemple utilise le facteur CCF de Google Cloud Storage (2)
   comme **proxy déclaré**.
2. `hdd_capacity_datacenter` — capacité moyenne d'un disque de centre de données, nécessaire pour
   ramener l'impact de fabrication d'un HDD au To. Tant qu'elle manque, V0.1 ne calcule la
   fabrication du stockage que pour des supports SSD.
3. `network_end_user_energy` — énergie du réseau d'accès vers l'utilisateur. Non utilisée en V0.1
   (trafic supposé équivalent).

## 6. Hypothèses explicites

Toutes les hypothèses sont **dans le profil**, jamais dans le code. Chacune peut être donnée sous
la forme d'une valeur unique ou d'un triplet :

```yaml
backup_copies: { bas: 1, central: 2, haut: 7 }
```

Convention : **`bas` est la valeur qui donne le MOINS d'émissions évitées** (scénario prudent),
`haut` celle qui en donne le plus. Un paramètre peut aussi désigner un facteur par son identifiant
(par exemple `pue: { bas: pue_aws, central: pue_aws, haut: pue_industry_avg }`).

Hypothèses à justifier par l'utilisateur du module (liste non exhaustive) : `k_d`, `B`, `n_env`,
`part_org`, `h_vcpu`, `u`, `L_s`, `R_byos`, le type de support (SSD par défaut), les zones
électriques des deux architectures.

## 7. Fourchette basse / centrale / haute

- **Centrale** : toutes les hypothèses à leur valeur `central`, facteurs à leur valeur nominale.
- **Basse** : toutes les hypothèses à `bas` ; pour les facteurs qui publient un `min`/`max`
  (Boavizta), le calcul retient celui des deux qui **réduit** le plus le résultat.
- **Haute** : symétrique (`haut`, et la borne de facteur qui l'**augmente** le plus).

Cette fourchette est un **encadrement par scénarios**, pas un intervalle de confiance statistique.
Elle ne couvre pas l'incertitude propre des facteurs qui ne publient pas de borne.

## 8. Limites et incertitudes

1. **Ordre de grandeur, pas une mesure.** Les coefficients CCF sont des moyennes de parc ; un
   fournisseur réel peut s'en écarter fortement.
2. **Allocation SaaS (`part_org`)**. C'est le paramètre le plus sensible et le moins observable.
   Une plateforme mutualisée sur des milliers de clients donne une part très faible ; une
   instance dédiée donne 1. Le résultat peut varier de plusieurs ordres de grandeur.
3. **Stockage préexistant**. La méthode suppose que l'organisation a déjà un stockage et ne
   l'agrandit pas pour Structory. Si l'ajout du journal fait franchir un palier d'abonnement ou
   de matériel, l'impact marginal est sous-estimé. Si l'organisation crée un stockage pour
   Structory (`preexisting_storage: false`), V0.1 **refuse** de calculer plutôt que de produire un
   chiffre trompeur.
4. **Compute à la demande côté BYOS**. Le recalcul (bilan, trésorerie) est fait dans des
   environnements tiers (Google Apps Script, navigateur, mobile) dont la consommation réelle
   n'est pas publiée ; `h_vcpu` est une estimation.
5. **Terminaux et réseau d'accès exclus**. Si le recalcul côté client allonge sensiblement le
   temps d'usage des terminaux, l'avantage BYOS est surestimé.
6. **Fabrication allouée linéairement** au volume occupé et à la durée de vie ; ne tient pas
   compte du taux de remplissage réel des disques (sous-remplissage → sous-estimation des deux
   côtés).
7. **Fin de vie non incluse** (limite des facteurs Boavizta utilisés).
8. **Effets rebond et indirects** non modélisés (par exemple : le BYOS encourage-t-il à conserver
   plus de données dans le stockage personnel ?).
9. **Facteurs À SOURCER** (§5) : tant qu'ils sont nuls, les hypothèses qui les remplacent sont
   affichées comme telles dans le rapport.

## 9. Évolution

Toute modification d'une valeur de facteur incrémente `version` dans `factors/factors.yaml` ; le
rapport mentionne la version utilisée. Toute modification de l'équation incrémente la version de
cette méthodologie (en-tête). Pistes V0.2 : sourcer les facteurs manquants, ajouter les
indicateurs Boavizta (eau, ADP), comparer avec les bornes CCF min/max par fournisseur.
