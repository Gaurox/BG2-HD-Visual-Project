# Threading and Failure Boundaries

The engine is effectively single-threaded for OpenGL rendering, but area loading and explicit
shutdown are treated as separate producers so ownership remains clear.

## Ownership

- `LoadArea` parses WED data and publishes immutable CPU snapshots. It never creates, binds, or
  deletes OpenGL objects.
- `DrawColorTone(Seam)` is the world-pass publication point. It resolves the active area, publishes
  the view transform once per frame, and flushes pending area textures while a GL context is current.
- The swap hook finalizes the opt-in map wide-view telemetry sample, advances the frame counter and
  refreshes time-dependent uniforms. The detector compares only a fixed history of sixteen render
  observations. After one trigger it stays disarmed until both view dimensions contract below the
  trigger threshold relative to the pre-expansion view. A completed eight-frame capture is
  formatted and logged only at this boundary; `LoadArea` merely requests its reset through an
  atomic flag.
- The optional 2.7.3 `CResPVR::Demand` diagnostic runs on the calling engine/render thread and
  wraps the native call exactly once. Thread-local scope state lets the already-installed GL hooks
  charge texture-name generation and compressed upload time to that demand without cross-thread
  attribution. Process I/O counters are sampled only for a likely first materialization; the
  bounded per-frame slowest-call table is protected by its own mutex and is read at the swap
  boundary. Disabling `PerformanceLogs` removes this engine hook entirely.
- The optional Phase 3e-A map-page shadow preparer has one owned worker. The render thread gives it
  only copied resrefs, a generation and an override path. The worker performs bounded file I/O,
  zlib inflation and PVR/DXT validation into private immutable bytes; it never calls the engine,
  native `Demand`, a logger callback, WGL or OpenGL. The render thread only observes and retires the
  result immediately before the unchanged native demand. Generation changes cancel stale work.
- The manifested Phase 3e-B0 boundary does not weaken that rule. A future decoded-PVR substitution
  may run only in the zlib-wrapper detour nested synchronously inside the render thread's exact
  `CResPVR::Demand` call. It may copy into the destination already allocated by native code, but the
  worker never sees that pointer and all cache, field, upload and release operations remain native.
- Safe-read region results are cached only for that frame epoch; `LoadArea`
  advances the epoch before touching a replacement object graph.
- Readability is not object lifetime. Area refreshes copy palette bytes before
  processing them, revalidate the WED pointer before publication, and commit
  only the newest refresh generation so an older callback cannot overwrite a
  newer area snapshot.
- Shader/program records are protected by `g_probeMutex`. Steady-state OpenGL introspection and
  shader-dump I/O copy the required record state and release that mutex first. One-time probe
  installation is serialized before those records become visible.
- Area snapshot publication is protected by `g_areaGpuMutex`; GL upload uses a copied
  `shared_ptr<const AreaGpuSnapshot>` after releasing the mutex.
- Uniform inputs are independent relaxed atomics. They are a latest-value snapshot, not a
  transaction; the render thread is the only consumer that calls OpenGL.
- `AppContext::activeArea`, `infGame`, and `wed` are atomic because load and
  render callbacks may observe them at different engine boundaries.

## Hook and Exception Rules

No C++ exception may cross an engine, OpenGL, SDL, GDI, EEex, or DLL export boundary. Detours catch
all exceptions only at those ABI boundaries, preserve the original engine call exactly once, and
treat diagnostics as optional. Internal helpers use ordinary typed errors or return values and do
not silently convert a failed OpenGL operation into success.

`ShutdownBindings` must run before unloading the DLL. It first disables engine entry-point hooks,
then removes frame and OpenGL probes, removes the engine hooks, and only then uninitializes MinHook
and clears shared state. `DllMain` never performs MinHook, logger, or OpenGL teardown while the
Windows loader lock is held.

Long-lived DLL workers use the shared trivially destructible `ProcessLifetimeWorker`. It retains a
module reference while worker code can execute. Normal shutdown first signals the feature queue,
then joins the worker and finally releases that reference; no worker join or CRT thread destructor
runs from `DllMain`.

## Runtime Invariants

1. Only a thread with the owning WGL context may touch enhancer GL objects.
2. A program is reclassified after every successful link and forgotten on deletion.
3. A recreated WGL context invalidates enhancer texture names, hook entry
   points, program classifications, and uniform locations; probes are
   reinstalled against the replacement context before processing programs.
4. A new area publishes a no-liquid generation before parsing, so stale masks cannot cross an area
   transition.
5. If the frame hook is unavailable, view publication remains correct and is
   time-coalesced across Seam calls instead of using the frame epoch.
6. A shadow page buffer is never a native resource: only the render-thread `CResPVR::Demand` may
   materialize or publish the engine texture in Phase 3e-A.
7. A Phase 3e-B consumer must use the exact manifested uncompress return address and a scoped
   thread-local page identity; every mismatch invokes original zlib and publishes nothing itself.
