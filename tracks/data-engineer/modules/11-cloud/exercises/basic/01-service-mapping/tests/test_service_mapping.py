import pytest

from testkit import Exercise

ex = Exercise(__file__)

EXPECTED = {
    "compute": ("EC2", "Virtual Machines", "Compute Engine"),
    "object_storage": ("S3", "Blob Storage", "Cloud Storage"),
    "managed_sql": ("RDS", "SQL Database", "Cloud SQL"),
    "etl": ("Glue", "Data Factory", "Dataflow"),
    "warehouse": ("Redshift", "Synapse Analytics", "BigQuery"),
    "streaming": ("Kinesis", "Event Hubs", "Pub/Sub"),
}


def m():
    return ex.module("cloud_map.py")


def test_catalog_complete():
    catalog = m().CATALOG
    assert list(catalog) == list(EXPECTED)
    names = []
    for category, (aws, azure, gcp) in EXPECTED.items():
        assert catalog[category] == {"aws": aws, "azure": azure, "gcp": gcp}, category
        names += catalog[category].values()
    assert "TODO" not in names
    assert len(names) == len(set(names)), "Mỗi ô một tên khác nhau"


@pytest.mark.parametrize(
    "name, expected",
    [
        ("S3", ("object_storage", "aws")),
        ("  amazon s3 ", ("object_storage", "aws")),
        ("Azure Blob Storage", ("object_storage", "azure")),
        ("Google Cloud Storage", ("object_storage", "gcp")),
        ("gcs", ("object_storage", "gcp")),
        ("Google Cloud SQL", ("managed_sql", "gcp")),
        ("Aurora", ("managed_sql", "aws")),
        ("Azure SQL Database", ("managed_sql", "azure")),
        ("ADF", ("etl", "azure")),
        ("AWS Glue", ("etl", "aws")),
        ("BigQuery", ("warehouse", "gcp")),
        ("Azure Synapse Analytics", ("warehouse", "azure")),
        ("GCP Pub/Sub", ("streaming", "gcp")),
        ("pubsub", ("streaming", "gcp")),
        ("Amazon EC2", ("compute", "aws")),
        ("Azure VM", ("compute", "azure")),
    ],
)
def test_lookup(name, expected):
    assert m().lookup(name) == expected


@pytest.mark.parametrize("name", ["Snowflake", "", "s4", "amazon"])
def test_lookup_unknown(name):
    with pytest.raises(ValueError):
        m().lookup(name)


def test_equivalent():
    eq = m().equivalent
    assert eq("BigQuery", "aws") == "Redshift"
    assert eq("BigQuery", "AZURE") == "Synapse Analytics"
    assert eq("Kinesis Data Streams", "gcp") == "Pub/Sub"
    assert eq("Event Hubs", "aws") == "Kinesis"
    assert eq("Glue", "gcp") == "Dataflow"
    assert eq("Azure SQL", "gcp") == "Cloud SQL"
    assert eq("gce", "aws") == "EC2"
    assert eq("amazon s3", "aws") == "S3"


def test_equivalent_bad_target():
    with pytest.raises(ValueError):
        m().equivalent("S3", "oracle")


def test_comparison_table_default():
    table = m().comparison_table()
    assert table.endswith("\n")
    lines = table.splitlines()
    assert lines[0] == "| Category | AWS | Azure | GCP |"
    assert lines[1] == "| --- | --- | --- | --- |"
    assert len(lines) == 2 + len(EXPECTED)
    assert lines[2] == "| compute | EC2 | Virtual Machines | Compute Engine |"
    assert lines[-1] == "| streaming | Kinesis | Event Hubs | Pub/Sub |"


def test_comparison_table_subset():
    lines = m().comparison_table(["warehouse", "etl"]).splitlines()
    assert lines[2:] == [
        "| warehouse | Redshift | Synapse Analytics | BigQuery |",
        "| etl | Glue | Data Factory | Dataflow |",
    ]
