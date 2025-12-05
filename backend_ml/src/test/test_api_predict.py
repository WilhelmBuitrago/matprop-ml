import pytest


@pytest.mark.parametrize("model_key", ["mf_2020", "mp-2019.4.1"])
def test_predict_from_file_downloadable_models(
    client, isolated_cache, cif_file, model_key
):
    response = client.post(f"/v1/predict/{model_key}", json={"filepath": str(cif_file)})

    assert response.status_code == 200
    data = response.json()

    # Validaciones formales de la API (ya normalizada)
    assert "model_key" in data
    assert data["model_key"] == model_key

    assert "properties" in data
    assert isinstance(data["properties"], dict)
    assert len(data["properties"]) > 0

    for prop, info in data["properties"].items():
        assert "value" in info
        assert isinstance(info["value"], (int, float))


def test_predict_local_model(client, cif_file):
    model_key = "Bandgap_MP_2018"

    response = client.post(f"/v1/predict/{model_key}", json={"filepath": str(cif_file)})

    assert response.status_code == 200
    data = response.json()

    assert data["model_key"] == model_key
    assert "properties" in data
    assert len(data["properties"]) > 0


def test_predict_structure_dict(client):
    structure = {
        "lattice": {"matrix": [[3, 0, 0], [0, 3, 0], [0, 0, 3]]},
        "sites": [{"species": [{"element": "C", "occu": 1}], "xyz": [0, 0, 0]}],
    }

    response = client.post("/v1/predict/Bandgap_MP_2018", json={"structure": structure})

    assert response.status_code == 200
    data = response.json()
    assert "properties" in data


def test_predict_invalid_model(client, cif_file):
    response = client.post(
        "/v1/predict/no_such_model", json={"filepath": str(cif_file)}
    )
    assert response.status_code == 400
