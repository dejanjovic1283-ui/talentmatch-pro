from __future__ import annotations

import json
import os
from collections.abc import Mapping
from typing import Final, TypeAlias, TypedDict, cast

import streamlit as st

from auth_utils import is_logged_in, is_pro_user, refresh_profile
from components.ui import (
    apply_global_styles,
    get_display_name,
    get_initials,
    render_page_intro,
    render_section_title,
    safe_html,
)
from i18n import get_locale


APP_URL: Final[str] = "https://talentmatchcv.com"
PRO_MONTHLY_PRICE: Final[str] = os.getenv("PRO_MONTHLY_PRICE", "$19").strip() or "$19"
OWNER_NAME: Final[str] = "Dejan Jović"
RELEASE_ID: Final[str] = "TMP-V3-FINAL-2026"


HeroAction: TypeAlias = tuple[str, str, str]
TrustItem: TypeAlias = tuple[str, str]
MetricItem: TypeAlias = tuple[str, str, str]
QuickAction: TypeAlias = tuple[str, str, str, str, str]
CoreFeature: TypeAlias = tuple[str, str, str]
AudienceCard: TypeAlias = tuple[str, str, str, tuple[str, ...]]
WorkflowStep: TypeAlias = tuple[str, str, str, str]
PricingPlan: TypeAlias = tuple[str, str, str, str, tuple[str, ...]]
ValueBlock: TypeAlias = tuple[str, str, tuple[str, ...]]
FinalBlock: TypeAlias = tuple[str, str, str, str, str, str]


class LocaleCatalog(TypedDict):
    seo_description: str
    hero_kicker: str
    hero_guest_title: str
    hero_user_title: str
    hero_subtitle: str
    workspace_badge: str
    hero_actions: tuple[HeroAction, ...]
    trust: tuple[TrustItem, ...]
    metrics: tuple[MetricItem, ...]
    quick_title: str
    quick_subtitle: str
    quick: tuple[QuickAction, ...]
    core_title: str
    core_subtitle: str
    core: tuple[CoreFeature, ...]
    audience_title: str
    audience_subtitle: str
    candidate: AudienceCard
    recruiter: AudienceCard
    workflow_title: str
    workflow_subtitle: str
    steps: tuple[WorkflowStep, ...]
    pricing_title: str
    pricing_subtitle: str
    free: PricingPlan
    pro: PricingPlan
    manage_plan: str
    value_title: str
    value: ValueBlock
    final: FinalBlock


COPY: Final[dict[str, LocaleCatalog]] = {
    "en": {
        "seo_description": "TalentMatch Pro is an AI-powered CV analysis and recruiter intelligence platform for ATS optimization, semantic matching, CV rewriting, candidate ranking, and professional reports.",
        "hero_kicker": "ENTERPRISE TALENT INTELLIGENCE",
        "hero_guest_title": "Build a stronger CV with AI",
        "hero_user_title": "Welcome back, {name}",
        "hero_subtitle": "Analyze CVs, improve ATS compatibility, compare semantic relevance, rewrite content, rank candidates, and export professional reports from one focused workspace.",
        "workspace_badge": "{plan} WORKSPACE",
        "hero_actions": (
            ("📄", "Start CV Analysis", "pages/cv_analysis.py"),
            ("📋", "Open ATS Checker", "pages/ats_checker.py"),
            ("💳", "View Pro plan", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "AI-powered workflows"),
            ("📄", "Professional reports"),
            ("🛡️", "Secure PayPal billing"),
        ),
        "metrics": (
            ("Workspace", "{plan}", "Your current membership and feature access"),
            ("AI tools", "6", "Analysis, ATS, Rewrite, Match, Recruiter, History"),
            ("Pro plan", "{price}", "Monthly subscription through PayPal"),
            ("Reports", "PDF", "TXT, CSV, and branded PDF exports"),
        ),
        "quick_title": "Quick actions",
        "quick_subtitle": "Open the workflows you use most without leaving your command center.",
        "quick": (
            ("📄", "Analyze CV", "Run a structured AI review against a real target role.", "pages/cv_analysis.py", "Open CV Analysis"),
            ("📋", "Check ATS", "Measure keyword coverage and prioritize missing terms.", "pages/ats_checker.py", "Open ATS Checker"),
            ("🧠", "Semantic Match", "Compare meaning, context, and recruiter readiness.", "pages/semantic_match.py", "Open Semantic Match"),
            ("👥", "Recruiter Workspace", "Rank candidates and manage the Candidate Database.", "pages/recruiter_mode.py", "Open Recruiter Mode"),
        ),
        "core_title": "Core workspace",
        "core_subtitle": "Every tool follows one consistent premium workflow from upload to export.",
        "core": (
            ("📄", "AI CV Analysis", "Compare a CV with a real job description and receive structured scores, strengths, gaps, and practical recommendations."),
            ("📋", "ATS Checker", "Identify matched and missing keywords so applications align more clearly with applicant tracking systems."),
            ("✍", "CV Rewrite AI", "Improve headlines, summaries, and experience bullets while preserving truthful candidate information."),
            ("🧠", "Semantic Match", "Compare meaning and context—not only exact keyword overlap—and evaluate recruiter readiness."),
            ("👥", "Recruiter Workspace", "Rank candidates, save results, manage status, favorites, notes, tags, and exports."),
            ("📥", "Professional Reports", "Export consistent TXT, CSV, and branded PDF reports for applications and recruiter workflows."),
        ),
        "audience_title": "Built for candidates and recruiters",
        "audience_subtitle": "One product, two focused workflows, and one consistent decision-support system.",
        "candidate": (
            "CANDIDATE WORKSPACE",
            "Improve every application",
            "Use AI analysis, ATS intelligence, semantic matching, and CV rewriting to strengthen relevance before applying.",
            ("Role-specific CV insights", "ATS keyword prioritization", "Downloadable professional reports"),
        ),
        "recruiter": (
            "RECRUITER WORKSPACE",
            "Make faster hiring decisions",
            "Rank candidates, store profiles, manage statuses, add notes and tags, and export decision-ready reports.",
            ("Candidate ranking and comparison", "Candidate Database management", "CSV, TXT, and PDF exports"),
        ),
        "workflow_title": "How TalentMatch Pro works",
        "workflow_subtitle": "A focused three-step process from source CV to actionable decision support.",
        "steps": (
            ("1", "Step 1", "Upload CV", "Secure PDF intake and validation"),
            ("2", "Step 2", "Add target role", "Use the exact job description"),
            ("3", "Step 3", "Get insights", "Scores, gaps, rewrites, and reports"),
        ),
        "pricing_title": "Simple plans",
        "pricing_subtitle": "Start free, then unlock the complete workflow through PayPal.",
        "free": ("STARTER", "Free", "$0", "Explore the core workflow before upgrading.", ("3 CV analyses", "ATS Checker access", "TXT exports")),
        "pro": ("MOST COMPLETE", "Pro", "/month", "The complete premium workflow for serious job search and recruiter use.", ("Unlimited analyses", "Professional PDF reports", "Semantic Match", "Recruiter Mode", "Candidate Database")),
        "manage_plan": "View plans or manage PayPal subscription",
        "value_title": "Why TalentMatch Pro?",
        "value": (
            "One premium workspace for better career and hiring decisions",
            "TalentMatch Pro combines AI CV analysis, ATS optimization, semantic matching, CV rewrite assistance, recruiter workflows, Candidate Database management, and downloadable reports in one consistent SaaS workspace.",
            ("Focused AI instead of generic advice", "Candidate and recruiter workflows in one product", "Clear outputs that can be reviewed, saved, and shared"),
        ),
        "final": (
            "Turn every CV into a clearer decision",
            "Start with a CV, add a real role, and let TalentMatch Pro transform the comparison into structured, actionable intelligence.",
            "Analyze a CV now",
            "Explore pricing",
            "Founder & Owner",
            "Original SaaS Product",
        ),
    },
    "sr_latn": {
        "seo_description": "TalentMatch Pro je AI platforma za analizu CV-a i regrutersku inteligenciju, ATS optimizaciju, semantičko podudaranje, prepravku CV-a, rangiranje kandidata i profesionalne izveštaje.",
        "hero_kicker": "ENTERPRISE INTELIGENCIJA ZA TALENTE",
        "hero_guest_title": "Napravite snažniji CV uz AI",
        "hero_user_title": "Dobro došli, {name}",
        "hero_subtitle": "Analizirajte CV, poboljšajte ATS kompatibilnost, uporedite semantičku relevantnost, unapredite sadržaj, rangirajte kandidate i izvezite profesionalne izveštaje iz jednog radnog prostora.",
        "workspace_badge": "{plan} RADNI PROSTOR",
        "hero_actions": (
            ("📄", "Pokreni analizu CV-a", "pages/cv_analysis.py"),
            ("📋", "Otvori ATS proveru", "pages/ats_checker.py"),
            ("💳", "Pogledaj Pro plan", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "AI radni tokovi"),
            ("📄", "Profesionalni izveštaji"),
            ("🛡️", "Bezbedno PayPal plaćanje"),
        ),
        "metrics": (
            ("Radni prostor", "{plan}", "Vaše trenutno članstvo i pristup funkcijama"),
            ("AI alati", "6", "Analiza, ATS, prepravka, podudaranje, regruter, istorija"),
            ("Pro plan", "{price}", "Mesečna pretplata preko PayPal-a"),
            ("Izveštaji", "PDF", "TXT, CSV i brendirani PDF izvoz"),
        ),
        "quick_title": "Brze akcije",
        "quick_subtitle": "Otvorite najčešće radne tokove bez napuštanja komandnog centra.",
        "quick": (
            ("📄", "Analiziraj CV", "Pokrenite strukturiranu AI analizu prema stvarnoj ciljnoj poziciji.", "pages/cv_analysis.py", "Otvori analizu CV-a"),
            ("📋", "Proveri ATS", "Izmerite pokrivenost ključnih reči i odredite prioritete.", "pages/ats_checker.py", "Otvori ATS proveru"),
            ("🧠", "Semantičko podudaranje", "Uporedite značenje, kontekst i spremnost za regrutera.", "pages/semantic_match.py", "Otvori Semantic Match"),
            ("👥", "Regruterski radni prostor", "Rangirajte kandidate i upravljajte Bazom kandidata.", "pages/recruiter_mode.py", "Otvori Recruiter Mode"),
        ),
        "core_title": "Glavni radni prostor",
        "core_subtitle": "Svaki alat prati isti premium tok od učitavanja do izvoza.",
        "core": (
            ("📄", "AI analiza CV-a", "Uporedite CV sa stvarnim opisom posla i dobijte strukturirane rezultate, prednosti, nedostatke i preporuke."),
            ("📋", "ATS provera", "Prepoznajte pronađene i nedostajuće ključne reči radi boljeg usklađivanja sa ATS sistemima."),
            ("✍", "AI prepravka CV-a", "Unapredite naslov, sažetak i iskustvo uz očuvanje istinitih podataka kandidata."),
            ("🧠", "Semantičko podudaranje", "Uporedite značenje i kontekst, a ne samo identične ključne reči."),
            ("👥", "Regruterski radni prostor", "Rangirajte kandidate, čuvajte rezultate i upravljajte statusima, beleškama, oznakama i izvozom."),
            ("📥", "Profesionalni izveštaji", "Izvezite konzistentne TXT, CSV i brendirane PDF izveštaje."),
        ),
        "audience_title": "Napravljeno za kandidate i regrutere",
        "audience_subtitle": "Jedan proizvod, dva fokusirana toka rada i jedinstven sistem za donošenje odluka.",
        "candidate": (
            "RADNI PROSTOR KANDIDATA",
            "Unapredite svaku prijavu",
            "Koristite AI analizu, ATS inteligenciju, semantičko podudaranje i prepravku CV-a pre prijavljivanja.",
            ("Uvidi prilagođeni konkretnoj ulozi", "Prioriteti ATS ključnih reči", "Profesionalni izveštaji za preuzimanje"),
        ),
        "recruiter": (
            "REGRUTERSKI RADNI PROSTOR",
            "Donosite brže odluke o zapošljavanju",
            "Rangirajte kandidate, čuvajte profile, upravljajte statusima, beleškama i izveštajima.",
            ("Rangiranje i poređenje kandidata", "Upravljanje Bazom kandidata", "CSV, TXT i PDF izvoz"),
        ),
        "workflow_title": "Kako TalentMatch Pro radi",
        "workflow_subtitle": "Fokusiran proces u tri koraka od CV-a do korisnih odluka.",
        "steps": (
            ("1", "Korak 1", "Učitajte CV", "Bezbedan unos i validacija PDF-a"),
            ("2", "Korak 2", "Dodajte ciljnu ulogu", "Koristite tačan opis posla"),
            ("3", "Korak 3", "Dobijte uvide", "Rezultati, nedostaci, prepravke i izveštaji"),
        ),
        "pricing_title": "Jednostavni planovi",
        "pricing_subtitle": "Počnite besplatno, a zatim otključajte ceo tok preko PayPal-a.",
        "free": ("POČETNI", "Besplatno", "$0", "Istražite osnovni tok pre nadogradnje.", ("3 analize CV-a", "Pristup ATS proveri", "TXT izvoz")),
        "pro": ("NAJKOMPLETNIJI", "Pro", "/mesečno", "Kompletan premium tok za ozbiljnu potragu za poslom i regrutere.", ("Neograničene analize", "Profesionalni PDF izveštaji", "Semantičko podudaranje", "Regruterski režim", "Baza kandidata")),
        "manage_plan": "Pogledaj planove ili upravljaj PayPal pretplatom",
        "value_title": "Zašto TalentMatch Pro?",
        "value": (
            "Jedan premium radni prostor za bolje karijerne i poslovne odluke",
            "TalentMatch Pro objedinjuje AI analizu CV-a, ATS optimizaciju, semantičko podudaranje, prepravku CV-a, regruterske tokove, Bazu kandidata i izveštaje.",
            ("Fokusiran AI umesto generičkih saveta", "Tokovi za kandidate i regrutere u jednom proizvodu", "Jasni rezultati koji se mogu čuvati i deliti"),
        ),
        "final": (
            "Pretvorite svaki CV u jasniju odluku",
            "Počnite sa CV-em, dodajte stvarnu ulogu i pretvorite poređenje u strukturirane uvide.",
            "Analiziraj CV sada",
            "Pogledaj cenovnik",
            "Osnivač i vlasnik",
            "Originalni SaaS proizvod",
        ),
    },
}


