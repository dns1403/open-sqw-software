# Mathematische Übergabe: Scattering Quantum Walks

**Ziel:** belastbare Grundlage für Architektur, Implementierung und Unit-Tests eines wissenschaftlichen Simulators für unitäre SQWs, Open Edge SQWs und induzierte Open Vertex SQWs.

**Primärquelle [J]:** Alain Joye, *Unitary and Open Scattering Quantum Walks on Graphs*, arXiv:2409.08428v2, 9. April 2026, 55 Seiten. Sämtliche Gleichungsnummern beziehen sich auf diese bereitgestellte Fassung. SHA-256 der geprüften Datei: `de3ccede8b943b57e87d1d89df1cba328a3011c87eabb4a67cb6aa8aa3dbb879`.

**Stand:** 4. November 2026. Rekonstruiert aus dem verfügbaren Gespräch, der bereitgestellten PDF und der früheren Zusammenfassung `RKHS Approach.txt`. Letztere ist keine unabhängige Fachquelle. Fehlende frühere Gesprächsteile werden nicht erfunden. Es wird keine Forschungsneuheit behauptet.

## Leseschlüssel und Beweisstatus

Jeder Ergebnisdatensatz enthält **A Aussage**, **B Voraussetzungen**, **C Beweis/Herleitung**, **D Quellenbezug** und **E Simulationsfolgen**. Die portable JSON-Datei enthält dieselben Datensätze und zusätzliche Algorithmenverträge.

- `PROVEN`: vollständige Herleitung im Dokument, gegebenenfalls unter ausdrücklich benannten klassischen Standardtheoremen.
- `PAPER_THEOREM`: direkt zitierter Satz aus dem Paper; längerer Originalbeweis nicht vollständig reproduziert.
- `CONDITIONAL`: nur unter den genau bezeichneten Zusatzannahmen oder der ausdrücklich gewählten Interpretation.
- `OPEN`: nicht bewiesen; keine Implementierungsoptimierung darauf gründen.

Herkunft `CHAT` bedeutet im verfügbaren Gespräch hergeleitet; `PAPER_SUPPLEMENT` bedeutet für die Simulatorübergabe ergänzte Quellenangabe; `AUDIT_NEW` kennzeichnet erst jetzt explizit hergeleitete Verstärkungen oder Korrekturen. Numerische Regressionstests sind **keine Beweise**.

## Inhaltsübersicht

0. Verbindliche Konventionen und Zeitachse
1. Unitärer SQW
2. Open Edge SQW: Instrument, Purifikation und exakte Markovreduktion
3. Edge-Walk: Stationarität, Konvergenz, Spektrum und Fluktuationen
4. Edge-Walk: Symmetrien, Lie-Gruppen, Zweizeitgesetze und Zeitumkehr
5. Induzierter Open Vertex SQW
6. RKHS, Momente, Transferoperatoren und Statistik
7. Explizite Referenzbeispiele
8. Simulationsalgorithmen und Komplexität
9. Getrennte neue Folgerungen
10. Fehlerregister, Grenzen und offene Fragen
11. Implementierungstabelle und Architekturprioritäten
12. Maschinenlesbare Spezifikation
13. Literaturregister

# 0. Verbindliche Konventionen

## 0.1 Standardvertrag `SIMPLE_STATIC`

Der Standardgraph ist ungerichtet, einfach, schleifenfrei, zusammenhängend und besitzt mindestens zwei Knoten. Er ist endlich oder abzählbar mit beschränkten Graden. Alle Streumatrizen sind zeitunabhängig und unitär.

\[
D=\{(x,y):x\sim y\},\qquad (x,y)\text{ bedeutet die Richtung }y\longrightarrow x.
\]

Der **erste Index ist das Ziel**, der zweite die Quelle. Für einen endlichen Graphen:
\[
m=|V|,\qquad d_x=|N(x)|,\qquad d=|D|=2|E|=\sum_xd_x.
\]

\[
\mathcal H_E=\ell^2(D),\quad
\mathcal H_x^I=\operatorname{span}\{|xy\rangle:y\sim x\},\quad
\mathcal H_x^O=\operatorname{span}\{|yx\rangle:y\sim x\}.
\]
\[
P_x^I=\sum_{y\sim x}Q_{xy},\qquad P_x^O=\sum_{y\sim x}Q_{yx},\qquad Q_{xy}=|xy\rangle\langle xy|.
\]

Jeder Knoten hat eine **fest gespeicherte geordnete Nachbarliste**. Die Zeile z und die Spalte y von S(x) bezeichnen den ausgehenden Port (z,x) beziehungsweise den eingehenden Port (x,y). Die Streuvorschrift lautet
\[
U_S|xy\rangle=\sum_{z\sim x}S_{zy}(x)|zx\rangle.
\]
Die Portreihenfolge ist Teil des Modells. Insbesondere selektiert eine DFT-Matrix bei uniformem Randvektor einen bestimmten geordneten Ausgangsport.

**Mehrfachkanten:** Das Beispiel §6.2 enthält ausdrücklich eine zusätzliche parallele Kante. Dafür sind Port-IDs (x,y,ℓ) nötig. Es gehört nicht unverändert zum einfachen Kernvertrag; die universelle Edge-Purifikation nach zwei Knotenergebnissen ist dort im Allgemeinen falsch. Siehe NEW-03 und das Fehlerregister.

## 0.2 Zufallszustand, Mittelwert, Gesetz und empirisches Maß

\[
\rho_n(\omega):\text{ konditionierter Zustand nach dem vollständigen Schritt},
\quad\bar\rho_n=\mathbb E\rho_n,
\quad\nu_n=\mathcal L(\rho_n),
\quad\widehat\nu_L=\frac1L\sum_{n=1}^L\delta_{\rho_n}.
\]

Diese vier Objekte müssen im API unterschieden werden. Ebenso ist die Born-Verteilung einer anschließenden Messung nicht generell das Gesetz des zuletzt gemessenen Labels.

- Edge: M ist **spaltenstochastisch**, \(q_{n+1}=Mq_n\).
- Vertex: P ist **zeilenstochastisch**, \(q_{n+1}=q_nP\).
- Gemeinsame Markovroutinen können die Zeilenkonvention \(T=M^{\mathsf T}\) beziehungsweise \(T=P\) verwenden, aber nur über einen expliziten Adapter.
- \(\|A\|_1=\operatorname{tr}\sqrt{A^*A}\), \(D_{\rm tr}(\rho,\tau)=\frac12\|\rho-\tau\|_1\).
- TV ist \(\sup_B|\mu(B)-\nu(B)|\), auf diskretem gemeinsamem Träger die halbe ℓ¹-Differenz.

Der konditionierte Dichtematrixprozess ist bei einem festen Instrument **schon ab Schritt0 Markov auf dem gesamten Zustandsraum**. Die besonderen Sätze „ab Schritt2/1“ besagen, dass er dann auf einer festen endlichen Familie reiner Zustände liegt und durch eine endliche klassische Kette repräsentiert werden kann.

## 0.3 Edge-Zeitachse: Messung vor U

\[
\rho_{n-1}\xrightarrow{X_n=x}
\widehat\rho_n=\frac{P_x^I\rho_{n-1}P_x^I}{\operatorname{tr}(P_x^I\rho_{n-1})}
\xrightarrow{U_S}\rho_n=U_S\widehat\rho_nU_S^*.
\]
Das Ergebnis X₁ wird aus ρ₀ gezogen, vor der ersten Streuung. Für n≥2 ist das klassische Gedächtnis \(E_n=(X_n,X_{n-1})\). Der nach Streuung vorliegende Zustand ist im Allgemeinen keine einzelne Kantenbasisbelegung, sondern \(U|E_n\rangle\).

## 0.4 Vertex-Zeitachse

X₁ hat Gesetz \(r_0(x)=\langle x|\rho_0|x\rangle\), danach wird \(\tau_{X_1}\) präpariert. Das Präparationslabel bei Schritt n hat Gesetz \(r_0P^{n-1}\), die Born-Verteilung einer folgenden Positionsmessung dagegen \(r_0P^n\).

Quellen: [J] §2, (2.1)–(2.7), §4.2, (4.26)–(4.38), §6, (6.18)–(6.25).

# 1. Unitärer Scattering Quantum Walk

### U-01 — Lokale unitäre Streuung und sparse Anwendung

**Status:** `PROVEN`; Herkunft `PAPER_SUPPLEMENT`.

**A. Aussage.** Mit \(F|xy\rangle=|yx\rangle\) und \(C=\bigoplus_xS(x)\) gilt
\[
U=FC,\qquad UP_x^I=P_x^OU,
\qquad\psi_{n+1}(z,x)=\sum_{y\sim x}S_{zy}(x)\psi_n(x,y).
\]
U ist unitär. Unter \(\rho\mapsto U\rho U^*\) bleiben Spur, Positivität, Rang, Eigenwerte, Reinheit und von-Neumann-Entropie erhalten.

**B. Voraussetzungen.** `SIMPLE_STATIC`; reine oder gemischte Anfangszustände; keine Zwischenmessung. Direkte Summen funktionieren auch auf dem abzählbaren Graphen.

**C. Beweis.** Die eingehenden Kantenblöcke bilden eine orthogonale direkte Summe. C ist die direkte Summe unitärer Matrizen. F ist eine involutive Basispermutation, also \(F=F^*=F^{-1}\). Daher ist FC unitär und bildet den Eingangsblock bei x auf den Ausgangsblock bei x ab. Die Zustandsinvarianten folgen aus unitärer Konjugation.

**D. Paper.** Definition2.1, Lemma2.3, (2.5)–(2.9), (3.9)–(3.12).

**E. Simulation.** Pro Knoten lokales Matvec, danach Arcflip; kein dichter globaler U notwendig. Aufwand \(O(\sum_xd_x^2)\) pro Ket, Speicher O(d). Für gemischte Zustände optional Faktor \(\rho=LL^*\) mit Update L→UL. Ein unitärer Walk darf nicht durch die Kette \(|U|^{\circ2}\) ersetzt werden: Diese verliert Interferenz. Tests T01,T02.

### U-02 — Unitäre Zeitmittel und fehlende universelle Relaxation

**Status:** `PROVEN`; Herkunft `CHAT/PAPER_SUPPLEMENT`.

**A. Aussage.** In endlicher Dimension mit \(U=\sum_\lambda\lambda E_\lambda\):
\[
\frac1L\sum_{n=0}^{L-1}U^n\rho U^{-n}\longrightarrow\sum_\lambda E_\lambda\rho E_\lambda.
\]
Der Fehler ist bei festem Spektrum O(1/L), mit eigenwertabstandsabhängiger Konstante. Für zwei Anfangszustände bleibt \(\|U^n\rho U^{-n}-U^n\tau U^{-n}\|_1=\|\rho-\tau\|_1\); alle Zustände können daher nicht gegen dasselbe Gleichgewicht relaxieren.

**B. Voraussetzungen.** Endlicher Graph für die angegebene Matrixformel. Im unendlichen Fall nur die gesonderten lokalen Spektral-/Zeitmittelaussagen des Papers anwenden.

**C. Beweis.** Zerlege ρ in Blöcke \(E_\lambda\rho E_\mu\). Ihr Zeitfaktor ist \((\lambda\bar\mu)^n\). Die Cesàrosumme bleibt1 für λ=μ und hat sonst Betrag höchstens \(2/(L|1-\lambda\bar\mu|)\). Die Spurnorm ist unitär invariant.

**D. Paper.** Lemma2.7, (2.16)–(2.19), Remark2.8; endliche Spektralrechnung.

**E. Simulation.** Bei degenerierten Eigenwerten ganze Spektralräume erhalten, nicht einzelne Eigenvektoren dephasieren. Nahe Entartungen führen zu großen Fehlerkonstanten. Stationäre unitäre Dichtematrizen erfüllen [U,ρ]=0. Test T03.

### U-03 — Sterne und verallgemeinerte Grover-Spektralabbildung

**Status:** `PAPER_THEOREM`; Herkunft `PAPER_SUPPLEMENT`.

**A. Aussage.** Für einen Stern mit b Blättern:
\[
U=\begin{pmatrix}0&D_\theta\\S&0\end{pmatrix},\qquad
U^{2n}=\operatorname{diag}((D_\theta S)^n,(SD_\theta)^n),
\quad\sigma(U)=\{\pm\sqrt\lambda:\lambda\in\sigma(D_\theta S)\}.
\]
Für \(S_\alpha(x)=|\omega(x)\rangle\langle\omega(x)|+e^{i\alpha}(I-|\omega(x)\rangle\langle\omega(x)|)\), normiertes ω und α≠0, definiere \(R=\sum_x|x\rangle\langle\omega(x)|\), \(T_\omega=RFR^*\). Dann
\[
(T_\omega)_{xy}=\overline{\omega_y(x)}\omega_x(y),\quad
\varphi_\alpha(\lambda)=\frac{\lambda^2-e^{i\alpha}}{\lambda(1-e^{i\alpha})}.
\]
Abseits der im Paper separat behandelten Ausnahmeigenwerte wird das U-Spektrum auf Tω abgebildet. Für \(\mu\in(-1,1)\) entstehen zwei Lösungen von \(\lambda^2-\mu(1-e^{i\alpha})\lambda-e^{i\alpha}=0\). Bei α=π lautet die innere Relation λ+λ⁻¹=2μ. Uniformes reelles ω ergibt die normierte Adjazenzmatrix.

**B. Voraussetzungen.** Exakte lokale Groverform beziehungsweise Sternstruktur; feste Basisreihenfolge. Ausnahmeigenwerte ±e^{iα}, Randwerte μ=±1 und α=0 nicht unbesehen in die innere Formel einsetzen.

**C. Beweis.** Sternformeln folgen durch Blockmultiplikation und Ähnlichkeit von DθS und SDθ. Die Tω-Koordinaten folgen direkt aus RFR*. Der vollständige Spektralabbildungsbeweis mit Ausnahmeigenräumen wird nicht hier erneut geführt; dafür gelten die zitierten Theoreme. Dies ist ausdrücklich keine als eigener vollständiger Chatbeweis rekonstruierte Aussage.

**D. Paper.** §3.3, Lemma3.6; §3.4, Theoreme3.9/3.11, Proposition3.13, (3.86)–(3.98), Appendix A.

**E. Simulation.** Analytische Testfixtures und optionale Dimensionsreduktion. Ausnahmeeigenräume und Vielfachheiten gesondert erfassen. Coined-QW-Adapter brauchen explizite Port-/Shift-Konventionen. Test T04.

# 2. Open Edge SQW: Instrument und Trajektorien

### E-01 — Krausoperatoren, Kanal und Diag

**Status:** `PROVEN`; Herkunft `CHAT/PAPER`.

**A. Aussage.**
\[
K(x)=UP_x^I=P_x^OU,\quad K(x)^*K(x)=P_x^I,\quad K(x)K(x)^*=P_x^O,
\]
\[
\Phi(A)=\sum_xK(x)AK(x)^*=U\mathcal D^I(A)U^*=\mathcal D^O(UAU^*),
\quad\mathcal D^\#(A)=\sum_xP_x^\#AP_x^\#.
\]
\[
\mathcal D^I\mathcal D^O=\mathcal D^O\mathcal D^I=\operatorname{Diag},\qquad
\operatorname{Diag}(A)=\sum_eQ_eAQ_e.
\]
Ergebniswahrscheinlichkeit und bedingtes Update sind \(p_x=\operatorname{tr}(P_x^I\rho)\) und \(K(x)\rho K(x)^*/p_x\) bei pₓ>0.

**B. Voraussetzungen.** `SIMPLE_STATIC`; beliebiger positiver Spur-eins-Anfangsoperator; vollständige Beobachtung des vorgegebenen Knoteninstruments.

**C. Beweis.** Aus Intertwining und Unitarität folgen die Krausidentitäten; Summation ergibt \(\sum K^*K=\sum KK^*=I\), also CPTP und in endlicher Dimension unital. Die beiden Pinchings sind HS-Projektionen. Ihr Produkt verwendet \(P_x^IP_y^O=Q_{xy}\) für Nachbarn und0 sonst. Mittelung über die normierten Zweige liefert Φ.

**D. Paper.** Lemma4.1, Definition4.2, Proposition4.3, (4.10)–(4.18), sowie (2.3)/(2.7).

**E. Simulation.** Dichtes Oracle und blockweise Implementation vergleichen. Nur die Eingangsblöcke \(P_x^I\rho P_x^I\) sind im nächsten Schritt relevant; innerhalb eines Blocks vorhandene Kohärenzen nicht entfernen. Nullzweige nicht normieren. Tests T05,T06.

### E-02 — Exakte Purifikation nach höchstens zwei Schritten

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für x∼y:
\[
K(x)K(y)=UP_x^IP_y^OU=UQ_{xy}U.
\]
Mit \(\eta_{xy}=U|xy\rangle\), \(\sigma_{xy}=|\eta_{xy}\rangle\langle\eta_{xy}|\) gilt
\[
K(x)K(y)\rho K(y)^*K(x)^*=
\langle xy|U\rho U^*|xy\rangle\,\sigma_{xy}.
\]
Somit für jedes zulässige Messpräfix und n≥2:
\[
\boxed{\rho_n=\sigma_{X_nX_{n-1}}.}
\]
Vor der letzten Streuung ist der Zustand Q, nachher \(\eta_{xy}=\sum_zS_{zy}(x)|zx\rangle\), im Allgemeinen eine kohärente Superposition.

**B. Voraussetzungen.** Einfacher schleifenfreier Graph, beliebige unitäre Coins, reiner **oder gemischter** Input. Keine Nichtnullannahme an Coin-Einträge. Endliche und abzählbare Graphen. Normierung nur für positive Wahrscheinlichkeiten endlicher Präfixe.

**C. Beweis.** Für Rang-eins-Q gilt \(QAQ=\langle e|A|e\rangle Q\). Einsetzen in \(UQU\rho U^*QU^*\) ergibt die Formel. Bei längeren Produkten \(W_n=K(x_n)\cdots K(x_1)\) schreibt man
\[
W_n=U|x_nx_{n-1}\rangle\langle x_nx_{n-1}|U W_{n-2}.
\]
Das Bild des unnormierten Zustands ist daher höchstens die Gerade \(\mathbb C\eta_{x_nx_{n-1}}\). Bei positiver Spur ist es genau diese Gerade und Normierung ergibt σ. Diese Argumentation beweist die Aussage direkt ohne Induktionslücke.

**D. Paper.** Folgerung aus (2.3), (2.7), §4.2; nicht bereits die bloße Aussage von Korollar4.5. Allgemeiner Purifikationsrahmen [PUR], [BFPP].

**E. Simulation.** Ab Schritt2 eine Arc-ID statt Dichtematrix/Ket pro Trajektorie. Rekonstruktion benötigt eine lokale S-Spalte. Ein reiner Input bleibt bereits ab dem ersten beobachteten Schritt rein; ein gemischter muss das nicht: bei ρ₀=I/d ist \(\rho_1(x)=P_x^O/d_x\). Ketgleichheiten sind nur bis auf globale Phase gemeint, Projektorgleichheiten exakt. Unbeobachtete Ergebnisse oder parallele Kanten verletzen Voraussetzungen. Tests T06,T07,T08,T24.

