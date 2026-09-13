"""
PulseCart Unit Test Suite - Milestone 4 Power BI Modeling & Verification
Tests F21 (Star Schema Architecture), F22 (DAX Library), F23 (Dashboard Specs),
and F24 (Reproduction Guide & PBIX Generator).
"""

import json
import os
import re
import sys
import zipfile
from pathlib import Path

import pytest

PROJECT_ROOT = Path(__file__).resolve().parent.parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

POWER_BI_DIR = PROJECT_ROOT / "power_bi"
SEMANTIC_MODEL_JSON = POWER_BI_DIR / "semantic_model.json"
SEMANTIC_MODEL_MD = POWER_BI_DIR / "semantic_model.md"
DAX_LIBRARY_FILE = POWER_BI_DIR / "dax_library.dax"
DAX_LIBRARY_MD = POWER_BI_DIR / "dax_library.md"
DASHBOARD_SPECS_MD = POWER_BI_DIR / "dashboard_specifications.md"
REPRODUCTION_GUIDE_MD = POWER_BI_DIR / "reproduction_guide.md"
GENERATE_PBIX_PY = POWER_BI_DIR / "generate_pbix.py"
PBIX_FILE = POWER_BI_DIR / "PulseCart_Analytics.pbix"
PBIT_FILE = POWER_BI_DIR / "PulseCart_Template.pbit"
MARTS_DIR = PROJECT_ROOT / "data" / "marts"


# ===========================================================================
# F21: Star Schema Semantic Model Architecture
# ===========================================================================
@pytest.mark.unit
@pytest.mark.feature("F21")
class TestF21SemanticModelUnit:
    """Unit tests for F21: Semantic Model TOM schema and star schema topology."""

    def test_semantic_model_json_exists_and_valid(self):
        assert SEMANTIC_MODEL_JSON.exists()
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        assert data.get("compatibilityLevel") == 1550
        assert "model" in data

    def test_four_fact_tables_present(self):
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        tables = {t["name"] for t in data["model"]["tables"]}
        expected_facts = {"fct_orders", "fct_funnel", "fct_user_retention", "fct_ab_test"}
        assert expected_facts.issubset(tables)

    def test_three_conformed_dimensions_present(self):
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        tables = {t["name"] for t in data["model"]["tables"]}
        expected_dims = {"dim_users", "dim_products", "dim_date"}
        assert expected_dims.issubset(tables)

    def test_disconnected_measures_table_present(self):
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        tables = {t["name"] for t in data["model"]["tables"]}
        assert "_Measures" in tables

    def test_active_and_inactive_date_relationships(self):
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        rels = data["model"]["relationships"]
        
        # Order date active
        order_active = [r for r in rels if r["fromTable"] == "fct_orders" and "order_date" in r["fromColumn"] and r["isActive"]]
        assert len(order_active) == 1
        
        # Shipping date inactive
        order_shipping = [r for r in rels if r["fromTable"] == "fct_orders" and "shipping" in r["fromColumn"] and not r["isActive"]]
        assert len(order_shipping) == 1

        # Activity month inactive
        activity_month = [r for r in rels if r["fromTable"] == "fct_user_retention" and "activity" in r["fromColumn"] and not r["isActive"]]
        assert len(activity_month) == 1

    def test_single_direction_cross_filtering(self):
        with open(SEMANTIC_MODEL_JSON, "r", encoding="utf-8") as f:
            data = json.load(f)
        for r in data["model"]["relationships"]:
            assert r.get("crossFilteringBehavior") == "oneDirection"

    def test_semantic_model_md_contains_erd_and_grains(self):
        assert SEMANTIC_MODEL_MD.exists()
        content = SEMANTIC_MODEL_MD.read_text(encoding="utf-8")
        assert "erDiagram" in content
        assert "VertiPaq" in content
        assert "fct_orders" in content
        assert "dim_date" in content