def _clone_locale(
    *,
    seo_description: str,
    hero_kicker: str,
    hero_guest_title: str,
    hero_user_title: str,
    hero_subtitle: str,
    workspace_badge: str,
    labels: Mapping[str, object],
) -> LocaleCatalog:
    """Create a complete locale using English structure and localized key content."""
    locale: dict[str, object] = dict(COPY["en"])
    locale.update(
        {
            "seo_description": seo_description,
            "hero_kicker": hero_kicker,
            "hero_guest_title": hero_guest_title,
            "hero_user_title": hero_user_title,
            "hero_subtitle": hero_subtitle,
            "workspace_badge": workspace_badge,
        }
    )
    locale.update(labels)
    return cast(LocaleCatalog, locale)


COPY["de"] = _clone_locale(
    seo_description="TalentMatch Pro ist eine KI-Plattform für Lebenslaufanalyse, ATS-Optimierung, semantischen Abgleich, Kandidatenranking und professionelle Berichte.",
    hero_kicker="ENTERPRISE TALENT INTELLIGENCE",
    hero_guest_title="Erstellen Sie einen stärkeren Lebenslauf mit KI",
    hero_user_title="Willkommen zurück, {name}",
    hero_subtitle="Analysieren Sie Lebensläufe, verbessern Sie die ATS-Kompatibilität, vergleichen Sie semantische Relevanz und exportieren Sie professionelle Berichte aus einem Arbeitsbereich.",
    workspace_badge="{plan} ARBEITSBEREICH",
    labels={
        "hero_actions": (("📄", "Lebenslaufanalyse starten", "pages/cv_analysis.py"), ("📋", "ATS-Prüfung öffnen", "pages/ats_checker.py"), ("💳", "Pro-Plan ansehen", "pages/pricing.py")),
        "trust": (("🤖", "KI-gestützte Arbeitsabläufe"), ("📄", "Professionelle Berichte"), ("🛡️", "Sichere PayPal-Abrechnung")),
        "metrics": (
            ("Arbeitsbereich", "{plan}", "Ihre aktuelle Mitgliedschaft und Ihr Funktionszugang"),
            ("KI-Werkzeuge", "6", "Analyse, ATS, Überarbeitung, Abgleich, Recruiter, Verlauf"),
            ("Pro-Plan", "{price}", "Monatliches Abonnement über PayPal"),
            ("Berichte", "PDF", "TXT-, CSV- und gebrandete PDF-Exporte"),
        ),
        "quick_title": "Schnellaktionen",
        "quick_subtitle": "Öffnen Sie Ihre wichtigsten Arbeitsabläufe direkt aus dem Command Center.",
        "quick": (
            ("📄", "Lebenslauf analysieren", "Führen Sie eine strukturierte KI-Prüfung für eine reale Zielrolle durch.", "pages/cv_analysis.py", "Lebenslaufanalyse öffnen"),
            ("📋", "ATS prüfen", "Messen Sie die Keyword-Abdeckung und priorisieren Sie fehlende Begriffe.", "pages/ats_checker.py", "ATS-Prüfung öffnen"),
            ("🧠", "Semantischer Abgleich", "Vergleichen Sie Bedeutung, Kontext und Recruiter-Bereitschaft.", "pages/semantic_match.py", "Semantischen Abgleich öffnen"),
            ("👥", "Recruiter-Arbeitsbereich", "Rangieren Sie Kandidaten und verwalten Sie die Kandidatendatenbank.", "pages/recruiter_mode.py", "Recruiter-Modus öffnen"),
        ),
        "core_title": "Zentraler Arbeitsbereich",
        "core_subtitle": "Jedes Werkzeug folgt demselben Premium-Ablauf vom Upload bis zum Export.",
        "core": (
            ("📄", "KI-Lebenslaufanalyse", "Vergleichen Sie einen Lebenslauf mit einer realen Stellenbeschreibung und erhalten Sie strukturierte Bewertungen, Stärken, Lücken und Empfehlungen."),
            ("📋", "ATS-Prüfung", "Erkennen Sie vorhandene und fehlende Keywords für eine klarere Abstimmung mit Bewerbermanagementsystemen."),
            ("✍", "KI-Lebenslaufüberarbeitung", "Verbessern Sie Überschriften, Zusammenfassungen und Erfahrungspunkte, ohne Kandidateninformationen zu verfälschen."),
            ("🧠", "Semantischer Abgleich", "Vergleichen Sie Bedeutung und Kontext statt nur exakter Keyword-Überschneidungen."),
            ("👥", "Recruiter-Arbeitsbereich", "Rangieren Sie Kandidaten und verwalten Sie Ergebnisse, Status, Favoriten, Notizen, Tags und Exporte."),
            ("📥", "Professionelle Berichte", "Exportieren Sie konsistente TXT-, CSV- und gebrandete PDF-Berichte."),
        ),
        "audience_title": "Für Bewerbende und Recruiter entwickelt",
        "audience_subtitle": "Ein Produkt, zwei fokussierte Arbeitsabläufe und ein konsistentes Entscheidungssystem.",
        "candidate": (
            "BEWERBER-ARBEITSBEREICH",
            "Verbessern Sie jede Bewerbung",
            "Nutzen Sie KI-Analyse, ATS-Intelligenz, semantischen Abgleich und Lebenslaufüberarbeitung vor der Bewerbung.",
            ("Rollenspezifische Lebenslaufeinblicke", "Priorisierung von ATS-Keywords", "Herunterladbare professionelle Berichte"),
        ),
        "recruiter": (
            "RECRUITER-ARBEITSBEREICH",
            "Treffen Sie schnellere Einstellungsentscheidungen",
            "Rangieren Sie Kandidaten, speichern Sie Profile, verwalten Sie Status, Notizen, Tags und entscheidungsreife Berichte.",
            ("Kandidatenranking und -vergleich", "Verwaltung der Kandidatendatenbank", "CSV-, TXT- und PDF-Exporte"),
        ),
        "workflow_title": "So funktioniert TalentMatch Pro",
        "workflow_subtitle": "Ein klarer Drei-Schritte-Prozess vom Lebenslauf bis zur umsetzbaren Entscheidung.",
        "steps": (
            ("1", "Schritt 1", "Lebenslauf hochladen", "Sichere PDF-Übernahme und Validierung"),
            ("2", "Schritt 2", "Zielrolle hinzufügen", "Verwenden Sie die exakte Stellenbeschreibung"),
            ("3", "Schritt 3", "Einblicke erhalten", "Bewertungen, Lücken, Überarbeitungen und Berichte"),
        ),
        "pricing_title": "Einfache Pläne",
        "pricing_subtitle": "Kostenlos starten und den vollständigen Ablauf über PayPal freischalten.",
        "free": ("STARTER", "Kostenlos", "$0", "Testen Sie den Kernablauf vor dem Upgrade.", ("3 Lebenslaufanalysen", "ATS-Prüfung", "TXT-Exporte")),
        "pro": ("VOLLSTÄNDIG", "Pro", "/Monat", "Der vollständige Premium-Ablauf für Bewerbende und Recruiter.", ("Unbegrenzte Analysen", "Professionelle PDF-Berichte", "Semantischer Abgleich", "Recruiter-Modus", "Kandidatendatenbank")),
        "manage_plan": "Pläne ansehen oder PayPal-Abonnement verwalten",
        "value_title": "Warum TalentMatch Pro?",
        "value": (
            "Ein Premium-Arbeitsbereich für bessere Karriere- und Einstellungsentscheidungen",
            "TalentMatch Pro verbindet KI-Lebenslaufanalyse, ATS-Optimierung, semantischen Abgleich, Überarbeitung, Recruiter-Workflows, Kandidatendatenbank und Berichte.",
            ("Fokussierte KI statt allgemeiner Ratschläge", "Bewerber- und Recruiter-Workflows in einem Produkt", "Klare Ergebnisse zum Prüfen, Speichern und Teilen"),
        ),
        "final": ("Machen Sie aus jedem Lebenslauf eine klarere Entscheidung", "Starten Sie mit einem Lebenslauf, fügen Sie eine echte Stelle hinzu und erhalten Sie strukturierte, umsetzbare Erkenntnisse.", "Lebenslauf jetzt analysieren", "Preise ansehen", "Gründer & Inhaber", "Originales SaaS-Produkt"),
    },
)

