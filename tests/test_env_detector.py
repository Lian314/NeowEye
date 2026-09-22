import os
import tempfile
import unittest
from env_detector import EnvironmentDetector, DiagnosticResult

class TestEnvironmentDetector(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.detector = EnvironmentDetector(app_root=self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_auto_bind_communication_mod(self):
        fake_exe = r"D:\Games\NeowEye\NeowEye.exe"
        ok, cfg_path = self.detector.auto_bind_communication_mod(exe_path=fake_exe)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(cfg_path))

        with open(cfg_path, "r", encoding="utf-8") as f:
            content = f.read()

        # Check forward slashes and format
        self.assertIn('command="D:/Games/NeowEye/NeowEye.exe" --mode stdin', content)
        self.assertIn('runAtGameStart=true', content)
        self.assertIn('verbose=false', content)

    def test_is_valid_game_dir(self):
        # Empty dir should fail
        self.assertFalse(self.detector._is_valid_game_dir(self.temp_dir.name))

        # Dir with desktop-1.0.jar should pass
        jar_path = os.path.join(self.temp_dir.name, "desktop-1.0.jar")
        with open(jar_path, "w") as f:
            f.write("mock jar")
        self.assertTrue(self.detector._is_valid_game_dir(self.temp_dir.name))

    def test_check_mods_local(self):
        game_dir = self.temp_dir.name
        # Initially all False
        status = self.detector.check_mods(game_dir)
        self.assertFalse(status["modthespire"])
        self.assertFalse(status["basemod"])
        self.assertFalse(status["communicationmod"])

        # Add ModTheSpire.jar in root
        with open(os.path.join(game_dir, "ModTheSpire.jar"), "w") as f:
            f.write("mts")

        # Add mods/BaseMod.jar and mods/CommunicationMod.jar
        mods_dir = os.path.join(game_dir, "mods")
        os.makedirs(mods_dir, exist_ok=True)
        with open(os.path.join(mods_dir, "BaseMod.jar"), "w") as f:
            f.write("basemod")
        with open(os.path.join(mods_dir, "CommunicationMod.jar"), "w") as f:
            f.write("comm")

        status2 = self.detector.check_mods(game_dir)
        self.assertTrue(status2["modthespire"])
        self.assertTrue(status2["basemod"])
        self.assertTrue(status2["communicationmod"])

    def test_custom_game_dir_persistence(self):
        game_dir = self.temp_dir.name
        with open(os.path.join(game_dir, "SlayTheSpire.exe"), "w") as f:
            f.write("exe")

        saved = self.detector.save_custom_game_dir(game_dir)
        self.assertTrue(saved)

        loaded = self.detector.load_custom_game_dir()
        self.assertEqual(os.path.normpath(loaded), os.path.normpath(game_dir))

    def test_offline_mod_installer(self):
        game_dir = os.path.join(self.temp_dir.name, "game")
        os.makedirs(game_dir, exist_ok=True)
        with open(os.path.join(game_dir, "SlayTheSpire.exe"), "w") as f:
            f.write("exe")

        # Create mock spire_mods/ folder in detector app_root
        spire_mods = os.path.join(self.temp_dir.name, "spire_mods")
        os.makedirs(spire_mods, exist_ok=True)
        with open(os.path.join(spire_mods, "ModTheSpire.jar"), "w") as f:
            f.write("mts")
        with open(os.path.join(spire_mods, "BaseMod.jar"), "w") as f:
            f.write("bm")
        with open(os.path.join(spire_mods, "CommunicationMod.jar"), "w") as f:
            f.write("cm")

        self.assertTrue(self.detector.has_offline_mod_kit())
        ok, msg = self.detector.install_offline_mods(game_dir)
        self.assertTrue(ok)
        self.assertTrue(os.path.exists(os.path.join(game_dir, "ModTheSpire.jar")))
        self.assertTrue(os.path.exists(os.path.join(game_dir, "mods", "BaseMod.jar")))
        self.assertTrue(os.path.exists(os.path.join(game_dir, "mods", "CommunicationMod.jar")))

if __name__ == "__main__":
    unittest.main()
