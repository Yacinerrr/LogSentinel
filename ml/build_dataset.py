import csv, collections

JEUX = {"openssh": "OpenSSH", "apache": "Apache", "openstack": "OpenStack",
        "windows": "Windows", "linux": "Linux"}

lignes = []
for nom, dossier in JEUX.items():
    etiquettes = {r["EventId"]: r["target_label"]
                 for r in csv.DictReader(open(f"data/labels/{nom}.csv", encoding="utf-8"))}
    brut = f"data/raw/{dossier}/{dossier}_2k.log_structured.csv"
    for r in csv.DictReader(open(brut, encoding="utf-8")):
        lignes.append((nom, r["Content"], etiquettes[r["EventId"]]))
for r in csv.DictReader(open("data/synthetic_logs.csv", encoding="utf-8")):
    lignes.append((r["source"], r["log_message"], r["target_label"]))
with open("data/labeled_logs.csv", "w", newline="", encoding="utf-8") as f:
    w = csv.writer(f, lineterminator="\n")
    w.writerow(["source", "log_message", "target_label"])
    w.writerows(lignes)

print(len(lignes), "lignes")
for lab, n in collections.Counter(l[2] for l in lignes).most_common():
    print(f"{n:6d}  {lab}")
