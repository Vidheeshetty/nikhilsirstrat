import pytest
import os
import shutil
from pathlib import Path

# Assuming src/convert_csv_to_parquet_w_meta_fixed_v5.py is the target script
# We'll need to simulate its environment or mock its external dependencies if any.
# For now, we'll just check if it runs without syntax errors.


@pytest.fixture(scope="module")
def setup_csv_data_for_conversion(tmp_path_factory):
    """
    Sets up a dummy CSV directory with a sample file for testing conversion.
    """
    test_data_dir = (
        tmp_path_factory.mktemp("test_csv_data") / "options" / "nse" / "nifty"
    )
    test_data_dir.mkdir(parents=True, exist_ok=True)

    # Create a dummy CSV file
    dummy_csv_content = """
symbol,timestamp,expiry,strike,option_type,bid,ask,last,volume,open_interest,totalBuyQuantity,totalSellQuantity,impliedVolatility,open_interest,pChange
NIFTY.NSE.OPT.19Jun2025.24800.PUT.NSE,2025-06-18 09:15:00,19Jun2025,24800,PUT,100.50,101.50,101.00,100,1000,500,550,20.0,1000,0.5
NIFTY.NSE.OPT.19Jun2025.24800.PUT.NSE,2025-06-18 09:16:00,19Jun2025,24800,PUT,100.60,101.60,101.10,120,1020,600,620,20.1,1020,0.6
"""
    dummy_csv_file = test_data_dir / "NIFTY_2025-06-18.csv"
    dummy_csv_file.write_text(dummy_csv_content)

    # Adjust the project root path for the script
    original_project_root = Path(__file__).resolve().parents[2]  # NTbasedPlatform root
    temp_project_root = tmp_path_factory.mktemp("temp_proj")

    # Simulate the project structure required by the script
    (temp_project_root / "data" / "options" / "nse" / "nifty").mkdir(
        parents=True, exist_ok=True
    )
    (temp_project_root / "catalog-data" / "my_nse_strategy" / "catalog").mkdir(
        parents=True, exist_ok=True
    )
    (temp_project_root / "catalog-data" / "my_nse_strategy" / "catalog-meta").mkdir(
        parents=True, exist_ok=True
    )

    # Copy the dummy CSV into the simulated data directory
    shutil.copytree(
        test_data_dir.parent.parent,
        temp_project_root / "data" / "options",
        dirs_exist_ok=True,
    )

    # Return the path to the script in the temp environment and the temp project root
    script_path = (
        Path(__file__).resolve().parent.parent.parent
        / "src"
        / "convert_csv_to_parquet_w_meta_fixed_v5.py"
    )
    temp_script_path = (
        temp_project_root / "src" / "convert_csv_to_parquet_w_meta_fixed_v5.py"
    )
    temp_script_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copyfile(script_path, temp_script_path)

    # Modify the script to use relative paths for catalogs and data if it uses absolute paths
    # This is a bit tricky; a more robust solution might involve mocking Path calls
    # For this test, we'll assume the script is designed to run from the project root
    # or we can modify the script's internal path variables for testing.

    yield temp_script_path, temp_project_root

    # No explicit cleanup needed for tmp_path_factory.mktemp


def test_csv_to_parquet_conversion_runs(setup_csv_data_for_conversion):
    """
    Tests that the CSV to Parquet conversion script runs without errors
    and creates expected output files.
    """
    script_path, temp_project_root = setup_csv_data_for_conversion

    # Ensure the script runs from the correct directory for its internal path logic
    original_cwd = os.getcwd()
    os.chdir(temp_project_root)

    try:
        import subprocess

        # Run the script as a subprocess
        result = subprocess.run(
            ["python3", str(script_path)],
            capture_output=True,
            text=True,
            check=False,  # Do not raise CalledProcessError for non-zero exit codes
        )

        print("\n--- Script stdout ---")
        print(result.stdout)
        print("\n--- Script stderr ---")
        print(result.stderr)

        assert result.returncode == 0, f"Script exited with error: {result.stderr}"

        # Verify output directories and files
        catalog_dir = temp_project_root / "catalog-data" / "my_nse_strategy" / "catalog"
        catalog_meta_dir = (
            temp_project_root / "catalog-data" / "my_nse_strategy" / "catalog-meta"
        )

        assert catalog_dir.is_dir(), "Catalog directory should be created"
        assert catalog_meta_dir.is_dir(), "Metadata catalog directory should be created"

        # Check for expected parquet files
        assert any(catalog_dir.glob("**/*.parquet")), (
            "Should contain parquet files in catalog"
        )
        assert any(catalog_meta_dir.glob("**/*.parquet")), (
            "Should contain parquet files in meta catalog"
        )

    finally:
        os.chdir(original_cwd)
