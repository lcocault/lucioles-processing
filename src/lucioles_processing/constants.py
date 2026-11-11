"""Constantes partagées."""

# Couleurs OPF associées à chaque niveau de l'indicateur (niveau 0 = meilleur, 4 = pire)
OPF_COLORS = ["#71d357", "#c4dd67", "#ffd457", "#ffb35b", "#ff1f37"]

# Couleur des communes sans donnée
NO_DATA_COLOR = "#9e9e9e"

# Noms des colonnes des fichiers produits (GPKG, GeoJSON) pour le code, le nom et le département
ADMIN_DEPT_COLUMN = "code_insee_du_departement"
ADMIN_NAME_COLUMN = "nom_officiel"
ADMIN_CODE_COLUMN = "code_insee"
