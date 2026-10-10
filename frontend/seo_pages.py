"""HTTP-rendered public pages for search engines and visitors.

The legal copy is read from the existing Streamlit pages, so the two views
cannot silently publish different versions of a policy. Pricing facts that
change with the plan are read from the interactive pricing page as well.
"""

from __future__ import annotations

import ast
import html
import re
from datetime import datetime, timezone
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
SITE_URL = "https://talentmatchcv.com"

POLICIES = {
    "/privacy": ("Privacy Policy", "How TalentMatch Pro collects, uses, and protects personal data."),
    "/terms": ("Terms of Service", "Terms for using TalentMatch Pro and its Free and Pro features."),
    "/refund": ("Refund Policy", "Subscription cancellations and refund requests for TalentMatch Pro."),
}


def _inline(text: str) -> str:
    """Render the small, known subset of Markdown used by the policies."""
    result = html.escape(text, quote=True)
    result = result.replace("&lt;br&gt;", "<br>").replace("&lt;br/&gt;", "<br>")

    def mail_link(match: re.Match[str]) -> str:
        label = match.group(1)
        address = match.group(2)
        return f'<a href="{html.escape(address, quote=True)}">{label}</a>'

    result = re.sub(r"\[([^\]]+)\]\((mailto:[^)\s]+)\)", mail_link, result)
    result = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", result)
    return result


def _markdown_to_html(source: str) -> str:
    rendered: list[str] = []
    for block in re.split(r"\n\s*\n", source.strip()):
        lines = [line.strip() for line in block.splitlines() if line.strip()]
        if not lines:
            continue
        if len(lines) == 1 and lines[0].startswith("## "):
            rendered.append(f"<h2>{_inline(lines[0][3:])}</h2>")
        elif all(line.startswith("- ") for line in lines):
            rendered.append("<ul>" + "".join(f"<li>{_inline(line[2:])}</li>" for line in lines) + "</ul>")
        elif all(line.startswith("## ") for line in lines):
            rendered.extend(f"<h2>{_inline(line[3:])}</h2>" for line in lines)
        else:
            rendered.append(f"<p>{_inline(' '.join(lines))}</p>")
    return "\n".join(rendered)


def _policy_body(slug: str) -> str:
    source = (BASE_DIR / "pages" / f"{slug}.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename=f"pages/{slug}.py")
    matches: list[str] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call) or not node.args:
            continue
        func = node.func
        if not (isinstance(func, ast.Attribute) and isinstance(func.value, ast.Name)
                and func.value.id == "st" and func.attr == "markdown"):
            continue
        value = node.args[0]
        if isinstance(value, ast.Constant) and isinstance(value.value, str):
            if value.value.strip().startswith("**Last Updated:"):
                matches.append(value.value)
    if len(matches) != 1:
        raise RuntimeError(f"Expected one public policy body in pages/{slug}.py")
    return _markdown_to_html(matches[0])


def _price_text(node: ast.AST, price: int) -> str:
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    if isinstance(node, ast.JoinedStr):
        parts: list[str] = []
        for value in node.values:
            if isinstance(value, ast.Constant) and isinstance(value.value, str):
                parts.append(value.value)
            elif (isinstance(value, ast.FormattedValue) and isinstance(value.value, ast.Name)
                  and value.value.id == "PRO_PRICE_USD" and value.format_spec is None):
                parts.append(str(price))
            else:
                raise RuntimeError("Unsupported FAQ format in pages/pricing.py")
        return "".join(parts)
    raise RuntimeError("Unsupported FAQ entry in pages/pricing.py")


