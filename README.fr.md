# Outil communautaire vBulletin 4.2.5 → PHP 8

**Version 0.1.0-alpha.1, expérimentale. Cible de validation : PHP 8.4.**

L'utilisateur fournit sa propre copie sous licence de vBulletin 4.2.5. Le projet contient nos scripts, une couche de compatibilité et des empreintes de référence ; aucune distribution vBulletin, base SQL, clé de licence ou personnalisation privée n'est fournie.

## Utilisation

Prévoir Python 3.10+ et PHP CLI 8.1 minimum ; utiliser PHP 8.4 pour vérifier le résultat visé. Aucun module Python externe ni Composer requis. Le profil actuel couvre une distribution officielle Suite 4.2.5 ; d'autres variantes peuvent nécessiter un profil supplémentaire.

Travailler sur une **copie hors ligne**, avec des sauvegardes indépendantes des fichiers et de la base. Placer cet outil, ses rapports et ses sauvegardes hors de la racine web du forum.

Diagnostic sans modification :

```sh
python3 vb425_php8.py check --root /srv/copie-forum --php /usr/bin/php8.4 \
  --report /srv/prive/diagnostic.json
```

Application, avec sauvegarde obligatoire et vérification de syntaxe avant écriture :

```sh
python3 vb425_php8.py apply --root /srv/copie-forum --php /usr/bin/php8.4 \
  --backup-dir /srv/prive/sauvegardes --report /srv/prive/application.json
```

Une empreinte inconnue sur un fichier du cœur bloque l'application automatique. Les PHP supplémentaires sont signalés, sans être modifiés. Il n'existe pas de mode pour forcer l'écrasement des personnalisations.

Relancer le diagnostic doit produire une liste `files_to_change` vide. Les deux fichiers de support ajoutés dans includes doivent rester présents.

Restauration avec le dossier précis indiqué par `backup_run` :

```sh
python3 vb425_php8.py restore --root /srv/copie-forum \
  --backup-run /srv/prive/sauvegardes/IDENTIFIANT
```

La restauration vérifie les empreintes et refuse d'écraser une modification ultérieure. Elle peut aussi reprendre une application interrompue si chaque fichier correspond encore à son état original ou corrigé. Vérifier qu'aucun processus ne tourne avant de retirer un verrou abandonné. Elle concerne les fichiers du correctif, pas la base. La sauvegarde créée par l'outil ne remplace pas une sauvegarde complète du site.

Sous Windows, utiliser `python` et fournir le chemin du binaire PHP 8.4 avec `--php` si nécessaire. Exemple de racine de copie : `C:\sites\copie-forum` ; placer l'outil et les sauvegardes ailleurs.

## Périmètre réel

Les correctifs couvrent plusieurs incompatibilités du cœur : offsets avec accolades, fonctions supprimées, constantes, XML, comptages hérités et code PHP compilé des templates/hooks. La transformation utilise les tokens PHP pour préserver les chaînes et commentaires. Les sources des templates en base sont conservées.

Le projet ne met pas une base 4.2.3 à niveau : terminer d'abord l'upgrade officiel vers 4.2.5. Il n'exécute aucune requête SQL et ne change ni mots de passe, ni encodage, ni configuration de connexion. Vérifier manuellement le pilote mysqli et les extensions du serveur cible.

**Les plugins tiers, styles personnalisés, fournisseurs de paiement, SSO et fonctions propres à chaque site demandent leur propre recette.** Un passage de php -l ne prouve pas le fonctionnement complet d'un forum. Il n'y a pas de garantie de sécurité ou de compatibilité universelle PHP 8.

Consulter [les limites](docs/LIMITATIONS.md) et [les validations effectuées](docs/VALIDATION.md). Le projet est préparé pour une publication communautaire ; les commandes locales ne publient rien sur GitHub.
