from __future__ import annotations

import struct
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
    def registry_bytes(version: int, metadata: int) -> bytes:
        data = bytearray(pipeline.REGISTRY_MAGIC)
        data.extend(struct.pack("<IIII", version, 2, 1, metadata))
        data.extend(b"TEST\0\0\0\0")
        data.extend(bytes(32))
        data.extend(struct.pack("<II", 1, 1))
        data.extend(struct.pack("<HHhhB3xI", 1, 1, 0, 0, 0, 4))
        representatives = np.full(256, 0xFFFF, dtype="<u2")
        representatives[1] = 0
        data.extend(representatives.tobytes())
        data.extend(bytes([1, 1, 1, 1]))
        data.extend(struct.pack("<II", 1, 0))
        return bytes(data)

    def test_registry_v2_carries_animation_id(self) -> None:
        with tempfile.TemporaryDirectory() as temporary:
            path = Path(temporary) / "registry"
            path.write_bytes(self.registry_bytes(2, 0xE400))
            info = pipeline.inspect_registry(path)
        self.assertEqual(info["version"], 2)
        self.assertEqual(info["animation_id"], "0xE400")
        self.assertEqual(info["frame_count"], 1)
        self.assertEqual(info["resources"], ["TEST"])

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


if __name__ == "__main__":
    unittest.main()
