# Does `--flip-normals` give the team's layer order on pscamillo's meshes too?

The PHerc0800 reproduction (`../PHerc0800_reproduction.md`) fixed `--flip-normals` using a *team* mesh. That only carries
over to pscamillo's meshes if both tools write the tifxyz grid with the same normal sign. This checks it geometrically.

Method (`orient.py`): for every grid cell, n = cross(P[i, j+1] − P[i, j], P[i+1, j] − P[i, j]) with the same formula for
every mesh, so a global sign convention cancels. The scroll axis at the team mesh's height is the median centroid of the
full-wrap pscamillo meshes in window z12272 (all five have 100 % angular coverage). Outward = n points away from the axis.

| mesh | vertices | mean n̂·r̂ | fraction outward |
|---|---:|---:|---:|
| team `20251028213516-auto_grown` (the reproduction mesh) | 5,833 | 0.900 | **1.000** |
| pscamillo `z12272_w020` | 6,550 | 0.413 | 0.766 |
| pscamillo `z12272_w040` | 12,529 | 0.649 | 0.969 |
| pscamillo `z12272_w060` | 18,200 | 0.694 | 0.998 |
| pscamillo `z12272_w080` | 23,680 | 0.713 | 1.000 |
| pscamillo `z12272_w100` | 29,680 | 0.730 | 0.998 |
| all 95 PHerc0800 pscamillo meshes, each about its own centroid | | | min 0.842, median **0.995**, max 1.000 |

Both point outward. So `--flip-normals` puts pscamillo's layers in the same physical order as the team's published PHerc0800
surface volume, and the "forward" maps in this atlas are in the team's convention. The w020 wraps sit closest to the
umbilicus, where the centroid is a rougher stand-in for the axis; that is where the fraction drops.
