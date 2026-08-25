from __future__ import annotations

import inspect
import json
import shutil
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import numpy as np


ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "pipeline" / "scripts"))

import run_creature_sprite_x2 as pipeline  # noqa: E402


class CreatureSpriteX2PipelineTests(unittest.TestCase):
    def make_frame(self, palette: np.ndarray | None = None) -> pipeline.SourceFrame:
        if palette is None:
            palette = np.zeros((256, 3), dtype=np.uint8)
            palette[1] = [10, 20, 30]
        indices = np.array([[0, 1]], dtype=np.uint8)
        rgba = np.array([[[0, 0, 0, 0], [10, 20, 30, 255]]], dtype=np.uint8)
        return pipeline.SourceFrame("TEST", 0, 2, 1, 0, 0, 0, indices, palette, rgba.tobytes())

    def test_exact_palette_mapping(self) -> None:
        frame = self.make_frame()
        output = np.array(
            [
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [10, 20, 30, 255],
                [10, 20, 30, 255],
                [0, 0, 0, 0],
                [0, 0, 0, 0],
                [10, 20, 30, 255],
                [10, 20, 30, 255],
            ],
            dtype=np.uint8,
        )
        mapped, representatives = pipeline.map_output(frame, output.tobytes())
        self.assertEqual(mapped.tolist(), [0, 0, 1, 1, 0, 0, 1, 1])
        self.assertEqual(int(representatives[0]), 0)
        self.assertEqual(int(representatives[1]), 1)

    def test_new_color_is_rejected(self) -> None:
        frame = self.make_frame()
        output = np.array([[9, 9, 9, 255]] * 8, dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "introduced"):
            pipeline.map_output(frame, output.tobytes())

    def test_partial_alpha_is_rejected(self) -> None:
        frame = self.make_frame()
        output = np.array([[10, 20, 30, 128]] * 8, dtype=np.uint8)
        with self.assertRaisesRegex(RuntimeError, "partial alpha"):
            pipeline.map_output(frame, output.tobytes())

    def test_legacy_job_keeps_x2_v2_contract(self) -> None:
        contract = pipeline.upscale_contract({})
        self.assertFalse(contract.explicit)
        self.assertEqual(contract.scale, 2)
        self.assertEqual(contract.registry_magic, b"IEECSX2\0")
        self.assertEqual(contract.registry_version, 2)
        self.assertEqual(contract.registry_filename, "CreatureSprites-X2.registry")

    def test_explicit_x4_uses_direct_xbr4x_v3_contract(self) -> None:
        contract = pipeline.upscale_contract(
            {
                "upscale": {
                    "scale": 4,
                    "algorithm": "XBR/xbr4X",
                    "passes": 1,
                    "antialias": False,
                    "xbr_blend": False,
                }
            }
        )
        self.assertTrue(contract.explicit)
        self.assertEqual(contract.adapter_mode, "xbr4x")
        self.assertEqual(contract.registry_magic, b"IEECSXN\0")
        self.assertEqual(contract.registry_version, 3)
        self.assertEqual(contract.registry_filename, "CreatureSprites-XN.registry")

    def test_creation_scale_switch_is_central_and_keeps_legacy_default(self) -> None:
        template: dict[str, object] = {}
        legacy = pipeline.creation_upscale_contract(template, None)
        explicit_x2 = pipeline.creation_upscale_contract(template, 2)
        explicit_x4 = pipeline.creation_upscale_contract(template, 4)
        self.assertFalse(legacy.explicit)
        self.assertEqual(legacy.scale, 2)
        self.assertTrue(explicit_x2.explicit)
        self.assertEqual(explicit_x2.registry_version, 3)
        self.assertEqual(explicit_x4.method["algorithm"], "XBR/xbr4X")
        self.assertEqual(explicit_x4.scale, 4)
        self.assertNotIn("upscale", template)

    def test_cli_exposes_generic_scale_and_frame_retention_switches(self) -> None:
        parser = pipeline.make_parser()
        explicit = parser.parse_args(
            [
                "new-character-job",
                "--job",
                "sprite/jobs/test-xbr4x.json",
                "--scale",
                "4",
                "--keep-upscaled-frames",
            ]
        )
        self.assertEqual(explicit.scale, 4)
        self.assertTrue(explicit.keep_upscaled_frames)
        legacy_alias = parser.parse_args(
            [
                "build",
                "--job",
                "sprite/jobs/test-xbr2x.json",
                "--keep-x2-frames",
            ]
        )
        self.assertTrue(legacy_alias.keep_upscaled_frames)

    def test_xn_adapter_exposes_direct_xbr4x_and_generic_protocol(self) -> None:
        adapter = (ROOT / "pipeline" / "scripts" / "xbr2x_batch.js").read_text(
            encoding="utf-8"
        )
        self.assertIn("xbr4x(srcBuffer", adapter)
        self.assertIn("XBRNBAT", adapter)
        self.assertIn("XBRNOUT", adapter)

    def test_xn_adapter_executes_both_protocols(self) -> None:
        fake_scalepix = """<script>
let classification = 'sprite';
function classifyBuffer() { return 'sprite'; }
function invertBufferInPlace() {}
function runXBR2X(source, width, height, destination) {
  for (let y = 0; y < height * 2; ++y)
    for (let x = 0; x < width * 2; ++x)
      destination[y * width * 2 + x] = source[Math.floor(y / 2) * width + Math.floor(x / 2)];
}
function xbr4x(source, width, height) {
  const destination = new Uint32Array(width * height * 16);
  for (let y = 0; y < height * 4; ++y)
    for (let x = 0; x < width * 4; ++x)
      destination[y * width * 4 + x] = source[Math.floor(y / 4) * width + Math.floor(x / 4)];
  return destination;
}
</script>"""
        frame = self.make_frame()
        with tempfile.TemporaryDirectory() as temporary:
            scalepix = Path(temporary) / "scalepix.html"
            scalepix.write_text(fake_scalepix, encoding="utf-8")
            legacy = pipeline.run_xbr2x([frame], scalepix, "node")
            explicit = pipeline.run_xbr(
                [frame], scalepix, "node", pipeline.direct_upscale_contract(4)
            )
        self.assertEqual((legacy[0][0], legacy[0][1], len(legacy[0][2])), (4, 2, 32))
        self.assertEqual((explicit[0][0], explicit[0][1], len(explicit[0][2])), (8, 4, 128))

    def test_explicit_upscale_routes_install_and_restore_to_xn_scripts(self) -> None:
        work_item = {
            "upscale": {
                "scale": 4,
                "algorithm": "XBR/xbr4X",
                "passes": 1,
                "antialias": False,
                "xbr_blend": False,
            }
        }
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=False).name,
            "Install-CreatureSprite-XN-Test.ps1",
        )
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=True).name,
            "Restore-CreatureSprite-XN-Test.ps1",
        )
        self.assertEqual(
            pipeline.install_restore_script({}, restore=False).name,
            "Install-CreatureSprite-X2-Test.ps1",
        )

    def test_armor_set_without_upscale_remains_strictly_legacy(self) -> None:
        work_item = {
            "_kind": "armor-set",
            "_members": [
                {
                    "upscale": {
                        "scale": 4,
                        "algorithm": "XBR/xbr4X",
                        "passes": 1,
                        "antialias": False,
                        "xbr_blend": False,
                    }
                }
            ],
        }
        contract = pipeline.effective_upscale_contract(work_item)
        self.assertFalse(contract.explicit)
        self.assertEqual(contract.scale, 2)
        self.assertEqual(
            pipeline.install_restore_script(work_item, restore=False).name,
            "Install-CreatureSprite-X2-Test.ps1",
        )

    def test_explicit_upscale_rejects_non_direct_or_blended_contracts(self) -> None:
        base = {
            "scale": 4,
            "algorithm": "XBR/xbr4X",
            "passes": 1,
            "antialias": False,
            "xbr_blend": False,
        }
        for update, message in (
            ({"passes": 2}, "passes"),
            ({"algorithm": "XBR/xbr2X"}, "algorithm"),
            ({"antialias": True}, "antialias"),
            ({"xbr_blend": True}, "xbr_blend"),
            ({"algorithm": "xbr4x"}, "algorithm"),
        ):
            with self.subTest(update=update):
                with self.assertRaisesRegex(RuntimeError, message):
                    pipeline.upscale_contract({"upscale": {**base, **update}})

    def test_x4_registry_preflight_uses_dense_scale_squared_payload(self) -> None:
        frame = self.make_frame()
        resources = [{"frames": [frame], "cycles": [{"frame_indices": [0]}]}]
        result = pipeline.preflight_registry_layout(resources, 4)
        self.assertEqual(result["index_bytes"], 32)
        self.assertEqual(result["registry_bytes"], 640)
        with self.assertRaisesRegex(RuntimeError, "before xBR"):
            pipeline.preflight_registry_layout(
                resources, 4, maximum_bytes=result["registry_bytes"] - 1
            )

    def test_build_preflight_precedes_xbr_dispatch(self) -> None:
        source = inspect.getsource(pipeline.build_pack)
        self.assertLess(
            source.index("preflight_registry_layout"), source.index("run_xbr(")
        )

    def test_character_runtime_profile_is_supported(self) -> None:
        pipeline.require_runtime_profile(
            {"animation": {"runtime_profile": "character-bg2ee-2.7.3.0"}}
        )

    def test_unknown_runtime_profile_is_rejected(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "unsupported-runtime-profile"):
            pipeline.require_runtime_profile(
                {"animation": {"runtime_profile": "character-unknown"}}
            )

    def test_install_and_restore_scripts_accept_character_bundles(self) -> None:
        for script_name in (
            "Install-CreatureSprite-X2-Test.ps1",
            "Restore-CreatureSprite-X2-Test.ps1",
        ):
            script = (ROOT / "pipeline" / "scripts" / script_name).read_text(
                encoding="utf-8"
            )
            self.assertIn(pipeline.JOB_SCHEMA, script)
            self.assertIn(pipeline.ARMOR_SET_SCHEMA, script)

    def test_install_scripts_prevent_registry_masking_and_support_recovery(self) -> None:
        legacy = (
            ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-X2-Test.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("CreatureSprites-XN.registry est présent", legacy)
        xn_install = (
            ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        ).read_text(encoding="utf-8")
        xn_restore = (
            ROOT / "pipeline" / "scripts" / "Restore-CreatureSprite-XN-Test.ps1"
        ).read_text(encoding="utf-8")
        self.assertIn("Publier l'état récupérable avant la première mutation", xn_install)
        self.assertIn("-RecoverInstalling", xn_install)
        self.assertIn("[switch]$RecoverInstalling", xn_restore)
        self.assertIn("$recoveringInterruptedInstall", xn_restore)
        self.assertIn("function Get-IniKey", xn_install)

    def test_character_runtime_has_no_texture_sweep_hook(self) -> None:
        hooks = (
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "src"
            / "iee"
            / "hooks.cpp"
        ).read_text(encoding="utf-8")
        self.assertNotIn("detour_draw_clear_textures", hooks)
        self.assertNotIn("Engine texture pool reset observed", hooks)
        self.assertIn("finish_composite_texture", hooks)
        self.assertLess(
            hooks.index("original(x, y, sourceRect, logicalSize, clipRect, flags)"),
            hooks.index("finish_composite_texture"),
        )

        runtime = (
            ROOT
            / "engine"
            / "InfinityEngine-Enhancer"
            / "source-patchee"
            / "src"
            / "iee"
            / "creature_sprite_x2.cpp"
        ).read_text(encoding="utf-8")
        self.assertNotIn("upload_bound_composite_locked", runtime)
        self.assertIn("delete-pending after queued draw", runtime)
        self.assertIn("descriptor + 0x24, out.secondaryGlName", runtime)
        self.assertIn("clear_private_recycled_secondary", runtime)
        self.assertIn("std::memcpy(secondaryField, &zero", runtime)
        self.assertIn("materialized.secondaryGlName == 0", runtime)

    def test_character_runtime_health_requires_transient_replacement_and_clean_pool(self) -> None:
        healthy = pipeline.runtime_session_health(
            "Composing creature sprite CHFB1A1 frame 000 via transient replacement "
            "id 42 (NEAREST, delete-pending after queued draw)",
            "character-bg2ee-2.7.3.0",
            {
                "CHFB1": [
                    "Composing creature sprite CHFB1A1 frame 000 via transient "
                    "replacement id 42 (NEAREST, delete-pending after queued draw)"
                ]
            },
        )
        self.assertTrue(healthy["runtime_health_pass"])

        unhealthy = pipeline.runtime_session_health(
            "Engine texture pool reset observed\nNo GL texture is bound",
            "character-bg2ee-2.7.3.0",
            {"CHFB1": ["Composing creature sprite CHFB1A1 frame 000 (NEAREST)"]},
        )
        self.assertFalse(unhealthy["runtime_health_pass"])
        self.assertEqual(unhealthy["texture_pool_reset_count"], 1)
        self.assertEqual(unhealthy["unbound_texture_warning_count"], 1)

        destructive = pipeline.runtime_session_health(
            "Composing creature sprite CHFB1A1 frame 000 in-place "
            "(NEAREST, no persistent engine texture id)",
            "character-bg2ee-2.7.3.0",
            {"CHFB1": ["in-place (NEAREST, no persistent engine texture id)"]},
        )
        self.assertFalse(destructive["runtime_health_pass"])
        self.assertEqual(destructive["character_unsafe_in_place_count"], 1)

    def test_explicit_qa_requires_xn_source_and_installed_hashes(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            root = Path(temporary)
            game = root / "game"
            run = root / "run"
            game.mkdir()
            registry = game / "iee-assets" / "creature-sprites" / "CreatureSprites-XN.registry"
            registry.parent.mkdir(parents=True)
            registry.write_bytes(b"xn")
            job = {
                "job_id": "qa-xn",
                "animation": {
                    "id": "0x6110",
                    "bam_prefix": "TEST",
                    "runtime_profile": "character-bg2ee-2.7.3.0",
                },
                "paths": {"game_root": str(game), "run_dir": str(run)},
                "upscale": pipeline.direct_upscale_contract(2).method,
            }
            state = {
                "installed_at_utc": "2026-08-25T18:00:00+00:00",
                "game_root": str(game),
                "targets": [
                    {
                        "relative_path": "iee-assets/creature-sprites/CreatureSprites-XN.registry",
                        "installed_present": True,
                        "installed_sha256": pipeline.sha256_file(registry),
                    }
                ],
            }
            pipeline.write_json(pipeline.active_state_path(job), state)
            log_template = """[2026-08-25 20:00:00] Creature sprite xBR2x pack ready: animation 0x6110, scale=x2, 1 resources, 1 frames, 4 index bytes; source={source}; filter=NEAREST; registry budget=128 MiB
[2026-08-25 20:00:01] Creature sprite xN owner scope installed: Character::Render
[2026-08-25 20:00:02] Creature sprite animation 0x6110 reached CGameAnimationTypeCharacter::Render
[2026-08-25 20:00:03] Creature sprite xBR2x uses an owner-scoped CVidPalette::Realize snapshot
[2026-08-25 20:00:04] Composing creature sprite TESTA1 frame 000 via transient replacement id 42 (NEAREST, delete-pending after queued draw)
"""
            log = game / "InfinityEngine-Enhancer.log"
            log.write_text(
                log_template.format(source="CreatureSprites-X2.registry"),
                encoding="utf-8",
            )
            wrong_source = pipeline.qa_log_report(job, write_report=False)
            self.assertFalse(wrong_source["pack_ready"])
            self.assertFalse(wrong_source["technical_pass"])
            log.write_text(
                log_template.format(source="CreatureSprites-XN.registry"),
                encoding="utf-8",
            )
            valid = pipeline.qa_log_report(job, write_report=False)
            self.assertTrue(valid["pack_ready"])
            self.assertTrue(valid["installed_files_match"])
            self.assertTrue(valid["technical_pass"])
            registry.write_bytes(b"changed")
            changed = pipeline.qa_log_report(job, write_report=False)
            self.assertFalse(changed["installed_files_match"])
            self.assertFalse(changed["technical_pass"])

    def test_character_identity_accepts_native_ini_body_family(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    resources = {
                        f"CHFB1{suffix}": (f"CHFB1{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                    resources["CHFB1INV"] = ("CHFB1INV", resource_type, 4)
                    return resources
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                    b"resref_paperdoll=CHFF\n"
                    b"resref_armor_base=B\nresref_armor_specific=F\n",
                    "data/Patch2.bif",
                )

        job = {
            "animation": {
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "armor_code": 1,
                "bam_prefix": "CHFB1",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        result = pipeline.verify_character_animation_identity(job, FakeIndex())
        self.assertEqual(result["body_resref"], "CHFB")
        self.assertEqual(result["armor_code"], 1)
        self.assertEqual(result["ids_symbol"], "FIGHTER_FEMALE_HUMAN")
        self.assertEqual(result["bam_prefix"], "CHFB1")
        self.assertEqual(result["resource_count"], 23)

    def test_legacy_character_job_defaults_to_body_layer(self) -> None:
        job = {"animation": {"armor_code": 1}}
        self.assertEqual(pipeline.character_layer_config(job), {"kind": "body"})

    @staticmethod
    def equipment_index(item_resref: str, item_type: int, animation_code: str):
        body_resources = {
            f"CHFB1{suffix}": (f"CHFB1{suffix}", pipeline.BAM_TYPE, 3)
            for suffix in pipeline.CHARACTER_BODY_SUFFIXES
        }
        equipment_suffixes = {
            "J6": ("A1", "A2", "A3", "A4", "A5", "A6", "A7", "A8", "A9", "CA", "G1", "SA", "SS", "SX"),
            "C0": ("A1", "A3", "A5", "G1", "SS"),
            "C4": ("A1", "A3", "A5", "G1", "SS"),
        }[animation_code]
        equipment_resources = {
            f"WQN{animation_code}{suffix}": (
                f"WQN{animation_code}{suffix}",
                pipeline.BAM_TYPE,
                4,
            )
            for suffix in equipment_suffixes
        }
        equipment_resources[f"WQN{animation_code}INV"] = (
            f"WQN{animation_code}INV",
            pipeline.BAM_TYPE,
            6,
        )
        item = bytearray(0x24)
        item[:8] = b"ITM V1  "
        struct.pack_into("<H", item, 0x1C, item_type)
        item[0x22:0x24] = animation_code.encode("ascii")

        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.ITM_TYPE:
                    return {item_resref: (item_resref, resource_type, 5)}
                if resource_type == pipeline.BAM_TYPE:
                    return {**body_resources, **equipment_resources}
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                if entry[0] == "6110":
                    return (
                        b"[general]\nanimation_type=6000\n[character]\n"
                        b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                        b"resref_armor_base=B\nresref_armor_specific=F\n"
                        b"height_code=WQN\nheight_code_helmet=WQN\n",
                        "data/Patch2.bif",
                    )
                if entry[0] == item_resref:
                    return bytes(item), "data/Items.bif"
                raise AssertionError(entry)

        return FakeIndex()

    def test_character_helmet_identity_comes_from_stock_itm_and_height_code(self) -> None:
        result = pipeline.character_equipment_spec(
            self.equipment_index("HELM01", 7, "J6"), 0x6110, "helmet", "HELM01"
        )
        self.assertEqual(result["bam_prefix"], "WQNJ6")
        self.assertEqual(result["item_animation_code"], "J6")
        self.assertEqual(result["equipment_height_code"], "WQN")
        self.assertEqual(result["resource_count"], 14)
        self.assertNotIn("WQNJ6INV", result["resources"])
        self.assertEqual(result["resources"][0], "WQNJ6A1")
        self.assertEqual(result["resources"][-1], "WQNJ6SX")

    def test_character_shield_identity_falls_back_to_general_height_code(self) -> None:
        for item_resref, animation_code in (("SHLD01", "C0"), ("SHLD08", "C4")):
            with self.subTest(item_resref=item_resref):
                result = pipeline.character_equipment_spec(
                    self.equipment_index(item_resref, 12, animation_code),
                    0x6110,
                    "shield",
                    item_resref,
                )
                self.assertEqual(result["bam_prefix"], f"WQN{animation_code}")
                self.assertEqual(result["equipment_height_code"], "WQN")
                self.assertEqual(result["resource_count"], 5)

    def test_character_equipment_rejects_wrong_item_category(self) -> None:
        with self.assertRaisesRegex(RuntimeError, "is not a helmet"):
            pipeline.character_equipment_spec(
                self.equipment_index("HELM01", 12, "J6"),
                0x6110,
                "helmet",
                "HELM01",
            )

    def test_character_equipment_job_rejects_declared_prefix_mismatch(self) -> None:
        job = {
            "animation": {
                "id": "0x6110",
                "ids_symbol": "FIGHTER_FEMALE_HUMAN",
                "layer": {"kind": "helmet", "item_resref": "HELM01"},
                "bam_prefix": "WQNC0",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "resolves to BAM prefix WQNJ6"):
            pipeline.verify_character_animation_identity(
                job, self.equipment_index("HELM01", 7, "J6")
            )

    def test_character_max_armor_uses_specific_body_resref(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6110": ("6110", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    return {
                        f"CHFF4{suffix}": (f"CHFF4{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6110 FIGHTER_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFB\n"
                    b"resref_armor_base=B\nresref_armor_specific=F\n",
                    "data/Patch2.bif",
                )

        result = pipeline.character_animation_spec(FakeIndex(), 0x6110, 4)
        self.assertEqual(result["base_body_resref"], "CHFB")
        self.assertEqual(result["body_resref"], "CHFF")
        self.assertEqual(result["bam_prefix"], "CHFF4")
        self.assertEqual(result["resource_count"], 23)

    def test_character_max_armor_resolution_matrix(self) -> None:
        cases = (
            (0x6110, "FIGHTER_FEMALE_HUMAN", "CHFB", "B", "F", "CHFF4"),
            (0x6010, "CLERIC_FEMALE_HUMAN", "CHFB", "B", "C", "CHFC4"),
            (0x6310, "THIEF_FEMALE_HUMAN", "CHFT", "T", "T", "CHFT4"),
        )

        for animation_id, symbol, base, armor_base, specific, expected in cases:
            class FakeIndex:
                def resource_map(self, resource_type: int):
                    if resource_type == pipeline.INI_TYPE:
                        name = f"{animation_id:04X}"
                        return {name: (name, resource_type, 1)}
                    if resource_type == pipeline.IDS_TYPE:
                        return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                    if resource_type == pipeline.BAM_TYPE:
                        return {
                            f"{expected}{suffix}": (f"{expected}{suffix}", resource_type, 3)
                            for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                        }
                    return {}

                def resolve(self, entry):
                    if entry[0] == "ANIMATE":
                        return (
                            f"IDS V1.0\n0x{animation_id:04X} {symbol}\n".encode("ascii"),
                            "data/Default.bif",
                        )
                    ini = (
                        f"[general]\nanimation_type={animation_id & 0xF000:04X}\n"
                        f"[character]\narmor_max_code=4\nsplit_bams=1\n"
                        f"resref={base}\nresref_armor_base={armor_base}\n"
                        f"resref_armor_specific={specific}\n"
                    )
                    return ini.encode("ascii"), "data/Patch2.bif"

            with self.subTest(animation_id=animation_id):
                result = pipeline.character_animation_spec(FakeIndex(), animation_id, 4)
                self.assertEqual(result["bam_prefix"], expected)

    def test_character_identity_rejects_thief_id_with_fighter_bams(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                if resource_type == pipeline.INI_TYPE:
                    return {"6310": ("6310", resource_type, 1)}
                if resource_type == pipeline.IDS_TYPE:
                    return {"ANIMATE": ("ANIMATE", resource_type, 2)}
                if resource_type == pipeline.BAM_TYPE:
                    return {
                        f"CHFT1{suffix}": (f"CHFT1{suffix}", resource_type, 3)
                        for suffix in pipeline.CHARACTER_BODY_SUFFIXES
                    }
                return {}

            def resolve(self, entry):
                if entry[0] == "ANIMATE":
                    return b"IDS V1.0\n0x6310 THIEF_FEMALE_HUMAN\n", "data/Default.bif"
                return (
                    b"[general]\nanimation_type=6000\n[character]\n"
                    b"armor_max_code=4\nsplit_bams=1\nresref=CHFT\n"
                    b"resref_armor_base=T\nresref_armor_specific=T\n",
                    "data/Patch2.bif",
                )

        job = {
            "animation": {
                "id": "0x6310",
                "ids_symbol": "THIEF_FEMALE_HUMAN",
                "armor_code": 1,
                "bam_prefix": "CHFB1",
                "runtime_profile": "character-bg2ee-2.7.3.0",
            }
        }
        with self.assertRaisesRegex(RuntimeError, "identity mismatch"):
            pipeline.verify_character_animation_identity(job, FakeIndex())

    def test_animation_symbol_resolves_exact_id(self) -> None:
        class FakeIndex:
            def resource_map(self, resource_type: int):
                return {"ANIMATE": ("ANIMATE", resource_type, 1)}

            def resolve(self, entry):
                return (
                    b"IDS V1.0\n0x6010 CLERIC_FEMALE_HUMAN\n"
                    b"0x6110 FIGHTER_FEMALE_HUMAN\n",
                    "data/Default.bif",
                )

        self.assertEqual(
            pipeline.animation_id_for_symbol(FakeIndex(), "FIGHTER_FEMALE_HUMAN"),
            0x6110,
        )

    def test_runtime_owner_labels_match_real_log_markers(self) -> None:
        self.assertEqual(
            pipeline.runtime_owner_labels("character-bg2ee-2.7.3.0"),
            ("Character::Render", "CGameAnimationTypeCharacter::Render"),
        )

    def test_runtime_log_session_must_be_exact_and_post_install(self) -> None:
        text = "\n".join(
            (
                "[2026-08-25 00:10:00.000] Creature sprite xBR2x pack ready: animation 0x6310, old",
                "[2026-08-25 00:20:00.000] Creature sprite xBR2x pack ready: animation 0x6110, stale",
                "[2026-08-25 00:30:00.000] Creature sprite xBR2x pack ready: animation 0x6110, current",
                "[2026-08-25 00:30:01.000] Composing creature sprite CHFB1A1 frame 000",
            )
        )
        session = pipeline.runtime_log_session_after_install(
            text,
            "Creature sprite xBR2x pack ready: animation 0x6110,",
            "2026-08-24T22:25:00+00:00",
        )
        self.assertIn("current", session)
        self.assertNotIn("stale", session)
        self.assertNotIn("0x6310", session)

    @staticmethod
    def registry_bytes(
        version: int,
        metadata: int,
        *,
        scale: int = 2,
        magic: bytes = pipeline.REGISTRY_MAGIC,
    ) -> bytes:
        data = bytearray(magic)
        data.extend(struct.pack("<IIII", version, scale, 1, metadata))
        data.extend(b"TEST\0\0\0\0")
        data.extend(bytes(32))
        data.extend(struct.pack("<II", 1, 1))
        index_bytes = scale * scale
        data.extend(struct.pack("<HHhhB3xI", 1, 1, 0, 0, 0, index_bytes))
        representatives = np.full(256, 0xFFFF, dtype="<u2")
        representatives[1] = 0
        data.extend(representatives.tobytes())
        data.extend(bytes([1]) * index_bytes)
        data.extend(struct.pack("<II", 1, 0))
        return bytes(data)

    def test_registry_v2_carries_animation_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(self.registry_bytes(2, 0xE400))
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["version"], 2)
        self.assertEqual(info["scale"], 2)
        self.assertEqual(info["registry_magic"], "IEECSX2")
        self.assertEqual(info["animation_id"], "0xE400")
        self.assertEqual(info["frame_count"], 1)
        self.assertEqual(info["resources"], ["TEST"])

    def test_registry_v3_carries_explicit_x4_scale(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(
                self.registry_bytes(
                    3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
                )
            )
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["version"], 3)
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["registry_magic"], "IEECSXN")
        self.assertEqual(info["animation_id"], "0x6110")
        self.assertEqual(info["index_bytes"], 16)

    def test_xn_installer_scans_v3_payload_bytes(self) -> None:
        powershell = shutil.which("pwsh") or shutil.which("powershell")
        if powershell is None:
            self.skipTest("PowerShell is required for the XN installer parser test")
        install_script = ROOT / "pipeline" / "scripts" / "Install-CreatureSprite-XN-Test.ps1"
        with tempfile.TemporaryDirectory() as temporary:
            registry = Path(temporary) / "CreatureSprites-XN.registry"
            registry.write_bytes(
                self.registry_bytes(
                    3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
                )
            )
            quote = lambda value: str(value).replace("'", "''")
            command = f"""
$tokens = $null
$errors = $null
$ast = [System.Management.Automation.Language.Parser]::ParseFile(
  '{quote(install_script)}', [ref]$tokens, [ref]$errors)
foreach ($name in @('Read-ExactBytes','Skip-RegistryBytes','Read-RegistryHeader')) {{
  $fn = $ast.FindAll({{ param($node)
    $node -is [System.Management.Automation.Language.FunctionDefinitionAst] -and
    $node.Name -eq $name
  }}, $true) | Select-Object -First 1
  Invoke-Expression $fn.Extent.Text
}}
Read-RegistryHeader '{quote(registry)}' | ConvertTo-Json -Compress
"""
            completed = subprocess.run(
                [powershell, "-NoProfile", "-Command", command],
                check=True,
                capture_output=True,
                text=True,
            )
        info = json.loads(completed.stdout)
        self.assertEqual(info["magic"], "IEECSXN")
        self.assertEqual(info["scale"], 4)
        self.assertEqual(info["index_bytes"], 16)

    def test_registry_inspector_matches_runtime_strictness(self) -> None:
        base = self.registry_bytes(
            3, 0x6110, scale=4, magic=pipeline.XN_REGISTRY_MAGIC
        )
        frame_offset = pipeline.REGISTRY_HEADER_BYTES + pipeline.REGISTRY_RESOURCE_HEADER_BYTES
        mutations: list[tuple[str, bytearray]] = []
        zero_width = bytearray(base)
        struct.pack_into("<H", zero_width, frame_offset, 0)
        mutations.append(("frame header", zero_width))
        reserved = bytearray(base)
        reserved[frame_offset + 9] = 1
        mutations.append(("frame header", reserved))
        oversized_cycle = bytearray(base)
        struct.pack_into("<I", oversized_cycle, len(oversized_cycle) - 8, 65537)
        mutations.append(("cycle slot", oversized_cycle))
        duplicate = bytearray(base)
        struct.pack_into("<I", duplicate, 16, 2)
        duplicate.extend(base[pipeline.REGISTRY_HEADER_BYTES :])
        mutations.append(("duplicate", duplicate))
        for message, raw in mutations:
            with self.subTest(message=message):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "registry"
                    path.write_bytes(raw)
                    with self.assertRaisesRegex(RuntimeError, message):
                        pipeline.inspect_registry(path)

    def test_registry_rejects_crossed_magic_and_version(self) -> None:
        cases = (
            (pipeline.REGISTRY_MAGIC, 3, 4),
            (pipeline.XN_REGISTRY_MAGIC, 2, 2),
        )
        for magic, version, scale in cases:
            with self.subTest(magic=magic, version=version, scale=scale):
                with tempfile.TemporaryDirectory() as temporary:
                    path = Path(temporary) / "registry"
                    path.write_bytes(
                        self.registry_bytes(
                            version, 0x6110, scale=scale, magic=magic
                        )
                    )
                    with self.assertRaisesRegex(RuntimeError, "header"):
                        pipeline.inspect_registry(path)

    def test_registry_aggregation_rejects_mixed_identity(self) -> None:
        x4 = {"registry_magic": "IEECSXN", "version": 3, "scale": 4}
        self.assertEqual(
            pipeline.require_compatible_registry_infos([x4, dict(x4)]),
            ("IEECSXN", 3, 4),
        )
        for mixed in (
            {**x4, "scale": 2},
            {**x4, "version": 2},
            {**x4, "registry_magic": "IEECSX2"},
        ):
            with self.subTest(mixed=mixed):
                with self.assertRaisesRegex(RuntimeError, "mixed magic/version/scale"):
                    pipeline.require_compatible_registry_infos([x4, mixed])

    def test_legacy_registry_is_mgo1_only(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(self.registry_bytes(1, 0))
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["animation_id"], "0xE400")

    def test_registry_rejects_invalid_cycle_lookup(self) -> None:
        raw = bytearray(self.registry_bytes(2, 0xE400))
        struct.pack_into("<I", raw, len(raw) - 4, 1)
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(raw)
            with self.assertRaisesRegex(RuntimeError, "cycle lookup"):
                    pipeline.inspect_registry(path)

    def test_installed_state_integrity_detects_changed_files(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            game = Path(temporary)
            target = game / "InfinityEngine-Enhancer.dll"
            target.write_bytes(b"runtime")
            state = {
                "game_root": str(game),
                "targets": [
                    {
                        "relative_path": "InfinityEngine-Enhancer.dll",
                        "installed_present": True,
                        "installed_sha256": pipeline.sha256_file(target),
                    }
                ],
            }
            self.assertTrue(pipeline.installed_state_integrity(state)["installed_files_match"])
            target.write_bytes(b"changed")
            self.assertFalse(pipeline.installed_state_integrity(state)["installed_files_match"])


if __name__ == "__main__":
    unittest.main()
