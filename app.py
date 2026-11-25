"""ImprimRési : envoi de fichiers à imprimer pour une résidence étudiante."""
from pathlib import Path

from flask import Flask, redirect, render_template_string, request, url_for
from werkzeug.utils import secure_filename

app = Flask(__name__)
app.config["MAX_CONTENT_LENGTH"] = 10 * 1024 * 1024  # 10 Mo maximum
DOSSIER_FICHIERS = Path("fichiers")

EXTENSIONS_AUTORISEES = {"pdf", "docx", "jpg", "jpeg", "png"}
TARIFS = {"noir": 0.10, "couleur": 0.50}  # prix par page en euros

demandes = []  # liste des demandes d'impression (en mémoire)

STYLE = """
<meta name="viewport" content="width=device-width, initial-scale=1">
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Poppins:wght@400;600;700&display=swap"
      rel="stylesheet">
<style>
  :root { --bleu: #4f46e5; --violet: #7c3aed; --fond: #f4f5fb; --texte: #1f2937; }
  * { box-sizing: border-box; }
  body { font-family: "Poppins", Arial, sans-serif; background: var(--fond);
         color: var(--texte); margin: 0; }
  header { background: linear-gradient(135deg, var(--bleu), var(--violet));
           color: white; padding: 40px 20px 90px; text-align: center; }
  header h1 { margin: 0; font-size: 2.4em; }
  header p { margin: 8px 0 0; opacity: 0.9; }
  nav { position: absolute; top: 20px; right: 25px; }
  nav a { color: white; text-decoration: none; font-weight: 600;
          background: rgba(255, 255, 255, 0.2); padding: 8px 16px;
          border-radius: 20px; }
  nav a:hover { background: rgba(255, 255, 255, 0.35); }
  .carte { background: white; max-width: 650px; margin: -60px auto 40px;
           padding: 35px; border-radius: 18px;
           box-shadow: 0 15px 40px rgba(0, 0, 0, 0.08); }
  .large { max-width: 950px; }
  h2 { margin-top: 0; }
  form { display: grid; gap: 18px; }
  .ligne { display: grid; grid-template-columns: repeat(2, minmax(0, 1fr));
           gap: 15px; }
  label { font-weight: 600; font-size: 0.9em; display: grid; gap: 6px; }
  input, select { width: 100%; padding: 12px; border: 2px solid #e5e7eb;
                  border-radius: 10px; font-size: 1em; font-family: inherit; }
  input:focus, select:focus { outline: none; border-color: var(--bleu); }
  .depot { border: 2px dashed #c7d2fe; background: #eef2ff; border-radius: 14px;
           padding: 25px; text-align: center; cursor: pointer; }
  .depot input { display: none; }
  .depot .icone { font-size: 2.5em; }
  #nom-fichier { color: var(--bleu); font-weight: 600; }
  .prix { background: #f5f3ff; border-radius: 12px; padding: 15px;
          display: flex; justify-content: space-between; align-items: center; }
  .prix strong { font-size: 1.6em; color: var(--violet); }
  button { background: linear-gradient(135deg, var(--bleu), var(--violet));
           color: white; border: none; border-radius: 12px; padding: 15px;
           font-size: 1.1em; font-weight: 600; cursor: pointer;
           font-family: inherit; }
  button:hover { opacity: 0.9; }
  .message { background: #ecfdf5; color: #065f46; padding: 15px;
             border-radius: 12px; border-left: 5px solid #10b981; }
  .erreur { background: #fef2f2; color: #991b1b; padding: 15px;
            border-radius: 12px; border-left: 5px solid #ef4444; }
  .stats { display: grid; grid-template-columns: repeat(3, 1fr); gap: 15px;
           margin-bottom: 25px; }
  .stat { background: #f5f3ff; border-radius: 14px; padding: 18px;
          text-align: center; }
  .stat strong { display: block; font-size: 1.8em; color: var(--violet); }
  table { width: 100%; border-collapse: collapse; }
  th { text-align: left; color: #6b7280; font-size: 0.85em; padding: 10px; }
  td { padding: 12px 10px; border-top: 1px solid #f3f4f6; }
  .badge { padding: 5px 12px; border-radius: 20px; font-size: 0.85em;
           font-weight: 600; white-space: nowrap; }
  .attente { background: #fef3c7; color: #92400e; }
  .fait { background: #d1fae5; color: #065f46; }
  .action { color: var(--bleu); font-weight: 600; text-decoration: none; }
  .vide { text-align: center; color: #6b7280; padding: 30px; }
  footer { text-align: center; color: #9ca3af; font-size: 0.85em;
           padding-bottom: 30px; }
</style>
"""