COPY["fr"] = _clone_locale(
    seo_description="TalentMatch Pro est une plateforme d’analyse de CV et d’intelligence recruteur par IA pour l’optimisation ATS, la correspondance sémantique et les rapports professionnels.",
    hero_kicker="INTELLIGENCE DES TALENTS D’ENTREPRISE",
    hero_guest_title="Créez un CV plus performant avec l’IA",
    hero_user_title="Bon retour, {name}",
    hero_subtitle="Analysez les CV, améliorez la compatibilité ATS, comparez la pertinence sémantique et exportez des rapports professionnels depuis un seul espace.",
    workspace_badge="ESPACE {plan}",
    labels={
        "hero_actions": (("📄", "Démarrer l’analyse du CV", "pages/cv_analysis.py"), ("📋", "Ouvrir la vérification ATS", "pages/ats_checker.py"), ("💳", "Voir l’offre Pro", "pages/pricing.py")),
        "trust": (("🤖", "Flux de travail par IA"), ("📄", "Rapports professionnels"), ("🛡️", "Paiement PayPal sécurisé")),
        "metrics": (
            ("Espace", "{plan}", "Votre abonnement actuel et l’accès aux fonctionnalités"),
            ("Outils IA", "6", "Analyse, ATS, réécriture, correspondance, recruteur, historique"),
            ("Offre Pro", "{price}", "Abonnement mensuel via PayPal"),
            ("Rapports", "PDF", "Exports TXT, CSV et PDF de marque"),
        ),
        "quick_title": "Actions rapides",
        "quick_subtitle": "Ouvrez vos flux essentiels sans quitter le centre de commande.",
        "quick": (
            ("📄", "Analyser le CV", "Lancez une analyse IA structurée pour un poste cible réel.", "pages/cv_analysis.py", "Ouvrir l’analyse de CV"),
            ("📋", "Vérifier l’ATS", "Mesurez la couverture des mots-clés et priorisez les éléments manquants.", "pages/ats_checker.py", "Ouvrir la vérification ATS"),
            ("🧠", "Correspondance sémantique", "Comparez le sens, le contexte et la préparation au recrutement.", "pages/semantic_match.py", "Ouvrir la correspondance"),
            ("👥", "Espace recruteur", "Classez les candidats et gérez la base de candidats.", "pages/recruiter_mode.py", "Ouvrir le mode recruteur"),
        ),
        "core_title": "Espace principal",
        "core_subtitle": "Chaque outil suit le même flux premium, du téléchargement à l’export.",
        "core": (
            ("📄", "Analyse de CV par IA", "Comparez un CV à une offre réelle et obtenez des scores, forces, écarts et recommandations structurés."),
            ("📋", "Vérificateur ATS", "Identifiez les mots-clés présents et manquants pour mieux aligner la candidature avec les systèmes ATS."),
            ("✍", "Réécriture de CV par IA", "Améliorez les titres, résumés et expériences sans modifier les informations véridiques."),
            ("🧠", "Correspondance sémantique", "Comparez le sens et le contexte, pas seulement les mots-clés identiques."),
            ("👥", "Espace recruteur", "Classez les candidats et gérez résultats, statuts, favoris, notes, tags et exports."),
            ("📥", "Rapports professionnels", "Exportez des rapports TXT, CSV et PDF de marque cohérents."),
        ),
        "audience_title": "Conçu pour les candidats et les recruteurs",
        "audience_subtitle": "Un produit, deux flux ciblés et un système cohérent d’aide à la décision.",
        "candidate": (
            "ESPACE CANDIDAT",
            "Améliorez chaque candidature",
            "Utilisez l’analyse IA, l’intelligence ATS, la correspondance sémantique et la réécriture avant de postuler.",
            ("Informations adaptées au poste", "Priorisation des mots-clés ATS", "Rapports professionnels téléchargeables"),
        ),
        "recruiter": (
            "ESPACE RECRUTEUR",
            "Prenez des décisions de recrutement plus rapides",
            "Classez les candidats, stockez les profils et gérez les statuts, notes, tags et rapports.",
            ("Classement et comparaison des candidats", "Gestion de la base de candidats", "Exports CSV, TXT et PDF"),
        ),
        "workflow_title": "Comment fonctionne TalentMatch Pro",
        "workflow_subtitle": "Un processus clair en trois étapes, du CV aux décisions exploitables.",
        "steps": (
            ("1", "Étape 1", "Télécharger le CV", "Réception et validation sécurisées du PDF"),
            ("2", "Étape 2", "Ajouter le poste cible", "Utilisez la description exacte du poste"),
            ("3", "Étape 3", "Obtenir les résultats", "Scores, écarts, réécritures et rapports"),
        ),
        "pricing_title": "Des offres simples",
        "pricing_subtitle": "Commencez gratuitement puis débloquez le flux complet avec PayPal.",
        "free": ("DÉCOUVERTE", "Gratuit", "$0", "Explorez le flux principal avant de passer à Pro.", ("3 analyses de CV", "Vérification ATS", "Exports TXT")),
        "pro": ("LE PLUS COMPLET", "Pro", "/mois", "Le flux premium complet pour les candidats et les recruteurs.", ("Analyses illimitées", "Rapports PDF professionnels", "Correspondance sémantique", "Mode recruteur", "Base de candidats")),
        "manage_plan": "Voir les offres ou gérer l’abonnement PayPal",
        "value_title": "Pourquoi TalentMatch Pro ?",
        "value": (
            "Un espace premium pour de meilleures décisions de carrière et de recrutement",
            "TalentMatch Pro réunit analyse de CV par IA, optimisation ATS, correspondance sémantique, réécriture, flux recruteur, base de candidats et rapports.",
            ("Une IA ciblée plutôt que des conseils génériques", "Flux candidats et recruteurs dans un seul produit", "Résultats clairs à consulter, enregistrer et partager"),
        ),
        "final": ("Transformez chaque CV en décision plus claire", "Commencez avec un CV, ajoutez un poste réel et obtenez des informations structurées et exploitables.", "Analyser un CV maintenant", "Voir les tarifs", "Fondateur et propriétaire", "Produit SaaS original"),
    },
)

COPY["es"] = _clone_locale(
    seo_description="TalentMatch Pro es una plataforma de análisis de CV e inteligencia de reclutamiento con IA para optimización ATS, coincidencia semántica y reportes profesionales.",
    hero_kicker="INTELIGENCIA EMPRESARIAL DE TALENTO",
    hero_guest_title="Crea un CV más sólido con IA",
    hero_user_title="Bienvenido de nuevo, {name}",
    hero_subtitle="Analiza currículums, mejora la compatibilidad ATS, compara la relevancia semántica y exporta reportes profesionales desde un solo espacio.",
    workspace_badge="ESPACIO {plan}",
    labels={
        "hero_actions": (("📄", "Iniciar análisis de CV", "pages/cv_analysis.py"), ("📋", "Abrir comprobador ATS", "pages/ats_checker.py"), ("💳", "Ver plan Pro", "pages/pricing.py")),
        "trust": (("🤖", "Flujos con IA"), ("📄", "Reportes profesionales"), ("🛡️", "Pago seguro con PayPal")),
        "metrics": (
            ("Espacio", "{plan}", "Tu membresía actual y acceso a funciones"),
            ("Herramientas IA", "6", "Análisis, ATS, reescritura, coincidencia, reclutador, historial"),
            ("Plan Pro", "{price}", "Suscripción mensual mediante PayPal"),
            ("Reportes", "PDF", "Exportaciones TXT, CSV y PDF con marca"),
        ),
        "quick_title": "Acciones rápidas",
        "quick_subtitle": "Abre tus flujos principales sin salir del centro de control.",
        "quick": (
            ("📄", "Analizar CV", "Ejecuta una revisión estructurada con IA para un puesto objetivo real.", "pages/cv_analysis.py", "Abrir análisis de CV"),
            ("📋", "Comprobar ATS", "Mide la cobertura de palabras clave y prioriza las que faltan.", "pages/ats_checker.py", "Abrir comprobador ATS"),
            ("🧠", "Coincidencia semántica", "Compara significado, contexto y preparación para reclutadores.", "pages/semantic_match.py", "Abrir coincidencia semántica"),
            ("👥", "Espacio de reclutamiento", "Clasifica candidatos y gestiona la Base de candidatos.", "pages/recruiter_mode.py", "Abrir modo reclutador"),
        ),
        "core_title": "Espacio principal",
        "core_subtitle": "Cada herramienta sigue el mismo flujo premium desde la carga hasta la exportación.",
        "core": (
            ("📄", "Análisis de CV con IA", "Compara un CV con una oferta real y recibe puntuaciones, fortalezas, brechas y recomendaciones estructuradas."),
            ("📋", "Comprobador ATS", "Identifica palabras clave presentes y ausentes para alinear mejor la candidatura con sistemas ATS."),
            ("✍", "Reescritura de CV con IA", "Mejora titulares, resúmenes y experiencia sin alterar información veraz."),
            ("🧠", "Coincidencia semántica", "Compara significado y contexto, no solo coincidencias exactas de palabras."),
            ("👥", "Espacio de reclutamiento", "Clasifica candidatos y gestiona resultados, estados, favoritos, notas, etiquetas y exportaciones."),
            ("📥", "Reportes profesionales", "Exporta reportes TXT, CSV y PDF con marca de forma coherente."),
        ),
        "audience_title": "Creado para candidatos y reclutadores",
        "audience_subtitle": "Un producto, dos flujos enfocados y un sistema coherente de apoyo a decisiones.",
        "candidate": (
            "ESPACIO DEL CANDIDATO",
            "Mejora cada candidatura",
            "Usa análisis con IA, inteligencia ATS, coincidencia semántica y reescritura antes de postularte.",
            ("Información específica para el puesto", "Priorización de palabras clave ATS", "Reportes profesionales descargables"),
        ),
        "recruiter": (
            "ESPACIO DEL RECLUTADOR",
            "Toma decisiones de contratación más rápidas",
            "Clasifica candidatos, guarda perfiles y gestiona estados, notas, etiquetas y reportes.",
            ("Clasificación y comparación de candidatos", "Gestión de la Base de candidatos", "Exportaciones CSV, TXT y PDF"),
        ),
        "workflow_title": "Cómo funciona TalentMatch Pro",
        "workflow_subtitle": "Un proceso claro de tres pasos desde el CV hasta decisiones prácticas.",
        "steps": (
            ("1", "Paso 1", "Cargar CV", "Recepción y validación segura del PDF"),
            ("2", "Paso 2", "Añadir puesto objetivo", "Usa la descripción exacta del puesto"),
            ("3", "Paso 3", "Obtener resultados", "Puntuaciones, brechas, reescrituras y reportes"),
        ),
        "pricing_title": "Planes sencillos",
        "pricing_subtitle": "Empieza gratis y desbloquea el flujo completo mediante PayPal.",
        "free": ("INICIAL", "Gratis", "$0", "Explora el flujo principal antes de mejorar el plan.", ("3 análisis de CV", "Comprobador ATS", "Exportaciones TXT")),
        "pro": ("MÁS COMPLETO", "Pro", "/mes", "El flujo premium completo para candidatos y reclutadores.", ("Análisis ilimitados", "Reportes PDF profesionales", "Coincidencia semántica", "Modo reclutador", "Base de candidatos")),
        "manage_plan": "Ver planes o gestionar la suscripción de PayPal",
        "value_title": "¿Por qué TalentMatch Pro?",
        "value": (
            "Un espacio premium para mejores decisiones profesionales y de contratación",
            "TalentMatch Pro reúne análisis de CV con IA, optimización ATS, coincidencia semántica, reescritura, flujos de reclutamiento, Base de candidatos y reportes.",
            ("IA enfocada en lugar de consejos genéricos", "Flujos para candidatos y reclutadores en un producto", "Resultados claros para revisar, guardar y compartir"),
        ),
        "final": ("Convierte cada CV en una decisión más clara", "Empieza con un CV, añade un puesto real y obtén información estructurada y práctica.", "Analizar un CV ahora", "Ver precios", "Fundador y propietario", "Producto SaaS original"),
    },
)