### E-03 — Markovmatrix, Initialisierung und Pfadwahrscheinlichkeiten

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.**
\[
K(z)\eta_{xy}=S_{zy}(x)\eta_{zx},\quad
M_{(zx),(xy)}=|S_{zy}(x)|^2,
\]
alle anderen Übergänge sind0. M ist bistochastisch. Die reduzierte Kette startet bei Schritt2 mit
\[
q_2(x,y)=\Pr(X_1=y,X_2=x)
=\langle xy|U\rho_0U^*|xy\rangle
=\langle xy|\Phi(\rho_0)|xy\rangle.
\]
Für den lokalen Eingangsblock \(A_y=(\langle yu|\rho_0|yv\rangle)_{u,v\sim y}\):
\[
q_2(x,y)=(S(y)A_yS(y)^*)_{x,x}.
\]
Für n≥2:
\[
\Pr(x_1,\ldots,x_n)=q_2(x_2,x_1)
\prod_{j=2}^{n-1}|S_{x_{j+1},x_{j-1}}(x_j)|^2.
\]

**B. Voraussetzungen.** E-02; statische Coins. Endliche Kette nur bei endlichem D, sonst abzählbare Kette.

**C. Beweis.** Projektion von \(U|xy\rangle\) auf den nächsten Eingangsblock z selektiert genau \(S_{zy}(x)|zx\rangle\). Die nächste Streuung ergibt die angegebene Krauswirkung und quadrierte Norm. Für q₂ nimmt man die Spur in E-02. Der Vektor \(U^*|xy\rangle\) liegt vollständig im Eingangsblock bei y, was die lokale Formel und die Gleichheit mit der Diagonale von Φρ₀ beweist. Unitarität liefert sämtliche Zeilen- und Spaltensummen1. Die Pfadformel folgt aus der Kettenregel.

**D. Paper.** Lemma5.3, (5.12)–(5.14), Remark5.4 und §4.2. M ist exakt die Matrix von \(\Phi^{\mathrm{Diag}}\), nicht eine neu angenäherte Markovmatrix.

**E. Simulation.** Speicherzustand (x,y); nächsten z aus Spalte y von \(|S(x)|^2\) ziehen, dann (z,x). X allein ist im Allgemeinen zweiter Ordnung, ab dem purifizierten Stadium bei flachen Coins einfacher Nachbar-Random-Walk. Für q₂ reichen lokale ρ₀-Blöcke, **nicht** bloß diagρ₀. Ein einmal gezogener Arc (x,y) aus q₂ liefert exakt beide ersten Ergebnisse X₁=y, X₂=x. Tests T07,T08,T09,T10.

### E-04 — Erreichbare Zustände und endliches Filtergedächtnis

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** \(\mathcal S_U=\{\sigma_e:e\in D\}\) ist absorbierend und orthogonal:
\(\operatorname{tr}(\sigma_e\sigma_f)=\delta_{ef}\). Jeder Atomzustand ist mit geeignetem Input erreichbar, etwa \(\rho_0=U^*Q_eU\) liefert q₂=δₑ. Für einen festgehaltenen Input ist die tatsächlich erreichbare Menge durch die von supp(q₂) im positiven M-Träger erreichbaren Arcs gegeben. Zwei verschiedene Priors mit demselben unter beiden kompatiblen Messpräfix liefern ab Schritt2 denselben bedingten Zustand.

**B. Voraussetzungen.** E-02; zur Filtervergleichsaussage müssen die benutzten Präfixe unter beiden Priors positive Wahrscheinlichkeit besitzen.

**C. Beweis.** Orthogonalität folgt aus U*U=I; das Inputbeispiel aus der q₂-Formel. Erreichbarkeit ist die übliche Markoverreichbarkeit. Der letzte-Zweierproduktbeweis zeigt, dass der normierte Zustand keine weitere Priorinformation enthält.

**D. Paper.** Modellspezifische Folgerung aus §4.2/§5 und E-02/E-03; allgemeine Einordnung [PUR], [BFPP].

**E. Simulation.** Exakte Beschränkung auf erreichbare Arcs möglich. „Alle möglichen Atome“ nicht mit „alle für diesen Input erreichbaren Atome“ verwechseln. Zwei Knoten-IDs sind ausreichendes Gedächtnis, nicht in jedem degenerierten Modell nachgewiesen minimal. Ein individueller unendlicher Pfad darf Wahrscheinlichkeit0 haben; es geht um seine zulässigen endlichen Präfixe. Tests T08,T09.

### E-05 — Mittelwerte, Born-Verteilungen und Observable ohne Dichtematrix

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Setze \(\mathcal B_U(q)=U\operatorname{diag}(q)U^*=\sum_eq_e\sigma_e\). Für n≥2:
\[
q_n=M^{n-2}q_2,\quad\nu_n=\sum_eq_n(e)\delta_{\sigma_e},\quad
\bar\rho_n=\Phi^n(\rho_0)=\mathcal B_U(q_n),\quad
\Phi\mathcal B_U=\mathcal B_UM.
\]
\[
\operatorname{diag}\bar\rho_n=Mq_n=q_{n+1},\qquad
\Pr(X_n=x)=\sum_yq_n(x,y).
\]
Für jede beschränkte Observable A und jede Funktion f auf den Atomen:
\[
\mathbb E\operatorname{tr}(A\rho_n)=\sum_eq_n(e)\langle\eta_e|A|\eta_e\rangle,
\quad\mathbb Ef(\rho_n)=\sum_eq_n(e)f(\sigma_e).
\]
Letzteres ist im Allgemeinen nicht f(\(\bar\rho_n\)).

**B. Voraussetzungen.** E-03, n≥2; abzählbar q∈ℓ¹ und beschränkte Observable. Für den Schritt1 gesondert E-01 verwenden.

**C. Beweis.** Aus dem Gesetz folgt der Mittelwert; Proposition4.8 identifiziert ihn mit Φⁿρ₀. Die Diagonale eines σₑ ist die e-te Spalte von M. Die Krauswirkung E-03 liefert das Intertwining. Diagonales A erfüllt Φ(A)=UAU*, und q₂ entspricht DiagΦρ₀; damit ergibt sich
\[
\Phi^n=\Phi\circ(\Phi^{\rm Diag})^{n-2}\circ\operatorname{Diag}\circ\Phi,
\]
also Korollar4.5.

**D. Paper.** Korollar4.5 (4.19), Proposition4.8 (4.38), Messzeitpunkte (4.23)–(4.24).

**E. Simulation.** Gemittelte Evolution als d reelle Gewichte. Physikalische Dichtematrix bei Bedarf als Ausgangsblöcke \(S(x)\operatorname{diag}(q_n(x,\cdot))S(x)^*\) rekonstruieren. diag(q) ist lediglich eine Darstellung in der U-rotierten Basis, nicht die physikalische ρ. Feste Observable atomweise vorrechnen. Ihre analytische Auswertung darf nicht mit einer zusätzlichen realen Messung verwechselt werden; letztere ändert das Instrument. Tests T09,T10,T11.

# 3. Edge-Walk: Invarianz, Konvergenz, Spektrum und Fluktuationen

### E-06 — Alle stationären Zustände und invarianten Maße

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** In endlicher Dimension bestehen affine Bijektionen
\[
M\pi=\pi\quad\longleftrightarrow\quad
\nu_\pi=\sum_e\pi_e\delta_{\sigma_e}\text{ invariant}
\quad\longleftrightarrow\quad\rho_\pi=\mathcal B_U(\pi)\text{ stationär}.
\]
Jede endliche bistochastische Kette zerfällt in abgeschlossene irreduzible Klassen Cⱼ ohne transiente Zustände. Alle stationären Verteilungen sind
\[
\pi=\sum_jw_j\frac{\mathbf1_{C_j}}{|C_j|},\quad w_j\ge0,\quad\sum_jw_j=1.
\]
Insbesondere sind \(u=\mathbf1/d\), \(\nu_U=d^{-1}\sum_e\delta_{\sigma_e}\) und I/d stets stationär. Bei Irreduzibilität sind sie eindeutig.

**B. Voraussetzungen.** Endlicher `SIMPLE_STATIC`-Graph, beliebige unitäre Coins. Eindeutigkeit benötigt Irreduzibilität, Existenz des kanonischen Maßes nicht.

**C. Beweis.** Jeder Zustand erreicht nach zwei Schritten die atomare Familie; ein invariantes Maß muss daher darauf getragen sein. Dort wirkt M. Jeder feste Dichteoperator erfüllt ρ=Φ²ρ und liegt deshalb im Bild von \(\mathcal B_U\). Diese ist injektiv, also folgt Mπ=π. Die positive uniforme stationäre Verteilung schließt transiente Zustände einer endlichen Kette aus, weil diese in jedem stationären Maß Gewicht0 haben. Auf jeder abgeschlossenen Klasse ist die Einschränkung bistochastisch und ihre eindeutige stationäre Verteilung uniform [MC].

**D. Paper.** Lemma5.3, Perron–Frobenius-Aussagen nach (5.14), Korollar5.7 für hinreichend irreduziblen Fall; die Maßkorrespondenz folgt aus der Trajektorienreduktion.

**E. Simulation.** SCC-Zerlegung statt willkürlicher Eigenvektorwahl bei mehrfacher Eigenvalue1. Klassenwahlgewichte eines Inputs sind \(\sum_{e\in C_j}q_2(e)\). Das uniforme kanonische Maß ist bei Reduzibilität nur eines von vielen. Tests T12,T13.

### E-07 — Gesetzes-, empirische und Zustandskonvergenz unterscheiden

**Status:** `PROVEN`; Herkunft `CHAT/PAPER`.

**A. Aussage.** Für gemeinsame orthogonale Atome:
\[
\|\mathcal B_U(q)-\mathcal B_U(p)\|_1=\|q-p\|_1=2\|\nu_q-\nu_p\|_{\rm TV},
\quad\|\mathcal B_U(q)-\mathcal B_U(p)\|_{\rm HS}=\|q-p\|_2.
\]
Ist M irreduzibel und aperiodisch, konvergiert νₙ exponentiell gegen νᵤ. Bei bloßer Irreduzibilität gilt auch periodisch fast sicher
\[
\frac1L\sum_{n=2}^{L+1}\delta_{\rho_n}\to\nu_U\quad\text{in TV},\qquad
\frac1L\sum_{n=2}^{L+1}\rho_n\to I/d\quad\text{in Spurnorm}.
\]
Das Cesàromittel der gemittelten Dynamik erfüllt bei endlicher Irreduzibilität auch im periodischen Fall
\[
\frac1L\sum_{n=0}^{L-1}\Phi^n(\rho_0)=I/d+O(L^{-1}).
\]
Dies ist eine Aussage über gemittelte Zustände, nicht über die zufälligen Fehler eines empirischen Pfadmittels. Die beschränkten geometrischen Summen der peripheren Nicht-1-Eigenwerte und die summierbaren inneren Spektralmoden begründen die Rate.

Der momentane Zustand konvergiert dagegen nicht:
\[
\|\rho_{n+1}-\rho_n\|_1=2,\qquad
\|\rho_n-I/d\|_1=2(1-1/d),\quad n\ge2.
\]
Wenn sämtliche lokalen Streumatrixeinträge ungleich0 sind, ist M irreduzibel, bei einem ungeraden Zyklus aperiodisch, andernfalls von Periode2. Mit strukturellen Nullen sind andere Klassen und Perioden möglich.

**B. Voraussetzungen.** Endliche Kette. Normidentitäten benötigen keine Irreduzibilität. Die erste Pfadnormidentität benötigt Schleifenfreiheit; bei Schleifen könnte derselbe Arc aufeinanderfolgen.

**C. Beweis.** In der orthonormalen Basis ηₑ sind die Differenzeigenwerte qₑ−pₑ. Der starke endliche Markov-Ergodensatz liefert alle empirischen Häufigkeiten gleichzeitig; auf endlichem Träger ist das TV-Konvergenz. Perron–Frobenius liefert bei Aperiodizität exponentielle Relaxation. Aufeinanderfolgende Arcs (x,y) und (z,x) sind wegen x≠y verschieden. Ihre Projektoren sind orthogonal, die Differenz besitzt Eigenwerte ±1. Ein reiner Projektor minus I/d hat Eigenwerte 1−1/d und −1/d mit Vielfachheit d−1.

**D. Paper.** Proposition5.5, Korollar5.7, (5.15)–(5.18). Der TV-Satz ist eine Folgerung aus dem dortigen Mittelwertsatz **plus** E-02. Pfadweiser Hintergrund [KM], allgemeine invariant-measure-Theorie [BFPP].

