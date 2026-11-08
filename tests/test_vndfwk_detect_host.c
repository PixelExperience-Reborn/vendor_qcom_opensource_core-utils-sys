/* Host-only behavioral test of unmodified Qualcomm vndfwk-detect.c.
 * This stub does NOT represent a real Android system property service.
 */
#include <stdbool.h>
#include <stdio.h>
#include <string.h>
#include <cutils/properties.h>
#include "vndfwk-detect.h"

static bool sys_enhanced;
static bool odm_enhanced;
static int property_calls;
static int wrong_property;

bool property_get_bool(const char *key, bool default_value) {
    ++property_calls;
    if (default_value) {
        ++wrong_property;
    }
    if (strcmp(key, "ro.vendor.qti.va_aosp.support") == 0) {
        return sys_enhanced;
    }
    if (strcmp(key, "ro.vendor.qti.va_odm.support") == 0) {
        return odm_enhanced;
    }
    ++wrong_property;
    return default_value;
}

int main(void) {
    for (int odm = 0; odm != 2; ++odm) {
        for (int sys = 0; sys != 2; ++sys) {
            odm_enhanced = (odm != 0);
            sys_enhanced = (sys != 0);
            property_calls = 0;
            wrong_property = 0;
            const int expected = odm | (sys << 1);
            const int actual = getVendorEnhancedInfo();
            const int framework = isRunningWithVendorEnhancedFramework();
            if (actual != expected || framework != sys ||
                wrong_property || property_calls != 3) {
                fprintf(stderr,
                        "Failed ODM=%d SYS=%d: flags=%d expected=%d, "
                        "framework=%d, wrong=%d calls=%d\n",
                        odm, sys, actual, expected, framework,
                        wrong_property, property_calls);
                return 1;
            }
        }
    }
    puts("PASS: original Qualcomm C property detector truth table (4 cases)");
    return 0;
}