COPY["it"] = _clone_locale(
    seo_description="TalentMatch Pro è una piattaforma di analisi CV e intelligence recruiter basata sull’IA per ottimizzazione ATS, corrispondenza semantica e report professionali.",
    hero_kicker="INTELLIGENCE AZIENDALE DEI TALENTI",
    hero_guest_title="Crea un CV più efficace con l’IA",
    hero_user_title="Bentornato, {name}",
    hero_subtitle="Analizza i CV, migliora la compatibilità ATS, confronta la rilevanza semantica ed esporta report professionali da un unico spazio.",
    workspace_badge="AREA {plan}",
    labels={
        "hero_actions": (("📄", "Avvia analisi CV", "pages/cv_analysis.py"), ("📋", "Apri controllo ATS", "pages/ats_checker.py"), ("💳", "Vedi piano Pro", "pages/pricing.py")),
        "trust": (("🤖", "Flussi basati sull’IA"), ("📄", "Report professionali"), ("🛡️", "Pagamento PayPal sicuro")),
        "metrics": (
            ("Area", "{plan}", "Il tuo abbonamento attuale e l’accesso alle funzioni"),
            ("Strumenti IA", "6", "Analisi, ATS, riscrittura, corrispondenza, recruiter, cronologia"),
            ("Piano Pro", "{price}", "Abbonamento mensile tramite PayPal"),
            ("Report", "PDF", "Esportazioni TXT, CSV e PDF con marchio"),
        ),
        "quick_title": "Azioni rapide",
        "quick_subtitle": "Apri i flussi principali senza lasciare il centro di controllo.",
        "quick": (
            ("📄", "Analizza CV", "Esegui una revisione strutturata con IA per un ruolo obiettivo reale.", "pages/cv_analysis.py", "Apri analisi CV"),
            ("📋", "Controlla ATS", "Misura la copertura delle parole chiave e dai priorità a quelle mancanti.", "pages/ats_checker.py", "Apri controllo ATS"),
            ("🧠", "Corrispondenza semantica", "Confronta significato, contesto e preparazione per il recruiter.", "pages/semantic_match.py", "Apri corrispondenza"),
            ("👥", "Area recruiter", "Classifica i candidati e gestisci il Database candidati.", "pages/recruiter_mode.py", "Apri modalità recruiter"),
        ),
        "core_title": "Area principale",
        "core_subtitle": "Ogni strumento segue lo stesso flusso premium dal caricamento all’esportazione.",
        "core": (
            ("📄", "Analisi CV con IA", "Confronta un CV con un annuncio reale e ricevi punteggi, punti di forza, lacune e raccomandazioni strutturate."),
            ("📋", "Controllo ATS", "Individua parole chiave presenti e mancanti per allineare meglio la candidatura ai sistemi ATS."),
            ("✍", "Riscrittura CV con IA", "Migliora titoli, riepiloghi ed esperienze senza alterare informazioni veritiere."),
            ("🧠", "Corrispondenza semantica", "Confronta significato e contesto, non solo parole chiave identiche."),
            ("👥", "Area recruiter", "Classifica candidati e gestisci risultati, stati, preferiti, note, tag ed esportazioni."),
            ("📥", "Report professionali", "Esporta report TXT, CSV e PDF con marchio in modo coerente."),
        ),
        "audience_title": "Creato per candidati e recruiter",
        "audience_subtitle": "Un prodotto, due flussi mirati e un sistema coerente di supporto alle decisioni.",
        "candidate": (
            "AREA CANDIDATO",
            "Migliora ogni candidatura",
            "Usa analisi IA, intelligence ATS, corrispondenza semantica e riscrittura prima di candidarti.",
            ("Informazioni specifiche per il ruolo", "Priorità delle parole chiave ATS", "Report professionali scaricabili"),
        ),
        "recruiter": (
            "AREA RECRUITER",
            "Prendi decisioni di assunzione più rapide",
            "Classifica candidati, salva profili e gestisci stati, note, tag e report.",
            ("Classifica e confronto dei candidati", "Gestione del Database candidati", "Esportazioni CSV, TXT e PDF"),
        ),
        "workflow_title": "Come funziona TalentMatch Pro",
        "workflow_subtitle": "Un processo chiaro in tre passaggi dal CV alle decisioni operative.",
        "steps": (
            ("1", "Passaggio 1", "Carica CV", "Acquisizione e convalida sicure del PDF"),
            ("2", "Passaggio 2", "Aggiungi ruolo obiettivo", "Usa la descrizione esatta del lavoro"),
            ("3", "Passaggio 3", "Ottieni risultati", "Punteggi, lacune, riscritture e report"),
        ),
        "pricing_title": "Piani semplici",
        "pricing_subtitle": "Inizia gratis e sblocca il flusso completo tramite PayPal.",
        "free": ("INIZIALE", "Gratuito", "$0", "Esplora il flusso principale prima dell’upgrade.", ("3 analisi CV", "Controllo ATS", "Esportazioni TXT")),
        "pro": ("PIÙ COMPLETO", "Pro", "/mese", "Il flusso premium completo per candidati e recruiter.", ("Analisi illimitate", "Report PDF professionali", "Corrispondenza semantica", "Modalità recruiter", "Database candidati")),
        "manage_plan": "Vedi i piani o gestisci l’abbonamento PayPal",
        "value_title": "Perché TalentMatch Pro?",
        "value": (
            "Un’area premium per migliori decisioni di carriera e assunzione",
            "TalentMatch Pro unisce analisi CV con IA, ottimizzazione ATS, corrispondenza semantica, riscrittura, flussi recruiter, Database candidati e report.",
            ("IA mirata invece di consigli generici", "Flussi per candidati e recruiter in un solo prodotto", "Risultati chiari da rivedere, salvare e condividere"),
        ),
        "final": ("Trasforma ogni CV in una decisione più chiara", "Inizia con un CV, aggiungi un ruolo reale e ottieni informazioni strutturate e operative.", "Analizza un CV ora", "Vedi prezzi", "Fondatore e proprietario", "Prodotto SaaS originale"),
    },
)


# English (US) intentionally reuses the complete English product copy.
# The selector distinguishes the locale while preserving established CV terminology.
COPY["en_us"] = cast(LocaleCatalog, dict(COPY["en"]))


COPY["pt_br"] = _clone_locale(
    seo_description="TalentMatch Pro é uma plataforma de análise de CV e inteligência para recrutamento com IA, otimização ATS, correspondência semântica, reescrita de CV, classificação de candidatos e relatórios profissionais.",
    hero_kicker="INTELIGÊNCIA EMPRESARIAL DE TALENTOS",
    hero_guest_title="Crie um CV mais forte com IA",
    hero_user_title="Bem-vindo de volta, {name}",
    hero_subtitle="Analise CVs, melhore a compatibilidade com ATS, compare a relevância semântica, reescreva conteúdo, classifique candidatos e exporte relatórios profissionais em uma única área de trabalho.",
    workspace_badge="{plan} ÁREA DE TRABALHO",
    labels={
        "hero_actions": (
            ("📄", "Iniciar análise de CV", "pages/cv_analysis.py"),
            ("📋", "Abrir verificador ATS", "pages/ats_checker.py"),
            ("💳", "Ver plano Pro", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "Fluxos de trabalho com IA"),
            ("📄", "Relatórios profissionais"),
            ("🛡️", "Pagamento seguro com PayPal"),
        ),
        "metrics": (
            ("Área de trabalho", "{plan}", "Seu plano atual e acesso aos recursos"),
            ("Ferramentas de IA", "6", "Análise, ATS, Reescrita, Correspondência, Recrutador, Histórico"),
            ("Plano Pro", "{price}", "Assinatura mensal pelo PayPal"),
            ("Relatórios", "PDF", "Exportações TXT, CSV e PDF com identidade visual"),
        ),
        "quick_title": "Ações rápidas",
        "quick_subtitle": "Abra os fluxos de trabalho que você mais usa sem sair do seu centro de comando.",
        "quick": (
            ("📄", "Analisar CV", "Execute uma avaliação estruturada com IA para uma vaga-alvo real.", "pages/cv_analysis.py", "Abrir Análise de CV"),
            ("📋", "Verificar ATS", "Meça a cobertura de palavras-chave e priorize os termos ausentes.", "pages/ats_checker.py", "Abrir Verificador ATS"),
            ("🧠", "Correspondência Semântica", "Compare significado, contexto e prontidão para recrutamento.", "pages/semantic_match.py", "Abrir Correspondência Semântica"),
            ("👥", "Área do Recrutador", "Classifique candidatos e gerencie o Banco de Candidatos.", "pages/recruiter_mode.py", "Abrir Modo Recrutador"),
        ),
        "core_title": "Área de trabalho principal",
        "core_subtitle": "Todas as ferramentas seguem um fluxo premium consistente, do upload à exportação.",
        "core": (
            ("📄", "Análise de CV com IA", "Compare um CV com uma descrição de vaga real e receba pontuações estruturadas, pontos fortes, lacunas e recomendações práticas."),
            ("📋", "Verificador ATS", "Identifique palavras-chave encontradas e ausentes para alinhar melhor a candidatura aos sistemas de rastreamento de candidatos."),
            ("✍", "Reescrita de CV com IA", "Aprimore títulos, resumos e experiências mantendo verdadeiras as informações do candidato."),
            ("🧠", "Correspondência Semântica", "Compare significado e contexto, não apenas a sobreposição exata de palavras-chave, e avalie a prontidão para recrutamento."),
            ("👥", "Área do Recrutador", "Classifique candidatos, salve resultados e gerencie status, favoritos, notas, tags e exportações."),
            ("📥", "Relatórios Profissionais", "Exporte relatórios TXT, CSV e PDF com identidade visual de forma consistente."),
        ),
        "audience_title": "Criado para candidatos e recrutadores",
        "audience_subtitle": "Um produto, dois fluxos de trabalho focados e um sistema consistente de apoio à decisão.",
        "candidate": (
            "ÁREA DO CANDIDATO",
            "Fortaleça cada candidatura",
            "Use análise com IA, inteligência ATS, correspondência semântica e reescrita de CV para melhorar a relevância antes de se candidatar.",
            ("Insights específicos para a vaga", "Priorização de palavras-chave ATS", "Relatórios profissionais para download"),
        ),
        "recruiter": (
            "ÁREA DO RECRUTADOR",
            "Tome decisões de contratação mais rápidas",
            "Classifique candidatos, armazene perfis, gerencie status, adicione notas e tags e exporte relatórios prontos para decisão.",
            ("Classificação e comparação de candidatos", "Gestão do Banco de Candidatos", "Exportações CSV, TXT e PDF"),
        ),
        "workflow_title": "Como o TalentMatch Pro funciona",
        "workflow_subtitle": "Um processo focado em três etapas, do CV de origem ao suporte prático à decisão.",
        "steps": (
            ("1", "Etapa 1", "Enviar CV", "Recebimento e validação seguros do PDF"),
            ("2", "Etapa 2", "Adicionar vaga-alvo", "Use a descrição exata da vaga"),
            ("3", "Etapa 3", "Obter insights", "Pontuações, lacunas, reescritas e relatórios"),
        ),
        "pricing_title": "Planos simples",
        "pricing_subtitle": "Comece grátis e desbloqueie o fluxo completo pelo PayPal.",
        "free": ("INICIAL", "Grátis", "$0", "Explore o fluxo principal antes de fazer upgrade.", ("3 análises de CV", "Acesso ao Verificador ATS", "Exportações TXT")),
        "pro": ("MAIS COMPLETO", "Pro", "/mês", "O fluxo premium completo para busca de emprego e recrutamento profissional.", ("Análises ilimitadas", "Relatórios PDF profissionais", "Correspondência Semântica", "Modo Recrutador", "Banco de Candidatos")),
        "manage_plan": "Ver planos ou gerenciar a assinatura do PayPal",
        "value_title": "Por que TalentMatch Pro?",
        "value": (
            "Uma área de trabalho premium para melhores decisões de carreira e contratação",
            "TalentMatch Pro reúne análise de CV com IA, otimização ATS, correspondência semântica, reescrita de CV, fluxos de recrutamento, Banco de Candidatos e relatórios para download em uma experiência SaaS consistente.",
            ("IA focada em vez de conselhos genéricos", "Fluxos de candidatos e recrutadores em um só produto", "Resultados claros para revisar, salvar e compartilhar"),
        ),
        "final": (
            "Transforme cada CV em uma decisão mais clara",
            "Comece com um CV, adicione uma vaga real e deixe o TalentMatch Pro transformar a comparação em inteligência estruturada e prática.",
            "Analisar um CV agora",
            "Ver preços",
            "Fundador e proprietário",
            "Produto SaaS original",
        ),
    },
)


