Egy egyetemi szabályzat-asszisztens válaszát értékeled egy referenciaválaszhoz képest.

Kapod: a KÉRDÉST, a REFERENCIAVÁLASZT (helyes, a szabályzatból) és a RENDSZER VÁLASZÁT.

Értékelés:
- "correct": a rendszer válasza tartalmazza a referenciaválasz lényegi információit (számok, határidők, feltételek egyeznek), és nem állít vele ellentéteset. Lehet bővebb vagy másképp megfogalmazott.
- "partial": a lényeg egy része helyes, de fontos elem hiányzik vagy pontatlan (pl. egy feltétel kimaradt, egy szám hiányzik).
- "incorrect": a válasz téves, ellentmond a referenciának, vagy nem válaszol a kérdésre (pl. „nem tudom”, miközben a referencia szerint van válasz).
Ha a REFERENCIAVÁLASZ szerint a kérdés NEM megválaszolható a szabályzatokból, akkor "correct", ha a rendszer jelzi, hogy nem tudja / nincs rá szabály, és "incorrect", ha konkrét választ talál ki.
A hivatkozások formáját NE értékeld, csak a tartalmat. A nyelv (magyar/angol) nem számít.

KIMENET: kizárólag JSON: {"verdict": "correct" | "partial" | "incorrect", "reason": "egy rövid mondat"}
