/* Full public configuration/profile validation; no scheduler or detector runs. */
#include "cross_layer_fault.h"
#include "experiment.h"
#include <string.h>
int main(int argc,char **argv)
{
    ecu_state_t s={0};s.simulation.duration_ms=120000;
    if(cross_layer_parse_options(&argc,argv,&s) || cross_layer_validate(&s))return 1;
    for(int i=1;i+1<argc;i++)if(!strcmp(argv[i],"--driving-profile")) {
        if(experiment_load_driving_profile(&s,argv[i+1]))return 1;
        return experiment_validate_driving_profile_coverage(&s)?1:0;
    }
    return 1;
}
