#include "ds_evidence.h"
#include <math.h>
#include <string.h>
void ds_empty(ds_mass_t *m) { memset(m, 0, sizeof(*m)); }
void ds_vacuous(ds_mass_t *m) { ds_empty(m); m->mass[DS_THETA] = 1; }
bool ds_assign(ds_mass_t *m, unsigned int subset, double mass)
{
    if (!subset || subset > DS_THETA || !isfinite(mass) || mass < 0 || mass > 1) return false;
    m->mass[subset] = mass;
    return true;
}
bool ds_normalize(ds_mass_t *m)
{
    double total = 0;
    if (m->mass[0] != 0) return false;
    for (unsigned int i = 1; i < DS_SIZE; i++) {
        if (!isfinite(m->mass[i]) || m->mass[i] < 0) return false;
        total += m->mass[i];
    }
    if (!isfinite(total) || total <= 0) return false;
    for (unsigned int i = 1; i < DS_SIZE; i++) m->mass[i] /= total;
    return true;
}
bool ds_valid(const ds_mass_t *m)
{
    double total = 0;
    if (m->mass[0] != 0) return false;
    for (unsigned int i = 1; i < DS_SIZE; i++) {
        if (!isfinite(m->mass[i]) || m->mass[i] < 0 || m->mass[i] > 1) return false;
        total += m->mass[i];
    }
    return fabs(total - 1) < 1e-10;
}
double ds_belief(const ds_mass_t *m, unsigned int subset)
{
    double result = 0;
    for (unsigned int i = 1; i < DS_SIZE; i++) if ((i & subset) == i) result += m->mass[i];
    return result;
}
double ds_plausibility(const ds_mass_t *m, unsigned int subset)
{
    double result = 0;
    for (unsigned int i = 1; i < DS_SIZE; i++) if (i & subset) result += m->mass[i];
    return result;
}
void ds_pignistic(const ds_mass_t *m, double scores[DS_ATOMS])
{
    for (unsigned int atom = 0; atom < DS_ATOMS; atom++) scores[atom] = 0;
    for (unsigned int i = 1; i < DS_SIZE; i++) {
        unsigned int count = 0;
        for (unsigned int b = 0; b < DS_ATOMS; b++) if (i & (1U << b)) count++;
        for (unsigned int b = 0; b < DS_ATOMS; b++) if (i & (1U << b)) scores[b] += m->mass[i] / count;
    }
}
bool ds_discount(const ds_mass_t *m, double r, ds_mass_t *out)
{
    if (!ds_valid(m) || !isfinite(r) || r < 0 || r > 1) return false;
    ds_mass_t result;
    ds_empty(&result);
    for (unsigned int i = 1; i < DS_SIZE; i++) result.mass[i] = r * m->mass[i];
    result.mass[DS_THETA] += 1 - r;
    *out = result;
    return true;
}
bool ds_combine(const ds_mass_t *a, const ds_mass_t *b, ds_rule_t rule,
                ds_mass_t *out, double *conflict)
{
    if (!ds_valid(a) || !ds_valid(b) || (rule != DS_DEMPSTER && rule != DS_YAGER)) return false;
    ds_mass_t result;
    ds_empty(&result);
    for (unsigned int i = 1; i < DS_SIZE; i++) {
        if (!a->mass[i]) continue;
        for (unsigned int j = 1; j < DS_SIZE; j++)
            if (b->mass[j]) result.mass[i & j] += a->mass[i] * b->mass[j];
    }
    *conflict = result.mass[0];
    result.mass[0] = 0;
    if (rule == DS_YAGER) result.mass[DS_THETA] += *conflict;
    else if (1 - *conflict <= 1e-12) { ds_vacuous(out); return false; }
    /* For Dempster, normalizing the nonempty sum is division by 1-K.
     * For Yager this only removes floating-point roundoff. */
    if (!ds_normalize(&result)) { ds_vacuous(out); return false; }
    *out = result;
    return true;
}
