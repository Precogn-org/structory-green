# Rapport Structory Green — Organisation exemple (fictive)

Outil `structory-green` 0.1.0 · facteurs version `2026.10.1` · méthode : METHODOLOGIE.md (V0.1)

## Résultat

| CO2e évité par an | bas | central | haut |
|---|---:|---:|---:|
| kg CO2e / an | 0.406 | **0.919** | 3.528 |

> **À lire avant de citer ce chiffre.** Le résultat par organisation est **petit** (central : 0.919 kg CO2e/an) et **très sensible** à une hypothèse non observable (de 0.431 à 99.94 kg/an dans l'analyse ci-dessous) : la part des serveurs SaaS attribuée à l'organisation (`saas.org_share`). Voir l'analyse de sensibilité ci-dessous. La fourchette est un encadrement par scénarios, pas un intervalle de confiance (METHODOLOGIE.md §7).

## Détail par poste (kg CO2e / an, scénario central)

| Poste | SaaS | BYOS (marginal) | Évité |
|---|---:|---:|---:|
| Stockage (copie de base) | 0.016 | 0.00026 | 0.0157 |
| Réplication et sauvegardes | 0.0811 | 0.00026 | 0.0809 |
| Environnements hors production | 0.00132 | 0 | 0.00132 |
| Compute (usage) | 0.417 | 0.00664 | 0.41 |
| Réseau inter-centres | 0.00121 | 7.56e-06 | 0.0012 |
| Fabrication (embodied) | 0.414 | 0.00377 | 0.41 |
| **Total** | **0.93** | **0.0109** | **0.919** |

Volumes (central) : journal 0.036 Go/an, 0.108 Go au total ; stockage physique SaaS 32.16 Go ; stockage marginal BYOS 0.216 Go. Les pièces jointes déjà présentes dans le stockage de l'organisation ne sont pas imputées au BYOS (METHODOLOGIE.md §3.1).

## Analyse de sensibilité : part des serveurs SaaS attribuée à l'organisation

Scénario central, seul `saas.org_share` varie.

| org_share | SaaS (kg/an) | BYOS (kg/an) | Évité (kg/an) |
|---:|---:|---:|---:|
| 0.0001 | 0.442 | 0.0109 | 0.431 |
| 0.001 | 0.532 | 0.0109 | 0.521 |
| 0.005 | 0.93 | 0.0109 | 0.919 |
| 0.02 | 2.422 | 0.0109 | 2.412 |
| 0.1 | 10.38 | 0.0109 | 10.37 |
| 1 | 99.95 | 0.0109 | 99.94 |

Lecture : `1` = instance SaaS dédiée à l'organisation ; `0.001` = une instance partagée par 1 000 organisations. Seuls le compute SaaS permanent et la fabrication des serveurs qui le portent varient avec ce paramètre ; le stockage n'en dépend pas.

## Hypothèses (HYPOTHESE = valeur du profil, non sourcée)

Convention : `bas` = valeur qui donne le moins d'émissions évitées.

| Paramètre | bas | central | haut |
|---|---:|---:|---:|
| `byos.memory_gb_per_vcpu` | 2 | 2 | 2 |
| `byos.storage_lifetime_years` | 4 | 5 | 6 |
| `byos.utilization` | 0.5 | 0.5 | 0.5 |
| `byos.vcpu_hours_per_year` | 50 | 10 | 2 |
| `saas.backup_copies` | 1 | 2 | 7 |
| `saas.derived_overhead` | 0.5 | 1 | 2 |
| `saas.environments[0].memory_gb` | 32 | 32 | 32 |
| `saas.environments[0].utilization` | 0.2 | 0.2 | 0.2 |
| `saas.environments[0].vcpu` | 8 | 8 | 8 |
| `saas.environments[1].memory_gb` | 16 | 16 | 16 |
| `saas.environments[1].utilization` | 0.05 | 0.05 | 0.05 |
| `saas.environments[1].vcpu` | 4 | 4 | 4 |
| `saas.non_prod_env_copies` | 0 | 1 | 2 |
| `saas.org_share` | 0.001 | 0.005 | 0.02 |
| `saas.storage_lifetime_years` | 6 | 5 | 4 |
| `unite_fonctionnelle.attachments_gb` | 5 | 5 | 5 |
| `unite_fonctionnelle.attachments_new_gb_per_year` | 1.5 | 1.5 | 1.5 |
| `unite_fonctionnelle.bytes_per_entry` | 1500 | 1500 | 1500 |
| `unite_fonctionnelle.entries_per_month` | 2000 | 2000 | 2000 |
| `unite_fonctionnelle.history_years` | 3 | 3 | 3 |

Notes du profil :

- Réplication BYOS : Google ne publie pas le facteur de Drive ; le central utilise le facteur CCF de Google Cloud Storage (2) comme approximation, le bas le facteur S3 (6) par prudence.
- org_share central 0,005 = une plateforme SaaS dont l'infrastructure ci-dessus sert environ 200 organisations.
- Échelle : vCPU SaaS permanents par organisation = org_share × vCPU du socle (12) ; heures vCPU BYOS par organisation = byos.vcpu_hours_per_year, servies par le VPS socle.
- Valeurs numériques d'illustration : à remplacer par les données réelles de l'organisation.

## Facteurs utilisés

| Facteur | Valeur | Unité | Statut | Source |
|---|---:|---|---|---|
| `cpu_max_watts_aws` | 3.5 | W/vCPU | SOURCE | Cloud Carbon Footprint, méthodologie, AWS Average Max Watts [lien](https://www.cloudcarbonfootprint.org/docs/methodology/) |
| `cpu_min_watts_aws` | 0.74 | W/vCPU | SOURCE | Cloud Carbon Footprint, méthodologie, AWS Average Min Watts [lien](https://www.cloudcarbonfootprint.org/docs/methodology/) |
| `embodied_ssd_per_tb` | 51.7 | kgCO2e/To | DERIVE | Calculé à partir des facteurs Boavizta ci-dessus (équation de la documentation SSD Boav… [lien](https://doc.api.boavizta.org/Explanations/components/ssd/) |
| `embodied_vcpu_year_aws_t3_medium` | 1.35 (0.797–2.11) | kgCO2e/(vCPU·an) | SOURCE | API Boavizta v2.4.1, GET /v1/cloud/instance?provider=aws&instance_type=t3.medium&durati… [lien](https://api.boavizta.org/v1/cloud/instance?provider=aws&instance_type=t3.medium&verbose=false&duration=8760&criteria=gwp) |
| `grid_intensity_eu27` | 0.21 | kgCO2e/kWh | SOURCE | Our World in Data, « Carbon intensity of electricity generation » (données Ember 2026 ;… [lien](https://ourworldindata.org/grapher/carbon-intensity-electricity) |
| `grid_intensity_ie` | 0.257 | kgCO2e/kWh | SOURCE | Our World in Data, « Carbon intensity of electricity generation » (Ember 2026), année 2… [lien](https://ourworldindata.org/grapher/carbon-intensity-electricity) |
| `memory_energy` | 0.000392 | kWh/(Go·h) | SOURCE | Cloud Carbon Footprint, méthodologie, MEMORY_COEFFICIENT [lien](https://www.cloudcarbonfootprint.org/docs/methodology/) |
| `network_inter_dc_energy` | 0.001 | kWh/Go | SOURCE | Cloud Carbon Footprint, méthodologie, NETWORKING_COEFFICIENT [lien](https://www.cloudcarbonfootprint.org/docs/methodology/) |
| `pue_aws` | 1.135 | sans unité | SOURCE | Cloud Carbon Footprint (Thoughtworks), AWS_CLOUD_CONSTANTS.PUE_AVG [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/aws/src/domain/AwsFootprintEstimationConstants.ts) |
| `pue_google` | 1.09 | sans unité | SOURCE | Google Data Centers — Efficiency, « In 2025, the average annual power usage effectivene… [lien](https://datacenters.google/efficiency/) |
| `pue_industry_avg` | 1.56 | sans unité | SOURCE | Uptime Institute, Global Data Center Survey 2024 (14e édition) — « industry average PUE… [lien](https://www.datacenterknowledge.com/energy-power-supply/data-center-industry-survey-highlights-cost-ai-and-sustainability-challenges) |
| `replication_aws_rds_aurora` | 6 | copies | SOURCE | Cloud Carbon Footprint, AWS_CLOUD_CONSTANTS.REPLICATION_FACTORS.RDS_AURORA [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/aws/src/domain/AwsFootprintEstimationConstants.ts) |
| `replication_aws_rds_backup` | 3 | copies | SOURCE | Cloud Carbon Footprint, AWS_CLOUD_CONSTANTS.REPLICATION_FACTORS.RDS_BACKUP [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/aws/src/domain/AwsFootprintEstimationConstants.ts) |
| `replication_aws_rds_multi_az` | 2 | copies | SOURCE | Cloud Carbon Footprint, AWS_CLOUD_CONSTANTS.REPLICATION_FACTORS.RDS_MULTI_AZ [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/aws/src/domain/AwsFootprintEstimationConstants.ts) |
| `replication_aws_s3` | 6 | copies | SOURCE | Cloud Carbon Footprint, AWS_CLOUD_CONSTANTS.REPLICATION_FACTORS.S3 [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/aws/src/domain/AwsFootprintEstimationConstants.ts) |
| `replication_gcp_cloud_storage` | 2 | copies | SOURCE | Cloud Carbon Footprint, GCP_CLOUD_CONSTANTS.REPLICATION_FACTORS.CLOUD_STORAGE_* [lien](https://github.com/cloud-carbon-footprint/cloud-carbon-footprint/blob/f584c549ee358d5980d36513267d007ecd3ee716/packages/gcp/src/domain/GcpFootprintEstimationConstants.ts) |
| `storage_ssd_energy` | 1.2 | Wh/(To·h) | SOURCE | Cloud Carbon Footprint, méthodologie, SSDCOEFFICIENT [lien](https://www.cloudcarbonfootprint.org/docs/methodology/) |

## Facteurs À SOURCER (non utilisés tels quels)

- `replication_google_drive`
- `network_end_user_energy`
- `hdd_capacity_datacenter`

## Ce que ce rapport ne mesure pas

Terminaux et réseau d'accès des utilisateurs, développement logiciel, fin de vie des équipements, autres impacts que le climat, effets rebond. Détail : METHODOLOGIE.md §3 et §8.
