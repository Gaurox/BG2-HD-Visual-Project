"""Complete scoped x2/x4 production, packs and native proofs; no installation."""
import hashlib
import json
from pathlib import Path
import subprocess
import sys
import time

RUN = Path(__file__).resolve().parent
ROOT = next(p for p in RUN.parents if (p / "pipeline/scripts/palette_playable.py").is_file())
sys.path.insert(0, str(ROOT / "pipeline/scripts"))
from palette_work_plan import WorkPlan, ResultCache, write_json

PACKS = ROOT / "sprite/.work/q3m-6100-20261001-v1"


def sha(path):
    with Path(path).open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def phase(name):
    write_json(RUN / "active-session.json", dict(phase=name, changed_at=time.time()))
    print(json.dumps(dict(phase=name)), flush=True)


def command(args, log):
    with (RUN / "captures" / log).open("wb") as stream:
        subprocess.run([sys.executable, "-u", "-B", *map(str, args)], cwd=ROOT,
                       stdout=stream, stderr=subprocess.STDOUT, check=True)


def production_receipt(scale, cache):
    data = json.loads((cache.root / "last-run.json").read_text())
    assert data["source_plan_sha256"] == cache.plan.descriptor["sha256"]
    assert data["counts"]["selected_unique_work"] == 95124
    log = RUN / "captures" / f"x{scale}-generation.log"
    data["log_sha256"] = sha(log)
    data["elapsed_seconds_from_log_lifetime"] = log.stat().st_mtime - log.stat().st_ctime
    write_json(RUN / f"x{scale}-production.json", data)


def assemble_and_verify(scale):
    phase(f"x{scale}-pack")
    command(["pipeline/scripts/palette_playable.py", "pack", "--scale", scale,
             "--animation-id", "0x6100", "--output", PACKS / f"x{scale}"], f"x{scale}-pack.log")
    phase(f"x{scale}-offline-verification")
    command([RUN / "verify_offline.py", "--scale", scale, "--pack", PACKS / f"x{scale}"], f"x{scale}-offline.log")


def main():
    plan = WorkPlan().validate_sources()
    cache2, cache4 = ResultCache(plan, 2), ResultCache(plan, 4)
    phase("waiting-for-x2-production")
    # The x2 producer was explicitly started for this selection before this driver.
    while not (cache2.root / "last-run.json").is_file():
        time.sleep(5)
    production_receipt(2, cache2)
    phase("x4-production-and-x2-pack")
    with (RUN / "captures/x4-generation.log").open("wb") as log:
        producer = subprocess.Popen([sys.executable, "-u", "-B", "pipeline/scripts/palette_playable.py",
                                     "run", "--scale", "4", "--animation-id", "0x6100", "--workers", "8"],
                                    cwd=ROOT, stdout=log, stderr=subprocess.STDOUT)
        try:
            assemble_and_verify(2)
            phase("waiting-for-x4-production")
            result = producer.wait()
            if result:
                raise RuntimeError(f"x4 producer failed: {result}")
        except BaseException:
            if producer.poll() is None:
                # Keep the independent authorized producer running; root can inspect/resume.
                phase("x2-verification-needs-attention-x4-producer-running")
                producer.wait()
            raise
    production_receipt(4, cache4)
    assemble_and_verify(4)
    paths = [f"x{s}-{kind}.json" for s in (2, 4) for kind in ("production", "verification")]
    evidence = {name: sha(RUN / name) for name in paths + ["scope.json", "native-control.json", "native-fixtures.json", "source-provenance.json"]}
    proofs = [json.loads((RUN / f"x{s}-verification.json").read_text()) for s in (2, 4)]
    assert all(p["status"] == "passed-offline-ready-for-manual-game" for p in proofs)
    write_json(RUN / "verification.json", dict(schema="bg2-playable-q3m-series-complete-v1",
        status="passed-offline-ready-for-manual-game", animation_id="0x6100", scales=[2, 4],
        resources_per_scale=656, frames_per_scale=180337, unique_work_per_scale=95124,
        evidence_sha256=evidence, ingame_validated=False, visual_qa_accepted=False))
    phase("complete-offline")
    plan.close()


if __name__ == "__main__":
    main()
