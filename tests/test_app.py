from io import BytesIO

from app import app, calculer_prix, demandes, extension_autorisee


def envoyer_fichier(client, nom_fichier):
    return client.post(
        "/",
        data={
            "nom": "Alice Martin",
            "chambre": "B204",
            "pages": "10",
            "copies": "2",
            "couleur": "noir",
            "fichier": (BytesIO(b"contenu de test"), nom_fichier),
        },
        content_type="multipart/form-data",
    )


def test_calcul_du_prix():
    assert calculer_prix(10, 2, "noir") == 2.0
    assert calculer_prix(3, 1, "couleur") == 1.5


def test_extensions():
    assert extension_autorisee("cours.pdf")
    assert extension_autorisee("photo.PNG")
    assert not extension_autorisee("virus.exe")
    assert not extension_autorisee("sansextension")


def test_page_formulaire():
    reponse = app.test_client().get("/")
    assert reponse.status_code == 200
    assert "Envoyer un document" in reponse.get_data(as_text=True)


def test_envoi_accepte(tmp_path, monkeypatch):
    monkeypatch.setattr("app.DOSSIER_FICHIERS", tmp_path)
    demandes.clear()
    reponse = envoyer_fichier(app.test_client(), "cours.pdf")
    assert reponse.status_code == 200
    assert len(demandes) == 1
    assert demandes[0]["prix"] == 2.0
    assert (tmp_path / "1_cours.pdf").exists()


def test_envoi_refuse(tmp_path, monkeypatch):
    monkeypatch.setattr("app.DOSSIER_FICHIERS", tmp_path)
    demandes.clear()
    reponse = envoyer_fichier(app.test_client(), "virus.exe")
    assert reponse.status_code == 400
    assert len(demandes) == 0


def test_marquer_imprime(tmp_path, monkeypatch):
    monkeypatch.setattr("app.DOSSIER_FICHIERS", tmp_path)
    demandes.clear()
    client = app.test_client()
    envoyer_fichier(client, "cours.pdf")
    client.get("/imprime/1")
    assert demandes[0]["imprime"] is True
    assert "Imprimé" in client.get("/accueil").get_data(as_text=True)