
from src.data.collecte import collecter
from src.data.pretraitement import pretraiter
from src.data.load_database import creer_base, charger


def main():

    print("1. Vérification de PostgreSQL...")
    creer_base()

    print("2. Collecte des données DVF + INSEE...")
    dvf, insee = collecter()

    print("3. Prétraitement et jointure DVF + INSEE...")
    dataset = pretraiter(dvf, insee)

    print(f"Dataset final : {dataset.shape}")

    print("4. Chargement dans PostgreSQL...")
    charger(dataset)

    print("Pipeline de données terminé avec succès !")


if __name__ == "__main__":
    main()