COPY["nl"] = _clone_locale(
    seo_description="TalentMatch Pro is een AI-platform voor CV-analyse en recruitment intelligence, ATS-optimalisatie, semantische matching, CV-herschrijving, kandidaatranking en professionele rapporten.",
    hero_kicker="ENTERPRISE TALENT INTELLIGENCE",
    hero_guest_title="Maak een sterker CV met AI",
    hero_user_title="Welkom terug, {name}",
    hero_subtitle="Analyseer CV’s, verbeter de ATS-compatibiliteit, vergelijk semantische relevantie, herschrijf inhoud, rangschik kandidaten en exporteer professionele rapporten vanuit één gerichte werkruimte.",
    workspace_badge="{plan} WERKRUIMTE",
    labels={
        "hero_actions": (
            ("📄", "CV-analyse starten", "pages/cv_analysis.py"),
            ("📋", "ATS-checker openen", "pages/ats_checker.py"),
            ("💳", "Pro-plan bekijken", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "AI-gestuurde workflows"),
            ("📄", "Professionele rapporten"),
            ("🛡️", "Veilige PayPal-betaling"),
        ),
        "metrics": (
            ("Werkruimte", "{plan}", "Je huidige lidmaatschap en functietoegang"),
            ("AI-tools", "6", "Analyse, ATS, Herschrijven, Match, Recruiter, Geschiedenis"),
            ("Pro-plan", "{price}", "Maandelijks abonnement via PayPal"),
            ("Rapporten", "PDF", "TXT-, CSV- en branded PDF-exports"),
        ),
        "quick_title": "Snelle acties",
        "quick_subtitle": "Open je meest gebruikte workflows zonder je commandocentrum te verlaten.",
        "quick": (
            ("📄", "CV analyseren", "Voer een gestructureerde AI-beoordeling uit voor een echte doelvacature.", "pages/cv_analysis.py", "CV-analyse openen"),
            ("📋", "ATS controleren", "Meet de dekking van zoekwoorden en geef prioriteit aan ontbrekende termen.", "pages/ats_checker.py", "ATS-checker openen"),
            ("🧠", "Semantische match", "Vergelijk betekenis, context en gereedheid voor recruiters.", "pages/semantic_match.py", "Semantische match openen"),
            ("👥", "Recruiterwerkruimte", "Rangschik kandidaten en beheer de Kandidatendatabase.", "pages/recruiter_mode.py", "Recruitermodus openen"),
        ),
        "core_title": "Centrale werkruimte",
        "core_subtitle": "Elke tool volgt één consistente premiumworkflow van upload tot export.",
        "core": (
            ("📄", "AI-CV-analyse", "Vergelijk een CV met een echte vacaturetekst en ontvang gestructureerde scores, sterke punten, hiaten en praktische aanbevelingen."),
            ("📋", "ATS-checker", "Identificeer gevonden en ontbrekende zoekwoorden zodat sollicitaties beter aansluiten op applicant tracking systems."),
            ("✍", "AI-CV-herschrijving", "Verbeter koppen, samenvattingen en ervaringspunten zonder waarheidsgetrouwe kandidaatinfo te wijzigen."),
            ("🧠", "Semantische match", "Vergelijk betekenis en context, niet alleen exacte overlap van zoekwoorden, en beoordeel recruiter-gereedheid."),
            ("👥", "Recruiterwerkruimte", "Rangschik kandidaten, sla resultaten op en beheer status, favorieten, notities, tags en exports."),
            ("📥", "Professionele rapporten", "Exporteer consistente TXT-, CSV- en branded PDF-rapporten voor sollicitatie- en recruitmentworkflows."),
        ),
        "audience_title": "Gebouwd voor kandidaten en recruiters",
        "audience_subtitle": "Eén product, twee gerichte workflows en één consistent beslissingsondersteunend systeem.",
        "candidate": (
            "KANDIDAATWERKRUIMTE",
            "Verbeter elke sollicitatie",
            "Gebruik AI-analyse, ATS-intelligentie, semantische matching en CV-herschrijving om relevantie vóór het solliciteren te versterken.",
            ("Functiespecifieke CV-inzichten", "Prioritering van ATS-zoekwoorden", "Downloadbare professionele rapporten"),
        ),
        "recruiter": (
            "RECRUITERWERKRUIMTE",
            "Neem sneller wervingsbeslissingen",
            "Rangschik kandidaten, bewaar profielen, beheer statussen, voeg notities en tags toe en exporteer beslisklare rapporten.",
            ("Kandidaatranking en vergelijking", "Beheer van de Kandidatendatabase", "CSV-, TXT- en PDF-exports"),
        ),
        "workflow_title": "Zo werkt TalentMatch Pro",
        "workflow_subtitle": "Een gericht proces in drie stappen van bron-CV naar bruikbare beslissingsondersteuning.",
        "steps": (
            ("1", "Stap 1", "CV uploaden", "Veilige PDF-inname en validatie"),
            ("2", "Stap 2", "Doelfunctie toevoegen", "Gebruik de exacte vacaturetekst"),
            ("3", "Stap 3", "Inzichten ontvangen", "Scores, hiaten, herschrijvingen en rapporten"),
        ),
        "pricing_title": "Eenvoudige plannen",
        "pricing_subtitle": "Begin gratis en ontgrendel daarna de volledige workflow via PayPal.",
        "free": ("STARTER", "Gratis", "$0", "Verken de kernworkflow voordat je upgradet.", ("3 CV-analyses", "Toegang tot ATS-checker", "TXT-exports")),
        "pro": ("MEEST COMPLEET", "Pro", "/maand", "De volledige premiumworkflow voor serieuze werkzoekenden en recruiters.", ("Onbeperkte analyses", "Professionele PDF-rapporten", "Semantische match", "Recruitermodus", "Kandidatendatabase")),
        "manage_plan": "Plannen bekijken of PayPal-abonnement beheren",
        "value_title": "Waarom TalentMatch Pro?",
        "value": (
            "Eén premiumwerkruimte voor betere carrière- en wervingsbeslissingen",
            "TalentMatch Pro combineert AI-CV-analyse, ATS-optimalisatie, semantische matching, CV-herschrijving, recruiterworkflows, Kandidatendatabasebeheer en downloadbare rapporten in één consistente SaaS-werkruimte.",
            ("Gerichte AI in plaats van algemeen advies", "Kandidaat- en recruiterworkflows in één product", "Duidelijke resultaten om te beoordelen, op te slaan en te delen"),
        ),
        "final": (
            "Maak van elk CV een duidelijkere beslissing",
            "Begin met een CV, voeg een echte functie toe en laat TalentMatch Pro de vergelijking omzetten in gestructureerde, bruikbare intelligence.",
            "Nu een CV analyseren",
            "Prijzen bekijken",
            "Oprichter en eigenaar",
            "Origineel SaaS-product",
        ),
    },
)


