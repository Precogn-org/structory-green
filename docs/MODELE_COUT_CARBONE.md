# Structory Green — modèle coût + carbone à l'échelle (BYOS + Structory face à un SaaS de référence)

> Statut : **V0.1, méthode de travail.** Complète [METHODOLOGIE.md](../METHODOLOGIE.md) (carbone
> pour une organisation) avec un **coût annuel** et une **extrapolation à N organisations**.
> Les chiffres servent à dimensionner un business plan. Ce ne sont ni des devis ni des mesures.

## 1. Question posée

Quel coût annuel (en EUR HT) et quelle empreinte (en tCO2e) pour **N organisations** :

- **SaaS classique** : l'éditeur recopie les données de chaque organisation dans sa base, les
  réplique, les sauvegarde et fait tourner des serveurs **permanents** ;
- **BYOS + Structory** : les données restent dans le stockage de chaque organisation.
  L'éditeur ne paie qu'un **socle** de calcul (API, recalculs) qui sert toutes les organisations.

Le coût est vu **du côté de l'éditeur**. Le **coût marginal pour l'organisation** BYOS (le
journal ajouté dans son propre stockage) est donné à part.

## 2. Postes

| Poste | SaaS (éditeur) | BYOS (éditeur) |
|---|---|---|
| Stockage | copie de base en volume bloc + pièces jointes en stockage objet | 0 : données chez l'organisation |
| Réplication et sauvegardes | réplicas multi-zone, environnements hors prod, sauvegardes de volume | 0 : celles du stockage de l'organisation, préexistantes |
| Compute | socle (prod + préprod) + vCPU ajoutés avec N | part du VPS socle + VPS ajoutés avec N |
| Réseau / egress | Go sortants × prix de l'egress (0 € chez OVH Public Cloud) | 0 € (trafic VPS illimité inclus) |
| Infrastructure | load balancer | aucune (hypothèse) |
| Exploitation | **non chiffrée** : prix À SOURCER | **non chiffrée** : prix À SOURCER |

## 3. Équations

Notations : `N` = nombre d'organisations ; `H = 8760` h/an ; `s` = scénario (bas, central, haut).

### 3.1 Coût SaaS

```
V0      = Σ vCPU des environnements du socle                      (12 dans l'exemple)
v       = org_share × V0                                          vCPU permanents par organisation
F_saas  = Σ_env prix_instance × H + n_LB × prix_LB × 12            coût FIXE (socle)
c_saas  = v_d·p_bloc + A·p_objet                                   stockage, par organisation
        + v_d·(R_db·(1+n_env) − 1)·p_bloc + v_d·B·p_sauvegarde     réplication et sauvegardes
        + egress_Go·p_egress                                       réseau
C_saas(N) = F_saas + N·c_saas + p_vcpu·H·max(0, N·v − V0)
```

`v_d` = journal + données dérivées (Go), `A` = pièces jointes (Go), `R_db`, `n_env`, `B` comme
dans METHODOLOGIE.md §4. Les prix `p_*` sont annualisés : prix horaire × 8760, prix mensuel × 12.

### 3.2 Coût BYOS

```
α       = RAM de production / RAM du VPS                           part du VPS socle imputée
H_vps   = vCPU_vps × H × u_max                                     vCPU·h utiles d'un VPS
h       = vCPU·h par organisation et par an                        (byos.vcpu_hours_per_year)
n_vps(N)= ceil( max(0, N·h − α·H_vps) / H_vps )                     VPS ajoutés au-delà du socle
C_byos(N) = α·P_vps + P_vps·n_vps(N)                               P_vps = prix annuel du VPS
Coût marginal pour l'organisation = 0 si le journal tient dans son quota existant,
                                    sinon V_j × p_objet (valeur indicative)
```

### 3.3 Carbone

Même structure : chaque vCPU, Go de RAM et Go stocké est converti en énergie puis en kgCO2e, avec
les facteurs de `factors/factors.yaml`.

