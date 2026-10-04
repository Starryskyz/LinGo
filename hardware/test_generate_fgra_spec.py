"""运行：python3 hardware/test_generate_fgra_spec.py（不依赖 pytest/Chisel）。"""

from copy import deepcopy
import contextlib
import io
import json
from pathlib import Path
import tempfile
import unittest

import generate_fgra_spec as gen


class SpecGeneratorTests(unittest.TestCase):
    def test_default_exact_bytes(self):
        self.assertEqual(gen.render_spec(gen.build_spec()), gen.DEFAULT_OUTPUT.read_bytes())

    def test_json_round_trip(self):
        spec = gen.build_spec()
        self.assertEqual(json.loads(gen.render_spec(spec)), spec)

    def test_current_layout(self):
        spec = gen.build_spec()
        self.assertEqual(spec["fgra_gpes"][1][2]["gpe_mode"], 2)
        self.assertEqual(spec["fgra_gpes"][3][3]["operations"], ["XCORE"])
        self.assertEqual(spec["fgra_gpes"][4][0]["operations"][-3:], ["FMUL", "FADDSUB", "FDIV"])
        self.assertNotIn("FMUL", spec["fgra_gpes"][4][1]["operations"])
        self.assertIn("FACC", spec["fgra_gpes"][2][0]["operations"])

    def test_rectangular_architecture(self):
        spec = gen.build_spec(gen.Architecture(pe_layout=[["basic"] * 4 for _ in range(3)]))
        self.assertEqual((spec["fgra_num_row"], spec["fgra_num_colum"]), (3, 4))
        self.assertEqual(spec["spad_num_banks"], 8)
        self.assertEqual(spec["fgra_iob_sram_addr_width"], 14)
        self.assertEqual((len(spec["fgra_cg_gibs"]), len(spec["fgra_cg_gibs"][0])), (4, 5))

    def test_more_than_32_iobs(self):
        spec = gen.build_spec(gen.Architecture(pe_layout=[["basic"] * 18 for _ in range(2)]))
        self.assertEqual(spec["spad_num_banks"], 36)
        self.assertEqual(spec["fgra_iob_sram_addr_width"], 17)
        self.assertEqual(len(spec["fgra_iobs"][0]), 18)

    def test_overrides_and_independent_cells(self):
        arch = gen.Architecture(pe_overrides={(0, 0): {"num_input_lut": 3}},
                                iob_overrides={(1, 2): {"max_delay_cg": 7}},
                                cg_gib_overrides={(0, 0): {"fclist": [1, 3, 4]}})
        spec = gen.build_spec(arch)
        self.assertEqual(spec["fgra_gpes"][0][0]["num_input_lut"], 3)
        self.assertEqual(spec["fgra_gpes"][0][1]["num_input_lut"], 0)
        self.assertEqual(spec["fgra_iobs"][1][2]["max_delay_cg"], 7)
        self.assertEqual(spec["fgra_cg_gibs"][0][0]["fclist"], [1, 3, 4])
        spec["fgra_gpes"][0][0]["operations"].append("ACC")
        self.assertNotIn("ACC", spec["fgra_gpes"][0][1]["operations"])
        self.assertNotIn("ACC", arch.pe_profiles["basic"]["operations"])

    def test_custom_profile_and_direct_cell(self):
        arch = gen.Architecture(pe_layout=[["mac", gen.pe(0, ["PASS", "ADD"]) ]])
        arch.pe_profiles["mac"] = gen.pe(0, ["PASS", "MAC"])
        spec = gen.build_spec(arch)
        self.assertEqual(spec["fgra_gpes"][0][0]["operations"], ["PASS", "MAC"])

    def test_no_mutation_of_configuration(self):
        arch = gen.Architecture()
        before = deepcopy(arch)
        gen.build_spec(arch)
        self.assertEqual(arch, before)

    def test_global_and_instance_values_are_distinct(self):
        spec = gen.build_spec()
        self.assertEqual(spec["fgra_iob_mode"], 3)
        self.assertEqual(spec["fgra_iobs"][0][0]["iob_mode"], 2)
        self.assertEqual(spec["fgra_gib_connect_flexibility_cg"]["num_otrack_per_opin"], 4)
        self.assertEqual(spec["fgra_cg_gibs"][0][0]["fclist"], [2, 2, 2])

    def test_gibs_derived_from_global_flexibility(self):
        spec = gen.build_spec(gen.Architecture(cg_gib_template=None))
        self.assertEqual(spec["fgra_cg_gibs"][0][0]["fclist"], [2, 4, 4])

    def test_sparse_fg_grid_shape(self):
        spec = gen.build_spec(gen.Architecture(parameters={
            "fgra_gpe_fg_rows": [0, 2, 4], "fgra_gpe_fg_columns": [1, 3],
        }))
        self.assertEqual((len(spec["fgra_fg_gibs"]), len(spec["fgra_fg_gibs"][0])), (4, 3))

    def test_invalid_architectures(self):
        invalid = [
            gen.Architecture(pe_layout=[]),
            gen.Architecture(pe_layout=[["basic"], ["basic", "basic"]]),
            gen.Architecture(pe_layout=[["unknown"]]),
            gen.Architecture(parameters={"fgra_num_colum": 8}),
            gen.Architecture(parameters={"unknown": 1}),
            gen.Architecture(parameters={"fgra_iob_num_sides": 4}),
            gen.Architecture(parameters={"fgra_iob_sram_banks_coalesce": 4}),
            gen.Architecture(parameters={"system_bus_beat_bits": 64}),
            gen.Architecture(parameters={"fgra_gpe_fg_rows": [6]}),
            gen.Architecture(pe_overrides={(6, 0): {"num_input_lut": 1}}),
            gen.Architecture(pe_layout=[[gen.pe(1, ["MUL", "FMUL"])]]),
            gen.Architecture(pe_layout=[[gen.pe(1, ["FDIV"])]]),
            gen.Architecture(pe_layout=[[gen.pe(2, ["ADD"])]]),
            gen.Architecture(iob_overrides={(0, 0): {"iob_mode": 0}}),
        ]
        for arch in invalid:
            with self.subTest(arch=arch), self.assertRaises(ValueError):
                gen.build_spec(arch)

    def test_cli_output_and_overwrite_protection(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "new.json"
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gen.main(["-o", str(output)]), 0)
                self.assertEqual(gen.main(["--check", str(output)]), 0)
                self.assertEqual(gen.main(["-o", str(output)]), 0)
            original = output.read_bytes()
            arguments = ["--rows", "2", "--cols", "3", "--pe-profile", "basic", "-o", str(output)]
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as exc:
                gen.main(arguments)
            self.assertEqual(exc.exception.code, 2)
            self.assertEqual(output.read_bytes(), original)
            with contextlib.redirect_stdout(io.StringIO()):
                self.assertEqual(gen.main(arguments + ["--force"]), 0)
            self.assertEqual(json.loads(output.read_bytes())["spad_num_banks"], 6)

    def test_check_reports_format_and_content_differences(self):
        with tempfile.TemporaryDirectory() as directory:
            output = Path(directory) / "check.json"
            spec = gen.build_spec()
            for content, expected in ((json.dumps(spec), "格式"), ("{}", "内容不同")):
                output.write_text(content, encoding="utf-8")
                captured = io.StringIO()
                with contextlib.redirect_stderr(captured):
                    self.assertEqual(gen.main(["--check", str(output)]), 1)
                self.assertIn(expected, captured.getvalue())
                self.assertEqual(output.read_text(), content)


if __name__ == "__main__":
    unittest.main()