COPY["ru"] = _clone_locale(
    seo_description="TalentMatch Pro — AI-платформа для анализа резюме и рекрутинговой аналитики, оптимизации ATS, семантического сопоставления, переписывания резюме, ранжирования кандидатов и профессиональных отчётов.",
    hero_kicker="КОРПОРАТИВНАЯ АНАЛИТИКА ТАЛАНТОВ",
    hero_guest_title="Создайте более сильное резюме с помощью ИИ",
    hero_user_title="С возвращением, {name}",
    hero_subtitle="Анализируйте резюме, улучшайте совместимость с ATS, сравнивайте семантическую релевантность, улучшайте содержание, ранжируйте кандидатов и экспортируйте профессиональные отчёты из единого рабочего пространства.",
    workspace_badge="{plan} РАБОЧЕЕ ПРОСТРАНСТВО",
    labels={
        "hero_actions": (
            ("📄", "Начать анализ резюме", "pages/cv_analysis.py"),
            ("📋", "Открыть проверку ATS", "pages/ats_checker.py"),
            ("💳", "Посмотреть план Pro", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "Рабочие процессы на основе ИИ"),
            ("📄", "Профессиональные отчёты"),
            ("🛡️", "Безопасная оплата через PayPal"),
        ),
        "metrics": (
            ("Рабочее пространство", "{plan}", "Ваш текущий тариф и доступ к функциям"),
            ("Инструменты ИИ", "6", "Анализ, ATS, Переписывание, Сопоставление, Рекрутер, История"),
            ("План Pro", "{price}", "Ежемесячная подписка через PayPal"),
            ("Отчёты", "PDF", "Экспорт TXT, CSV и брендированных PDF"),
        ),
        "quick_title": "Быстрые действия",
        "quick_subtitle": "Открывайте наиболее используемые рабочие процессы, не покидая центр управления.",
        "quick": (
            ("📄", "Анализировать резюме", "Запустите структурированный анализ ИИ для реальной целевой вакансии.", "pages/cv_analysis.py", "Открыть анализ резюме"),
            ("📋", "Проверить ATS", "Измерьте покрытие ключевых слов и расставьте приоритеты для недостающих терминов.", "pages/ats_checker.py", "Открыть проверку ATS"),
            ("🧠", "Семантическое сопоставление", "Сравните смысл, контекст и готовность с точки зрения рекрутера.", "pages/semantic_match.py", "Открыть семантическое сопоставление"),
            ("👥", "Рабочее пространство рекрутера", "Ранжируйте кандидатов и управляйте Базой кандидатов.", "pages/recruiter_mode.py", "Открыть режим рекрутера"),
        ),
        "core_title": "Основное рабочее пространство",
        "core_subtitle": "Каждый инструмент следует единому премиальному процессу от загрузки до экспорта.",
        "core": (
            ("📄", "AI-анализ резюме", "Сравните резюме с реальным описанием вакансии и получите структурированные оценки, сильные стороны, пробелы и практические рекомендации."),
            ("📋", "Проверка ATS", "Определите найденные и недостающие ключевые слова, чтобы лучше согласовать заявку с системами отслеживания кандидатов."),
            ("✍", "AI-переписывание резюме", "Улучшайте заголовки, резюме профиля и пункты опыта, сохраняя достоверность информации кандидата."),
            ("🧠", "Семантическое сопоставление", "Сравнивайте смысл и контекст, а не только точное совпадение ключевых слов, и оценивайте готовность для рекрутера."),
            ("👥", "Рабочее пространство рекрутера", "Ранжируйте кандидатов, сохраняйте результаты и управляйте статусами, избранным, заметками, тегами и экспортом."),
            ("📥", "Профессиональные отчёты", "Экспортируйте согласованные TXT-, CSV- и брендированные PDF-отчёты для заявок и рекрутинговых процессов."),
        ),
        "audience_title": "Для кандидатов и рекрутеров",
        "audience_subtitle": "Один продукт, два сфокусированных рабочих процесса и единая система поддержки решений.",
        "candidate": (
            "РАБОЧЕЕ ПРОСТРАНСТВО КАНДИДАТА",
            "Усильте каждую заявку",
            "Используйте AI-анализ, ATS-аналитику, семантическое сопоставление и переписывание резюме, чтобы повысить релевантность до подачи заявки.",
            ("Инсайты для конкретной вакансии", "Приоритизация ключевых слов ATS", "Профессиональные отчёты для скачивания"),
        ),
        "recruiter": (
            "РАБОЧЕЕ ПРОСТРАНСТВО РЕКРУТЕРА",
            "Принимайте решения о найме быстрее",
            "Ранжируйте кандидатов, храните профили, управляйте статусами, добавляйте заметки и теги и экспортируйте готовые к решению отчёты.",
            ("Рейтинг и сравнение кандидатов", "Управление Базой кандидатов", "Экспорт CSV, TXT и PDF"),
        ),
        "workflow_title": "Как работает TalentMatch Pro",
        "workflow_subtitle": "Сфокусированный трёхэтапный процесс от исходного резюме до практической поддержки решений.",
        "steps": (
            ("1", "Шаг 1", "Загрузите резюме", "Безопасная загрузка и проверка PDF"),
            ("2", "Шаг 2", "Добавьте целевую вакансию", "Используйте точное описание вакансии"),
            ("3", "Шаг 3", "Получите инсайты", "Оценки, пробелы, переписывание и отчёты"),
        ),
        "pricing_title": "Простые тарифы",
        "pricing_subtitle": "Начните бесплатно, затем откройте полный рабочий процесс через PayPal.",
        "free": ("СТАРТОВЫЙ", "Бесплатно", "$0", "Изучите основной процесс перед переходом на Pro.", ("3 анализа резюме", "Доступ к проверке ATS", "Экспорт TXT")),
        "pro": ("САМЫЙ ПОЛНЫЙ", "Pro", "/месяц", "Полный премиальный процесс для серьёзного поиска работы и рекрутинга.", ("Неограниченные анализы", "Профессиональные PDF-отчёты", "Семантическое сопоставление", "Режим рекрутера", "База кандидатов")),
        "manage_plan": "Посмотреть тарифы или управлять подпиской PayPal",
        "value_title": "Почему TalentMatch Pro?",
        "value": (
            "Единое премиальное пространство для лучших карьерных и кадровых решений",
            "TalentMatch Pro объединяет AI-анализ резюме, оптимизацию ATS, семантическое сопоставление, помощь в переписывании резюме, рекрутинговые процессы, управление Базой кандидатов и загружаемые отчёты.",
            ("Фокусированный ИИ вместо общих советов", "Процессы для кандидатов и рекрутеров в одном продукте", "Понятные результаты для проверки, сохранения и обмена"),
        ),
        "final": (
            "Превратите каждое резюме в более ясное решение",
            "Начните с резюме, добавьте реальную вакансию и позвольте TalentMatch Pro превратить сравнение в структурированную и практическую аналитику.",
            "Анализировать резюме сейчас",
            "Посмотреть цены",
            "Основатель и владелец",
            "Оригинальный SaaS-продукт",
        ),
    },
)


COPY["zh_cn"] = _clone_locale(
    seo_description="TalentMatch Pro 是一款由 AI 驱动的简历分析与招聘智能平台，提供 ATS 优化、语义匹配、简历改写、候选人排序和专业报告。",
    hero_kicker="企业级人才智能",
    hero_guest_title="使用 AI 打造更强的简历",
    hero_user_title="欢迎回来，{name}",
    hero_subtitle="在一个专注的工作区中分析简历、提升 ATS 兼容性、比较语义相关性、改写内容、对候选人排序并导出专业报告。",
    workspace_badge="{plan} 工作区",
    labels={
        "hero_actions": (
            ("📄", "开始简历分析", "pages/cv_analysis.py"),
            ("📋", "打开 ATS 检查", "pages/ats_checker.py"),
            ("💳", "查看 Pro 方案", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "AI 驱动工作流"),
            ("📄", "专业报告"),
            ("🛡️", "安全的 PayPal 付款"),
        ),
        "metrics": (
            ("工作区", "{plan}", "您当前的会员方案和功能访问权限"),
            ("AI 工具", "6", "分析、ATS、改写、匹配、招聘、历史记录"),
            ("Pro 方案", "{price}", "通过 PayPal 按月订阅"),
            ("报告", "PDF", "TXT、CSV 和品牌化 PDF 导出"),
        ),
        "quick_title": "快捷操作",
        "quick_subtitle": "无需离开控制中心，即可打开您最常使用的工作流。",
        "quick": (
            ("📄", "分析简历", "针对真实目标职位运行结构化 AI 评估。", "pages/cv_analysis.py", "打开简历分析"),
            ("📋", "检查 ATS", "衡量关键词覆盖率并优先处理缺失术语。", "pages/ats_checker.py", "打开 ATS 检查"),
            ("🧠", "语义匹配", "比较含义、上下文以及面向招聘人员的准备度。", "pages/semantic_match.py", "打开语义匹配"),
            ("👥", "招聘工作区", "对候选人排序并管理候选人数据库。", "pages/recruiter_mode.py", "打开招聘模式"),
        ),
        "core_title": "核心工作区",
        "core_subtitle": "每个工具都遵循从上传到导出的统一高级工作流。",
        "core": (
            ("📄", "AI 简历分析", "将简历与真实职位描述进行比较，并获得结构化评分、优势、差距和实用建议。"),
            ("📋", "ATS 检查", "识别已匹配和缺失的关键词，使申请与候选人跟踪系统更清晰地对齐。"),
            ("✍", "AI 简历改写", "在保持候选人信息真实的前提下，改进标题、摘要和经历要点。"),
            ("🧠", "语义匹配", "比较含义和上下文，而不只是精确关键词重叠，并评估招聘准备度。"),
            ("👥", "招聘工作区", "对候选人排序、保存结果，并管理状态、收藏、备注、标签和导出。"),
            ("📥", "专业报告", "为求职和招聘工作流导出统一的 TXT、CSV 和品牌化 PDF 报告。"),
        ),
        "audience_title": "为候选人和招聘人员打造",
        "audience_subtitle": "一个产品、两个专注工作流和一套统一的决策支持系统。",
        "candidate": (
            "候选人工作区",
            "提升每一次申请",
            "在申请前使用 AI 分析、ATS 智能、语义匹配和简历改写来提高相关性。",
            ("针对职位的简历洞察", "ATS 关键词优先级", "可下载的专业报告"),
        ),
        "recruiter": (
            "招聘工作区",
            "更快做出招聘决策",
            "对候选人排序、保存档案、管理状态、添加备注和标签，并导出可用于决策的报告。",
            ("候选人排序与比较", "候选人数据库管理", "CSV、TXT 和 PDF 导出"),
        ),
        "workflow_title": "TalentMatch Pro 如何工作",
        "workflow_subtitle": "从原始简历到可执行决策支持的三步专注流程。",
        "steps": (
            ("1", "步骤 1", "上传简历", "安全接收并验证 PDF"),
            ("2", "步骤 2", "添加目标职位", "使用准确的职位描述"),
            ("3", "步骤 3", "获取洞察", "评分、差距、改写和报告"),
        ),
        "pricing_title": "简单方案",
        "pricing_subtitle": "免费开始，然后通过 PayPal 解锁完整工作流。",
        "free": ("入门", "免费", "$0", "升级前先体验核心工作流。", ("3 次简历分析", "ATS 检查访问权限", "TXT 导出")),
        "pro": ("最完整", "Pro", "/月", "适合认真求职和招聘使用的完整高级工作流。", ("无限分析", "专业 PDF 报告", "语义匹配", "招聘模式", "候选人数据库")),
        "manage_plan": "查看方案或管理 PayPal 订阅",
        "value_title": "为什么选择 TalentMatch Pro？",
        "value": (
            "一个高级工作区，帮助做出更好的职业和招聘决策",
            "TalentMatch Pro 将 AI 简历分析、ATS 优化、语义匹配、简历改写辅助、招聘工作流、候选人数据库管理和可下载报告整合到统一的 SaaS 工作区中。",
            ("专注型 AI，而非泛泛建议", "候选人与招聘工作流整合在一个产品中", "结果清晰，可查看、保存和分享"),
        ),
        "final": (
            "让每份简历都转化为更清晰的决策",
            "从一份简历开始，添加真实职位，让 TalentMatch Pro 将比较结果转化为结构化、可执行的人才智能。",
            "立即分析简历",
            "查看价格",
            "创始人兼所有者",
            "原创 SaaS 产品",
        ),
    },
)