def _pricing_data() -> tuple[int, list[tuple[str, str, str]], list[tuple[str, str]]]:
    source = (BASE_DIR / "pages" / "pricing.py").read_text(encoding="utf-8-sig")
    tree = ast.parse(source, filename="pages/pricing.py")
    values: dict[str, ast.AST] = {}
    for node in tree.body:
        if isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name) and target.id in {"PRO_PRICE_USD", "comparison", "faq_items"}:
                    values[target.id] = node.value
    if set(values) != {"PRO_PRICE_USD", "comparison", "faq_items"}:
        raise RuntimeError("Pricing page is missing plan facts used by the public page")
    price = ast.literal_eval(values["PRO_PRICE_USD"])
    comparison = ast.literal_eval(values["comparison"])
    faq_node = values["faq_items"]
    if not isinstance(price, int) or price <= 0 or not isinstance(faq_node, ast.List):
        raise RuntimeError("Invalid public pricing data")
    faq: list[tuple[str, str]] = []
    for entry in faq_node.elts:
        if not isinstance(entry, ast.Tuple) or len(entry.elts) != 2:
            raise RuntimeError("Invalid pricing FAQ entry")
        faq.append((_price_text(entry.elts[0], price), _price_text(entry.elts[1], price)))
    if not isinstance(comparison, list) or not all(
        isinstance(row, tuple) and len(row) == 3 and all(isinstance(item, str) for item in row)
        for row in comparison
    ):
        raise RuntimeError("Invalid pricing comparison")
    return price, comparison, faq


def _page(path: str, title: str, description: str, body: str) -> str:
    canonical = SITE_URL + path
    escaped_title = html.escape(f"{title} | TalentMatch Pro", quote=True)
    escaped_description = html.escape(description, quote=True)
    escaped_canonical = html.escape(canonical, quote=True)
    year = datetime.now(timezone.utc).year
    return f"""<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{escaped_title}</title>
  <meta name="description" content="{escaped_description}">
  <meta name="robots" content="index, follow">
  <link rel="canonical" href="{escaped_canonical}">
  <meta property="og:type" content="website">
  <meta property="og:title" content="{escaped_title}">
  <meta property="og:description" content="{escaped_description}">
  <meta property="og:url" content="{escaped_canonical}">
  <link rel="icon" href="/seo/favicon.png" type="image/png">
  <link rel="stylesheet" href="/seo/public.css">
</head>
<body>
  <a class="skip-link" href="#main">Skip to content</a>
  <header class="site-header">
    <div class="container header-row">
      <a class="brand" href="/" aria-label="TalentMatch Pro home"><span class="brand-mark">◎</span> TalentMatch Pro</a>
      <nav aria-label="Main navigation"><a href="/">Home</a><a href="/pricing">Pricing</a><a href="/privacy">Privacy</a><a href="/terms">Terms</a><a href="/refund">Refunds</a><a href="/?view=app">Open app</a></nav>
    </div>
  </header>
  <main id="main" class="container">
    {body}
  </main>
  <footer class="site-footer">
    <div class="container footer-row">
      <div><strong>TalentMatch Pro</strong><br>AI-powered CV and recruiter workflows.</div>
      <div><a href="mailto:support@talentmatchcv.com">support@talentmatchcv.com</a><br>Serbia</div>
      <div><a href="/pricing">Pricing</a> · <a href="/privacy">Privacy</a> · <a href="/terms">Terms</a> · <a href="/refund">Refunds</a></div>
    </div>
    <div class="container copyright">© {year} TalentMatch Pro. Review AI-generated outputs before use.</div>
  </footer>
</body>
</html>"""