```
E_vcpu(u) = [W_min + u·(W_max − W_min)]·H/1000 + RAM_par_vcpu·c_m·H        kWh/an
CO2_saas(N) = [E_socle + (N·v − V0)⁺ · E_vcpu(u_add)] · PUE_saas · CI_saas
            + (V0 + (N·v − V0)⁺) · EF_vcpu  +  N · d_saas
CO2_byos(N) = [vCPU_alloués · P(u_charge)·H/1000 + RAM_allouée·c_m·H] · PUE_ovh · CI_byos
            + vCPU_alloués · EF_vcpu  +  N · d_byos
```

- `d_saas`, `d_byos` : carbone **des données** d'une organisation (stockage, réplication,
  environnements, réseau inter-centres, fabrication des disques), repris du modèle par
  organisation (METHODOLOGIE.md §4). `d_byos` ne compte que les octets ajoutés au stockage existant.
- `vCPU_alloués = (α + n_vps)·vCPU_vps`, `u_charge = min(u_max, N·h / (vCPU_alloués·H))`.
- Pour éviter un double comptage, le compute BYOS à la demande est entièrement porté par le VPS
  socle. Le calcul éventuellement fait chez Google (Apps Script) n'est pas compté en plus.

### 3.4 Effet d'échelle

- **SaaS** : le socle `F_saas` s'amortit, puis le coût par organisation tend vers
  `c_saas + p_vcpu·H·v`. Il reste **proportionnel à N**, car chaque organisation mobilise des vCPU
  permanents et des copies de ses données.
- **BYOS** : le socle (une fraction d'un VPS à quelques euros par mois) suffit pour des milliers
  d'organisations. Au-delà, on ajoute des VPS **par paliers**, au rythme du calcul réellement
  consommé (`h`) et non de capacités permanentes. Le coût par organisation tend vers
  `P_vps·h / H_vps`.

## 4. Sources

- **Prix** : [`factors/prices.yaml`](../factors/prices.yaml), version `2026.10.0`, EUR HT, relevés
  le 2026-10-08 dans l'API publique de catalogue OVHcloud FR (cloud : catalogId 9694 ; VPS :
  catalogId 9773).
  - Instances b3-16 et b3-32.
  - vCPU dérivé de b3-8.
  - Volume high-speed : 0,086 €/Go/mois.
  - Volume backup : 0,000015 €/Go/h.
  - Object Storage Standard : 0,00000972 €/Go/h.
  - Egress d'instance : 0 €.
  - Load Balancer S : 6 €/mois.
  - VPS-1 2026 : 6,49 €/mois (4 vCore, 8 Go).
  - Exploitation : **À SOURCER** (null).
- **Facteurs carbone** : [`factors/factors.yaml`](../factors/factors.yaml), version `2026.10.1`.
  Ajout de `pue_ovh` = 1,24 (OVHcloud, KPIs FY2025, ligne « OVH Group »).
- **Socle BYOS** : mesure interne du 08/10/2026 sur le VPS de production PreCogn (OVH, lecture
  seule) :
  - 7 751 Mo de RAM, sans swap ;
  - API analyzor : 4 workers, environ 0,8 Go ;
  - modèle IA local qwen2.5-coder:3b : 2 092 Mo, chargé à la demande ;
  - le reste sert aux sessions de développement et est **exclu**.

  Pas de mesure CPU, réseau ou disque par organisation : ces valeurs restent des **HYPOTHÈSES**.

## 5. Hypothèses (profil `examples/org_exemple.yaml`, section `echelle`)

Convention : `bas` est la valeur la **moins favorable** au BYOS (moins d'écart de coût et de
carbone).

| Hypothèse | bas | central | haut | Commentaire |
|---|---:|---:|---:|---|
| `saas.org_share` (→ v = org_share × 12 vCPU) | 0,001 (0,012 vCPU) | 0,005 (0,06 vCPU) | 0,02 (0,24 vCPU) | **Hypothèse dominante** |
| `byos.vcpu_hours_per_year` (h) | 50 | 10 | 2 | Aucune mesure par organisation |
| `byos.ram_production_gb` (→ α) | 7,751 (VPS entier) | 2,892 (API + IA) | 0,8 (API seule) | Mesure interne 08/10/2026 |
| `echelle.byos.utilisation_max` | 0,5 | 0,5 | 0,5 | Charge CPU cible avant d'ajouter un VPS |
| `echelle.byos.grid` | UE-27 | France | France | Localisation du VPS supposée en France |
| `echelle.saas.egress_gb_par_org` | 1 | 5 | 20 | Sans effet sur le coût (egress OVH à 0 €) |
| `saas.backup_copies`, `derived_overhead`, `non_prod_env_copies` | voir METHODOLOGIE.md | | | |

