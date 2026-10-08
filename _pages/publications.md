---
title: "Publications"
permalink: /publications/
---

{% if site.data.publications and site.data.publications.size > 0 %}
{% assign pubs = site.data.publications %}
{% assign years = pubs | map: "year" | uniq | sort | reverse %}
{% for y in years %}
## {{ y }}
{% for p in pubs %}{% if p.year == y %}
{% if p.doi %}{% assign link = "https://doi.org/" | append: p.doi %}{% else %}{% assign link = p.url %}{% endif %}
<p class="pub">
  <a href="{{ link }}"><strong>{{ p.title }}</strong></a><br>
  {{ p.authors | replace: "Dahhay Lee", "<strong>Dahhay Lee</strong>" }}<br>
  <em>{{ p.journal }}</em>{% if p.volume %}, {{ p.volume }}{% endif %}{% if p.pages %}, {{ p.pages }}{% endif %} ({{ p.year }}){% if p.doi %}<br>DOI: <a href="{{ link }}">{{ p.doi }}</a>{% endif %}
</p>
{% endif %}{% endfor %}
{% endfor %}
{% else %}
준비 중이에요.
{% endif %}