# ===========================================================================
# F22: Comprehensive DAX Measure Library
# ===========================================================================
@pytest.mark.unit
@pytest.mark.feature("F22")
class TestF22DAXLibraryUnit:
    """Unit tests for F22: 74+ production DAX measures across 5 display folders."""

    def test_dax_library_file_exists(self):
        assert DAX_LIBRARY_FILE.exists()
        assert DAX_LIBRARY_MD.exists()

    def test_at_least_74_measures_parsed(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        measure_names = re.findall(r'/\*\s*\[(.*?)\]\s*Folder:', content)
        assert len(measure_names) >= 74, f"Found only {len(measure_names)} measures"

    def test_five_display_folders_defined(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        folders = set(re.findall(r'Folder:\s*([^\r\n]+)', content))
        expected_folders = {"01_Executive", "02_Funnel", "03_Retention", "04_Experiment", "05_Helper_Stats"}
        assert expected_folders == folders

    def test_divide_safeguard_used_in_ratios(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        # Ensure DIVIDE is ubiquitous for ratios
        assert "DIVIDE([Gross Revenue], [Total Orders], 0)" in content
        assert "DIVIDE(" in content

    def test_time_intelligence_dateadd_used(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        assert "DATEADD" in content
        assert "DATESINPERIOD" in content

    def test_two_proportion_zscore_formula(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        assert "DIVIDE([AB Absolute Uplift], [AB Pooled Standard Error], 0)" in content

    def test_chi_square_srm_formula(self):
        content = DAX_LIBRARY_FILE.read_text(encoding="utf-8")
        assert "VAR Expected = ([AB Control Sessions] + [AB Treatment Sessions]) / 2" in content
        assert "DIVIDE(([AB Control Sessions] - Expected)^2, Expected)" in content


# ===========================================================================
# F23: 4-Page Executive Dashboard Layout Specs
# ===========================================================================
@pytest.mark.unit
@pytest.mark.feature("F23")
class TestF23DashboardSpecsUnit:
    """Unit tests for F23: 4-page UI specifications, coordinates, and WCAG contrast."""

    def test_dashboard_specs_markdown_exists(self):
        assert DASHBOARD_SPECS_MD.exists()

    def test_all_four_pages_specified(self):
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        expected_pages = ["Executive Overview", "Funnel Analysis", "Retention & Cohorts", "A/B Test Experiment"]
        for page in expected_pages:
            assert page in content

    def test_aspect_ratio_16_to_9(self):
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        assert "1920" in content
        assert "1080" in content

    def test_executive_headline_cards(self):
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        expected_kpis = ["Gross Revenue", "Total Orders", "Average Order Value", "Conversion Rate", "Total Sessions"]
        for kpi in expected_kpis:
            assert kpi in content

    def test_funnel_visual_stepped_stages(self):
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        assert "6-Stage" in content or "6 stepped stages" in content.lower() or "stage 6" in content.lower()

    def test_srm_status_badge_colors(self):
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        assert "#10B981" in content  # Emerald
        assert "#F43F5E" in content  # Rose

    def test_visual_coordinates_within_canvas_and_no_overlaps(self):
        """Parse coordinate tables in markdown and verify zero collisions."""
        content = DASHBOARD_SPECS_MD.read_text(encoding="utf-8")
        # Match markdown table rows: | `V1_1` | ... | 40 | 120 | 350 | 130 |
        coord_pattern = re.compile(r'\|\s*`([Vv]\d+_\d+)`\s*\|[^|]*\|[^|]*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|\s*(\d+)\s*\|')
        matches = coord_pattern.findall(content)
        assert len(matches) >= 30, f"Expected at least 30 visual coordinates, found {len(matches)}"

        pages = {}
        for vid, x, y, w, h in matches:
            page_prefix = vid.split("_")[0]
            if page_prefix not in pages:
                pages[page_prefix] = []
            rect = {"id": vid, "x": int(x), "y": int(y), "w": int(w), "h": int(h)}
            # Bounds check
            assert rect["x"] >= 0 and rect["y"] >= 0
            assert rect["x"] + rect["w"] <= 1920, f"{vid} exceeds canvas width: {rect['x'] + rect['w']}"
            assert rect["y"] + rect["h"] <= 1080, f"{vid} exceeds canvas height: {rect['y'] + rect['h']}"
            pages[page_prefix].append(rect)

        # Collision check
        for page_prefix, rects in pages.items():
            assert len(rects) <= 15, f"Page {page_prefix} exceeded visual count budget: {len(rects)}"
            for i in range(len(rects)):
                for j in range(i + 1, len(rects)):
                    r1, r2 = rects[i], rects[j]
                    overlap = not (
                        r1["x"] + r1["w"] <= r2["x"] or
                        r2["x"] + r2["w"] <= r1["x"] or
                        r1["y"] + r1["h"] <= r2["y"] or
                        r2["y"] + r2["h"] <= r1["y"]
                    )
                    assert not overlap, f"Collision detected on {page_prefix} between {r1['id']} and {r2['id']}"


# ===========================================================================
# F24: Power BI Reproduction Guide & PBIX Assets
# ===========================================================================
@pytest.mark.unit
@pytest.mark.feature("F24")
class TestF24ReproductionGuidePBIXUnit:
    """Unit tests for F24: 7-phase reproduction guide, generator script, and verified assets."""

    def test_seven_phases_documented(self):
        assert REPRODUCTION_GUIDE_MD.exists()
        content = REPRODUCTION_GUIDE_MD.read_text(encoding="utf-8")
        phases = [
            "Phase 1: Environment & Options Configuration",
            "Phase 2: Data Source Connection & Ingestion",
            "Phase 3: Semantic Model & Relationship Topology",
            "Phase 4: DAX Measure Library Implementation",
            "Phase 5: Report Canvas Layout & Page Construction",
            "Phase 6: Verification & QA Matrix",
            "Phase 7: Publishing & Service Configuration",
        ]
        for phase in phases:
            assert phase in content

    def test_auto_datetime_disabled_rule(self):
        content = REPRODUCTION_GUIDE_MD.read_text(encoding="utf-8")
        assert "File -> Options -> Current File -> Data Load -> Uncheck Auto Date/Time" in content

    def test_pbix_script_executable(self):
        assert GENERATE_PBIX_PY.exists()
        # Verify it can be imported or invoked
        import power_bi.generate_pbix as gen
        assert hasattr(gen, "main")
        assert hasattr(gen, "validate_data_marts")
        assert hasattr(gen, "parse_dax_library")
        assert hasattr(gen, "validate_semantic_model")
        assert hasattr(gen, "create_pbix_package")

    def test_pbix_and_pbit_assets_physically_exist(self):
        # Run the generator to guarantee files are fresh and verified
        import power_bi.generate_pbix as gen
        gen.main()

        assert PBIX_FILE.exists(), f"Missing physical PBIX file: {PBIX_FILE}"
        assert PBIT_FILE.exists(), f"Missing physical PBIT file: {PBIT_FILE}"
        assert PBIX_FILE.stat().st_size > 0
        assert PBIT_FILE.stat().st_size > 0

    def test_pbix_zip_archive_structure(self):
        assert zipfile.is_zipfile(PBIX_FILE)
        with zipfile.ZipFile(PBIX_FILE, "r") as zf:
            namelist = zf.namelist()
            assert "[Content_Types].xml" in namelist
            assert "DataModelSchema" in namelist
            assert "Report/Layout" in namelist
            assert "Settings" in namelist

            # Validate DataModelSchema contains measures
            schema_data = zf.read("DataModelSchema").decode("utf-16le")
            schema_json = json.loads(schema_data)
            assert schema_json["compatibilityLevel"] == 1550
            measures_table = [t for t in schema_json["model"]["tables"] if t["name"] == "_Measures"][0]
            assert len(measures_table["measures"]) >= 74
