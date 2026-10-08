# Coût et carbone à l'échelle — BYOS + Structory face à un SaaS de référence

Facteurs `2026.10.1` · prix `2026.10.0` (EUR HT, catalogue public OVHcloud FR) · équations : docs/MODELE_COUT_CARBONE.md

> Coût vu de l'**éditeur**. Le poste **exploitation** (personnes) n'est pas chiffré (prix À SOURCER) : les totaux ne couvrent que l'infrastructure. Le coût marginal pour l'organisation BYOS est donné à part.

## Scénario bas

| Organisations | Coût SaaS (€/an) | Coût BYOS (€/an) | SaaS €/org | BYOS €/org | tCO2e SaaS | tCO2e BYOS | tCO2e évitées |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 761 | 78 | 2 761,23 | 77,8800 | 0,100 | 0,019 | 0,081 |
| 1 000 | 3 542 | 234 | 3,54 | 0,2336 | 0,460 | 0,103 | 0,357 |
| 10 000 | 34 794 | 2 259 | 3,48 | 0,2259 | 4,639 | 1,012 | 3,627 |
| 100 000 | 347 316 | 22 274 | 3,47 | 0,2227 | 46,428 | 10,045 | 36,383 |

À 100 000 organisations : 1 200 vCPU permanents côté SaaS ; côté BYOS, part du VPS socle 1,00 + 285 VPS supplémentaire(s). Coût marginal pour une organisation BYOS : 0,00 €/an.

## Scénario central

| Organisations | Coût SaaS (€/an) | Coût BYOS (€/an) | SaaS €/org | BYOS €/org | tCO2e SaaS | tCO2e BYOS | tCO2e évitées |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 762 | 29 | 2 761,82 | 29,0581 | 0,100 | 0,003 | 0,097 |
| 1 000 | 14 899 | 107 | 14,90 | 0,1069 | 0,947 | 0,016 | 0,931 |
| 10 000 | 148 364 | 496 | 14,84 | 0,0496 | 9,505 | 0,097 | 9,408 |
| 100 000 | 1 483 020 | 4 468 | 14,83 | 0,0447 | 95,083 | 0,916 | 94,167 |

À 100 000 organisations : 6 000 vCPU permanents côté SaaS ; côté BYOS, part du VPS socle 0,37 + 57 VPS supplémentaire(s). Coût marginal pour une organisation BYOS : 0,00 €/an.

## Scénario haut

| Organisations | Coût SaaS (€/an) | Coût BYOS (€/an) | SaaS €/org | BYOS €/org | tCO2e SaaS | tCO2e BYOS | tCO2e évitées |
|---:|---:|---:|---:|---:|---:|---:|---:|
| 1 | 2 767 | 8 | 2 767,19 | 8,0382 | 0,131 | 0,001 | 0,131 |
| 1 000 | 60 633 | 86 | 60,63 | 0,0859 | 3,460 | 0,012 | 3,448 |
| 10 000 | 605 708 | 164 | 60,57 | 0,0164 | 34,652 | 0,045 | 34,607 |
| 100 000 | 6 056 451 | 943 | 60,56 | 0,0094 | 346,569 | 0,372 | 346,197 |

À 100 000 organisations : 24 000 vCPU permanents côté SaaS ; côté BYOS, part du VPS socle 0,10 + 12 VPS supplémentaire(s). Coût marginal pour une organisation BYOS : 0,00 €/an.
