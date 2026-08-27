#include "hooks.h"
#include "bridge_transition.h"
#include "iee/core/version.h"


extern "C" __declspec(dllexport) const char * __stdcall GetIEEVersion() {
    return IEE_VERSION;
}


extern "C" __declspec(dllexport) bool __stdcall IsActive() {
    return iee::hooks::is_active();
}

// Reserved for the future action/door hook. The current visual validation
// reaches the same path with F9 and never mutates the game's bridge state.
extern "C" __declspec(dllexport) bool __stdcall RequestAR1300BridgeTransition() {
    return iee::bridge::request();
}
