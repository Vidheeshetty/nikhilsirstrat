from utils.data_adapters.conversion_config import ConverterConfig


def test_load_yaml(tmp_path):
    yaml_content = (
        "source_csv: 'data/*.csv'\n"
        "destination_catalog: 'catalog-data/shared/catalog'\n"
        "destination_meta: 'catalog-data/shared/catalog-meta'\n"
    )
    cfg_file = tmp_path / "cfg.yaml"
    cfg_file.write_text(yaml_content)

    cfg = ConverterConfig.from_yaml(cfg_file)

    assert cfg.source_csv == "data/*.csv"
    assert cfg.destination_catalog.endswith("catalog")
    assert cfg.data_kind == "bar"  # default