COPY["ar_ae"] = _clone_locale(
    seo_description="TalentMatch Pro منصة مدعومة بالذكاء الاصطناعي لتحليل السير الذاتية وذكاء التوظيف، وتحسين ATS، والمطابقة الدلالية، وإعادة صياغة السيرة الذاتية، وترتيب المرشحين، والتقارير الاحترافية.",
    hero_kicker="ذكاء المواهب للمؤسسات",
    hero_guest_title="أنشئ سيرة ذاتية أقوى بالذكاء الاصطناعي",
    hero_user_title="مرحبًا بعودتك، {name}",
    hero_subtitle="حلّل السير الذاتية، وحسّن التوافق مع ATS، وقارن الصلة الدلالية، وأعد صياغة المحتوى، ورتّب المرشحين، وصدّر تقارير احترافية من مساحة عمل واحدة مركزة.",
    workspace_badge="مساحة عمل {plan}",
    labels={
        "hero_actions": (
            ("📄", "بدء تحليل السيرة الذاتية", "pages/cv_analysis.py"),
            ("📋", "فتح فحص ATS", "pages/ats_checker.py"),
            ("💳", "عرض خطة Pro", "pages/pricing.py"),
        ),
        "trust": (
            ("🤖", "سير عمل مدعوم بالذكاء الاصطناعي"),
            ("📄", "تقارير احترافية"),
            ("🛡️", "دفع آمن عبر PayPal"),
        ),
        "metrics": (
            ("مساحة العمل", "{plan}", "عضويتك الحالية وإمكانية الوصول إلى الميزات"),
            ("أدوات الذكاء الاصطناعي", "6", "التحليل، ATS، إعادة الصياغة، المطابقة، التوظيف، السجل"),
            ("خطة Pro", "{price}", "اشتراك شهري عبر PayPal"),
            ("التقارير", "PDF", "تصدير TXT وCSV وPDF بعلامة تجارية"),
        ),
        "quick_title": "إجراءات سريعة",
        "quick_subtitle": "افتح مسارات العمل الأكثر استخدامًا دون مغادرة مركز التحكم.",
        "quick": (
            ("📄", "تحليل السيرة الذاتية", "شغّل مراجعة منظمة بالذكاء الاصطناعي لوظيفة مستهدفة حقيقية.", "pages/cv_analysis.py", "فتح تحليل السيرة الذاتية"),
            ("📋", "فحص ATS", "قِس تغطية الكلمات المفتاحية وحدد أولوية المصطلحات المفقودة.", "pages/ats_checker.py", "فتح فحص ATS"),
            ("🧠", "المطابقة الدلالية", "قارن المعنى والسياق ومدى الجاهزية من منظور مسؤول التوظيف.", "pages/semantic_match.py", "فتح المطابقة الدلالية"),
            ("👥", "مساحة عمل التوظيف", "رتّب المرشحين وأدر قاعدة بيانات المرشحين.", "pages/recruiter_mode.py", "فتح وضع التوظيف"),
        ),
        "core_title": "مساحة العمل الأساسية",
        "core_subtitle": "تتبع كل أداة سير عمل احترافيًا موحدًا من الرفع إلى التصدير.",
        "core": (
            ("📄", "تحليل السيرة الذاتية بالذكاء الاصطناعي", "قارن السيرة الذاتية بوصف وظيفي حقيقي واحصل على درجات منظمة ونقاط قوة وفجوات وتوصيات عملية."),
            ("📋", "فحص ATS", "حدد الكلمات المفتاحية المتطابقة والمفقودة لتتوافق الطلبات بصورة أوضح مع أنظمة تتبع المتقدمين."),
            ("✍", "إعادة صياغة السيرة الذاتية بالذكاء الاصطناعي", "حسّن العناوين والملخصات ونقاط الخبرة مع الحفاظ على صحة معلومات المرشح."),
            ("🧠", "المطابقة الدلالية", "قارن المعنى والسياق، وليس فقط التطابق الحرفي للكلمات المفتاحية، وقيّم الجاهزية للتوظيف."),
            ("👥", "مساحة عمل التوظيف", "رتّب المرشحين واحفظ النتائج وأدر الحالات والمفضلة والملاحظات والوسوم وعمليات التصدير."),
            ("📥", "التقارير الاحترافية", "صدّر تقارير TXT وCSV وPDF موحدة وذات هوية بصرية لطلبات التوظيف ومسارات عمل مسؤولي التوظيف."),
        ),
        "audience_title": "مصمم للمرشحين ومسؤولي التوظيف",
        "audience_subtitle": "منتج واحد، ومسارا عمل مركزان، ونظام موحد لدعم القرار.",
        "candidate": (
            "مساحة عمل المرشح",
            "حسّن كل طلب توظيف",
            "استخدم تحليل الذكاء الاصطناعي وذكاء ATS والمطابقة الدلالية وإعادة صياغة السيرة الذاتية لتعزيز الصلة قبل التقديم.",
            ("رؤى مخصصة للوظيفة", "تحديد أولوية كلمات ATS المفتاحية", "تقارير احترافية قابلة للتنزيل"),
        ),
        "recruiter": (
            "مساحة عمل مسؤول التوظيف",
            "اتخذ قرارات توظيف أسرع",
            "رتّب المرشحين واحفظ الملفات وأدر الحالات وأضف الملاحظات والوسوم وصدّر تقارير جاهزة لاتخاذ القرار.",
            ("ترتيب المرشحين ومقارنتهم", "إدارة قاعدة بيانات المرشحين", "تصدير CSV وTXT وPDF"),
        ),
        "workflow_title": "كيف يعمل TalentMatch Pro",
        "workflow_subtitle": "عملية مركزة من ثلاث خطوات من السيرة الذاتية الأصلية إلى دعم قرار قابل للتنفيذ.",
        "steps": (
            ("1", "الخطوة 1", "ارفع السيرة الذاتية", "استقبال PDF والتحقق منه بأمان"),
            ("2", "الخطوة 2", "أضف الوظيفة المستهدفة", "استخدم الوصف الوظيفي الدقيق"),
            ("3", "الخطوة 3", "احصل على الرؤى", "درجات وفجوات وإعادة صياغة وتقارير"),
        ),
        "pricing_title": "خطط بسيطة",
        "pricing_subtitle": "ابدأ مجانًا ثم افتح سير العمل الكامل عبر PayPal.",
        "free": ("البدء", "مجاني", "$0", "استكشف سير العمل الأساسي قبل الترقية.", ("3 تحليلات للسيرة الذاتية", "الوصول إلى فحص ATS", "تصدير TXT")),
        "pro": ("الأكثر اكتمالًا", "Pro", "/شهريًا", "سير العمل الاحترافي الكامل للبحث الجاد عن عمل واستخدام مسؤولي التوظيف.", ("تحليلات غير محدودة", "تقارير PDF احترافية", "المطابقة الدلالية", "وضع التوظيف", "قاعدة بيانات المرشحين")),
        "manage_plan": "عرض الخطط أو إدارة اشتراك PayPal",
        "value_title": "لماذا TalentMatch Pro؟",
        "value": (
            "مساحة عمل احترافية واحدة لقرارات مهنية وتوظيفية أفضل",
            "يجمع TalentMatch Pro تحليل السير الذاتية بالذكاء الاصطناعي، وتحسين ATS، والمطابقة الدلالية، والمساعدة في إعادة صياغة السيرة الذاتية، ومسارات عمل التوظيف، وإدارة قاعدة بيانات المرشحين، والتقارير القابلة للتنزيل في مساحة SaaS موحدة.",
            ("ذكاء اصطناعي مركز بدلًا من النصائح العامة", "مسارات المرشحين ومسؤولي التوظيف في منتج واحد", "نتائج واضحة يمكن مراجعتها وحفظها ومشاركتها"),
        ),
        "final": (
            "حوّل كل سيرة ذاتية إلى قرار أوضح",
            "ابدأ بسيرة ذاتية، وأضف وظيفة حقيقية، ودع TalentMatch Pro يحول المقارنة إلى ذكاء منظم وقابل للتنفيذ.",
            "حلّل سيرة ذاتية الآن",
            "استكشف الأسعار",
            "المؤسس والمالك",
            "منتج SaaS أصلي",
        ),
    },
)


def _catalog() -> LocaleCatalog:
    return COPY.get(get_locale(), COPY["en"])


def _text(key: str, **variables: str) -> str:
    value = cast(str, _catalog().get(key, COPY["en"].get(key, key)))
    rendered = str(value)
    try:
        return rendered.format(**variables)
    except (KeyError, ValueError):
        return rendered


def _dashboard_css() -> None:
    theme = str(st.session_state.get("tm_theme", "system"))
    tokens = (
        "--tm-surface:rgba(15,23,42,.88);--tm-text:#f8fafc;--tm-muted:#cbd5e1;"
        "--tm-border:rgba(148,163,184,.22);--tm-shadow:0 24px 64px rgba(0,0,0,.30);"
        "--tm-workspace-badge-bg:rgba(251,191,36,.12);--tm-workspace-badge-text:#fde68a;"
        "--tm-workspace-badge-border:rgba(251,191,36,.58);"
        "--tm-workspace-badge-shadow:0 10px 26px rgba(0,0,0,.18);"
        if theme == "dark"
        else
        "--tm-surface:rgba(255,255,255,.92);--tm-text:#0f172a;--tm-muted:#64748b;"
        "--tm-border:rgba(148,163,184,.24);--tm-shadow:0 22px 60px rgba(15,23,42,.09);"
        "--tm-workspace-badge-bg:#0f172a;--tm-workspace-badge-text:#ffffff;"
        "--tm-workspace-badge-border:#0f172a;"
        "--tm-workspace-badge-shadow:0 10px 26px rgba(15,23,42,.20);"
    )
    st.markdown(
        f"""
        <style>
        :root{{{tokens}--tm-primary:#2563eb;--tm-success:#10b981;--tm-soft:rgba(37,99,235,.10)}}
        .tm-grid{{display:grid;gap:1rem;width:100%}}
        .tm-grid-4{{grid-template-columns:repeat(4,minmax(0,1fr))}}
        .tm-grid-3{{grid-template-columns:repeat(3,minmax(0,1fr))}}
        .tm-grid-2{{grid-template-columns:repeat(2,minmax(0,1fr))}}
        .tm-card,.tm-panel{{border:1px solid var(--tm-border);background:var(--tm-surface);color:var(--tm-text);box-shadow:var(--tm-shadow);backdrop-filter:blur(16px)}}
        .tm-card{{position:relative;overflow:hidden;padding:1.4rem;border-radius:25px;min-height:100%;transition:transform .2s ease,border-color .2s ease,box-shadow .2s ease}}
        .tm-card:hover{{transform:translateY(-4px);border-color:rgba(37,99,235,.36);box-shadow:0 28px 72px rgba(37,99,235,.13)}}
        .tm-metric{{min-height:176px}}
        .tm-metric:before{{content:"";position:absolute;inset:0 0 auto;height:4px;background:linear-gradient(90deg,var(--tm-primary),var(--tm-success))}}
        .tm-label,.tm-eyebrow{{color:var(--tm-primary);font-size:.72rem;font-weight:950;text-transform:uppercase;letter-spacing:.13em}}
        .tm-value{{color:var(--tm-text);font-size:2.08rem;font-weight:950;letter-spacing:-.055em;line-height:1;margin:.72rem 0 .6rem}}
        .tm-title{{color:var(--tm-text);font-size:1.08rem;font-weight:950;letter-spacing:-.03em;margin:.35rem 0}}
        .tm-copy{{color:var(--tm-muted);line-height:1.62}}
        .tm-icon{{width:50px;height:50px;border-radius:17px;display:flex;align-items:center;justify-content:center;background:var(--tm-soft);font-size:1.35rem;margin-bottom:.9rem}}
        .tm-points{{display:flex;flex-direction:column;gap:.62rem;margin-top:1.05rem}}
        .tm-point{{display:flex;align-items:flex-start;gap:.58rem;color:var(--tm-text);font-weight:780;line-height:1.45}}
        .tm-check{{flex:0 0 auto;width:22px;height:22px;border-radius:999px;display:inline-flex;align-items:center;justify-content:center;background:rgba(16,185,129,.14);color:#047857;font-size:.76rem;font-weight:950}}
        .tm-step-number{{width:42px;height:42px;border-radius:15px;display:flex;align-items:center;justify-content:center;background:linear-gradient(135deg,var(--tm-primary),var(--tm-success));color:white;font-weight:950;margin-bottom:.9rem}}
        .tm-pro{{border-color:rgba(37,99,235,.40);background:radial-gradient(circle at top right,rgba(37,99,235,.16),transparent 38%),radial-gradient(circle at bottom left,rgba(16,185,129,.13),transparent 38%),var(--tm-surface)}}
        .tm-price{{color:var(--tm-text);font-size:2.35rem;font-weight:950;letter-spacing:-.06em;margin:.32rem 0 .48rem}}
        .tm-unit{{color:var(--tm-muted);font-size:.95rem;font-weight:800;letter-spacing:0}}
        .tm-panel{{padding:1.75rem;border-radius:29px;background:radial-gradient(circle at 8% 12%,rgba(37,99,235,.14),transparent 34%),radial-gradient(circle at 92% 88%,rgba(16,185,129,.12),transparent 34%),var(--tm-surface)}}
        .tm-final{{padding:2rem;border-radius:30px;background:radial-gradient(circle at 12% 18%,rgba(37,99,235,.28),transparent 36%),radial-gradient(circle at 88% 82%,rgba(16,185,129,.22),transparent 36%),linear-gradient(135deg,#0f172a,#111827);color:white}}
        .tm-final .tm-title{{color:white;font-size:clamp(1.65rem,3vw,2.45rem)}}.tm-final .tm-copy{{color:#cbd5e1;max-width:780px}}
        .tm-pill-row{{display:flex;flex-wrap:wrap;gap:.65rem;margin-top:1rem}}.tm-pill{{padding:.42rem .75rem;border-radius:999px;border:1px solid rgba(251,191,36,.35);background:rgba(251,191,36,.10);color:#fde68a;font-size:.72rem;font-weight:900}}
        .tm-hero .tm-pill.tm-pill-dark{{background:var(--tm-workspace-badge-bg)!important;color:var(--tm-workspace-badge-text)!important;border:1px solid var(--tm-workspace-badge-border)!important;box-shadow:var(--tm-workspace-badge-shadow)!important;text-shadow:none!important;opacity:1!important}}
        .tm-trust{{padding:.85rem 1rem;border-radius:18px;border:1px solid var(--tm-border);background:var(--tm-surface);color:var(--tm-muted);font-weight:820;text-align:center}}
        .tm-spacer{{height:2.45rem}}
        div[data-testid="stPageLink"] a{{min-height:3.25rem;border-radius:16px;font-weight:900;transition:transform .18s ease,box-shadow .18s ease}}
        div[data-testid="stPageLink"] a:hover{{transform:translateY(-2px);box-shadow:0 16px 36px rgba(37,99,235,.13)}}
        @media(max-width:1100px){{.tm-grid-4{{grid-template-columns:repeat(2,minmax(0,1fr))}}.tm-grid-3{{grid-template-columns:repeat(2,minmax(0,1fr))}}}}
        @media(max-width:760px){{.tm-grid-4,.tm-grid-3,.tm-grid-2{{grid-template-columns:1fr}}.tm-metric{{min-height:auto}}.tm-final{{padding:1.45rem}}}}
        @media(prefers-reduced-motion:reduce){{.tm-card,div[data-testid="stPageLink"] a{{transition:none!important}}}}
        </style>
        """,
        unsafe_allow_html=True,
    )