def _pricing_body(price: int, comparison: list[tuple[str, str, str]], faq: list[tuple[str, str]]) -> str:
    rows = "\n".join(
        "<tr>" + "".join(f"<td>{html.escape(cell)}</td>" for cell in row) + "</tr>"
        for row in comparison
    )
    questions = "\n".join(
        f"<details><summary>{html.escape(question)}</summary><p>{html.escape(answer)}</p></details>"
        for question, answer in faq
    )
    return f"""
    <section class="hero">
      <span class="eyebrow">TalentMatch Pro pricing</span>
      <h1>One workspace. Every CV workflow.</h1>
      <p class="lead">Start free, then unlock AI-powered CV analysis, ATS optimisation, CV rewriting, semantic matching, recruiter workflows, Candidate Database access, and professional reports.</p>
      <a class="button" href="/pricing?view=app">Open pricing and billing in the app</a>
      <p class="note">PayPal handles checkout and recurring subscription management. Sign in to upgrade.</p>
    </section>
    <section aria-labelledby="plans-heading">
      <h2 id="plans-heading">Choose your plan</h2>
      <div class="plan-grid">
        <article class="plan"><span class="eyebrow">Starter workspace</span><h3>Free</h3><p class="amount">$0<span>/month</span></p><p>No payment method required.</p>
          <ul><li>3 CV analyses</li><li>ATS Checker access</li><li>CV Rewrite preview</li><li>TXT export</li></ul>
          <p>Premium PDF reports, Semantic Match, and Recruiter Workspace are part of Pro.</p>
        </article>
        <article class="plan featured"><span class="eyebrow">Complete workflow</span><h3>TalentMatch Pro</h3><p class="amount">${price}<span>/month</span></p><p>Recurring monthly subscription via PayPal.</p>
          <ul><li>Unlimited CV analyses</li><li>Premium PDF reports and TXT exports</li><li>Full CV Rewrite AI workflow</li><li>Semantic Match intelligence</li><li>Recruiter Mode and Candidate Database</li><li>Full saved History</li></ul>
          <a class="button" href="/pricing?view=app">Log in and upgrade through PayPal</a>
        </article>
      </div>
    </section>
    <section aria-labelledby="comparison-heading">
      <h2 id="comparison-heading">Feature comparison</h2>
      <div class="table-scroll"><table><thead><tr><th scope="col">Feature</th><th scope="col">Free</th><th scope="col">Pro</th></tr></thead><tbody>{rows}</tbody></table></div>
    </section>
    <section aria-labelledby="billing-heading">
      <h2 id="billing-heading">Secure checkout and account control</h2>
      <p>Checkout and subscription approval take place on PayPal pages. TalentMatch Pro does not store payment card details. Manage or cancel the recurring subscription through your PayPal account. After approval, the app synchronises Pro access with your account.</p>
      <p>Read the <a href="/terms">Terms of Service</a>, <a href="/privacy">Privacy Policy</a>, and <a href="/refund">Refund Policy</a> before subscribing.</p>
    </section>
    <section aria-labelledby="faq-heading"><h2 id="faq-heading">Frequently asked questions</h2>{questions}</section>
    <section class="cta"><h2>Ready to use the complete workflow?</h2><p>Pro costs ${price} USD per month through PayPal. Create an account or sign in in the app to start the subscription.</p><a class="button" href="/pricing?view=app">Open pricing in the app</a></section>
    <section class="contact"><h2>Billing support</h2><p>Email <a href="mailto:support@talentmatchcv.com">support@talentmatchcv.com</a> with billing or subscription questions.</p></section>
    """