## 6. Résultats (exemple, scénario central et fourchette bas–haut)

Généré par `structory-green examples/org_exemple.yaml --out examples/ --scale 1,1000,10000,100000`.
Détail : [`examples/org_exemple_echelle.md`](../examples/org_exemple_echelle.md). CSV pour le
business plan : [`examples/org_exemple_echelle.csv`](../examples/org_exemple_echelle.csv)
(séparateur `;`, virgule décimale).

**Coût éditeur, EUR HT par an, hors exploitation :**

| Organisations | SaaS, central (bas–haut) | BYOS, central (fourchette) |
|---:|---:|---:|
| 1 | 2 762 (2 761–2 767) | 29 (8–78) |
| 1 000 | 14 899 (3 542–60 633) | 107 (86–234) |
| 10 000 | 148 364 (34 794–605 708) | 496 (164–2 259) |
| 100 000 | 1 483 020 (347 316–6 056 451) | 4 468 (943–22 274) |

**Carbone, tCO2e par an :**

| Organisations | SaaS, central (bas–haut) | BYOS, central (fourchette) | Évitées, central (bas–haut) |
|---:|---:|---:|---:|
| 1 | 0,10 (0,10–0,13) | 0,003 (0,001–0,019) | 0,10 (0,08–0,13) |
| 1 000 | 0,95 (0,46–3,46) | 0,016 (0,012–0,103) | 0,93 (0,36–3,45) |
| 10 000 | 9,50 (4,64–34,65) | 0,097 (0,045–1,012) | 9,41 (3,63–34,61) |
| 100 000 | 95,08 (46,43–346,57) | 0,916 (0,372–10,045) | 94,17 (36,38–346,20) |

Lecture, scénario central, 10 000 organisations : SaaS 148 364 €/an, dont 134 551 € de compute,
13 742 € de stockage et de copies, et 72 € de load balancer. BYOS 496 €/an, soit 0,37 du VPS socle
et 6 VPS ajoutés.

## 7. Limites

1. **Le résultat dépend d'abord de deux hypothèses non mesurées.** La première est le compute
   permanent par organisation côté SaaS (`v`). La seconde est le compute à la demande par
   organisation côté BYOS (`h`). Au central, l'écart est de 525 vCPU·h/an pour le SaaS contre
   10 vCPU·h/an pour le BYOS, soit un rapport d'environ 50. **Mesurer `h` sur les applications
   Structory réelles est la priorité suivante.**
2. **Exploitation non chiffrée** (prix À SOURCER) : les totaux ne couvrent que l'infrastructure.
   Le SaaS porte en plus la responsabilité des sauvegardes, de la restauration et de la sécurité
   des données. Ce coût humain réel n'est pas modélisé.
3. **Prix catalogue sans remise.** À 100 000 organisations, un éditeur SaaS négocierait ses prix
   et optimiserait ses copies. La fourchette basse couvre une partie de cet effet, pas tout.
4. **Une seule grille (OVHcloud FR).** Les grilles GCP et AWS ne sont pas encore intégrées : leurs
   pages de prix sont dynamiques et leurs API de catalogue demandent une clé. Elles sont à ajouter
   dans `prices.yaml` avant toute comparaison multi-fournisseur.
5. **Facteurs énergie AWS appliqués à OVH** (puissance par vCPU, fabrication par vCPU selon
   Boavizta pour une instance t3.medium). C'est une approximation, signalée comme telle.
6. Les bornes min/max des facteurs Boavizta ne sont pas propagées dans l'extrapolation V0.1 : on
   utilise les valeurs nominales.
7. Le VPS socle mesuré héberge aussi des sessions de développement. Elles sont exclues par la
   part `α` (RAM), mais le partage CPU réel n'a pas été mesuré.
