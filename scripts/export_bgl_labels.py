
import csv
from pathlib import Path

SOURCE = Path("data/interim/bgl_critical_templates.csv")
OUTPUT = Path("data/labels/bgl.csv")

# Templates retenus provisoirement pour Critical Error.
# Les cas matériels nécessitant une confirmation d'impact restent exclus.
approved_templates = {
    "rts panic! - stopping execution",
    "kernel panic",
    "rts: kernel terminated for reason <*>",
    "Error: unable to mount filesystem",
}

OUTPUT.parent.mkdir(parents=True, exist_ok=True)

exported = 0

with SOURCE.open("r", encoding="utf-8-sig", newline="") as source:
    rows = csv.DictReader(source)

    with OUTPUT.open("w", encoding="utf-8-sig", newline="") as output:
        writer = csv.DictWriter(
            output,
            fieldnames=["EventTemplate", "Label"],
        )
        writer.writeheader()

        for row in rows:
            template = row["EventTemplate"]

            if template in approved_templates:
                writer.writerow({
                    "EventTemplate": template,
                    "Label": "Critical Error",
                })
                exported += 1

print(f"Templates exportés : {exported}")
print(f"Fichier créé : {OUTPUT}")
