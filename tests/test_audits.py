import struct
import sys
import unittest
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
from audit_settings_bytecode import hazards
from audit_dex import argument_words


class AuditRegressionTests(unittest.TestCase):
    def test_unused_constructor_is_rejected(self):
        self.assertTrue(hazards("public com.armsx2.config.Settings();"))
        self.assertTrue(hazards("public com.armsx2.config.Settings(int, kotlin.jvm.internal.DefaultConstructorMarker);"))

    def test_default_copy_is_rejected(self):
        self.assertTrue(hazards("public static com.armsx2.config.Settings copy$default(...);"))

    def test_explicit_constructor_is_allowed(self):
        self.assertEqual([], hazards("public com.armsx2.config.Settings(int, boolean, java.lang.String);"))

    def test_dex_words_include_wide_primitives_but_not_wide_arrays(self):
        self.assertEqual(8, argument_words("IJDLjava/lang/String;[J[[D"))
        self.assertEqual(246, argument_words("I" * 246))
        self.assertEqual(255, argument_words("I" * 254 + "Lkotlin/jvm/internal/DefaultConstructorMarker;"))


if __name__ == "__main__":
    unittest.main()
