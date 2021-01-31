# vegetables_order

## Installation

1. Installer Python : le plus simple est d'installer la distribution [Anaconda](https://www.anaconda.com/distribution/). 
   C'est un peu gros mais ça permet d'avoir presque tous les modules nécessaires installés. Répondre aux différentes
   questions, en particulier sur le répertoire d'installation.
1. Démarrer un terminal (sur Mac, utiliser l'application `Terminal` qui se trouve dans le dossier `Applications)
   et exécuter la commande suivante pour vérifier que l'environnement Python est bien celui
installé à l'étape précédente (vérifier le répertoire qui doit être le même que celui entré lors de l'installation) :
   
   ```bash
   which python
   ```

1. Exécuter la commande suivante (répondre `Y` à toutes les questions) :

   ```bash
   conda install reportlab
   ```
   
1. Installer l'application de traitement du formulaire :

   ```bash
   curl  https://raw.githubusercontent.com/jouvin/vegetables_order/master/process_orders.py > process_orders.py
   chmod 755 process_orders.py
   ```

## Traitement du formulaire

Après avoir récupéré la liste des commandes sur Framaforms dans un fichier CSV qui sera sauvé dans le même répertoire
que `process_orders.py , il faut exécuter la commande suivante :

```bash
./process_orders.py --out commandes.pdf nom_du_fichier_csv
```

Si cela fonctionne correctement, cela doit produire un fichier commandes.pdf qui contient les commandes par jour de livraison
et par client, avec à la fin pour chaque produits la quantité à récolter (somme de toutes les commandes).