**E. Simulation.** Für Fehlerkontrolle bei n≥2 kann exakt zwischen Kanalspurnorm und Zustandsgesetz-TV umgerechnet werden. Empirische Knotenergebnisfrequenzen sind dₓ/d. Irreduzibilität/Periode am positiven M-Träger prüfen. SLEM \(r_*<1\) beschreibt die exponentielle Wurzelrate; wegen Jordanblöcken ist nicht immer O(\(r_*^n\)) ohne Polynomfaktor korrekt. Sicher ist O(\(r'^n\)) für jedes r′>r*. Tests T12,T13,T14.

### E-08 — Spektrum, Nullmoden, Entanglement-breaking und Produkt-Purifikation

**Status:** `PROVEN`; Herkunft `CHAT/PAPER`.

**A. Aussage.** In endlicher Dimension:
\[
\Phi^\dagger\Phi=\mathcal D^I,\quad
\operatorname{rank}\Phi=\sum_xd_x^2,\quad
\dim\ker\Phi=d^2-\sum_xd_x^2,
\quad\sigma(\Phi)\setminus\{0\}=\sigma(M)\setminus\{0\}.
\]
Eigenvektoren Mq=λq liefern Eigenoperatoren \(\mathcal B_U(q)\). Bei einem Grad≥2 ist Φ nicht diagonalisierbar; periphere Eigenwerte sind semisimpel. Der EB-Index ist1, wenn alle Grade1 sind, sonst2.

Es existiert kein zweidimensionales E, auf dem alle endlichen Krausprodukte skalierte Isometrien sind. Schon die Produkte der Länge2 schließen dies aus.

**B. Voraussetzungen.** Endliche Dimension für Rang und Spektralvielfachheiten. Der Rang-eins-Produktbeweis selbst gilt abzählbar. \(\dagger\) ist der Hilbert–Schmidt-Superoperatoradjungierte.

**C. Beweis.** Aus Φ=Adᵤ DI folgt Φ†Φ=DI und dessen Rang ist die Summe der Blockquadrate. Nichtverschwindende Spektren und periphere Aussagen folgen aus Theorem5.1/Remark5.2 und E-05. Nondiagonalisierbarkeit folgt auch aus rankΦ>rankΦ²=d (NEW-02). Φ² hat durch E-02 eine Rang-eins-Krausdarstellung und ist damit EB [EB]. Ein mindestens zweidimensionaler Eingangsblock trägt jedoch einen mit einer Hilfsumgebung verschränkten Zustand, den DI unverändert lässt; die anschließende unitäre Konjugation erhält Verschränkung. Daher ist Φ selbst dann nicht EB.

Für die Produktbedingung würde \(P_EW^*WP_E=a_WP_E\) bei a>0 Rang2 haben, obwohl W ein Rang-eins-Zweierprodukt ist. Also müssten alle WPₑ=0 sein. Aber \(\sum_{x,y}(K(x)K(y))^*K(x)K(y)=I\); Kompression auf E ist ein Widerspruch.

**D. Paper.** Theorem5.1, Remark5.2. Allgemeine EB-Charakterisierung [EB], Indexbegriff [EBI], Purifikationsbedingungen [PUR]/[BFPP]. Der exakte Index1/2 ist eine Modellfolgerung.

**E. Simulation.** Nichtverschwindende Spektren über d×d-M statt d²×d²-Supermatrix berechnen. Keine Eigenbasis von Φ voraussetzen. Dichte Supermatrix nur als kleines Oracle. Schur-/Krylovverfahren sind stabiler als numerische Jordanzerlegung. Tests T15,T16.

### E-09 — Poisson-Gleichung und zentraler Grenzwertsatz

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für reelles f auf den Atomen setze \(g(e)=f(\sigma_e)-\nu_U(f)\). Löse
\[
(I-M^{\mathsf T})h=g,\qquad\sum_eh(e)=0.
\]
Dann bei endlicher Irreduzibilität
\[
\sqrt L\left[\frac1L\sum_{n=2}^{L+1}f(\rho_n)-\nu_U(f)\right]
\Rightarrow\mathcal N(0,s_f^2),\quad
s_f^2=\frac1d\sum_e[h(e)^2-(M^{\mathsf T}h(e))^2].
\]
Für eine allgemeine Zeilenkette T mit π ist der entsprechende Solve \((I-T+\mathbf1\pi)h=f-\pi f\), Varianz \(\pi[h^2-(Th)^2]\).

**B. Voraussetzungen.** Endliche irreduzible Kette; Aperiodizität nicht erforderlich, beliebiger Initialzustand, endlicher Warmstart. Varianz darf0 sein.

**C. Beweis.** Auf zentrierten Funktionen ist I−T invertierbar. Es gilt
\[
\sum_{k=0}^{L-1}g(E_k)=\sum_{k=0}^{L-1}[h(E_{k+1})-(Th)(E_k)]+h(E_0)-h(E_L).
\]
Die Summe ist ein Martingal mit beschränkten Inkrementen. Ihre mittlere bedingte Varianz konvergiert nach dem Ergodensatz zu \(\pi[Th^2-(Th)^2]=\pi[h^2-(Th)^2]\). Beschränktheit liefert Lindeberg; der Martingal-CLT und der O(1)-Randterm beweisen die Aussage. Dies verwendet einen Standard-CLT, nicht bloß numerische Plausibilität.

**D. Paper/Literatur.** Kein eigener Satz in [J]; allgemeiner Quantentrajektorienrahmen und Methode [BFP], endliche Markov-Spezialisierung.

**E. Simulation.** Korrelationskorrigierte Standardfehler durch Poisson-Solve statt i.i.d.-Formel. O(1/L) beim Kanal-Cesàromittel ist keine Pfadfehlerschranke; typische Fluktuation ist O(1/√L). Test T17.

### E-10 — Exakter empirischer RKHS-Fehler und Kemeny-Konstante

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für \(k_r(\rho,\tau)=(\operatorname{tr}\rho\tau)^r\), r≥1, und stationäre L Schritte:
\[
\mathbb E\operatorname{MMD}_{k_r}^2(\widehat\nu_L,\nu_U)
=\frac{1-1/d}{L}+\frac2{dL^2}\sum_{t=1}^{L-1}(L-t)(\operatorname{tr}M^t-1).
\]
Bei Irreduzibilität gilt, auch periodisch,
\[
\mathbb E\operatorname{MMD}_{k_r}^2=\frac{\mathcal V(M)}L+O(L^{-2}),\quad
\mathcal V(M)=\frac1d\sum_{j=2}^d\frac{1-|\lambda_j|^2}{|1-\lambda_j|^2}
=\frac{2\mathcal K(M)-(d-1)}d,
\quad\mathcal K(M)=\sum_{j=2}^d\frac1{1-\lambda_j}.
\]
Eigenwerte werden algebraisch gezählt. \(\mathcal V=0\) genau bei einer deterministischen zyklischen Permutation.

**B. Voraussetzungen.** Endlicher Kantenwalk; **stationärer Start** für die exakte finite-L-Formel. Irreduzibel für die asymptotische Variante mit nur einer Eigenvalue1.

**C. Beweis.** Die Features auf den Atomen sind orthonormal, daher ist die zentrierte stationäre Autokorrelation \(c_t=(\operatorname{tr}M^t-1)/d\). Quadrieren des empirischen Featuresummanden ergibt die erste Formel. Benutze
\[
\sum_{t=1}^{L-1}(L-t)\lambda^t=\frac{L\lambda}{1-\lambda}+\frac{\lambda^{L+1}-\lambda}{(1-\lambda)^2}
\]
und \(\operatorname{tr}M^t=\sum_j\lambda_j^t\). Konjugierte Paare liefern den reellen nichtnegativen Ausdruck, keine Diagonalisierbarkeit nötig. Bei V=0 liegen alle Eigenwerte auf dem Einheitskreis. Alle Singulärwerte sind≤1, aber ihr Produkt ist dann |det M|=1; alle sind1. Eine nichtnegative orthogonale stochastische Matrix ist eine Permutation, irreduzibel also ein einziger Zyklus.

**D. Literatur.** Chatfolgerung; Fundamentalmatrix/Kemeny-Hintergrund [DOYLE].

**E. Simulation.** Analytische Monte-Carlo-Fehlerkurven. Nicht einfach auf nichtstationäre Anfangsverteilungen übertragen. Die einzelne Observable hängt zusätzlich von Eigenrichtungen ab; diese Gesamtfehlersumme nur von Eigenwerten. Test T18.

### E-11 — Nichtkontraktion in einem Schritt, strikte Zweischritt-Mischung und flache Coins

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Setze \(B=\bigoplus_x|S(x)|^{\circ2}\), \(M=FB\), \(\Pi=\mathbf1\mathbf1^{\mathsf T}/d\). Stets gilt \(\|M-\Pi\|_{2\to2}=1\). Sind alle lokalen Einträge ungleich0 und der Graph nichtbipartit, dann
\[
c_2=\|M^2-\Pi\|_{2\to2}<1,\qquad
\|M^nq-u\|_2\le c_2^{\lfloor n/2\rfloor}\|q-u\|_2.
\]
Bei flachen Coins \(|S_{zy}(x)|^2=1/d_x\) definiere
\[
J|x\rangle=\frac1{\sqrt{d_x}}\sum_{y\sim x}|xy\rangle,\quad
A_{\rm norm}=J^*FJ,
\quad(A_{\rm norm})_{xy}=\frac{\mathbf1_{x\sim y}}{\sqrt{d_xd_y}}.
\]
Dann \(M=FJJ^*\) und für n≥1
\[
M^n=FJ A_{\rm norm}^{n-1}J^*,\qquad
\|M^n-\Pi\|_{2\to2}=\beta^{n-1},\quad\beta=\max_{j\ge2}|\mu_j(A_{\rm norm})|.
\]

**B. Voraussetzungen.** Endlicher einfacher zusammenhängender Graph. Strikte Kontraktion nur unter genannten zusätzlichen Positivitäts-/Nichtbipartitheitsannahmen. Flache Formeln nur bei uniformen lokalen Betragsquadraten.

**C. Beweis.** Bistochastizität liefert ℓ²-Kontraktion via Jensen. Ein zentrierter blockkonstanter Vektor \(a_{xy}=c_x\), \(\sum_xd_xc_x=0\), erfüllt Ba=a und Ma=Fa, also keine strikte Ein-Schritt-Kontraktion. Bei positiven Bₓ ist Gleichheit in Jensen nur blockkonstant möglich. Normerhaltung über zwei Schritte verlangt sowohl a als auch Fa blockkonstant; dann sind die cₓ entlang gerader Wege gleich. Nichtbipartite Zusammenhangsgraphen verbinden so alle Knoten, weshalb im zentrierten Raum nur0 bleibt. Endliche Kompaktheit gibt die strikte Normschranke. Bei flachen Coins ist B=JJ*, die Potenzformel folgt durch Multiplikation. Für \(w_x=\sqrt{d_x/d}\) gilt \(Jw=FJw=\mathbf1/\sqrt d\). Die äußeren Isometrien erhalten die Operatornorm der zentrierten normierten Adjazenzpotenz.

**D. Paper.** Aus (3.9)–(3.12), (5.13)–(5.14) hergeleitet; diese genauen Normformeln sind zusätzliche Chatfolgerungen.

**E. Simulation.** Keine Konvergenzentscheidung allein anhand des größten Singulärwerts. Flache Coins ermöglichen eine m-dimensionale Graphreduktion. Bei bipartitem Graph β=1. Fourier-Coins sind flach; Grover-Coins im Allgemeinen nicht. Tests T19,T20.

### E-12 — Entropie, Spektralreduktion und elektrische Widerstände

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Bei flacher Streuung:
\[
\det(\lambda I_d-M)=\lambda^{d-m}\det(\lambda I_m-A_{\rm norm}),\quad
\mathcal V(M)=\frac{d-2m+1+2\sum_{j=2}^m(1-\mu_j)^{-1}}d.
\]
Ist G zusätzlich k-regulär:
\[
\mathcal V(M)=1-\frac2k+\frac1{km}+\frac{2\operatorname{Kf}(G)}{m^2}.
\]
Stationäre Entropierate:
\[
h_U=-\frac1d\sum_x\sum_{y,z\sim x}|S_{zy}(x)|^2\log|S_{zy}(x)|^2,
\quad0\le h_U\le\frac1d\sum_xd_x\log d_x.
\]
Für n≥2 ist die gemittelte Reinheit \(\operatorname{tr}(\bar\rho_n^2)=\sum_eq_n(e)^2\), die Entropie \(S(\bar\rho_n)=-\sum_eq_n(e)\log q_n(e)\). Bedingte Zustände haben Reinheit1/Entropie0. Φ erhöht in endlicher Dimension die Entropie nichtnegativ: S(Φρ)≥S(ρ).

**B. Voraussetzungen.** Endliche Dimension; Spektral-/Widerstandsformeln nur flache Coins, letzte zusätzlich Regularität. 0log0=0.

**C. Beweis.** M=(FJ)J* und J*FJ=A liefern die AB/BA-Determinantenidentität. Die d−m zusätzlichen Nulleigenwerte in E-10 liefern die Formel. Bei Regularität ist \(1-\mu_j=\ell_j/k\) und \(\operatorname{Kf}(G)=m\sum_{j\ge2}\ell_j^{-1}\) [KIRCHHOFF]. Die Entropierate ist der uniforme Mittelwert der Spaltenentropien, maximal bei lokal uniformen Ausgängen. Mean-Purity/-Entropie folgen aus seinen Eigenwerten q. Das Pinching ist eine unitäre Phasenmittelung; Entropiekonkavität und unitäre Invarianz ergeben S(Φρ)≥S(ρ).

**D. Paper/Literatur.** [J] (4.16) für Entropie; weitere Folgerungen aus E-10/E-11; [DOYLE], [KIRCHHOFF].

**E. Simulation.** Entropie/Purity ohne Dichtematrixdiagonalisierung. Widerstandsformel als unabhängiger Graphbenchmark, nicht ungeprüft auf irreguläre Graphen übertragen. Pfadentropierate ist weder bedingte Zustandsentropie noch Mischungsrate. Tests T18,T20.

# 4. Edge-Walk: Symmetrien und Lie-Theorie

### E-13 — Gleichheit der kanonischen invarianten Maße

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für endliche Unitaries:
\[
\nu_U=\nu_{\widetilde U}
\iff \widetilde U|e\rangle=e^{i\theta_e}U|\pi(e)\rangle
\iff U^*\widetilde U=P_\pi D_\theta.
\]
Für SQW-Familien auf demselben Graphen ist dies äquivalent zu
\[
\widetilde S(x)=S(x)P_xD_x\quad\forall x.
\]
Die monomialen Unitaries bilden den Normalisator \(N(T_x)=T_x\rtimes\mathfrak S_{d_x}\). Die kanonischen Maße werden durch
\[
\mathcal M_G\cong\prod_xU(d_x)/N(T_x),\qquad
\dim_{\mathbb R}\mathcal M_G=\sum_x(d_x^2-d_x)
\]
parametrisiert. Für den Dreiknotenbaum ergibt sich ℝP². Ein einzelner reiner Zustand liegt auf \(\mathbb{CP}^{d-1}\cong U(d)/(U(1)\times U(d-1))\).

**B. Voraussetzungen.** Endlicher fester beschrifteter Graph; kanonisches **gleichgewichtetes** Maß. Bei Reduzibilität werden dadurch nicht alle möglichen nichtuniformen stationären Maße klassifiziert. Kein Quotient nach Graphautomorphismen, außer ausdrücklich hinzugefügt.

**C. Beweis.** Gleichheit der diskreten Maße permutiert deren verschiedenen Atome. Gleiche normierte Rang-eins-Projektoren bedeuten Ketgleichheit bis auf eine Phase. Bei einer eingehenden Kante am Knoten x liegt das Bild beider Streuoperatoren im Ausgangsblock x; orthogonale Ausgangsblöcke verbieten eine Permutation zu einem anderen Knoten. Koeffizientenvergleich liefert die lokale Bedingung. Der Normalisator permutiert die minimalen Diagonalprojektoren und ist daher genau monomial. Quotientendimension folgt aus dimU(n)=n² und dimT=n. Für Grad2 ist U(2)/T² die Blochkugeloberfläche S²; Vertauschen orthogonaler Geraden ist Antipodenidentifikation, also ℝP².

**D. Quellen.** Lokale Struktur [J] (2.7). Allgemeine MASA-/Normalisator-/Flaggengeometrie [ZCV]; keine behauptete Neuheit dieser Lie-Theorie.

**E. Simulation.** Lokaler Spaltenabgleich bis auf Phase/Permutation vergleicht die Ensembles. Gleiches Ensemble bedeutet nicht gleicher Kanal, nicht gleiche M und nicht gleiche Mischungsrate. Der Schwerpunkt ist immer I/d, während die Atome von S einschließlich relativer Spaltenkomponentenphasen abhängen. Tests T21,T22,T35.

### E-14 — Gleiche Maße, unterschiedliche Dynamik; endliche Permutationsoptimierung

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für \(\widetilde U=URD_\theta\) gilt \(\widetilde M=MR\). In gemeinsamer Beschriftung durch die physischen Atome σₑ ist der zweite Übergangskern dagegen RM. Beide sind permutationsähnlich zueinander, nicht allgemein ähnlich zu M. Singulärwerte und stationäre Entropierate bleiben gleich, Eigenwerte und Mischung können sich ändern. Innerhalb einer festen kanonischen Maßklasse gibt es genau \(\prod_xd_x!\) verschiedene Zustandskerne RM; Spaltenphasen erzeugen keine weiteren.

**B. Voraussetzungen.** E-13. Aussagen über Relaxationsraten beziehen sich auf tatsächlich irreduzible aperiodische Kandidaten. Die Klasse eines festen Maßes kann auch nichtmischende Kandidaten enthalten.

**C. Beweis.** Rechtsmultiplikation durch R permutiert Spalten der Betragsquadrate; D fällt aus ihnen heraus. Die Zuordnung \(\widetilde\sigma_e=\sigma_{\pi(e)}\) konjugiert MR in RM. Permutationsmultiplikation erhält Singulärwerte; die Spaltenentropiesumme bleibt ebenfalls gleich. Lokal vertauschbare Zeilen von M besitzen disjunkte nichtleere Spaltenträger: Zeile (x,y) liegt in den Spalten des Eingangsblocks bei y. Daher kann keine nichttriviale lokale Zeilenpermutation M fixieren, was die genaue Anzahl beweist. X-02 zeigt unterschiedliche SLEMs explizit.

**D. Quellen.** Modellspezifische Chatfolgerung aus [J] (5.13) und E-13.

**E. Simulation.** Bei kleinen Graden exakte Enumeration lokaler Permutationen für ein vorgegebenes Optimierungsziel möglich. Ein allgemein effizienter Optimierungsalgorithmus wurde nicht gezeigt. Phasenoptimierung verbessert innerhalb dieser Klasse nicht die reduzierte stationäre Mischung, kann aber kohärente Warmstarts verändern. Caches für M, Atome und volle Kanäle trennen. Tests T21,T22,T40.

### E-15 — Zweizeitgesetze lösen die Weyl-Permutationsmehrdeutigkeit auf

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Beim kanonischen stationären Start:
\[
\Gamma_U=\frac1d\sum_{e,f}M_{f,e}\delta_{(\sigma_e,\sigma_f)}.
\]
\[
\Gamma_U=\Gamma_{\widetilde U}\iff\widetilde S(x)=S(x)D_x\quad\forall x.
\]
Bei schon gleichem Einzeitmaß mit lokaler Permutation π:
\[
\|\Gamma_U-\Gamma_{\widetilde U}\|_{\rm TV}=\frac{\#\{e:\pi(e)\ne e\}}d,
\quad
\operatorname{MMD}_{k_2\otimes k_2}^2=\frac{\|M-RM\|_F^2}{d^2}.
\]
Zweizeitgesetze werden damit durch \(\prod_xU(d_x)/T_x\) statt durch \(\prod_xU(d_x)/N(T_x)\) klassifiziert.

**B. Voraussetzungen.** Endlicher einfacher Graph, fester physikalischer Zustandsraum, alle Atome stationär mit Gewicht1/d.

**C. Beweis.** Gleiche Zweizeitgesetze haben gleiche Randmaße. Nach E-13/E-14 ist ihr Vergleich daher M=RM. Die disjunkten nichtleeren Zeilenträger erzwingen R=I. Umgekehrt lassen individuelle Spaltenphasen die Atome und Übergänge unverändert. Jede bewegte Zeile hat zur ersetzenden Zeile ℓ¹-Abstand2, wodurch die TV-Formel folgt. Paarfeatures auf orthogonalen Atomen sind orthonormal; Ausmultiplizieren ergibt die Frobeniusformel. Der Produktkernel identifiziert zunächst die Randträger durch R-02 und danach die Paargewichte.

**D. Quellen.** Chatfolgerung; Ausgangspunkt [J] §4.2 und (5.13). Keine Vollständigkeits-/Neuheitsrecherche zu dieser speziellen Klassifikation behauptet.

**E. Simulation.** Paarzähler unterscheiden Dynamiken mit gleichem stationärem Mittel und Maß. Wegen Markov bestimmen sie alle stationären Mehrzeitgesetze, jedoch nicht alle ersten Schritte aus beliebigen kohärenten Inputs. Test T21.

### E-16 — Richtungsangepasste Zeitumkehr und Birkhoff-Darstellung

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Die Umkehr von \((x,y)\to(z,x)\) als räumlicher Pfad ist \((x,z)\to(y,x)\). Dementsprechend
\[
M=FM^{\mathsf T}F\iff B_x=B_x^{\mathsf T}\quad\forall x
\iff |S_{zy}(x)|^2=|S_{yz}(x)|^2.
\]
Für Grade≤2 gilt dies automatisch. Gewöhnliches M=Mᵀ gilt dagegen nur für Bₓ=I. Für \(\Theta(\sigma_e,\sigma_f)=(\sigma_{Ff},\sigma_{Fe})\):
\[
\operatorname{MMD}_{k_2\otimes k_2}^2(\Gamma_U,\Theta_*\Gamma_U)
=\frac1{d^2}\sum_x\|B_x-B_x^{\mathsf T}\|_F^2.
\]
Eine Birkhoffzerlegung \(M=\sum_ja_jP_{\pi_j}\) realisiert die reduzierte Kette auch als i.i.d. zufällige Permutationswirkung; die entsprechenden Zustandsunitaries sind \(UP_{\pi_j}U^*\). Gruppenbahnen der erzeugten endlichen Permutationsgruppe sind die irreduziblen Klassen.

**B. Voraussetzungen.** Endlicher einfacher Graph. Es geht um die gemessenen Pfade, nicht automatisch um antiunitäre Zeitumkehrsymmetrie von U. Birkhoffgewichte positiv auf den benutzten Permutationen.

**C. Beweis.** M=FB impliziert FMᵀF=FBᵀ. Ein nichtzurückstreuender Übergang hat keinen gewöhnlichen umgekehrten Übergang auf denselben gerichteten Arcs; Symmetrie M=Mᵀ erzwingt daher ausschließlich Zurückstreuung. 2×2-bistochastische Blöcke sind symmetrisch. Die Kernelidentität folgt aus orthogonalen Paarfeatures. Die alternative Permutationsdarstellung folgt aus Birkhoff–von Neumann. Inversen endlicher Permutationen sind positive Potenzen, also stimmen erreichbare Mengen mit Gruppenbahnen überein.

**D. Quellen.** Flip [J] (3.9), Markovstruktur (5.13); Birkhoff–von Neumann ist klassischer Hintergrund.

**E. Simulation.** Reversal-Test mit Arcflip versehen. Die alternative Random-unitary-Darstellung gilt auf der purifizierten Familie; daraus folgt nicht Gleichheit des vollen Kanals auf beliebigen Dichtematrizen. Lokales Spaltensampling ist meist einfacher als Birkhoffzerlegung. Test T23.

### E-17 — Poissonisierung und die ursprünglich diskutierten (Isom)-Annahmen

**Status:** `CONDITIONAL`; Herkunft `CHAT`.

**A. Aussage.** Für die ausdrücklich zusätzlich gewählte Lindbladkonstruktion Cₓ=K(x), H=0 gilt
\[
\mathcal L=\Phi-\mathrm{id},\qquad e^{t\mathcal L}=e^{-t}\sum_{n\ge0}\frac{t^n}{n!}\Phi^n.
\]
Bei endlichem irreduziblem M relaxiert diese Halbgruppe gegen I/d, ohne Aperiodizität. Nach dem zweiten Sprung sind konditionierte Zustände rein; zwischen Sprüngen bleibt der normierte Zustand gleich.

Für einen Unterraum E ist \(K|_E=cV\), V Isometrie E→H, äquivalent zu \(P_EK^*KP_E=|c|^2P_E\), auch bei c=0. Unter der im Chat verwendeten Interpretation der Screenshot-Hypothese ist die Vereinigung problematischer zweidimensionaler Unterräume projektiv
\[
\mathbb P(W),\qquad W=\bigoplus_{d_x\ge2}\mathcal H_x^I.
\]
Die Hamilton-Orbitbedingung lautet \(\bigcap_t e^{itH}W=\{0\}\), äquivalent dazu, dass W keinen Eigenvektor des selbstadjungierten H enthält. Für H=0 und W≠0 scheitert sie, während die Produkt-Purifikation E-08 gilt.

**B. Voraussetzungen.** Endliche Dimension; keine Identifikation eines beliebigen Lindbladmodells mit dem diskreten Walk. Die bibliografische Quelle der ursprünglichen Screenshots wurde nicht vollständig identifiziert; die Interpretation der Skalare pro Krausoperator ist explizit.

**C. Beweis.** \(\sum K^*K=I\) ergibt L=Φ−I. Eigenwerte λ werden zu λ−1; außer λ=1 liegen sie strikt in der linken Halbebene. Für die Isometrieäquivalenz setze T=K|E und nutze T*T=aI; bei a>0 V=T/√a, bei a=0 T=0. Grad-eins-Blöcke können wegen Rangvergleich keinen Anteil eines solchen 2D-E tragen. Umgekehrt wählt man zu jedem Blockanteil ψₓ in W einen orthogonalen ηₓ gleicher Norm; E=span(ψ,η) erfüllt die Kompressionsbedingung. Der Hamiltonschnitt ist der größte in W enthaltene H-invariante Unterraum; in endlicher Dimension enthält jeder nichttriviale davon einen Eigenvektor.

**D. Quellen.** Eigenständige Konstruktion; [PUR]/[BFPP] betreffen die diskrete Produktbedingung. Es wurde kein allgemeiner kontinuierlicher Ergodensatz durch einfaches Ersetzen von (Isom) bewiesen.

**E. Simulation.** Optional Poisson-Event-Backend mit Rate1. Zweiter Sprung ist nicht deterministische Zeit2. Hinzufügen eines H verändert die Dynamik und erfordert neue Prüfung. Poissonisierung ist nicht dasselbe wie eine exakte Einbettung \(e^{\mathcal L}=\Phi\); ein nichtinvertierbarer endlicher Kanal kann nicht selbst der Exponentialwert einer endlichen linearen Generatormatrix sein.

# 5. Induzierter Open Vertex SQW

### V-01 — Exakte induzierte Präparation und komplexe Konjugationen

**Status:** `PROVEN`; Herkunft `PAPER/CHAT`.

**A. Aussage.** Zusätzlich zu S seien normierte lokale Randvektoren ω(x) und Phasen βₓ vorgegeben. Setze
\[
R=\sum_x|x\rangle\langle\omega(x)|,\qquad RR^*=I_V,\quad R^*R=\Pi_\omega,
\]
\[
v(x)=S(x)\omega(x),\quad
\theta(x)=\sum_{z\sim x}\overline{\omega_x(z)}v_z(x)|z\rangle,
\quad s_x=\|\theta(x)\|^2=\sum_{z\sim x}|\omega_x(z)|^2|v_z(x)|^2\le1,
\]
\[
\chi(x)=\theta(x)+e^{i\beta_x}\sqrt{1-s_x}|x\rangle,
\quad G(x)=|\chi(x)\rangle\langle x|,
\quad\Psi(\rho)=\sum_xG(x)\rho G(x)^*.
\]
Hier ist \(\omega_x(z)\) die Komponente des Randvektors **am Knoten z** in Richtung des Nachbarn x. Der Balken ist wesentlich. Die rohe Kompression \(\widetilde\Phi=\operatorname{Ad}_R\circ\Phi\circ\operatorname{Ad}_{R^*}\) hat Krausoperatoren \(|\theta(x)\rangle\langle x|\) und ist allgemein nur spurnichtvermehrend. Die konkret gewählte Ψ ist CPTP.

**B. Voraussetzungen.** `SIMPLE_STATIC`, normierte ω, unitäre S, genau die kohärente Vervollständigung (6.15). Loopfreiheit garantiert θ(x)⊥|x〉. Multigraphen brauchen die Portsumme NEW-03.

**C. Beweis.** \(R^*|x\rangle=\omega(x)\), \(K(x)\omega(x)=\sum_zv_z(x)|zx\rangle\). Danach liefert R den Koeffizienten \(\langle\omega(z)|zx\rangle=\overline{\omega_x(z)}\). Andere Eingangslabels werden annihiliert; daher ist \(RK(x)R^*=|\theta(x)\rangle\langle x|\). Normierung von v und |ω-Komponenten|≤1 liefert s≤1. Die orthogonale Selbstkomponente stellt Norm1 her; somit \(\sum_xG(x)^*G(x)=I\).

**D. Paper.** (6.1)–(6.17), Definition6.1, (6.27). Die Konjugationsstriche wurden in der PDF visuell geprüft. Der gedruckte Nebensatz unter (6.14) zur Spurerhaltung der rohen Kompression ist ohne weitere Annahme zu stark; siehe AUD-02.

**E. Simulation.** Einmal v,θ,s,χ und P vorrechnen. Sparse χ hat höchstens dₓ+1 Komponenten. Sω benötigt O(Σdₓ²), nachher χ-Speicher O(m+d). Kein Edge-Kanal muss explizit gebaut werden. Nicht θ durch θ/||θ|| ersetzen und nicht die fehlende Masse durch einen separaten Krausoperator ergänzen: das wären andere Modelle. s>1 außerhalb Rundungstoleranz ist ein Fehler, kein Anlass für sqrt(abs(1−s)). Tests T25,T26,T27.

### V-02 — Sofortige Reinheit und exakte klassische Labelkette

**Status:** `PROVEN`; Herkunft `CHAT/PAPER`.

**A. Aussage.** Mit \(\tau_x=|\chi(x)\rangle\langle\chi(x)|\):
\[
G(x)\rho G(x)^*=\rho_{xx}\tau_x,\quad \rho_n=\tau_{X_n}\quad(n\ge1),
\quad P_{xy}=|\langle y|\chi(x)\rangle|^2.
\]
\[
r_0(x)=\rho_{0,xx},\quad q_n=r_0P^{n-1},\quad
\nu_n=\sum_xq_n(x)\delta_{\tau_x},\quad
\bar\rho_n=\sum_xq_n(x)\tau_x,\quad
\operatorname{diag}\bar\rho_n=r_0P^n.
\]
Die Pfadwahrscheinlichkeit ist \(r_0(x_1)\prod_{j=1}^{n-1}P_{x_jx_{j+1}}\). Anfangskohärenzen sind ab Schritt1 irrelevant.

**B. Voraussetzungen.** V-01 oder allgemeiner ein normiertes Rank-one-Präparationsinstrument G(x)=|χ(x)〉〈x|; beliebiger reiner/gemischter Input, endlicher oder abzählbarer Raum.

**C. Beweis.** Rang-eins-Ausmultiplizieren ergibt ρₓₓτₓ. Normieren liefert τₓ. Die nächste Ergebniswahrscheinlichkeit ist \(\langle y|\tau_x|y\rangle=P_{xy}\). Summation über Pfade ergibt qₙ und νₙ. Die Diagonale jedes τₓ ist gerade die Zeile x von P; deshalb tritt beim Born-Gesetz ein zusätzliches P auf.

**D. Paper.** Theorem6.2, (6.18)–(6.28). Die konkrete Trajektorieninterpretation folgt aus der gewählten Krausfamilie. Ψ ist schon in einem Schritt entanglement-breaking [EB].

**E. Simulation.** Pro Pfad ein Knotenlabel, Sampling aus einer P-Zeile. Den reinen Zustand nur bei Ausgabe rekonstruieren. Der Zustand nach X₁ ist χ(X₁), nicht |X₁〉. Gemittelter Kanal als m-Gewichte. Tests T28,T29.

### V-03 — Doppelte Atome, Erreichbarkeit und Lumpability

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Verschiedene Labels können denselben Projektor präparieren. Aus τₓ=τ_z folgt Pₓᵧ=P_zᵧ für alle y. Für Klassen \(\mathcal C_i\) identischer Atome ist
\[
T_{ij}=\sum_{y\in\mathcal C_j}P_{xy},\qquad x\in\mathcal C_i,
\]
eine wohldefinierte exakte Zustandskette. Ihr Anfangsgewicht ist \(\widehat r_0(i)=\sum_{x\in\mathcal C_i}r_0(x)\). Bei einem festen Input sind nur die von supp(r₀) im P-Träger erreichbaren Atome relevant.

**B. Voraussetzungen.** Exakte Projektorgleichheit, nicht nur Vektorähnlichkeit. Alle G-Präparationen bleiben normiert. Keine Orthogonalität nötig.

**C. Beweis.** Pₓᵧ=〈y|τₓ|y〉 beweist identische Zeilen. Daher ist die aggregierte Zeile unabhängig vom Repräsentanten; die bedingte nächste Klassenverteilung hängt nur von der aktuellen Klasse ab. Das ist starke Lumpability. Erreichbarkeit folgt aus der Labelkette.

**D. Quellen.** Folgerung aus [J] (6.16), (6.18), klassische Lumpability.

**E. Simulation.** Optional weniger Atom-IDs als Vertex-IDs. Für vollständige Knotenergebnisrecords entweder Labels beibehalten oder innerhalb der Zielklasse die korrekte bedingte Labelwahl mitsampeln. Eine toleranzbasierte Zusammenlegung ist eine neue Approximation und benötigt eine eigene Fehlerschranke. Test T30.

### V-04 — Stationäre Korrespondenz und zeitversetzte Rekonstruktion des Gesetzes

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Definiere \(\mathcal R_V(\rho)=\operatorname{diag}\rho\) als Zeile, \(\mathcal B_V(q)=\sum_xq_x\tau_x\). Dann
\[
\Psi=\mathcal B_V\mathcal R_V,\quad \mathcal R_V\mathcal B_V(q)=qP.
\]
Stationäre Labelverteilungen π, invariante Zustandsmaße νπ und stationäre Dichtematrizen \(\bar\rho_\pi\) stehen in affiner Bijektion:
\[
\pi P=\pi\longleftrightarrow\nu_\pi=\sum_x\pi_x\delta_{\tau_x}
\longleftrightarrow\bar\rho_\pi=\sum_x\pi_x\tau_x,
\quad\pi=\operatorname{diag}\bar\rho_\pi.
\]
Dies gilt auch bei doppelten Atomen. Ferner für jedes aktuelle Gesetz:
\[
\nu_{n+1}=\sum_x\langle x|\bar\rho_n|x\rangle\delta_{\tau_x}.
\]
In endlicher Dimension stimmen die nichtverschwindenden Eigenwerte einschließlich algebraischer Vielfachheiten von Ψ und P überein.

**B. Voraussetzungen.** Endliche Dimension für die Spektralaussage. Die stationären Korrespondenzen gelten auch abzählbar, sofern stationäre ℓ¹-Verteilungen bzw. Dichteoperatoren existieren. Der Walk ist fest: verschiedene Walks können bei gleichem Mittel verschiedene Maße besitzen.

**C. Beweis.** Die Faktorisierung ist V-02. Für stationäres π ist \(\mathcal R_V\mathcal B_V(\pi)=\pi\), also injektiv. Ist Ψρ=ρ, dann π=diagρ stationär und ρ=Bπ. Ein invariantes Maß muss das nächste Gesetz sein; dessen Gewichte erhält man durch Integration der linearen Funktionen ρₓₓ, also aus seinem Mittel. Dies beweist die Bijektion auch bei zusammenfallenden Atomen. Die Spektralgleichheit ist die endliche AB/BA-Identität; für λ≠0 transportieren die Faktoren die verallgemeinerten Eigenräume.

**D. Paper.** Faktorisierung/Potenzen Theorem6.2, stationäre Mittel Korollar6.4; vollständige Maßkorrespondenz und zeitversetzte Rekonstruktion sind Chatfolgerungen.

**E. Simulation.** Stationäranalyse über m×m-P statt m²×m²-Ψ. Der aktuelle Mittelwert bestimmt die **nächste** volle Zustandsverteilung, im Allgemeinen nicht die aktuelle. Eindeutigkeit kann auch bei Reduzibilität mit nur einer geschlossenen Klasse vorliegen. Tests T29,T30,T31.

### V-05 — Konvergenz, Transienten und Normvergleich

**Status:** `PROVEN`; Herkunft `CHAT/PAPER`.

**A. Aussage.** Für stationäres π gilt
\[
\tfrac12\|q_{n+1}-\pi\|_1\le
\tfrac12\|\bar\rho_n-\bar\rho_\pi\|_1\le
\|\nu_n-\nu_\pi\|_{\rm TV}\le
\tfrac12\|q_n-\pi\|_1.
\]
Irreduzibilität liefert fast sichere empirische Konvergenz; zusätzliche Aperiodizität gewöhnliche exponentielle Konvergenz der Gesetze. Allgemeiner genügt eine einzige aperiodische geschlossene Klasse mit transientem Rest. Bei mehreren geschlossenen Klassen Cⱼ sind die Grenzmischgewichte
\[
a_j=\sum_xr_0(x)h_j(x),\qquad h_j(x)=\Pr_x(\text{Absorption in }C_j).
\]
Eine einzelne Trajektorie wählt eine Klasse und besitzt deren empirisches Grenzmaß.

**B. Voraussetzungen.** Endliche Kette. In unendlicher Dimension zusätzliche Rekurrenz-/Eintrittszeitannahmen erforderlich. Der Normvergleich selbst gilt für jede vorhandene stationäre Verteilung.

**C. Beweis.** Diagonalmessung kontrahiert Spurdistanz und liefert qₙ₊₁−π. Baryzentren kontrahieren TV in Spurdistanz. Das Pushforward von Labels auf Zustände kontrahiert TV. Daraus folgt die Ungleichungskette. Klassische Markov-Ergodensätze liefern Konvergenz. Die Absorptionsfunktionen lösen h=Ph auf dem transienten Teil mit entsprechenden Randwerten auf geschlossenen Klassen.

**D. Paper.** Korollar6.4, Remark6.5; reduzible Gewichtung ist klassische Markovtheorie und korrigiert im DFT-Fall die gedruckten (6.67)–(6.70), siehe AUD-01.

**E. Simulation.** Transiente Initialmasse nicht entfernen. Anders als beim Edge-Walk kann die momentane Trajektorie zu einem absorbierenden reinen Zustand konvergieren. Label-CLT mit T=P,π wie E-09, bei Reduzibilität klassenweise. Gleiche Exponenten aufgrund der zeitverschobenen Schranken bedeuten nicht gleiche Vorfaktoren. Tests T31,T32.

### V-06 — Unitalität, Phasen und Präparationssymmetrien

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** In endlicher Dimension mit quadratischer Spaltenmatrix Cχ:
\[
\Psi(I)=C_\chi C_\chi^*,\quad
\Psi\text{ unital}\iff C_\chi\text{ unitär}\iff\{\chi(x)\}\text{ orthonormal}.
\]
P bistochastisch allein genügt nicht. Für ein stationäres Ensemble:
\[
\operatorname{tr}(\bar\rho_\pi^2)=\sum_{x,y}\pi_x\pi_y|\langle\chi(x)|\chi(y)\rangle|^2.
\]
P ist unabhängig von βₓ, die Atome und Ψ allgemein nicht. Für feste ω,β gilt aus S′(x)=S(x)Rₓ und Rₓω(x)=ω(x) dagegen Gleichheit der ganzen Präparation. Diese erste Parametrisierungsstufe ist U(dₓ)/U(dₓ−1), eine Sphäre, nicht automatisch ein projektiver Raum.

**B. Voraussetzungen.** Endlicher Vertexraum, genau ein normierter Präparationsvektor pro Basislabel. Bei den induzierten Symmetrien ω und β unverändert.

**C. Beweis.** CC*=I für eine quadratische Matrix impliziert C*C=I. Die Reinheitsformel folgt durch Ausmultiplizieren. Die Selbstkomponente von χ liegt orthogonal zu den Nachbarkomponenten, weshalb β aus Betragsquadraten verschwindet, nicht aus Offdiagonalen der Projektoren. Rₓω=ω liefert S′ω=Sω. Der Stabilisator eines normierten Vektors in U(dₓ) ist U(dₓ−1). Eine Phase von v=Sω ist relativ zur Selbstkomponente relevant, daher keine unbedingte weitere U(1)-Quotientierung.

**D. Paper.** (6.10)–(6.18), Remark6.5(ii), §6.1.1. Die vollständige Klassifikation aller S mit gleichem induzierten Vertex-Kanal wurde nicht bewiesen.

**E. Simulation.** P kann bei β-Sweeps gecacht werden, χ und Observable müssen aktualisiert werden. Für uniformes ω beim α-Grover ist sogar χ unabhängig von α. Tests T25,T33,T34.

### V-07 — Frameoperator, Momentenabbildung und Ensemble-Stabilisator

**Status:** `CONDITIONAL`; Herkunft `CHAT`.

**A. Aussage.** Setze \(F_\pi=(\sqrt{\pi_x}\chi(x))_x\). Dann
\[
F_\pi F_\pi^*=\bar\rho_\pi,\quad
\operatorname{diag}(F_\pi^*F_\pi)=\pi,\quad
\operatorname{diag}(F_\pi F_\pi^*)=\pi P.
\]
Stationarität ist somit \(\operatorname{diag}(FF^*-F^*F)=0\), bis auf Konvention die Nullmomentenbedingung für die Toruswirkung F→DFD*. Die Zeile Pₓ,• ist die projektive Torusmomentenabbildung von [χ(x)] auf die Betragsquadrate.

Für ein endliches Ensemble **verschiedener** reiner Atome mit positiven Gewichten verbinde i,j, wenn 〈χᵢ|χⱼ〉≠0. Hat dieser Überlappungsgraph c Komponenten und der Ketspann Dimension ℓ in ℂᵐ, dann
\[
K_\nu^0\cong U(1)^c\times U(m-\ell)
\]
für die Identitätskomponente des unitären Ensemble-Stabilisators. Seine Orbitmannigfaltigkeit ist U(m)/Kν.

**B. Voraussetzungen.** Endliche Dimension; allgemeine Ensemblegeometrie. Es ist nicht bewiesen, dass die gesamte induzierte SQW-Parameterfamilie ein einzelner glatter homogener oder symplektischer Quotientenraum ist.

**C. Beweis.** Zeilen-/Spaltennormen ergeben die Framegleichungen. Unter DFD* hat Fᵧₓ das Gewicht αᵧ−αₓ; die quadratische Momentenabbildung ist die Differenz der entsprechenden Zeilen-/Spaltennormen [FRAME]. Stationarität entspricht zugleich Flusserhaltung Jₓᵧ=πₓPₓᵧ, nicht notwendigerweise detaillierter Balance. Eine kontinuierliche Symmetrie kann endlich viele verschiedene Atome nicht vertauschen und muss auf jedem Ket als Phase wirken. Nichtnull innere Produkte erzwingen gleiche Phasen entlang des Überlappungsgraphen; dessen Komponenten spannen orthogonale Räume auf. Auf unbenutztem Komplement bleibt U(m−ℓ) frei.

**D. Literatur.** [FRAME] für Momentenabbildungen; die Stationaritätsspezialisierung und Stabilisatorherleitung sind Chatfolgerungen. [ZCV] ist der orthogonale Spezialfall.

**E. Simulation.** Optionale Gauge-/Fluss-/Ensemblediagnostik. Pairwise Fidelity-Gram-Matrizen enthalten nicht die gesamte komplexe Konfiguration; Dreifachphasen können zusätzliche Informationen tragen. Kein Ersatz für den konkreten Konstruktor V-01.

# 6. RKHS, Momente und statistische Verfahren

### R-01 — Tensor-Kernel und explizite MMD-Formeln

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für r≥1:
\[
k_r(\rho,\tau)=(\operatorname{tr}(\rho\tau))^r,
\quad\varphi_r(\rho)=\rho^{\otimes r},\quad
m_r(\nu)=\int\rho^{\otimes r}\nu(d\rho).
\]
Für Atome τᵢ und Wahrscheinlichkeitszeilen q,p:
\[
K^{(r)}_{ij}=|\langle\chi_i|\chi_j\rangle|^{2r},\qquad
\operatorname{MMD}_{k_r}^2(\nu_q,\nu_p)=(q-p)K^{(r)}(q-p)^{\mathsf T}.
\]
Auf einem festen Edge-Träger K=I und MMD=||q−p||₂; somit \(\frac12\mathrm{MMD}\le\mathrm{TV}\le\frac{\sqrt d}{2}\mathrm{MMD}\).
Für zwei kanonische Edge-Maße, W=U*Ũ:
\[
\operatorname{MMD}_{k_2}^2(\nu_U,\nu_{\widetilde U})
=\frac2{d^2}\left(d-\sum_{e,f}|W_{ef}|^4\right)
=\frac2{d^2}\sum_x\left(d_x-\sum_{i,j}|(S(x)^*\widetilde S(x))_{ij}|^4\right).
\]
Sie verschwindet genau unter E-13; das Maximum ist 2(d−m)/d².

**B. Voraussetzungen.** Endliche Atomfamilien; für globale Maßtheorie zunächst endlichdimensionaler Zustandsraum. Bei reinem Zustand repräsentieren χᵢ normierte Kets.

**C. Beweis.** Die Tensor-HS-Featureform beweist Positivdefinitheit. Ausmultiplizieren des Mean-Abstands liefert die Gramformel. Für verschiedene orthonormale Basen ist \(\operatorname{tr}(\sigma_e\widetilde\sigma_f)=|W_{ef}|^2\); die beiden Meannormquadrate sind1/d. In einem unitären n×n-Block liegt die Summe der vierten Beträge zwischen1 undn. Oberes Ende verlangt monomiale Matrix, unteres uniformes Betragsquadrat1/n. Das beweist Verschwindungs- und Maximumscharakterisierung.

**D. Literatur.** Allgemeine Kernel-Mittelwerte und MMD [KME]; allgemeine äquivalente MASA-Metrik [ZCV]. Lokale SQW-Form folgt aus der Blockstruktur.

**E. Simulation.** Keine Tensorarrays erzeugen, nur Overlaps/Gram-Matrizen. Der lineare Kernel sieht beim Vergleich uniformer Edge-Ensembles stets nur I/d; auf bekanntem festen orthogonalen Träger bestimmt er dagegen alle Gewichte. Quadratischer Kernel ist nicht global charakteristisch auf beliebigen Maßen. Tests T35,T36.

### R-02 — Identifizierbarkeit durch Tensor-Momente

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für s verschiedene reine Atome gilt auf bekanntem Träger K⁽ʳ⁾>0 für r≥max(1,s−1). Mit \(b_j=\nu(k_r(\cdot,\tau_j))\) sind Gewichte q=bK⁻¹. Wenn die Kets einen ℓ-dimensionalen Raum aufspannen, genügt nach [CHEFLES] bereits r≥s−ℓ+1. Das sind hinreichende, keine allgemeinen Minimalgrade.

Ein Maß mit höchstens s verschiedenen reinen Atomen wird durch seinen s-ten Tensor-Moment gegenüber **allen** Wahrscheinlichkeitsmaßen auf Dichtematrizen identifiziert. Für ein orthogonales Ensemble beliebiger Gewichte genügt dafür stets der **zweite** Moment. Mit \(\eta=\max_{i\ne j}\operatorname{tr}(\tau_i\tau_j)<1\) gilt zusätzlich \(\lambda_{\min}(K^{(r)})\ge1-(s-1)\eta^r\).

**B. Voraussetzungen.** Endliche reine Atomfamilie. Bekannter Träger/Gewichtsrekonstruktion und unbekannter Träger/Maßidentifikation sind unterschiedliche Probleme.

**C. Beweis.** Die Polynome
\[
L_j(\rho)=\prod_{i\ne j}\frac{1-\operatorname{tr}(\rho\tau_i)}{1-\operatorname{tr}(\tau_j\tau_i)}
\]
erfüllen Lⱼ(τᵢ)=δᵢⱼ. Auf trρ=1 homogenisiert man sie auf Grad r; sie gehören dann zum Tensor-RKHS. Testen einer linearen Relation der Features gegen Lⱼ erzwingt alle Koeffizienten0. Chefles' Mehrkopien-Unabhängigkeit ist die verstärkte hinreichende Schranke; lineare Unabhängigkeit der Kets impliziert jene ihrer Projektoren.

Für unbekannten Träger ist \(F(\rho)=\prod_j(1-\operatorname{tr}(\rho\tau_j))\ge0\) und verschwindet genau auf den Atomen. Gleichheit der s-ten Momente impliziert durch partielle Spuren alle niedrigeren Momente, also für den Konkurrenten ebenfalls ∫F=0. Danach bestimmen Lⱼ die Gewichte. Im orthogonalen Fall ersetzt \(F=1-\sum_e(\operatorname{tr}(\rho\sigma_e))^2\) das Produkt; seine Nullstellen sind genau die orthogonalen Atome, weshalb Grad2 reicht. Die Eigenwertschranke ist Gershgorin.

**D. Literatur.** Elementare Chatbeweise; [CHEFLES], Eq.(2.3), für die Mehrkopien-Schärfung. Keine allgemeine effiziente Inversionsmethode für unbekannten Träger bewiesen.

**E. Simulation.** Solve statt expliziter Inverse; Konditionszahl ausgeben. Höherer Grad verbessert Separation, kann Schätzfehler empfindlicher machen. Nichtorthogonalität allein bedeutet keine Singularität des linearen Projektor-Kernels. Test T36.

### R-03 — MASA-Projektion, Lie-Tangentialmetrik und Torus-Twirling

**Status:** `PROVEN`; Herkunft `CHAT/LITERATURE`.

**A. Aussage.**
\[
\mathcal E_U(A)=\sum_e\operatorname{tr}(\sigma_eA)\sigma_e
=U\operatorname{Diag}(U^*AU)U^*
\]
Zudem ist
\[
\nu_U=\nu_{\widetilde U}\iff U\mathcal A_{\rm diag}U^*=\widetilde U\mathcal A_{\rm diag}\widetilde U^*
\iff\mathcal E_U=\mathcal E_{\widetilde U}.
\]
Die minimalen Projektoren einer endlichdimensionalen MASA sind eindeutig bestimmt und gerade die Ensembleatome. Die Abbildung E_U ist die HS-Projektion auf die MASA \(U\mathcal A_{\rm diag}U^*\), und
\[
\mathcal E_U(A)=d\operatorname{tr}_2[(I\otimes A)m_2(\nu_U)],
\]
\[
d^2\operatorname{MMD}_{k_2}^2
=\|\mathcal E_U-\mathcal E_{\widetilde U}\|_{\rm HS,super}^2
=\sum_{e,f}\|[\sigma_e,\widetilde\sigma_f]\|_{\rm HS}^2.
\]
Für X*=-X, Uₜ=Ueᵗˣ:
\[
\dot\sigma_e=U[X,Q_e]U^*,\quad
\operatorname{MMD}_{k_2}^2(\nu_U,\nu_{U_t})
=\frac{4t^2}{d^2}\sum_{e\ne f}|X_{ef}|^2+O(t^4).
\]
Die unsichtbaren kontinuierlichen Richtungen sind die diagonalen Torusalgebren. Die Mean-Einbettung realisiert den Quotienten aus E-13 injektiv; wegen Kompaktheit ist sie ein Homöomorphismus auf ihr Bild.

**B. Voraussetzungen.** Endlicher Edge-Walk; blockdiagonale X für lokal zulässige Variationen, allgemeine X für die globale U(d)-Geometrie.

**C. Beweis.** Rang-eins-Identität σAσ=tr(σA)σ liefert Projektion und partielle Spur. Die Kreuzspur der Superprojektionen ist Σ|Wₑf|⁴. Für reine P,Q mit c=trPQ gilt ||[P,Q]||²=2(c−c²), woraus die Kommutatorformel folgt. Differenzieren liefert den Lie-Kommutator. Die Vierpotenzensumme hat führende Abnahme \(2t^2\sum_{e\ne f}|X_{ef}|^2\) und ist gerade in t, da e⁻ᵗˣ=(eᵗˣ)*; daher O(t⁴). Die Pinchings DI/DO sind Haarmittel über \(\sum_xe^{i\alpha_x}P_x^I\) bzw. \(\sum_xe^{i\beta_x}P_x^O\). Gemeinsam multiplizieren sie |xy〉 mit e^{i(αₓ+βᵧ)}; verschiedene einfache Arcs haben verschiedene Charaktere, also vollständiges Diag.

**D. Literatur.** [ZCV] enthält die allgemeine MASA-, Flaggen-, Distanz- und Differentialgeometrie, insbesondere Propositionen1,4,6. Die RKHS-Normierung ist unsere Verbindung dazu. [J] (4.13),(4.17) für Pinchings.

**E. Simulation.** Distanzberechnung aus lokalen relativen Unitaries, keine Supermatrix. \(\mathcal E_U\) ist nicht Φ²: innen steht U*AU statt UAU*. Das uniforme Basisensemble ist ein projektives1-Design, im Allgemeinen kein2-Design. Test T35.

### R-04 — Charakteristischer Allmomenten-Kernel und Ensemble-Orbits

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Auf dem endlichdimensionalen Dichtematrixraum ist
\[
k_\kappa(\rho,\tau)=e^{\kappa(\operatorname{tr}(\rho\tau)-1)},\qquad\kappa>0,
\]
charakteristisch, mit Featurefolge
\[
\varphi_\kappa(\rho)=\bigoplus_{r\ge0}\sqrt{e^{-\kappa}\kappa^r/r!}\,\rho^{\otimes r}.
\]
Die unitäre Konjugationswirkung ist isometrisch im RKHS, und der Stabilisator des Mean-Embeddings ist genau der Maßstabilisator. Für ein endliches Ensemble verschiedener reiner Atome positiver Gewichte ist die Ableitung des Mean-Embeddings entlang eᵗˣ genau dann null, wenn [X,τᵢ]=0 für alle i.

**B. Voraussetzungen.** Endliche Zustandsdimension für das kompakte Momentargument; die infinitesimale Aussage benutzt Reinheit und endlichen Träger.

**C. Beweis.** Positive Exponentialkoeffizienten implizieren aus gleicher Einbettung gleiche Tensor-Momente aller Grade. Polynome trennen Dichtematrizen und sind auf dem kompakten Raum dicht in C(X); gleiche Polynommittel bestimmen das Maß. Die Kernelinvarianz folgt aus Spurinvarianz. Die Differentiation der Featurefolge ist zulässig, weil \(\sum_r r^2\kappa^r/r!<\infty\) und die unitäre Orbitkurve beschränkte Ableitung hat. Für die Ableitung teste gegen \(L_i(\rho)\operatorname{tr}(A(\rho-\tau_i))\). An anderen reinen Atomen verschwinden Wert und relevante Ableitung des Faktors 1−tr(ρτⱼ); an τᵢ bleibt \(p_i\operatorname{tr}(A[X,\tau_i])\). Für alle hermiteschen A ist dies nur bei [X,τᵢ]=0 null.

**D. Literatur.** Allgemeine charakteristische Einbettungen [KME]; diese konkreten Tensor-/Orbitfolgerungen wurden im Chat hergeleitet.

**E. Simulation.** Nur Kernelwerte auswerten, keine unendlichen Tensorarrays. Eine interne Fidelity-Gram-Tabelle ist weniger informativ als sämtliche Kernelwerte gegen externe Referenzzustände. Beispiel: |0〉, (|0〉+|1〉)/√2, (|0〉+i|1〉)/√2 und ihre konjugierte geordnete Konfiguration haben dieselben paarweisen Fidelitys, aber Dreifachspur (1+i)/4 bzw. (1−i)/4. Eine gemeinsame unitäre Abbildung zwischen den geordneten Konfigurationen ist deshalb ausgeschlossen. Injektivität garantiert keine numerisch stabile Trägerrekonstruktion.

### R-05 — Höhere Momente haben dieselben nichtverschwindenden Zeitmoden

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für das Vertex-Instrument definiere
\[
\mathcal B_r(q)=\sum_xq_x\tau_x^{\otimes r},\quad
\mathcal R_r(A)=\operatorname{diag}(\operatorname{tr}_{2,\ldots,r}A),\quad
\mathcal T_r=\mathcal B_r\mathcal R_r.
\]
Dann
\[
m_r(\nu_{n+1})=\mathcal T_rm_r(\nu_n),\quad
\mathcal R_r\mathcal B_r(q)=qP,\quad
\sigma(\mathcal T_r)\setminus\{0\}=\sigma(P)\setminus\{0\}.
\]
Außerdem \(K^{(1)}-PP^{\mathsf T}\succeq0\).

**B. Voraussetzungen.** Endlicher Vertex-Walk oder allgemeines Rang-eins-Präparationsinstrument; r≥1.

**C. Beweis.** Partielle Spur eines r-ten Zustandsmoments ist der erste Moment, weil trρ=1. Dieser bestimmt nach V-04 das nächste Gesetz. Die AB/BA-Identität liefert das Spektrum. K¹ ist die HS-Gram-Matrix der τₓ; PPᵀ die Gram-Matrix ihrer Diagonalen. Die Differenz ist die Gram-Matrix ihrer Offdiagonalanteile und daher positiv semidefinit.

**D. Quellen.** Folgerung aus [J] (6.16) und der Faktorisierung; allgemeiner Transferoperatorrahmen [TRANSFER].

**E. Simulation.** Momente über P/q statt exponentiell große Tensor-Supermatrizen propagieren. \(\mathbb E\rho^{\otimes r}\ne(\mathbb E\rho)^{\otimes r}\); \(\mathcal T_r\ne\Psi^{\otimes r}\) im Allgemeinen. Test T37.

### R-06 — Zweizeit-Kernel rekonstruieren den Übergangskern

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für eine stationäre Zeilenkette T auf verschiedenen Atomen, positive π und K>0:
\[
Q=\operatorname{diag}(\pi)T,\quad
B_{ab}=\mathbb E_\pi[k(\rho_n,\tau_a)k(\rho_{n+1},\tau_b)]= (KQK)_{ab}.
\]
Also Q=K⁻¹BK⁻¹, π=Zeilensummen(Q) und Tᵢⱼ=Qᵢⱼ/πᵢ. Mit A=Q−Qᵀ ist die Produktkernel-Diskrepanz zur gewöhnlichen Zeitumkehr
\[
\mathcal I_k^2=\operatorname{tr}(A^{\mathsf T}KAK)=\|K^{1/2}AK^{1/2}\|_F^2.
\]
Sie verschwindet genau bei detaillierter Balance.

**B. Voraussetzungen.** Bekannte unterschiedliche Atome; positiver Gram-Rang, positive stationäre Besuchsgewichte, tatsächlich stationäre Daten. Bei Edge-Ketten ggf. zusätzlich Richtungsflip E-16, nicht bloß gewöhnliche Umkehr.

**C. Beweis.** Ausmultiplizieren der Erwartung ergibt ΣπᵢTᵢⱼKᵢₐKⱼᵦ. Invertierbarkeit erlaubt Rekonstruktion. Die Produktkernel-Quadratform auf Paaren ist \(\sum A_{ij}A_{ab}K_{ia}K_{jb}\), also die angegebene Norm. K>0 impliziert Null nur bei A=0. Stationarität fordert bloß gleiche Zeilen-/Spaltensummen von Q und lässt Kreisströme zu.

**D. Literatur.** Exakte endliche Spezialisierung von Kernelkorrelations-/Transferoperatoren [TRANSFER].

**E. Simulation.** Zweizeitdiagnostik erkennt Dynamiken, die Einzeitmaß und sogar Spektrum nicht unterscheiden. Bei singulärem K oder unbesuchten Atomen ist Rekonstruktion nur auf dem beobachtbaren Teil möglich. Löse lineare Systeme statt explizit zu invertieren. Test T38.

### R-07 — Stationaritätsresiduum und Lyapunov-Kernel

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Für endliches irreduzibles T und K>0:
\[
D_k(q)^2=q(I-T)K(I-T)^{\mathsf T}q^{\mathsf T},\quad D_k(q)=0\iff q=\pi.
\]
Mit Z=(I−T+1π)⁻¹:
\[
\operatorname{MMD}_k(\nu_q,\nu_\pi)\le\|K^{-1/2}ZK^{1/2}\|_2D_k(q).
\]
Bei zusätzlicher Aperiodizität setze A=T−1π und
\[
H=\sum_{n\ge0}A^nK(A^{\mathsf T})^n>0,\quad H-AHA^{\mathsf T}=K.
\]
\[
V(q)=(q-\pi)H(q-\pi)^{\mathsf T}
=\sum_{n\ge0}\operatorname{MMD}_k^2(\nu_{qT^n},\nu_\pi),
\quad V(qT)=V(q)-\operatorname{MMD}_k^2(\nu_q,\nu_\pi).
\]

**B. Voraussetzungen.** Finite irreducible T; Aperiodizität nur für die konvergente Lyapunov-Reihe, nicht für den Residualsolve.

**C. Beweis.** K>0 macht das Residuum nur bei qT=q null. Für a=q−π ist a1=0 und a(I−T+1π)=q−qT; daraus folgt die Schranke durch Einfügen von K^{±1/2}. Bei Spektralradius(A)<1 konvergiert die Reihe und teleskopiert zur Lyapunovgleichung. Da aTⁿ=aAⁿ, folgen die V-Identitäten. Mit \(c=\lambda_{\min}(H^{-1/2}KH^{-1/2})>0\) ist V(qT)≤(1−c)V(q).

**D. Literatur.** Endliche lineare Algebra und klassische diskrete Lyapunov-Theorie [LYAP], hier als Kernelmetrik interpretiert.

**E. Simulation.** Kleines Residuum allein ist kein Gleichgewichtsnachweis ohne Konditionsfaktor. H optional mit Lyapunovsolver statt Potenzsumme. Der Kernel H ist dynamikabhängig und nur auf dem gegebenen endlichen Träger definiert. Nicht bei Periodizität unbesehen verwenden. Test T39.

### R-08 — Empirische RKHS-Fluktuationen allgemeiner endlicher Ketten

**Status:** `PROVEN`; Herkunft `CHAT`.

**A. Aussage.** Im stationären Fall:
\[
c_t=\sum_{ij}\pi_i(T^t)_{ij}K_{ij}-\pi K\pi^{\mathsf T},\qquad
\mathbb E\operatorname{MMD}_k^2(\widehat\nu_L,\nu_\pi)
=\frac{c_0}L+\frac2{L^2}\sum_{t=1}^{L-1}(L-t)c_t.
\]
Aus \(\sqrt L(\widehat q_L-\pi)\Rightarrow Z\) folgt
\[
L\operatorname{MMD}_k^2(\widehat\nu_L,\nu_\pi)\Rightarrow ZKZ^{\mathsf T}.
\]
Bei irreduzibler aperiodischer Kette ist der führende erwartete Koeffizient \(c_0+2\sum_{t\ge1}c_t\); periodisch kann diese ungemittelte Korrelationsreihe divergieren, obwohl der Poisson-CLT gilt.

**B. Voraussetzungen.** Endlicher Träger; stationärer Start für die exakte endliche Erwartungsformel, Irreduzibilität für den CLT. Keine i.i.d.-Annahme.

**C. Beweis.** Mit \(\xi_n=\varphi(\rho_n)-m(\nu_\pi)\) ist E〈ξ₀,ξₜ〉=cₜ. Das Quadrat der empirischen Featuresumme ergibt die Erwartungsformel. Cramér–Wold aus den skalaren Poisson-CLTs liefert den Vektorgrenzwert; stetige Abbildung z→zKzᵀ den quadratischen Grenzwert. Aperiodische endliche Ketten haben summierbare Korrelationen einschließlich Σt|cₜ|, was den O(L⁻²)-Rest ergibt.

**D. Literatur.** Klassische Martingal-/Markov-Grenzsätze, allgemeine Quantentrajektorienvariante [BFP].

**E. Simulation.** Fehlerbalken mit Autokorrelation berechnen. Der Grenzwert der quadrierten MMD ist eine gewichtete Chi-Quadrat-Variable, keine Gaußvariable. Der CLT ist schwache Konvergenz; diskrete finite empirische Häufigkeiten können nicht in TV gegen ein nichtdegeneriertes stetiges Gaußmaß konvergieren. Tests T17,T18,T38.

# 7. Explizite Referenzbeispiele

Die Beispiele sind ausgerechnete Test-Orakel, keine neuen Behauptungen über Forschungsneuheit. Die finite Kernrechnungen werden im beigefügten Testsatz geprüft; Aussagen über unendliche Grenzwerte beruhen auf den angegebenen Beweisen/Quellen.

## X-01 — Dreiknotenbaum x–y–z, [J] §5.1

Nachbarreihenfolge am Zentrum: (x,z). Hilbertbasis des Papers: (|yx〉,|yz〉,|xy〉,|zy〉). **Davon verschieden** ist die Markovbasis in (5.28): (xy),(zy),(yx),(yz).

Für \(S(y)=\begin{pmatrix}a&b\\c&d_0\end{pmatrix}\), \(r=|a|^2=|d_0|^2\), setze
\[
\varphi_x=a|xy\rangle+c|zy\rangle,\quad\varphi_z=b|xy\rangle+d_0|zy\rangle.
\]
Die vier Atome sind Qᵧₓ, Qᵧ_z, |φₓ〉〈φₓ|, |φ_z〉〈φ_z| in dieser Reihenfolge. Es gilt
\[
M_r=\begin{pmatrix}0&0&r&1-r\\0&0&1-r&r\\1&0&0&0\\0&1&0&0\end{pmatrix},
\quad\det(\lambda I-M_r)=(\lambda^2-1)(\lambda^2-(2r-1)).
\]

Für 0≤r<1 ist das invariante Zustandsmaß die eindeutige Gleichverteilung auf diesen vier Atomen. Für 0<r<1 ist die Periode2; für r=0 liegt ein deterministischer Viererzyklus vor. Für r=1 entstehen zwei geschlossene Zweierzyklen. Alle invarianten Maße sind dann
\[
\nu_\lambda=\frac\lambda2(\delta_{Q_{yx}}+\delta_{Q_{xy}})
+\frac{1-\lambda}2(\delta_{Q_{yz}}+\delta_{Q_{zy}}),\quad\lambda\in[0,1].
\]
Beim Identity-Coin ist die linke Auswahlwahrscheinlichkeit des konkreten Anfangszustands \(\operatorname{tr}((Q_{yx}+Q_{xy})\rho_0)\).

Hadamardkonvention des Papers:
\[
H=\frac1{\sqrt2}\begin{pmatrix}1&1\\-1&1\end{pmatrix},\quad
\varphi_\pm=(|xy\rangle\pm|zy\rangle)/\sqrt2,
\]
\[
\nu_H=\tfrac14(\delta_{Q_{yx}}+\delta_{Q_{yz}}+
\delta_{|\varphi_-\rangle\langle\varphi_-|}+
\delta_{|\varphi_+\rangle\langle\varphi_+|}).
\]
Die beiden Superpositionsatome sind keine Kantenbasiszustände. Ihr Baryzentrum ist dennoch I₄/4. Das Spektrum mit algebraischen Vielfachheiten lautet 1,−1,0,0; der Nullteil ist nicht diagonalisierbar. Die Formulierung „simple spectrum“ an dieser Stelle der Quelle nicht als vier algebraisch einfache Eigenwerte interpretieren.

Für r<1 liefert die Poisson-Gleichung
\[
s_f^2=\frac{r}{8(1-r)}(f_1+f_3-f_2-f_4)^2.
\]
Denn \((1-r)(h_1-h_2)=(f_1+f_3-f_2-f_4)/2\), und nur Zustände3,4 tragen mit jeweils r(1−r)(h₁−h₂)² zur bedingten Varianz bei. Bei Hadamard hat eine einzelne Besuchshäufigkeit Varianz1/8; die gesamte erwartete empirische MMD hat Koeffizient1/2. Beim Swap r=0 ist der CLT degeneriert, mit bloßem O(1/L)-Randfehler. Bei r=1 ist innerhalb der zufällig gewählten Klasse zu zentrieren, nicht um eine globale Mischung.

**Warmstarttest:** Die beiden reinen Inputs \((|yx\rangle\pm|yz\rangle)/\sqrt2\) haben dieselbe Basisdiagonale, erzeugen unter H aber unterschiedliche deterministische q₂. Anfangskohärenzen dürfen nicht vergessen werden. Tests T08,T12,T13,T17,T18.

## X-02 — Dreieck: gleiches invariantes Maß, andere Mischungsrate

An jedem Knoten mit derselben Zeilen-/Spaltennachbarordnung:
\[
S_r=\begin{pmatrix}\sqrt r&\sqrt{1-r}\\\sqrt{1-r}&-\sqrt r\end{pmatrix},\quad
\widetilde S_r=S_r\begin{pmatrix}0&1\\1&0\end{pmatrix},\quad0<r<1.
\]
Die zweite Familie ist eine lokale Spaltenpermutation, also gleiches kanonisches Maß. Ihre Kantenmatrix hat aber Parameter1−r. In Reihenfolge (01),(02),(10),(12),(20),(21):
\[
M_r=\begin{pmatrix}
0&0&r&1-r&0&0\\0&0&0&0&r&1-r\\r&1-r&0&0&0&0\\
0&0&0&0&1-r&r\\1-r&r&0&0&0&0\\0&0&1-r&r&0&0
\end{pmatrix}.
\]
\[
\det(\lambda I-M_r)=(\lambda-1)(\lambda-(1-2r))
[\lambda^2+(1-r)\lambda+(1-2r)]^2.
\]
Bei r=1/4 ist der SLEM1/√2, bei r=3/4 dagegen (1+√33)/8. Beide sind irreduzibel und aperiodisch. Singulärwerte und kanonisches Maß stimmen überein, exponentielle Raten nicht. Tests T21,T22.

## X-03 — Hadamard-Edge-Walk auf der Zahlengeraden, [J] §5.2

In der Arcindexkonvention von (5.30):
\[
Me_{2k}=\tfrac12(e_{2k-2}+e_{2k-1}),\quad
Me_{2k+1}=\tfrac12(e_{2k+2}+e_{2k+3}).
\]
Stationarität bedeutet \(\pi_{2k}=\pi_{2k+1}=a_k\), \(2a_k=a_{k-1}+a_{k+1}\). Also aₖ=A+Bk. Nichtnegativität auf ganz ℤ erzwingt B=0. Kein nichtnull konstantes Gewicht ist in ℓ¹; es existiert kein invariantes Wahrscheinlichkeitsmaß. Das σ-finite invariante Zählmaß \(\sum_e\delta_{\sigma_e}\) ist bis auf positiven Faktor eindeutig unter σ-finiten invarianten Maßen.

Diese Nichtexistenz gilt allgemeiner für jede unendliche irreduzible bistochastische Kette: Ein nichtnull stationärer ℓ¹-Vektor nimmt sein positives Maximum an; die stationäre Zeilenmittelung zwingt alle positiven Vorgänger ebenfalls zum Maximum. Irreduzibilität macht den Vektor überall konstant, unmöglich in ℓ¹.

Aus Appendix B ergibt sich bei qₜ=Mᵗe₀, t≥1:
\[
\|q_t\|_2^2=\frac1{2\cdot4^{t-1}}\binom{2t-2}{t-1}
\sim\frac1{2\sqrt{\pi t}}.
\]
Die Kernel-Einbettung konvergiert also gegen0, aber0 ist kein eingebettetes Wahrscheinlichkeitsmaß. Die Wahrscheinlichkeitseinbettung ist in diesem unendlichen Fall nicht abgeschlossen. Lokale Matrixelemente des mittleren Zustands können gegen0 gehen, während seine Spur1 bleibt; das ist weder Spurnormkonvergenz noch schwache Konvergenz in der Dualität Traceklasse/beschränkte Operatoren gegen0, denn I ist ein Gegen-Testoperator.

Nach dem Warmup ist der gemessene Knoten ein einfacher symmetrischer Random Walk. Er ist rekurrent, obwohl die Verteilung sich ausbreitet. Für die Inkrementfunktion f(σₓᵧ)=x−y gibt es einen gewöhnlichen ±1-Inkrement-CLT, obwohl kein stationäres Zustandswahrscheinlichkeitsmaß existiert. Nicht den stationären Satz E-09 auf den Gesamtzustandsraum anwenden.

## X-04 — Induzierte Grover- und DFT-Vertex-Walks

Für uniformes \(\omega_y(x)=1/\sqrt{d_x}\) und \(L_z(x)=\sum_{y\sim x}S_{zy}(x)\) folgt aus (6.38)–(6.40):
\[
\theta_z(x)=\frac{L_z(x)}{\sqrt{d_xd_z}},\quad
P_{xz}=\frac{|L_z(x)|^2}{d_xd_z},\quad
P_{xx}=1-\sum_{z\sim x}\frac{|L_z(x)|^2}{d_xd_z}.
\]
Für α-Grover ist L_z(x)=1; damit Pₓ_z=1/(dₓd_z) auf Nachbarn, P symmetrisch und πₓ=1/m. Bei festen β sind **alle** Präparationsvektoren und der ganze Kanal α-unabhängig, nicht nur P. Der stationäre Mittelzustand ist im Allgemeinen nicht I/m.

Für die DFT-Konvention \(S_{jk}=d_x^{-1/2}e^{-2\pi ijk/d_x}\), j,k=0,…,dₓ−1, wird der erste Port selektiert. Bezeichne den ersten Nachbarn mit N(x). Dann
\[
\chi(x)=\frac{|N(x)\rangle}{\sqrt{d_{N(x)}}}
+e^{i\beta_x}\sqrt{1-1/d_{N(x)}}|x\rangle,
\quad P_{x,N(x)}=1/d_{N(x)},\quad P_{xx}=1-1/d_{N(x)}.
\]
Jede Zusammenhangskomponente Cⱼ des funktionalen N-Graphen besitzt genau einen Zyklus Cycⱼ. Auf diesem ist
\[
\pi_x^{(j)}=\frac{d_{N(x)}}{\sum_{z\in\mathrm{Cyc}_j}d_z},
\]
außerhalb0. Der Beweis ist konstanter Zyklusfluss πₓ/d_N(x).

**Wesentliche Korrektur:** Das Grenzgewicht dieses Zyklus ist r₀(Cⱼ), nicht r₀(Cycⱼ). Alle transiente Masse des Einzugsbereichs wird absorbiert. Gegenbeispiel mit zwei Komponenten des funktionalen Graphen: ungerichteter Pfad0–1–2–3–4 und Nachbarordnungen `0:[1],1:[0,2],2:[1,3],3:[4,2],4:[3]`. Dann sind die Zyklen {0,1} und {3,4};2 ist transient zur ersten Klasse. P ist
\[
\begin{pmatrix}
1/2&1/2&0&0&0\\1&0&0&0&0\\0&1/2&1/2&0&0\\0&0&0&0&1\\0&0&0&1/2&1/2
\end{pmatrix}.
\]
Start bei2 hat auf beiden Zyklen anfänglich Masse0, aber Grenzverteilung (2/3,1/3,0,0,0). Eine Grenzformel mit Gesamtmasse0 ist falsch. Tests T32,T34. Dies betrifft den Wortlaut (6.67)–(6.70), nicht die korrekten lokalen P-Formeln.

## X-05 — Unendliches Vertex-DFT-Beispiel §6.2

Die Zahlengerade besitzt eine **zusätzliche parallele** Kante zwischen0 und1, also d₀=d₁=3 und sonst Grad2. Das vollständige induzierte Modell benötigt Portbuchhaltung. Alternativ kann der explizite Präparationswalk als Fixture eingegeben werden; die Simple-Edge-Purifikationsgarantie gilt dafür nicht automatisch.

Einzige stationäre Labelverteilung: π₀=π₁=1/2, mit geschlossenem Block
\[
P_C=\begin{pmatrix}2/3&1/3\\1/3&2/3\end{pmatrix}.
\]
\[
\chi_0=\sqrt{2/3}e^{i\beta_0}|0\rangle+\sqrt{1/3}|1\rangle,
\quad\chi_1=\sqrt{1/3}|0\rangle+\sqrt{2/3}e^{i\beta_1}|1\rangle.
\]
\[
\nu_\beta=\tfrac12(\delta_{\tau_0}+\delta_{\tau_1}),\quad
\eta=\operatorname{tr}(\tau_0\tau_1)=\tfrac89\cos^2((\beta_0+\beta_1)/2),\quad
\operatorname{tr}(\bar\rho_\beta^2)=(1+\eta)/2.
\]
Für Anfang innerhalb der Klasse mit q₀=(1/2+a,1/2−a):
\[
q_t-\pi=a3^{-t}(1,-1),\quad\mathrm{TV}=|a|3^{-t},
\quad D_{\rm tr}=|a|3^{-t}\sqrt{1-\eta},
\quad\mathrm{MMD}_{k_2}^2=2a^2\,3^{-2t}(1-\eta^2).
\]
Besuchshäufigkeits-CLT-Varianz ist1/2, und
\(L\operatorname{MMD}_{k_2}^2(\widehat\nu_L,\nu_\beta)\Rightarrow(1-\eta^2)\chi_1^2\).
Der Faktor folgt aus der einzigen zentrierten Zweizustandsrichtung. Die Phasen verändern die Quantengeometrie, nicht die klassische Rate1/3. Bei beliebigen unendlichen Anfangsverteilungen dominieren unter Umständen Eintrittszeittails; eine startpunktweise exponentielle Aussage aus Lemma6.13 ist keine uniforme globale Rate über alle Inputs.

## X-06 — Zwei Umlaufrichtungen eines Vertex-DFT-Dreiecks

Wähle β=0 und N₊(x)=x+1 mod3 beziehungsweise N₋(x)=x−1. Beide erzeugen dieselbe Atommenge \(\tau_j=|\psi_j\rangle\langle\psi_j|\), \(\psi_j=(|j\rangle+|j+1\rangle)/\sqrt2\), mit gleichem uniformen Maß. In gemeinsamer Atombeschriftung
\[
T_+=(I+C)/2,\quad T_-=T_+^{\mathsf T},\quad
C=\begin{pmatrix}0&1&0\\0&0&1\\1&0&0\end{pmatrix}.
\]
Beide besitzen Eigenwerte1, 1/4±i√3/4 und SLEM1/2. Mit K=(15/16)I+(1/16)11ᵀ und Q₊−Q₋=(C−Cᵀ)/6 ist
\[
\operatorname{MMD}_{k_2\otimes k_2}^2(\Lambda_{T_+},\Lambda_{T_-})=75/512.
\]
Beweis: Differenz hat Zeilensummen0 und Frobeniusnormquadrat1/6; in R-06 einsetzen. Einzeitmaß und Mischungsrate erkennen den Unterschied nicht, Zweizeitstatistik schon. Test T38.

## X-07 — Gleiche Edge-Matrix, andere stationäre Quantenzustandsmaße

Beim Dreiknotenbaum setze am Zentrum
\[
S_\theta=\frac1{\sqrt2}\begin{pmatrix}1&1\\-e^{i\theta}&e^{i\theta}\end{pmatrix}.
\]
Alle Betragsquadrate und daher M sind gleich. Die zwei zentralen Atome sind jedoch Projektoren auf
\(\varphi_\pm^{(\theta)}=(|xy\rangle\pm e^{i\theta}|zy\rangle)/\sqrt2\).
Für θ=0 und θ=π/2 sind die Maße verschieden, obwohl ihre Baryzentren beide I₄/4 sind. Für \(A=|xy\rangle\langle zy|+|zy\rangle\langle xy|\) gilt
\[
\int(\operatorname{tr}(A\rho))^2\,\nu_\theta(d\rho)=\tfrac12\cos^2\theta.
\]
Der erste Observable-Mittelwert allein sieht den Unterschied nicht. Dies illustriert, welche Phaseninformation der Simulator trotz klassischer Trajektoriensampling-Engine bei der Zustandsrekonstruktion behalten muss.

# 8. Exakte Algorithmen und Ressourcen

## 8.1 Unitärer Ket-Backend

```text
psi = psi0
repeat each requested step:
    next = zeros(d, complex)
    for x in vertices:
        incoming = psi[incoming_arc_ids[x]]
        next[outgoing_arc_ids[x]] = S[x] @ incoming
    psi = next
    emit requested amplitudes or analytic observables
```

Keine Zwischenmessung und keine automatische physikalische Renormalisierung. Normdrift ist zunächst ein Diagnosewert. Bei gemischtem Input einen niedrigrangigen Faktor L analog aktualisieren, falls vorhanden.

## 8.2 Edge: direktes gemeinsames Warmstart-Sampling

```text
require graph.simple and graph.loopless
for y in vertices:
    A_y = principal_block(rho0, incoming_arc_ids[y])
    B_y = S[y] @ A_y @ S[y].adjoint()
    for local_x, x in enumerate(neighbors[y]):
        q2[arc(target=x, source=y)] = real(B_y[local_x,local_x])
validate_probability(q2)
sample e=(x,y) from q2
record X1=y, X2=x
if state_at_step_1_requested:
    rho1_outgoing_block = B_y / trace(A_y)
emit step_2 as EdgeAtom(e)
for n from 2 to horizon-1:
    x,y = target(e),source(e)
    sample z from abs(S[x][:,neighbor_index(x,y)])**2
    e = arc(target=z,source=x)
    record X_(n+1)=z
    emit EdgeAtom(e)
```

Diese Paarziehung erzeugt exakt beide ersten Messergebnisse mit dem ursprünglichen gemeinsamen Gesetz. Sie ist kein nachträglicher Zusatzmessprozess. Bei Horizon0 direkt ρ₀ ausgeben; bei Horizon1 nur die erste Messung/Streuung ausführen. Online-APIs sollten nicht ungefragt X₂ vorziehen.

## 8.3 Edge: sequentieller Online-Warmstart

```text
p1[y] = trace(principal_block(rho0, incoming[y]))
sample y from p1
A = principal_block(rho0, incoming[y])
rho1_local = (S[y] @ A @ S[y].adjoint()) / p1[y]
emit X1=y and rho1_local in outgoing basis at y
sample x from real(diagonal(rho1_local))
e = (x,y)
emit X2=x and EdgeAtom(e)
# then use the one-arc update above
```

Für reinen Input kann der lokale Vektorblock statt A verwendet werden. Für diagonal gemischten Input vereinfacht sich die q₂-Berechnung zu lokalen Betragsquadratmatrizen. Für allgemeine gemischte Inputs ist diese Vereinfachung unzulässig. In NumPy für Hauptblöcke `rho[np.ix_(ids,ids)]` benutzen, nicht `rho[ids,ids]`, das nur Diagonaleinträge selektieren würde.

## 8.4 Gemittelte Edge-Entwicklung

```text
q = initialize_q2(rho0)
for n=2,...,horizon:
    state_law = AtomLaw(edge_atoms, q)
    analytic_A = dot(q, atom_expectations_A)   # optional cached values
    born_edge_distribution = apply_M(q)       # time offset is intentional
    if full_physical_density_requested:
        for x in vertices:
            outgoing_block[x] = S[x] @ diag(q[incoming[x]]) @ S[x].adjoint()
    emit requested quantities
    q = apply_M(q)
```

`apply_M` ist ein lokales Produkt mit \(|S(x)|^2\) plus Arcflip. Schritt1 separat berechnen. Keine Dichtematrix nötig, außer sie wird tatsächlich angefordert. Nichtlinearer Zustandstest f wird auf einzelnen Atomen gemittelt.

## 8.5 Vertex-Konstruktor und Sampling

```text
for x in vertices:
    v = S[x] @ omega[x]
    theta = sparse_zero_vector(m)
    for z in neighbors[x]:
        theta[z] = conjugate(omega[z][neighbor_index(z,x)]) * v[neighbor_index(x,z)]
    s = norm(theta)**2
    validate s <= 1 + declared_roundoff_tolerance
    chi[x] = theta
    chi[x][x] = exp(1j*beta[x]) * sqrt(max(0,1-s))
    P[x,:] = abs(chi[x])**2
r0 = real(diagonal(rho0))
sample x from r0
emit step_1 as VertexAtom(x)
for n=1,...,horizon-1:
    sample x_next from row P[x,:]
    x = x_next
    emit step_(n+1) as VertexAtom(x)
```

Das Abschneiden winziger negativer Rundungsreste ist erst nach bestandener Gültigkeitsprüfung zulässig. Für parallele Ports NEW-03 verwenden. Für das mittlere Modell startet q bei r₀; Schritt1 rekonstruiert Σqₓτₓ, erst danach q←qP. Keine irrtümliche Voranwendung von P.

## 8.6 Stationäranalyse

1. Positiven gerichteten Übergangsträger bestimmen; mathematische Nullstruktur von Rundungsartefakten trennen. Besonders DFT-Zeilen können theoretisch exakt0 sein, numerisch jedoch 10⁻³² liefern. Eine blind angewandte `entry>0`-Regel würde dann falsche SCCs ergeben. Analytische Supportmasken oder eine explizit dokumentierte Fehlertoleranz verwenden.
2. SCCs und geschlossene Klassen ermitteln. Im finite Edge-Modell sind alle SCCs geschlossen; im Vertex-Modell kann es Transienten geben.
3. Klassenstationaritäten lösen. Edge: uniform pro Klasse. Vertex: πP=π und π1=1 auf jeder Klasse.
4. Perioden aus gcd der Zykellängen bestimmen; praktikabel mittels BFS-Tiefen und gcd der Zahlen `depth[i]+1-depth[j]` über Trägerkanten. Eigenphasenrundung ersetzt keine Trägeranalyse.
5. Vertex-Absorption über transienten Block Q und Eintrittsmatrix R durch Solve `(I-Q)h=R` bzw. klassensummierte rechte Seiten berechnen. Nie transiente Initialmasse weglassen.
6. Bei mehreren Klassen die ganze Familie stationärer Maße beziehungsweise inputabhängige Absorptionsmischung ausgeben, keinen willkürlich gewählten Eigenvektor als eindeutige Antwort.

## 8.7 Aufwand und Speicher

Mit \(L_S=\sum_xd_x^2\):

| Aufgabe | Repräsentation | Typischer exakter Aufwand |
|---|---|---|
| Unitärer Ket-Schritt | d komplexe Amplituden | O(L_S) |
| Unitärer Rank-r-Input | d×r-Faktor | O(r L_S) |
| Edge-Warmstart, gemischt | Eingangsblöcke, insgesamt L_S Einträge | naive lokale Konjugation O(Σdₓ³) |
| Edge-Trajektorie nach2 | eine Arc-ID | O(dₓ) direktes Sampling, O(1) nach Aliasvorbereitung |
| Edge-Mittel nach2 | d reelle Gewichte | O(L_S), ohne explizites M |
| Vertex-Vorbereitung | sparse χ-Spalten | O(L_S), danach O(m+d) Speicher |
| Vertex-Trajektorie | eine Vertex-ID | O(dₓ+1), aliasbasiert O(1) |
| Vertex-Mittel | m Gewichte | O(m+d) für sparse P |
| Physikalische Edge-Dichte | Ausgangsblöcke | nur bei Bedarf lokal rekonstruieren |
| Vertex-Dichte | gewichtete sparse χχ*-Summe | O(Σ(dₓ+1)²) mögliche Beiträge |
| Edge-MMD auf festem Träger | q−p | O(d) |
| Vertex-MMD | Gram-Matrix K | O(s²) für dichte Quadratform |

Alias-Tabellen benötigen O(L_S) Edge- bzw. O(m+d) Vertex-Speicher. Kosten einer beliebigen dichten Observable kommen hinzu; Komprimierung des Zustands macht eine dichte Observable nicht automatisch billig.

## 8.8 Unendliche Graphen und endliche Horizonte

Bei endlich unterstütztem Input wächst die kausale Reichweite pro lokalem Schritt höchstens um eine Kante. Ein dynamischer sparse Simulator kann nötige Nachbarschaften mit ihren ursprünglichen Graden und Coins erschließen. Exakt ist ein endliches Fenster nur, wenn der gesamte benötigte Kausalbereich einschließlich seiner Streuports erfasst ist.

Rand-Coins abzuschneiden und neu zu normieren definiert einen anderen Walk. Reflektierende, absorbierende und periodische Ränder sind explizite Modellentscheidungen. Bei unendlich unterstützten Inputs muss Trunkierungsfehler getrennt kontrolliert werden; es wurde keine allgemeine uniforme Tail-/Mixing-Abschätzung bewiesen.

# 9. Getrennte neue Folgerungen der Übergabe

Die folgenden Verstärkungen werden ausdrücklich nicht als schon früher vollständig bewiesene Chatresultate ausgegeben.

### NEW-01 — Vollständige Edge-Kanalgleichheit hat eine kleinere Gauge-Gruppe

**Status:** `PROVEN`; Herkunft `AUDIT_NEW`.

**A. Aussage.** Für denselben beschrifteten Graphen:
\[
\Phi_S=\Phi_{\widetilde S}\iff\widetilde S(x)=e^{i\alpha_x}S(x)\quad\forall x.
\]
Eine Phase pro Knoten ist erlaubt, beliebige unterschiedliche Spaltenphasen im Allgemeinen nicht.

**B. Voraussetzungen.** Vergleich als lineare Kanäle auf **allen** Eingangsoperatoren/Dichtematrizen, nicht nur auf der purifizierten Familie oder im stationären Zustand.

**C. Beweis.** Beschränke A auf einen Eingangsblock x. Gleichheit beider Kanäle bedeutet Gleichheit der unitären Konjugation durch S(x) und Ŝ(x) auf der vollen Matrixalgebra. W=S*Ŝ muss mit allen Matrizen kommutieren, also skalar sein; wegen Unitarität W=e^{iα}I. Umgekehrt löschen sich diese Krausphasen in KρK* aus.

**D. Quellen.** Neue elementare Folgerung aus [J] (4.8),(4.12), ergänzend zu E-13/E-15. Keine Neuheitsbehauptung.

**E. Simulation.** Getrennte Äquivalenz-/Cachetypen für `same_unitary`, `same_channel`, `same_stationary_path_law`, `same_invariant_measure`, `same_transition_matrix`. Individuelle Spaltenphase kann q₂ eines kohärenten Inputs ändern. Test T40.

### NEW-02 — Exakte Kanalränge und Perturbationsschranken

**Status:** `PROVEN`; Herkunft `AUDIT_NEW`.

**A. Aussage.**
\[
\operatorname{rank}\Phi^2=d,\qquad
\operatorname{rank}\Phi^n=\operatorname{rank}M^{n-2}\quad(n\ge2).
\]
Für zwei Familien auf demselben Graphen:
\[
\|U_S-U_{S'}\|_{2\to2}=\sup_x\|S(x)-S'(x)\|_{2\to2}=:\delta,
\]
\[
\|U_S^n-U_{S'}^n\|\le n\delta,\qquad
\|\Phi_S^n(\rho)-\Phi_{S'}^n(\rho)\|_1\le2n\delta.
\]

**B. Voraussetzungen.** Endliche Dimension für Ränge. Normformeln auch auf abzählbarer direkter Summe. Feste endliche Zeit; keine stationäre Parameterstabilität ohne weitere Spektralannahmen.

**C. Beweis.** \(\Phi^n=\mathcal B_U M^{n-2}\mathcal R_2\), wobei \(\mathcal R_2(A)=\operatorname{diag}(UAU^*)\). B ist injektiv, R₂ surjektiv mit Urbild U*diag(q)U. Daher ergibt sich exakt der Zwischenrang. Für die Norm U=F⊕S verwenden. Potenzdifferenzen teleskopieren. Für Kanäle ist der Ein-Schritt-Spurnormunterschied höchstens2δ||A||₁, durch zweimalige Dreiecksungleichung bei unitärer Konjugation und Kontraktivität des Pinchings. Die Teleskopsumme der CPTP-Potenzen liefert die Schranke.

**D. Paper.** Korollar4.5 für Faktorisierung. Lemma2.4 gibt eine schwächere Schranke über lokale HS-Normen; die Operatornormgleichheit folgt aus (3.11)–(3.12).

**E. Simulation.** Oracle-Tests für Ränge und endliche Robustheit. Numerical rank ist toleranzabhängig, kein stabiler Jordan-Zertifikator. Tests T15,T41.

### NEW-03 — Multigraph-Porterweiterung und Gegenbeispiel zur universellen Edge-Purifikation

**Status:** `PROVEN`; Herkunft `AUDIT_NEW`.

**A. Aussage.** Auf einem schleifenfreien Multigraphen mit mₓᵧ parallelen Ports:
\[
P_x^IP_y^O=\sum_{\ell=1}^{m_{xy}}Q_{xy,\ell}=:Q^{\rm ports}_{xy},\quad
K(x)K(y)=UQ^{\rm ports}_{xy}U,
\quad\operatorname{rank}(K(x)K(y))=m_{xy}.
\]
Universelle Purifikation nach zwei groben Knotenergebnissen ist daher falsch. Für die Vertex-Kompression bleibt dagegen RK(x)R*=|θ(x)〉〈x|, mit
\[
\theta_z(x)=\sum_{\ell:x\leftrightarrow z}\overline{\omega_{(z,x,\ell)}(z)}v_{(x,z,\ell)}(x).
\]
Die Portsumme geschieht **vor** dem Betragsquadrat; ||θ||≤1 folgt aus Kontraktivität von R.

**B. Voraussetzungen.** Explizite Erweiterung: eindeutig identifizierte Ports und Reverse-Arc-Paarung, lokale unitäre Portmatrizen, keine Schleifen. Nicht Teil des einfachen Kernvertrags.

**C. Beweis.** Beide Knotensubraumprojektoren sind in der Arc-Port-Basis diagonal; ihr Schnitt besteht aus allen parallelen Arcs. Multiplikation mit unitärem U erhält den Rang. Gegenbeispiel: zwei Knoten, zwei parallele Kanten, lokale Coins I. Ein gleichmäßiges Gemisch zweier Parallelports wechselt deterministisch zwischen Knoten und behält für immer Rang2/Reinheit1/2. Bei der Vertex-Kompression annihiliert K(x)R* weiterhin alle Basislabels außer x, weshalb nur eine nichtnull Spalte bleibt. Die Portsumme folgt direkt aus R; die loopfreie Vervollständigung ist orthogonal zum Selbstzustand.

**D. Paper.** §6.2 verwendet einen Multigraphen. Diese allgemeine portweise Erweiterung wird hier explizit formuliert, nicht als bereits ausformulierter allgemeiner Satz der Quelle ausgegeben.

**E. Simulation.** E-02 automatisch nur bei einfacher Graphklasse freigeben. Multigraphen brauchen einen quantenmechanischen Edge-Fallback oder eine **anders definierte**, portauflösende Messung. Vertex-§6.2 kann über Portbackend oder direkte χ-Fixture simuliert werden. Test T24.

### NEW-04 — Gewöhnliche Konvergenz bei den induzierten Grover-/DFT-Beispielen

**Status:** `PROVEN`; Herkunft `AUDIT_NEW`.

**A. Aussage.** Auf endlichen einfachen zusammenhängenden Graphen mit m>2 ist die uniform-ω-Grover-Vertexkette irreduzibel und aperiodisch. Jede geschlossene Klasse der DFT-Vertexkette ist ebenfalls aperiodisch. Deshalb konvergieren ihre momentanen Gesetze gewöhnlich, im DFT-Fall zur korrekten Einzugsbereichsmischung. Der Zweiknotengraph ist die periodische Ausnahme.

**B. Voraussetzungen.** Genau die uniform-ω-Konstruktionen aus X-04; nicht alle beliebigen Vertex-Walks.

**C. Beweis.** Grover hat positive Nachbarübergänge, also Irreduzibilität. Bei m>2 existiert ein Knoten höheren Grades und ein Nachbar x, bei dem ein Summand 1/d_z<1 ist; daher Pₓₓ>0. Eine Selbstschleife genügt zur Aperiodizität. DFT-Klassen sind N-Zyklen. Länge≥3 erzwingt graphische Grade≥2 und Selbstübergänge. Bei einem Zweierzyklus können unter Zusammenhang und m>2 nicht beide Endpunkte Grad1 haben, also existiert ebenfalls ein Selbstübergang. Endlicher transienter Rest wird absorbiert.

**D. Paper.** Neue Folgerung aus (6.44),(6.49), Lemma6.9; stärker als eine bloße Cesàroformulierung, aber nur im angegebenen Spezialfall.

**E. Simulation.** Analytischer Klassencheck für Fixtures. Allgemeines Backend trotzdem mit SCC-/Periodenalgorithmus, nicht pauschaler Aperiodizitätsannahme. Tests T32,T34.

# 10. Kritisches Fehlerregister

## AUD-01: Gewichte in (6.67)–(6.70)

Die geprüfte PDF beschreibt die rechten Eigenvektoren 1ᵢ als nur auf Cycᵢ getragen und verwendet r₀(Cycᵢ). Bei transienten Knoten sind diese Vektoren nicht die korrekten Absorptionsfunktionen. Im funktionalen N-Graphen müssen sie auf der ganzen Einzugsbereichskomponente Cᵢ liegen; korrekt ist r₀(Cᵢ). Allgemein gilt r₀hᵢ. Das explizite Pfad5-Gegenbeispiel X-04 hat in der gedruckten Gewichtung Gesamtmasse0, tatsächlich aber1. Dies ist eine nachgewiesene Korrektur, keine nur vermutete Inkonsistenz. T32.

## AUD-02: Spurerhaltung unter (6.14)

Die Aussage, die rohe Kompression sei nur für |V|=2 TP, lässt ohne Zusatzannahme die Nullkomponenten von v(x) außer Acht. Korrekt ist
\[
\widetilde\Phi\text{ TP}\iff\|\theta(x)\|=1\ \forall x
\iff v_z(x)\ne0\Longrightarrow|\omega_x(z)|=1\quad\forall x,z\sim x.
\]
Gegenbeispiel: Pfad0–1–2–3, S=I überall; ω auf Paarpartner der perfekten Paarung (0,1),(2,3) konzentriert. Dann θ-Spalten e₁,e₀,e₃,e₂ haben alle Norm1. Der Graph ist zusammenhängend mit vier Knoten, die rohe Kompression trotzdem TP. Die kohärente Vervollständigung bleibt korrekt und fügt in diesem Fall nichts hinzu. T27.

## AUD-03: Multigraph in §6.2

Die zusätzliche Kante zwischen0 und1 macht Endpunktlabels als Arc-IDs mehrdeutig. Ohne Portindex ist die Behauptung „zwei gemessene Knoten bestimmen die gerichtete Kante“ falsch. Die Edge-Purifikation darf hier nicht stillschweigend angewandt werden. NEW-03/T24 geben ein Gegenbeispiel und die richtige portweise Algebra.

## AUD-04: Fehlender Faktor in (4.31)

Die rechte Seite der gedruckten Gleichung hat Spur \(\Pr(X_2=x_2\mid X_1=x_1)\), die linke Seite Spur \(\mathbb P_2(x_1,x_2)\). Korrekt ist
\[
\rho_2\mathbb P_2(x_1,x_2)=
\mathbb P_1(x_1)\,UP_{x_2}^I\rho_1P_{x_2}^IU^*.
\]
Der Faktor \(\mathbb P_1(x_1)\) fehlt im gedruckten Ausdruck. Die allgemeine unnormierte Krauswortformel Wₙρ₀Wₙ* ist konsistent und sollte im Referenzcode maßgeblich sein. T42.

## AUD-05: Konjugation und Zeitkonvention

In θ steht \(\overline{\omega_x(z)}\), am Nachbarknoten z ausgewertet. OCR/Plaintext-Extraktion verliert gelegentlich den Balken; deshalb wurde die PDF-Seite visuell geprüft. Ein komplexer Randvektortest ist notwendig, reale uniforme Fixtures genügen nicht. Ebenso: Edge-Messung vor U, q₂ als gemeinsames Zweiergebnisgesetz, qₙ versus Mqₙ; Vertex qₙ=r₀Pⁿ⁻¹ versus Born r₀Pⁿ. T26/T09/T29.

## AUD-06: Weitere Grenzen früherer pauschaler Formulierungen

- Instrumentgleichheit, Kanalgleichheit, Maßgleichheit und gleiche Betragsquadratmatrix sind verschiedene Relationen.
- Nichtselektives Diag purifiziert nicht; beobachtete Rang-eins-Zweige tun es.
- Vollständig beobachtete Record-Präfixe sind vorausgesetzt. Ein unbeobachtetes Ergebnis muss als Mischung weitergeführt werden.
- Ein reiner Zustand ist nicht automatisch ein Kantenbasiszustand; die gespeicherte Arc-ID parametrisiert einen gestreuten reinen Zustand.
- Aperiodizität allein reicht nicht für eindeutige globale Konvergenz; Irreduzibilität allein nicht für gewöhnliche momentane Konvergenz.
- Ein verbundenes Ausgangsgraph G kann durch Coin-Nullen eine reduzible Kantenkette erzeugen. Mit Nullen können Perioden>2 auftreten.
- Jordanfaktoren verhindern im Allgemeinen eine exakte O(r_*ⁿ)-Schranke allein aus dem SLEM.
- Korollar5.7 ist zunächst ein Mittelwert-/Kanalsatz, nicht unmittelbar ein Trajektorien-TV-Satz.
- Empirische Pfadmittel sind keine Ensemble-Cesàromittel; O(1/L) und CLT-Skala1/√L betreffen unterschiedliche Fehler.
- Invariante Maße müssen nicht anziehend sein. Stationäre Mischungen geschlossener Klassen sind im Allgemeinen nicht ergodisch.
- Nichtorthogonale Projektoren können linear unabhängig sein; der lineare Kernel muss nicht singulär sein.
- P bistochastisch erzwingt keine Unitalität von Ψ. Nur orthonormale vollständige Präparationsfamilien tun das.
- Paarkernel-Gramwerte allein enthalten nicht jede geometrische Phase. Vollständige Kernel-Einbettungen gegen externe Zustände enthalten mehr Information.
- Das Edge-Normalisatorquotient klassifiziert kanonische uniforme Ensembles, nicht sämtliche stationären Maße reduzierbarer Walks und nicht pauschal Vertex-Ensembles.
- Gleiche deterministische Samplingmatrix erlaubt Caching von Wahrscheinlichkeiten, nicht das Verwerfen der komplexen Coin-/Präparationsdaten für Quantenzustandsausgaben.
- Unendliche Gleichverteilung ist kein Wahrscheinlichkeitsmaß. Lokaler Zerfall ist keine Spurnormkonvergenz; MMD-Cauchy braucht keinen Wahrscheinlichkeitsgrenzwert.
- Startpunktabhängige unendliche exponentielle Schranken sind keine uniforme Rate über beliebige Inputs.
- Der ursprüngliche Screenshot-(Isom)-Satz ist nicht bibliografisch vollständig rekonstruiert. Es wurde kein allgemeiner Lindblad-Ergodensatz durch Abschwächung einer Hypothese bewiesen.
- Zusätzliche physische Messungen von Observablen ändern das Instrument. Analytische Erwartungswertausgabe auf rekonstruierten Zuständen ist davon zu unterscheiden.
- Zeitabhängige Coins erzeugen zeitabhängige Atome/Übergänge. Die statischen stationären und Orthogonalitätsaussagen wurden dafür nicht pauschal bewiesen.

## AUD-07: Offene beziehungsweise nicht freigegebene Forschungsfunktionen

`OPEN`: global effizient optimale Mischung innerhalb einer festen Maßklasse; vollständige Klassifikation aller induzierbaren nichtorthogonalen Vertex-Ensembles; scharfe minimale Tensorgrade bei unbekanntem Träger; robuste unbekannte Phasenrekonstruktion aus eingeschränkten Messdaten; allgemeine endliche klassische Reduktion grober Edge-Trajektorien auf Multigraphen; uniforme unendliche Mixing-/Tail-Schätzungen ohne Zusatzannahmen.

Eine vollständige endliche Permutationsenumeration ist bewiesen möglich, aber nicht generell effizient. Kernel-Identifizierbarkeit ist kein Beweis algorithmischer Stabilität. Die bewiesenen statischen Kernresultate können unabhängig von diesen offenen Erweiterungen implementiert werden.

# 11. Implementierungsrelevante Übersicht

Die Reihenfolge entspricht praktischer Priorität. Bei allen als bewiesen markierten Optimierungen gelten die angegebenen Vorbedingungen.

| Ergebnis | Gültigkeitsbedingungen | Algorithmische Vereinfachung | Nutzen für Simulator | Beweisstatus |
|---|---|---|---|---|
| U-01 lokale Streuung | statische unitäre Coins, feste Ports | blockweises Matvec plus Flip | Fundament aller Modelle | PROVEN / Paper |
| E-02/E-03 Edge-Purifikation | einfache schleifenfreie Graphen, volles Instrument, n≥2 | eine Arc-ID pro Pfad | exakte Trajektorienbeschleunigung | PROVEN |
| E-03 Warmstart | beliebiger gemischter Input | nur lokale Eingangsblöcke nötig | korrekte Anfangskohärenzen | PROVEN |
| E-05 Edge-Mittel | gleicher Vertrag, n≥2 | d Gewichte statt d² Matrix | exakte Ensembleentwicklung | PROVEN |
| V-01 Vertex-Konstruktor | normiertes ω, unitäres S, konkrete Vervollständigung | lokale Sω, sparse χ | korrekte Konjugation/Normierung | PROVEN / Paper |
| V-02 Vertex-Trajektorie | normierte Rang-eins-Präparation, n≥1 | eine Vertex-ID | exaktes klassisches Sampling | PROVEN |
| V-02/V-04 Vertex-Mittel | festes Präparationsinstrument | m Gewichte, sparse P | kein Kanal-Superoperator | PROVEN |
| E-06/V-05 Stationarität | endliche Ketten | SCC + lokale lineare Systeme | Klassen/Transienten korrekt behandeln | PROVEN + Standardtheorie |
| E-07/V-05 Perioden | tatsächlicher positiver Träger | gcd-Periodentest | schützt vor falschen Konvergenzclaims | PROVEN |
| E-04/V-03 Reduktion | Erreichbarkeit, exakte Atomgleichheit | kleinerer aktiver Zustandsraum | Speicher/CPU | PROVEN |
| E-08/NEW-02 Spektrum/Rang | endliche Dimension | Markovmatrix statt Supermatrix | Spektraldaten viel billiger | PROVEN / Paper |
| E-11 flache Coins | uniforme lokale Betragsquadrate | normierte Adjazenzmatrix | zusätzliche Graphreduktion | PROVEN |
| E-09/R-08 CLT | finite irreduzible Klasse | Poisson-Solve | korrekte Fehlerbalken | PROVEN mit Standard-CLT |
| E-13/E-15 Gauge | kanonische uniforme Edge-Ensembles | lokale Spaltenabgleiche | Modell-/Cachevergleich | PROVEN |
| R-01/R-02 RKHS | spezifizierter Kernel/Träger | Overlaps statt Tensorarrays | Maßvergleich/Identifizierbarkeit | PROVEN |
| R-06 Zweizeit | K invertierbar, positive stationäre Gewichte | Paarstatistik | Dynamikrekonstruktion | PROVEN |
| R-07 Residual/Lyapunov | irred.; Lyapunov zusätzlich aper. | dynamikangepasste Metrik | Stationaritäts-/Stabilitätsdiagnostik | PROVEN |
| NEW-01 volle Kanalgauge | feste Input-/Graphbasis | strengere Cache-Schlüssel | verhindert falsches Modell-Merging | PROVEN, Übergabeergänzung |
| NEW-03 Portmodell | explizite Reverse-Port-IDs, loopfrei | Vertex-Rang1 bleibt, Edge-Fallback | sichere Multigraphunterstützung | PROVEN, explizite Erweiterung |
| Infinite finite horizon | endliche kausale Reichweite oder Fehlerschranke | dynamisch sparse Graphbereiche | unendliche Modelle | CONDITIONAL |
| Optimale Mischung | kleine lokale Permutationsräume | vollständige Enumeration | optionale Forschungsanalyse | endliche Suche PROVEN; allgemeine Effizienz OPEN |

## 11.1 Notwendige Grundfunktionen

**Strukturelles Datenmodell:** stabile Vertex-, Arc- und optional Port-IDs; `source`, `target`, `reverse_arc`, geordnete Nachbarlisten; Graphklasse und Randbedingungen. Lokale S-Matrizen mit Validierung und Parameterversion. Vertex-Erweiterung mit ω,β; zusätzlich explizite χ-Präparationsmodelle, klar von „induced from edge“ unterschieden.

**Getrennte Engines:** unitärer Evolver, Edge-Instrument, Vertex-Präparationsinstrument. Für jedes Modell eine kleine dichte Referenzimplementation. Primitive Funktionen: `apply_unitary`, `apply_channel`, `outcome_probabilities`, `conditional_update`, `prepare_edge_q2`, `apply_M`, `build_vertex_preparations`, `apply_P`.

**Explizite Ausgabetypen:** `ConditionalState`, `MeanState`, `StateLaw`, `EmpiricalMeasure`, `BornDistribution`; komprimierte `EdgeAtom(arc_id)` und `VertexAtom(vertex_id)` mit lazy Rekonstruktion. Die Zeitstufe und Messphase sind Metadaten, etwa `after_scattering`, `after_measurement_before_scattering`, `next_measurement_distribution`.

**Validierung:** lokale Unitarität, ω-/χ-Normen, Hermitizität, Positivität, Spur1, vollständige Krausnormalisierung, M-Zeilen/Spalten- bzw. P-Zeilensummen. Große Verletzungen zurückweisen, nicht automatisch „reparieren“. Toleranzen dimensions-/konditionsgerecht wählen; die Tests verwenden kleine Float64-Fixtures mit 2·10⁻¹⁰ als Standardtoleranz.

**Reproduzierbarkeit:** injizierter RNG, Seed, Nachbarordnung, Parameterversion, Eingabezustand und Samplingalgorithmus protokollieren. Äquivalente Sampler müssen dasselbe Gesetz, nicht notwendigerweise denselben Record zu demselben Seed erzeugen.

## 11.2 Mathematisch begründete Optimierungen

Statische Übergangsspalten/-zeilen cachen; Edge-Warmstart auf Eingangsblöcke beschränken; danach Atom-IDs; Mittelwerte als Gewichtsvektoren; feste Observable atomweise vorrechnen; exakte Erreichbarkeit/Lumpability; SCC-basierte Stationäranalyse; Edge-Entropie/Purity aus q; flache Coins über normierte Adjazenz; physikalische Dichtematrizen nur auf Anforderung.

Jede Optimierung benötigt einen Vorbedingungscheck und Vergleich gegen den unabhängigen dichten Pfad. Der Referenzpfad darf nicht entfernt werden, nur weil die Optimierung bewiesen ist.

## 11.3 Optionale Erweiterungen

CLT-/Spektral-/MMD-Diagnostik, Zweizeitgesetze, Fluss-/Reversal-Tests, MASA-/Gaugevergleiche, Stern-/Grover-Spektraloracles, Poissonisierung, Entropieraten, Permutationsenumeration, Multigraphports und Infinite-Graph-Backends. Diese Erweiterungen müssen den Messvertrag der Grundmodelle sichtbar lassen.

## 11.4 Nicht als exakte Optimierung freigegeben

Unkontrolliertes Löschen kleiner Wahrscheinlichkeiten; toleranzbasiertes Atom-Clustering ohne Fehlerschranke; Ersetzen nichtlinearer Zustandsstatistiken durch f(mean); universelle Multigraph-Reinheit; allgemeine Vertex-Normalisatorquotienten; Phasenrekonstruktion allein aus P-Records; uniforme unendliche Normkonvergenz; Randtrunkierung ohne Kausal-/Tailnachweis.

# 12. Maschinenlesbare Spezifikation und Tests

`spec/mathematical_results.json` registriert alle 39 Ergebnis-IDs dieses Dokuments mit A–E-Texten, Voraussetzungen, Status, Quellen und Testverknüpfungen. Zusätzliche `contract`-Felder benennen mathematische Eingaben, Vorbedingungen, erwartete Ausgaben und Invarianten für Kernalgorithmen. Formeln sind LaTeX-/Formelstrings, kein automatisch ausführbarer Beweiser.

`spec/mathematical_results.schema.json` beschreibt die Datenstruktur. `spec/test_cases.json` verknüpft Test-IDs T01–T42 mit tatsächlichen Methoden. `spec/reference_fixtures.json` enthält einige unabhängig ausgeschriebene Benchmarkmatrizen. `tests/reference_checks.py` ist ein kleines NumPy-Test-Orakel, **kein Produktionssimulator**. `validation_report.json` dokumentiert den wirklich ausgeführten Lauf.

Beispielvertrag:

```json
{
  "id": "E-02",
  "proof_status": "PROVEN",
  "origin": "CHAT",
  "contract": {
    "model": "open_edge_sqw",
    "inputs": {
      "graph": "simple undirected loopless graph with fixed neighbor order",
      "scattering": "static local unitary matrices",
      "initial_state": "positive semidefinite trace-one density",
      "record_prefix": "vertex outcomes of positive cylinder probability"
    },
    "preconditions": ["measurement-before-unitary", "fully observed record", "n >= 2"],
    "outputs": {
      "state_tag": "EdgeAtom(target=X_n, source=X_(n-1))",
      "ket": "U|X_n X_(n-1)>",
      "density": "ket * ket.adjoint()"
    },
    "invariants": ["trace=1", "rank=1", "rho^2=rho"],
    "reject_for": ["parallel arcs with only coarse vertex measurement", "unobserved outcomes", "different instrument"]
  },
  "test_case_ids": ["T06", "T07", "T08", "T24"]
}
```

Ein Coding-Agent soll zuerst §0, E-01–E-05, V-01–V-05 und das Fehlerregister lesen. Danach die konkreten Algorithmen in §8 und die Verträge umsetzen. Die Behauptung „finite classical reduction“ ist exakt mathematisch; Floating-point-Arithmetik und Pseudozufall sind eine weitere numerische Ebene.

Mindesttests: komplexe reine und gemischte Inputs; dichter-vs-reduzierter Verlauf; Schritt0/1/2; Kohärenz-Gegenbeispiel für q₂; T3 H/I/Swap; Dreieck mit gleichem Maß und verschiedenen SLEMs; komplexes ω gegen RUR*; DFT-Transienten; negative Multigraph-Reinheitsprobe; bistochastisches aber nichtunitales Vertexbeispiel; Gauge-Unterschiede zwischen Ensembles und Kanälen. Die beigefügten42 Tests sind deterministische Identitätstests, keine flaky Monte-Carlo-p-value-Tests.

# 13. Quellen- und Literaturregister

Eine Quellenangabe behauptet nicht, dass jede konkrete SQW-Folgerung dort bereits so formuliert wurde. Der jeweilige A–E-Datensatz trennt direkte Quellenresultate und eigene Herleitungen. Es wurde keine erschöpfende Neuheitsrecherche durchgeführt.

**[J]** Alain Joye, *Unitary and Open Scattering Quantum Walks on Graphs*, arXiv:2409.08428v2, 9. April 2026. Maßgeblich: bereitgestellte PDF mit oben dokumentiertem Hash. https://arxiv.org/abs/2409.08428v2 . Definition2.1; (2.3)–(2.7); Lemmas2.3/2.7; §3.3/3.4; Definition4.2; Proposition4.3; Korollar4.5; §4.2/Proposition4.8; Theorem5.1; Lemma5.3; Proposition5.5; Korollar5.7; Definition6.1; Theorem6.2; Korollar6.4; §§5.1,5.2,6.1,6.2. Auditänderungen in §10 ausdrücklich gekennzeichnet.

**[PUR]** Hans Maassen, Burkhard Kümmerer, *Purification of quantum trajectories*, arXiv:quant-ph/0505084. https://arxiv.org/abs/quant-ph/0505084 . Allgemeiner Purifikations-/dunkler-Unterraum-Rahmen; unser Rang-eins-Beweis ist endlichzeitig und spezieller.

**[BFPP]** Tristan Benoist, Martin Fraas, Yan Pautrat, Clément Pellegrini, *Invariant Measure for Quantum Trajectories*, arXiv:1703.10773. https://arxiv.org/abs/1703.10773 . Theorem1.1 unter (Pur) und (phi-Erg) liefert exponentielle Wasserstein-Konvergenz einer Periodenblockmittelung. Nicht als aperiodizitätsfreier TV-Satz momentaner Gesetze zitieren.

**[KM]** Burkhard Kümmerer, Hans Maassen, *A Pathwise Ergodic Theorem for Quantum Trajectories*, arXiv:quant-ph/0406213; J. Phys. A37 (2004), 11889–11896. https://arxiv.org/abs/quant-ph/0406213 . Allgemeine pfadweise Zeitmittel; bei unseren endlichen Reduktionen genügt die klassische Kette.

**[BFP]** Tristan Benoist, Jan-Luka Fatras, Clément Pellegrini, *Limit theorems for Quantum Trajectories*, arXiv:2302.06191v2. https://arxiv.org/abs/2302.06191 . LLN, funktionaler CLT, iterierter Logarithmus und moderate Abweichungen; Poisson-Gleichung/Martingalapproximation. Der konkrete endliche Varianzbeweis steht hier in E-09.

**[EB]** Michael Horodecki, Peter W. Shor, Mary Beth Ruskai, *General Entanglement Breaking Channels*, arXiv:quant-ph/0302031; Rev. Math. Phys.15 (2003), 629–641. https://arxiv.org/abs/quant-ph/0302031 . Rang-eins-Kraus-/Measure-and-Prepare-/EB-Äquivalenz.

**[EBI]** Ludovico Lami, Vittorio Giovannetti, *Entanglement-Breaking Indices*, arXiv:1411.2517. https://arxiv.org/abs/1411.2517 . Allgemeine Iterationsindizes; exakter SQW-Index1/2 hier direkt bewiesen.

**[ZCV]** Paolo Zanardi, Lorenzo Campos Venuti, *Quantum coherence generating power, maximally abelian subalgebras, and Grassmannian Geometry*, arXiv:1706.07872v2; J. Math. Phys.59,012203 (2018). https://arxiv.org/abs/1706.07872 . Enger Literaturvorläufer für MASAs, Normalisatoren/Flaggenräume, Projektionsdistanz, Kommutatoren und Differentialgeometrie (insbesondere Propositionen1,4,6). Die quadratische MMD ist eine anders normierte Darstellung dieser bekannten Geometrie.

**[KME]** Bharath K. Sriperumbudur, Arthur Gretton, Kenji Fukumizu, Bernhard Schölkopf, Gert R. G. Lanckriet, *Hilbert Space Embeddings and Metrics on Probability Measures*, JMLR11 (2010), 1517–1561. https://www.jmlr.org/papers/v11/sriperumbudur10a.html . Charakteristische Kernel und Metriken von Maßen. Endliche Tensorinterpolation in R-02 ist separat bewiesen.

**[TRANSFER]** Stefan Klus, Ingmar Schuster, Krikamol Muandet, *Eigendecompositions of Transfer Operators in Reproducing Kernel Hilbert Spaces*, arXiv:1712.01572; Journal of Nonlinear Science (2019). https://arxiv.org/abs/1712.01572 . Transfer-/Conditional-Embedding-/Kernelkorrelationsrahmen; unsere Formeln sind exakte endliche Instanzen, keine Behauptung über die Genauigkeit eines generischen Approximationsverfahrens.

**[FRAME]** Tom Needham, Clayton Shonkwiler, *Symplectic Geometry and Connectivity of Spaces of Frames*, arXiv:1804.05899; Advances in Computational Mathematics47,5 (2021). https://arxiv.org/abs/1804.05899 . Momentenabbildungen von Frameoperator und Spaltennormen; stationäre SQW-Bilanz ist eine Spezialisierung.

**[CHEFLES]** Anthony Chefles, *Unambiguous Discrimination Between Linearly Dependent States With Multiple Copies*, arXiv:quant-ph/0105016v3; Phys. Rev. A64,062305 (2001). https://arxiv.org/abs/quant-ph/0105016 . Eq.(2.3): N≤C+D−1 als hinreichende Bedingung für lineare Unabhängigkeit von C-fachen Kopien. Nicht mit einer universell scharfen Minimalgradformel für Projektorgrammatrizen verwechseln.

**[DOYLE]** Peter G. Doyle, *The Kemeny constant of a Markov chain*, arXiv:0909.2636. https://arxiv.org/abs/0909.2636 . Fundamentalmatrix-, Spektral- und Fluktuationshintergrund.

**[MC]** J. R. Norris, *Markov Chains*, Cambridge University Press (1997); ergänzend David A. Levin, Yuval Peres, *Markov Chains and Mixing Times*, 2. Auflage, mit Beiträgen von Elizabeth L. Wilmer, AMS (2017). Feste Referenzausgaben zu Klassen, Perioden, Ergodensätzen und Mischung; Norris ist auch in [J] zitiert.

**[KIRCHHOFF]** Ivan Gutman, Bojan Mohar, *The quasi-Wiener and the Kirchhoff indices coincide*, J. Chem. Inf. Comput. Sci.36 (1996), 982–985. Verwendete Standardidentität \(\operatorname{Kf}(G)=m\sum_{j\ge2}\ell_j^{-1}\); die SQW-Verknüpfung E-12 ist hier hergeleitet.

**[LYAP]** Stephen Boyd, Stanford EE363, *Linear quadratic Lyapunov theory*, Abschnitt zur diskreten Lyapunov-Gleichung. https://web.stanford.edu/class/ee363/lectures/lq-lyap.pdf . Hintergrund der Reihenkonstruktion R-07.

## Abschließender Geltungsbereich

Die tragfähige Kette lautet: konkrete Krausstruktur → exakte reine Atomfamilie → klassische Labelkette → stationäre Maße/Grenzsätze; Lie- und RKHS-Geometrie klassifizieren beziehungsweise messen zusätzliche Zustandsinformation. Die meisten allgemeinen mathematischen Bausteine sind etablierte Theorie. Die im Dokument bewiesenen SQW-spezifischen Folgerungen lassen sich daraus als eigenständige Implementierungsverträge verwenden. Ungeprüfte Verallgemeinerungen, verdeckte Messwechsel und fragliche gedruckte Formeln sind nicht Teil dieser Freigabe.