def _structured_data() -> None:
    price = PRO_MONTHLY_PRICE.replace("$", "").strip() or "19"
    payload = {
        "@context": "https://schema.org",
        "@type": "SoftwareApplication",
        "name": "TalentMatch Pro",
        "applicationCategory": "BusinessApplication",
        "operatingSystem": "Web",
        "url": APP_URL,
        "description": _text("seo_description"),
        "offers": {"@type": "Offer", "price": price, "priceCurrency": "USD"},
        "creator": {"@type": "Person", "name": OWNER_NAME},
    }
    st.markdown(
        f'<script type="application/ld+json">{json.dumps(payload, ensure_ascii=False)}</script>',
        unsafe_allow_html=True,
    )


def _spacer() -> None:
    st.markdown('<div class="tm-spacer"></div>', unsafe_allow_html=True)


def _points(items: tuple[str, ...]) -> str:
    return "".join(
        f'<div class="tm-point"><span class="tm-check">✓</span>{safe_html(item)}</div>'
        for item in items
    )


def _hero_actions() -> None:
    actions = _catalog()["hero_actions"]
    columns = st.columns(3)
    for column, (icon, label, page) in zip(columns, actions):
        with column:
            st.page_link(page, label=f"{icon} {label}", use_container_width=True)

    trust = "".join(
        f'<div class="tm-trust">{safe_html(icon)} {safe_html(label)}</div>'
        for icon, label in _catalog()["trust"]
    )
    st.markdown(f'<div class="tm-grid tm-grid-3">{trust}</div>', unsafe_allow_html=True)


def _metrics(plan: str) -> None:
    cards = ""
    for label, value, note in _catalog()["metrics"]:
        value = str(value).format(plan=plan, price=PRO_MONTHLY_PRICE)
        cards += (
            '<div class="tm-card tm-metric">'
            f'<div class="tm-label">{safe_html(label)}</div>'
            f'<div class="tm-value">{safe_html(value)}</div>'
            f'<div class="tm-copy">{safe_html(note)}</div>'
            '</div>'
        )
    st.markdown(f'<div class="tm-grid tm-grid-4">{cards}</div>', unsafe_allow_html=True)


def _quick_actions() -> None:
    render_section_title(_text("quick_title"), _text("quick_subtitle"))
    columns = st.columns(4)
    for column, (icon, title, copy, page, button) in zip(columns, _catalog()["quick"]):
        with column:
            with st.container(border=True):
                st.markdown(f"### {icon} {title}")
                st.caption(copy)
                st.page_link(page, label=button, use_container_width=True)


def _core_features() -> None:
    render_section_title(_text("core_title"), _text("core_subtitle"))
    cards = "".join(
        (
            '<div class="tm-card">'
            f'<div class="tm-icon">{safe_html(icon)}</div>'
            f'<div class="tm-title">{safe_html(title)}</div>'
            f'<div class="tm-copy">{safe_html(copy)}</div>'
            '</div>'
        )
        for icon, title, copy in _catalog()["core"]
    )
    st.markdown(f'<div class="tm-grid tm-grid-3">{cards}</div>', unsafe_allow_html=True)


def _audience() -> None:
    render_section_title(_text("audience_title"), _text("audience_subtitle"))
    cards = []
    for eyebrow, title, copy, items in (_catalog()["candidate"], _catalog()["recruiter"]):
        cards.append(
            '<div class="tm-card">'
            f'<div class="tm-eyebrow">{safe_html(eyebrow)}</div>'
            f'<div class="tm-title">{safe_html(title)}</div>'
            f'<div class="tm-copy">{safe_html(copy)}</div>'
            f'<div class="tm-points">{_points(items)}</div>'
            '</div>'
        )
    st.markdown(f'<div class="tm-grid tm-grid-2">{"".join(cards)}</div>', unsafe_allow_html=True)


def _workflow() -> None:
    render_section_title(_text("workflow_title"), _text("workflow_subtitle"))
    cards = "".join(
        (
            '<div class="tm-card">'
            f'<div class="tm-step-number">{safe_html(number)}</div>'
            f'<div class="tm-eyebrow">{safe_html(label)}</div>'
            f'<div class="tm-title">{safe_html(title)}</div>'
            f'<div class="tm-copy">{safe_html(copy)}</div>'
            '</div>'
        )
        for number, label, title, copy in _catalog()["steps"]
    )
    st.markdown(f'<div class="tm-grid tm-grid-3">{cards}</div>', unsafe_allow_html=True)


def _pricing() -> None:
    render_section_title(_text("pricing_title"), _text("pricing_subtitle"))
    free_kicker, free_title, free_price, free_copy, free_features = _catalog()["free"]
    pro_kicker, pro_title, pro_unit, pro_copy, pro_features = _catalog()["pro"]

    st.markdown(
        (
            '<div class="tm-grid tm-grid-2">'
            '<div class="tm-card">'
            f'<div class="tm-eyebrow">{safe_html(free_kicker)}</div>'
            f'<div class="tm-title">{safe_html(free_title)}</div>'
            f'<div class="tm-price">{safe_html(free_price)}</div>'
            f'<div class="tm-copy">{safe_html(free_copy)}</div>'
            f'<div class="tm-points">{_points(free_features)}</div>'
            '</div>'
            '<div class="tm-card tm-pro">'
            f'<div class="tm-eyebrow">{safe_html(pro_kicker)}</div>'
            f'<div class="tm-title">{safe_html(pro_title)}</div>'
            f'<div class="tm-price">{safe_html(PRO_MONTHLY_PRICE)}<span class="tm-unit">{safe_html(pro_unit)}</span></div>'
            f'<div class="tm-copy">{safe_html(pro_copy)}</div>'
            f'<div class="tm-points">{_points(pro_features)}</div>'
            '</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )
    st.page_link("pages/pricing.py", label=f"💳 {_text('manage_plan')}", use_container_width=True)


def _value() -> None:
    render_section_title(_text("value_title"))
    headline, copy, items = _catalog()["value"]
    st.markdown(
        (
            '<div class="tm-panel">'
            f'<div class="tm-title" style="font-size:1.35rem">{safe_html(headline)}</div>'
            f'<div class="tm-copy">{safe_html(copy)}</div>'
            f'<div class="tm-points">{_points(items)}</div>'
            '</div>'
        ),
        unsafe_allow_html=True,
    )


def _final_cta() -> None:
    title, copy, primary, secondary, owner_label, original_product = _catalog()["final"]
    st.markdown(
        (
            '<div class="tm-final">'
            f'<div class="tm-title">{safe_html(title)}</div>'
            f'<div class="tm-copy">{safe_html(copy)}</div>'
            '<div class="tm-pill-row">'
            f'<span class="tm-pill">{safe_html(owner_label)}: {safe_html(OWNER_NAME)}</span>'
            f'<span class="tm-pill">{safe_html(original_product)}</span>'
            f'<span class="tm-pill">{safe_html(RELEASE_ID)}</span>'
            '</div></div>'
        ),
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        st.page_link("pages/cv_analysis.py", label=f"📄 {primary}", use_container_width=True)
    with c2:
        st.page_link("pages/pricing.py", label=f"💳 {secondary}", use_container_width=True)


def render_landing() -> None:
    """Render the localized TalentMatch Pro v3 enterprise dashboard."""
    apply_global_styles()
    _dashboard_css()
    _structured_data()

    if is_logged_in() and not st.session_state.get("landing_profile_loaded"):
        refresh_profile()
        st.session_state["landing_profile_loaded"] = True

    name = get_display_name()
    plan = "PRO" if is_pro_user() else "FREE"
    title = (
        _text("hero_user_title", name=name)
        if is_logged_in()
        else _text("hero_guest_title")
    )

    render_page_intro(
        kicker=_text("hero_kicker"),
        title=title,
        subtitle=_text("hero_subtitle"),
        icon=get_initials(name),
        badge=_text("workspace_badge", plan=plan),
    )

    _hero_actions()
    _spacer()
    _metrics(plan)
    _spacer()
    _quick_actions()
    _spacer()
    _core_features()
    _spacer()
    _audience()
    _spacer()
    _workflow()
    _spacer()
    _pricing()
    _spacer()
    _value()
    _spacer()
    _final_cta()
