/* Configuration parser only: no simulation or detector execution. */
#include "cross_layer_fault.h"
int main(int argc,char **argv) {
 ecu_state_t s={0};s.simulation.duration_ms=120000;
 if(cross_layer_parse_options(&argc,argv,&s))return 1;
 return cross_layer_validate(&s)?1:0;
}
