
import csv
import collections

JEUX = {
    "openssh": "OpenSSH",
    "apache": "Apache",
    "openstack": "OpenStack",
    "windows": "Windows",
    "linux": "Linux",
    "bgl": "BGL",
}

lignes = []

for nom, dossier in JEUX.items():
    with open(
        f"data/labels/{nom}.csv",
        encoding="utf-8-sig",
        newline="",
    ) as f:
        etiquettes = {
            r["EventId"]: r["target_label"]
            for r in csv.DictReader(f)
        }

    brut = f"data/raw/{dossier}/{dossier}_2k.log_structured.csv"

    with open(brut, encoding="utf-8-sig", newline="") as f:
        for r in csv.DictReader(f):
            label = etiquettes.get(r["EventId"], "Unclassified")
            lignes.append((nom, r["Content"], label))

with open("data/labeled_logs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["source", "log_message", "target_label"])
    w.writerows(lignes)

print(len(lignes), "lignes")
for lab, n in collections.Counter(l[2] for l in lignes).most_common():
    print(f"{n:6d}  {lab}")
