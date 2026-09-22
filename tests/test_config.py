from __future__ import annotations

import unittest

from tracker.config import (
    PRESETS,
    _merge_defaults,
    apply_profile,
    delete_profile,
    is_builtin_profile,
    profile_names,
    put_profile,
    rename_profile,
    sanitize_profile_name,
    snapshot_profile,
)


class ProfileTests(unittest.TestCase):
    def test_sanitize_name(self) -> None:
        self.assertEqual(sanitize_profile_name("  Green  Map  "), "Green Map")
        self.assertEqual(sanitize_profile_name("x" * 80), "x" * 40)
        self.assertEqual(sanitize_profile_name(""), "")

    def test_legacy_custom_preset_migrates(self) -> None:
        data = _merge_defaults(
            {
                "line_color": [0, 255, 0],
                "custom_preset": {"thickness": 6, "line_color": [0, 255, 0]},
            }
        )
        self.assertIn("Custom", data["profiles"])
        self.assertEqual(data["profiles"]["Custom"]["thickness"], 6)
        self.assertEqual(data["head_marker"], "crosshair")
        self.assertNotIn("custom_preset", data)

    def test_save_load_rename_delete(self) -> None:
        data = _merge_defaults({"thickness": 4.5, "line_color": [0, 255, 0]})
        data = put_profile(data, "Green")
        self.assertEqual(data["active_profile"], "Green")
        self.assertIn("Green", data["profiles"])
        self.assertEqual(data["profiles"]["Green"]["thickness"], 4.5)
        self.assertNotIn("profiles", snapshot_profile(data))

        data["thickness"] = 1.0
        data = apply_profile(data, "Green")
        self.assertEqual(data["thickness"], 4.5)

        data = rename_profile(data, "Green", "Forest")
        self.assertEqual(data["active_profile"], "Forest")
        self.assertNotIn("Green", data["profiles"])
        self.assertIn("Forest", profile_names(data))

        data = delete_profile(data, "Forest")
        self.assertNotIn("Forest", data["profiles"])
        self.assertEqual(data["active_profile"], "Classic")
        self.assertEqual(data["head_marker"], "crosshair")

    def test_builtin_names_are_protected(self) -> None:
        data = _merge_defaults({})
        self.assertTrue(is_builtin_profile("Classic"))
        with self.assertRaises(ValueError):
            put_profile(data, "Classic")
        with self.assertRaises(ValueError):
            rename_profile(data, "Classic", "Mine")
        with self.assertRaises(ValueError):
            delete_profile(data, "Neon")

    def test_apply_builtin_keeps_saved_profiles(self) -> None:
        data = put_profile(_merge_defaults({"thickness": 8}), "Mine")
        data = apply_profile(data, "Classic")
        self.assertEqual(data["active_profile"], "Classic")
        self.assertEqual(data["thickness"], PRESETS["Classic"]["thickness"])
        self.assertIn("Mine", data["profiles"])


if __name__ == "__main__":
    unittest.main()
