#ifndef DS_EVIDENCE_H
#define DS_EVIDENCE_H
#include <stdbool.h>
/* Closed-world frame: six atoms, 64 subsets. Empty set always has zero mass. */
#define DS_ATOMS 6U
#define DS_SIZE (1U << DS_ATOMS)
#define DS_THETA (DS_SIZE - 1U)
typedef struct { double mass[DS_SIZE]; } ds_mass_t;
typedef enum { DS_DEMPSTER, DS_YAGER } ds_rule_t;
void ds_empty(ds_mass_t *m);
void ds_vacuous(ds_mass_t *m);
bool ds_assign(ds_mass_t *m, unsigned int subset, double mass);
bool ds_normalize(ds_mass_t *m);
bool ds_valid(const ds_mass_t *m);
double ds_belief(const ds_mass_t *m, unsigned int subset);
double ds_plausibility(const ds_mass_t *m, unsigned int subset);
void ds_pignistic(const ds_mass_t *m, double scores[DS_ATOMS]);
bool ds_discount(const ds_mass_t *m, double reliability, ds_mass_t *out);
/* Returns false at total Dempster conflict; out becomes vacuous, K stays 1.
 * Aliasing input/output is supported. Caller must surface this fallback. */
bool ds_combine(const ds_mass_t *a, const ds_mass_t *b, ds_rule_t rule,
                ds_mass_t *out, double *conflict);
#endif