PAGE_ENVOI = STYLE + """
<header>
  <nav><a href="{{ url_for('accueil_residence') }}">🏢 Espace accueil</a></nav>
  <h1>🖨️ ImprimRési</h1>
  <p>Pas d'imprimante ? Envoyez vos documents, récupérez-les à l'accueil.</p>
</header>
<div class="carte">
  <h2>Envoyer un document à imprimer</h2>
  {% if message %}<p class="message">✅ {{ message }}</p>{% endif %}
  {% if erreur %}<p class="erreur">⚠️ {{ erreur }}</p>{% endif %}
  <form method="post" enctype="multipart/form-data">
    <div class="ligne">
      <label>Nom et prénom
        <input name="nom" placeholder="Ex : Alice Martin" required></label>
      <label>Numéro de chambre
        <input name="chambre" placeholder="Ex : B204" required></label>
    </div>
    <label class="depot">
      <span class="icone">📄</span>
      <span id="nom-fichier">Cliquez pour choisir votre fichier</span>
      <small>PDF, Word, JPG ou PNG · 10 Mo maximum</small>
      <input type="file" name="fichier" id="fichier" required>
    </label>
    <div class="ligne">
      <label>Nombre de pages
        <input type="number" name="pages" id="pages" min="1" value="1"></label>
      <label>Nombre d'exemplaires
        <input type="number" name="copies" id="copies" min="1" value="1"></label>
    </div>
    <label>Type d'impression
      <select name="couleur" id="couleur">
        <option value="noir">⚫ Noir et blanc · 0,10 € / page</option>
        <option value="couleur">🌈 Couleur · 0,50 € / page</option>
      </select>
    </label>
    <div class="prix">
      <span>Prix estimé</span>
      <strong id="prix">0,10 €</strong>
    </div>
    <button type="submit">Envoyer à l'impression</button>
  </form>
</div>
<footer>ImprimRési · Projet DevOps</footer>
<script>
  const tarifs = { noir: 0.10, couleur: 0.50 };
  function majPrix() {
    const pages = Number(document.getElementById("pages").value) || 0;
    const copies = Number(document.getElementById("copies").value) || 0;
    const type = document.getElementById("couleur").value;
    const prix = (pages * copies * tarifs[type]).toFixed(2).replace(".", ",");
    document.getElementById("prix").textContent = prix + " €";
  }
  ["pages", "copies", "couleur"].forEach(
    (id) => document.getElementById(id).addEventListener("input", majPrix)
  );
  document.getElementById("fichier").addEventListener("change", (e) => {
    const nom = e.target.files[0] ? e.target.files[0].name : "";
    document.getElementById("nom-fichier").textContent =
      nom || "Cliquez pour choisir votre fichier";
  });
</script>
"""

PAGE_ACCUEIL = STYLE + """
<header>
  <nav><a href="{{ url_for('envoyer') }}">← Formulaire résident</a></nav>
  <h1>🏢 Espace accueil</h1>
  <p>Suivi des demandes d'impression de la résidence</p>
</header>
<div class="carte large">
  <div class="stats">
    <div class="stat"><strong>{{ demandes|length }}</strong>demandes</div>
    <div class="stat">
      <strong>{{ demandes|rejectattr("imprime")|list|length }}</strong>en attente
    </div>
    <div class="stat">
      <strong>{{ "%.2f"|format(demandes|sum(attribute="prix")) }} €</strong>
      à encaisser
    </div>
  </div>
  {% if demandes %}
  <table>
    <tr><th>N°</th><th>Résident</th><th>Chambre</th><th>Fichier</th>
        <th>Détail</th><th>Prix</th><th>Statut</th></tr>
    {% for d in demandes %}
    <tr>
      <td>#{{ d.numero }}</td>
      <td>{{ d.nom }}</td>
      <td>{{ d.chambre }}</td>
      <td>📄 {{ d.fichier }}</td>
      <td>{{ d.pages }} p. × {{ d.copies }}
        {% if d.couleur == "couleur" %}🌈{% else %}⚫{% endif %}</td>
      <td><strong>{{ "%.2f"|format(d.prix) }} €</strong></td>
      <td>
        {% if d.imprime %}<span class="badge fait">✅ Imprimé</span>
        {% else %}
        <span class="badge attente">⏳ En attente</span><br>
        <a class="action" href="{{ url_for('marquer_imprime', numero=d.numero) }}">
          Marquer imprimé</a>
        {% endif %}
      </td>
    </tr>
    {% endfor %}
  </table>
  {% else %}
  <p class="vide">📭 Aucune demande pour le moment.</p>
  {% endif %}
</div>
<footer>ImprimRési · Projet DevOps</footer>
"""


def extension_autorisee(nom_fichier):
    """Vérifie que le fichier a une extension acceptée."""
    if "." not in nom_fichier:
        return False
    return nom_fichier.rsplit(".", 1)[1].lower() in EXTENSIONS_AUTORISEES


def calculer_prix(pages, copies, couleur):
    """Calcule le prix d'une impression."""
    return round(pages * copies * TARIFS[couleur], 2)


@app.route("/", methods=["GET", "POST"])
def envoyer():
    if request.method == "GET":
        return render_template_string(PAGE_ENVOI)

    fichier = request.files.get("fichier")
    if not fichier or not extension_autorisee(fichier.filename):
        erreur = "Fichier refusé : formats acceptés PDF, Word, JPG, PNG."
        return render_template_string(PAGE_ENVOI, erreur=erreur), 400

    numero = len(demandes) + 1
    nom_fichier = f"{numero}_{secure_filename(fichier.filename)}"
    DOSSIER_FICHIERS.mkdir(exist_ok=True)
    fichier.save(DOSSIER_FICHIERS / nom_fichier)

    pages = int(request.form.get("pages", 1))
    copies = int(request.form.get("copies", 1))
    couleur = request.form.get("couleur", "noir")
    demande = {
        "numero": numero,
        "nom": request.form["nom"],
        "chambre": request.form["chambre"],
        "fichier": nom_fichier,
        "pages": pages,
        "copies": copies,
        "couleur": couleur,
        "prix": calculer_prix(pages, copies, couleur),
        "imprime": False,
    }
    demandes.append(demande)
    message = (
        f"Demande n°{numero} envoyée ! Prix : {demande['prix']:.2f} €. "
        "Vous serez prévenu(e) quand elle sera prête à l'accueil."
    )
    return render_template_string(PAGE_ENVOI, message=message)


@app.route("/accueil")
def accueil_residence():
    return render_template_string(PAGE_ACCUEIL, demandes=demandes)


@app.route("/imprime/<int:numero>")
def marquer_imprime(numero):
    for demande in demandes:
        if demande["numero"] == numero:
            demande["imprime"] = True
    return redirect(url_for("accueil_residence"))


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)