def _home_body(price: int) -> str:
    """Public landing content, available in the initial HTML response."""
    return f"""
    <section class="hero home-hero">
      <span class="eyebrow">AI career and recruiter intelligence</span>
      <h1>Build a stronger CV with AI</h1>
      <p class="lead">TalentMatch Pro brings CV analysis, ATS checking, CV rewriting, semantic job matching, and recruiter workflows into one workspace. Compare a CV with a real job description, find gaps worth addressing, and review clear recommendations before you apply or make a hiring decision.</p>
      <div class="inline-actions"><a class="button" href="/?view=app">Open the app</a><a class="button secondary" href="/pricing">Explore plans</a></div>
      <p class="note">Start with the Free plan. The Pro subscription is ${price} USD per month through PayPal.</p>
    </section>
    <section aria-labelledby="tools-heading">
      <h2 id="tools-heading">Tools for every CV workflow</h2>
      <p>Use focused tools to understand a candidate’s experience, improve the clarity of a CV, and compare qualifications with the role at hand.</p>
      <div class="feature-grid">
        <article class="feature-card"><h3>CV Analysis</h3><p>Compare a CV with a job description and review strengths, gaps, and practical suggestions.</p></article>
        <article class="feature-card"><h3>ATS Checker</h3><p>See matched and missing terms so you can improve the relevance of an application.</p></article>
        <article class="feature-card"><h3>CV Rewrite AI</h3><p>Refine summaries and experience descriptions while keeping the candidate’s facts accurate.</p></article>
        <article class="feature-card"><h3>Semantic Match</h3><p>Compare meaning and context across a CV and a role, beyond identical keywords.</p></article>
        <article class="feature-card"><h3>Recruiter Mode</h3><p>Rank candidates, compare results, and organise profiles in the Candidate Database.</p></article>
        <article class="feature-card"><h3>Professional reports</h3><p>Save your work and export available TXT, CSV, or PDF reports for review and sharing.</p></article>
      </div>
    </section>
    <section aria-labelledby="workflow-heading">
      <h2 id="workflow-heading">How it works</h2>
      <div class="step-grid">
        <article class="feature-card"><span class="eyebrow">Step 1</span><h3>Upload a CV</h3><p>Add the document you have the right to use and select the relevant workflow.</p></article>
        <article class="feature-card"><span class="eyebrow">Step 2</span><h3>Add the target role</h3><p>Use a real job description to give the analysis the right context.</p></article>
        <article class="feature-card"><span class="eyebrow">Step 3</span><h3>Review the insights</h3><p>Check the scores, suggestions, rewrites, and reports before using them.</p></article>
      </div>
    </section>
    <section aria-labelledby="audience-heading">
      <h2 id="audience-heading">Built for candidates and recruiters</h2>
      <div class="plan-grid">
        <article class="plan"><h3>For job seekers</h3><p>Understand how a CV fits a particular role. Prioritise missing skills and keywords, rewrite unclear sections, and prepare a more focused application.</p></article>
        <article class="plan"><h3>For recruiters</h3><p>Compare candidates against role requirements, organise profiles and notes, and export structured results to support a careful review.</p></article>
      </div>
    </section>
    <section class="cta"><h2>Start free, upgrade when you need more</h2><p>The Free plan includes three CV analyses and ATS Checker access. Pro adds unlimited analyses, full rewriting and matching workflows, recruiter tools, and premium PDF reports for ${price} USD per month via PayPal.</p><div class="inline-actions"><a class="button" href="/?view=app">Enter the workspace</a><a class="button secondary" href="/pricing">Compare Free and Pro</a></div></section>
    <section class="contact"><h2>Questions?</h2><p>Contact <a href="mailto:support@talentmatchcv.com">support@talentmatchcv.com</a>. Review the <a href="/privacy">Privacy Policy</a>, <a href="/terms">Terms of Service</a>, and <a href="/refund">Refund Policy</a> before subscribing.</p></section>
    """


def build_pages() -> dict[str, str]:
    price, comparison, faq = _pricing_data()
    result = {
        "/": _page(
            "/",
            "AI CV Analysis and ATS Checker",
            "Analyze CVs, check ATS compatibility, rewrite content, match jobs, and compare candidates with TalentMatch Pro.",
            _home_body(price),
        ),
        "/pricing": _page(
            "/pricing",
            "Pricing",
            f"TalentMatch Pro Free and Pro plans. Pro costs ${price} USD per month through PayPal.",
            _pricing_body(price, comparison, faq),
        )
    }
    for path, (title, description) in POLICIES.items():
        result[path] = _page(
            path, title, description,
            f'<article class="policy"><h1>{html.escape(title)}</h1>{_policy_body(path[1:])}</article>',
        )
    return result


PUBLIC_HTML = build_pages()
